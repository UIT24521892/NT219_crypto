-- 003_role_separation_and_hybrid.sql
-- PHASE 2 — Role separation (reviewer / signer) + hybrid signature columns.
--
-- Apply order on an existing PostgreSQL database: 001 -> 002 -> 003.
-- Fresh demo databases receive equivalent columns/enum values from SQLAlchemy
-- create_all(); this file upgrades a live DB without data loss.
--
-- Idempotent: every statement is guarded (ADD VALUE IF NOT EXISTS,
-- ADD COLUMN IF NOT EXISTS, existence checks) so re-running is a no-op.
--
-- NOTE: ALTER TYPE ... ADD VALUE cannot run inside a transaction block, so the
-- enum extensions are listed FIRST, before the BEGIN/COMMIT section.
--
-- Enum storage convention (matches 002): SQLAlchemy stores the Python enum
-- MEMBER NAME (uppercase) as the PostgreSQL label, e.g. CITIZEN / ADMIN.

ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'REVIEWER';
ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'SIGNER';

BEGIN;

-- --- documents: hybrid signature + QR + signed-PDF columns ---------------- --
ALTER TABLE documents ADD COLUMN IF NOT EXISTS mldsa_signature   BYTEA;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS qr_signature      BYTEA;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS qr_payload        JSONB;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS signed_pdf_path   VARCHAR(500);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS public_key_ref    VARCHAR(100);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS qr_public_key_ref VARCHAR(100);

-- --- migrate legacy FALCON-512 signature bytes into the ML-DSA column ------ --
-- Old rows hold FALCON-512 signatures. They are preserved only as historical
-- bytes under the new column name; they will NOT verify under ML-DSA-44 and
-- such documents should be re-signed. The legacy column is then dropped.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'documents' AND column_name = 'falcon_signature'
    ) THEN
        UPDATE documents
           SET mldsa_signature = falcon_signature
         WHERE mldsa_signature IS NULL AND falcon_signature IS NOT NULL;
        ALTER TABLE documents DROP COLUMN falcon_signature;
    END IF;
END $$;

-- --- public_keys: support per-algorithm trust registry entries ------------- --
-- 002 created public_keys with algorithm defaulting to 'FALCON-512'. The hybrid
-- registry now stores ML-DSA-44 and Ed25519 keys; drop the FALCON default so new
-- inserts must state their algorithm explicitly.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'public_keys') THEN
        ALTER TABLE public_keys ALTER COLUMN algorithm DROP DEFAULT;
    END IF;
END $$;

COMMIT;

-- --- OPTIONAL role data migration (review before running on a live demo) --- --
-- The plan maps the former single 'admin' account onto the new 'signer' role.
-- This is left COMMENTED OUT so applying 003 never silently locks an admin out
-- of admin-only endpoints. In Phase 3, 'admin' keeps full rights (super-user),
-- and require_reviewer / require_signer also accept 'admin'. To adopt strict
-- separation of duty, create dedicated reviewer + signer accounts, then run:
--
--   UPDATE users SET role = 'SIGNER' WHERE role = 'ADMIN';
