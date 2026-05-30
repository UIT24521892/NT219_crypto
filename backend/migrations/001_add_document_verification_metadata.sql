-- Apply once when upgrading an existing PostgreSQL database.
-- Fresh demo databases receive these columns from SQLAlchemy create_all().

ALTER TABLE documents
    ADD COLUMN IF NOT EXISTS signing_public_key BYTEA,
    ADD COLUMN IF NOT EXISTS qr_issued_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS qr_expires_at TIMESTAMPTZ;
