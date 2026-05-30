# Threat Model - Citizen Services Portal

## 1. Scope

The portal accepts citizen PDF uploads, allows an admin to sign approved files
with FALCON-512, publishes a URL-based online QR code, and exports a signed
offline verification package.

Protected assets:

- Citizen accounts and JWT access tokens.
- Uploaded PDF bytes and their SHA-256 hashes.
- FALCON private key material.
- Signing-time FALCON public keys.
- QR verification metadata and audit logs.

## 2. Trust Boundaries

| Boundary | Untrusted side | Trusted side |
|---|---|---|
| Browser to API | Browser, public internet | FastAPI validation and RBAC |
| API to PostgreSQL | API input | ORM models and database constraints |
| API to filesystem | Uploaded bytes | UUID-named PDF storage |
| Key storage | Disk contents | AES-256-GCM decryption with `KEY_PASSPHRASE` |
| Public QR verification | Anonymous scanner | Read-only verification endpoint |

## 3. STRIDE Analysis

| Threat | STRIDE | Risk | Mitigation | Evidence |
|---|---|---|---|---|
| JWT forgery | Spoofing | Attacker impersonates citizen or admin | Verify HS256 JWT signature and expiry; load active user from DB; enforce `require_admin` | `backend/app/security.py`, `backend/app/auth_middleware.py`; manual citizen sign test |
| PDF tampering after signing | Tampering | Modified PDF appears authentic | Re-read PDF and verify its FALCON signature with the signing-time public key | `scripts/attack_forgery.py`; online tamper demo |
| PDF tampering before signing | Tampering | Server signs bytes different from uploaded hash | Recompute SHA-256 immediately before sign and reject mismatch | `backend/app/api/documents.py`; integration test |
| QR replay after expiry | Spoofing / Replay | Old QR remains accepted indefinitely | Store `qr_expires_at`; reject expired online QR metadata; enforce `ex` in offline CLI | `scripts/attack_replay.py`; integration test |
| Private key leakage | Information disclosure | Attacker can create signatures | Encrypt private key at rest using AES-256-GCM and PBKDF2-HMAC-SHA256; source passphrase from `KEY_PASSPHRASE` | `backend/app/crypto/key_manager.py`, `tests/test_key_manager.py` |
| Key rotation breaks old documents | Denial of service | Old valid files become unverifiable | Store `signing_public_key` on every signed document and verify with that key | `backend/app/models.py`, `backend/app/api/verify.py` |
| DB tampering | Tampering | Signature metadata or paths are modified | FALCON verification detects inconsistent signature/PDF combinations; audit logs retain outcomes | Online verify invalid demo |
| IDOR document access | Information disclosure | Citizen reads another citizen's file | Owner-or-admin lookup returns 404 for unauthorized access | `_get_doc_or_404()` and integration test |
| Citizen signs documents | Elevation of privilege | Citizen creates official signed records | Protect sign route with `require_admin` | Manual and integration RBAC tests |
| Citizen reads audit records | Information disclosure | Security log metadata leaks | Protect `/audit` with `require_admin` | Manual and integration RBAC tests |
| Verify endpoint abuse | Denial of service | Public endpoint can be spammed | Apply Nginx `limit_req` to `/verify` | `deploy/nginx-citizen-portal.conf` |

## 4. QR Contracts

Online QR codes encode a public URL:

```text
/verify?d=<document_uuid>
```

The server checks document status, signing-time public key, QR expiry, file
presence, SHA-256 digest and FALCON signature.

Offline verification packages contain the minified signed payload:

```json
{"v":1,"id":"...","h":"...","s":"...","ts":1700000000,"ex":1800000000,"alg":"FALCON-512"}
```

The package also carries the signing-time public key encoded as unpadded
Base64URL so `scripts/verify_qr.py` can verify without database access.

## 5. Remaining Risks

- Local Uvicorn runs do not apply the Nginx `/verify` rate limit used by EC2.
- Existing PostgreSQL databases must apply
  `backend/migrations/001_add_document_verification_metadata.sql`.
- FALCON key initialization should occur once before starting multiple Uvicorn
  workers to avoid a first-start race.
- `access_token` remains in `localStorage` for demo convenience. A production
  deployment should prefer a hardened `HttpOnly` cookie design.
