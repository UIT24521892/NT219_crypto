-- 004_agencies.sql
-- PHASE 11 — Government bodies (agencies) as the issuing authority.
--
-- Apply order on an existing PostgreSQL database: 001 -> 002 -> 003 -> 004.
-- Fresh demo databases receive equivalent tables/columns from SQLAlchemy
-- create_all(); this file upgrades a live DB without data loss.
--
-- A signer acts on behalf of an agency. The agency is recorded per signed
-- document (id + a snapshot of its name) and bound into the signed QR + PDF, so
-- a verifier can see which government body issued the document. There is still a
-- single State post-quantum signing key — agencies are organizational
-- attribution, not separate key holders.
--
-- Idempotent: every statement is guarded so re-running is a no-op.

BEGIN;

-- --- agencies table -------------------------------------------------------- --
CREATE TABLE IF NOT EXISTS agencies (
    id          SERIAL PRIMARY KEY,
    code        VARCHAR(32)  NOT NULL UNIQUE,
    name        VARCHAR(200) NOT NULL,
    level       VARCHAR(40)  NOT NULL DEFAULT 'central',
    is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- --- users: which agency a signer/reviewer acts for ------------------------ --
ALTER TABLE users ADD COLUMN IF NOT EXISTS agency_id INTEGER REFERENCES agencies(id);

-- --- documents: issuing agency (FK + snapshot name) ------------------------ --
ALTER TABLE documents ADD COLUMN IF NOT EXISTS signing_agency_id   INTEGER REFERENCES agencies(id);
ALTER TABLE documents ADD COLUMN IF NOT EXISTS signing_agency_name VARCHAR(200);

-- --- seed a few government bodies ------------------------------------------ --
-- is_active is listed explicitly: when the table was first created by SQLAlchemy
-- create_all() the column may lack a server-side default, so a bare INSERT would
-- violate NOT NULL.
INSERT INTO agencies (code, name, level, is_active) VALUES
    ('GOV',  'Chính phủ',                'central',    TRUE),
    ('MOJ',  'Bộ Tư pháp',               'ministry',   TRUE),
    ('MPS',  'Bộ Công an',               'ministry',   TRUE),
    ('UBND', 'Ủy ban Nhân dân cấp tỉnh', 'provincial', TRUE)
ON CONFLICT (code) DO NOTHING;

COMMIT;

-- --- OPTIONAL: assign existing signer accounts to a default agency --------- --
-- Left commented so applying 004 never silently changes who issues on whose
-- behalf. To put every current signer under "Chính phủ", review then run:
--
--   UPDATE users SET agency_id = (SELECT id FROM agencies WHERE code = 'GOV')
--    WHERE role = 'SIGNER' AND agency_id IS NULL;
