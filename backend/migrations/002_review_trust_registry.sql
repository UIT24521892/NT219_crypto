-- 002_review_trust_registry.sql
-- Chạy trên PostgreSQL DB hiện tại để thêm workflow duyệt trước khi ký
-- và Trust Registry / Public Key Directory.

BEGIN;

-- SQLAlchemy Enum với Python enum thường lưu TÊN enum member trong PostgreSQL.
ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'PENDING_REVIEW';
ALTER TYPE document_status ADD VALUE IF NOT EXISTS 'APPROVED';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'public_key_status') THEN
        CREATE TYPE public_key_status AS ENUM ('ACTIVE', 'REVOKED', 'EXPIRED');
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS public_keys (
    id UUID PRIMARY KEY,
    key_id VARCHAR(100) UNIQUE NOT NULL,
    algorithm VARCHAR(50) NOT NULL DEFAULT 'FALCON-512',
    public_key_bytes BYTEA NOT NULL,
    fingerprint VARCHAR(64) UNIQUE NOT NULL,
    owner_name VARCHAR(255) NOT NULL DEFAULT 'Issuing Authority',
    status public_key_status NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_public_keys_key_id ON public_keys(key_id);
CREATE INDEX IF NOT EXISTS ix_public_keys_fingerprint ON public_keys(fingerprint);
CREATE INDEX IF NOT EXISTS ix_public_keys_status ON public_keys(status);

ALTER TABLE documents ADD COLUMN IF NOT EXISTS reviewed_by UUID NULL REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ NULL;
ALTER TABLE documents ADD COLUMN IF NOT EXISTS review_note TEXT NULL;

-- Convert các document cũ đang PENDING thành pending_review theo workflow mới.
UPDATE documents SET status = 'PENDING_REVIEW' WHERE status = 'PENDING';

COMMIT;
