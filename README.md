# Citizen Services Portal - NT219 Topic 11

Cổng dịch vụ công minh họa luồng ký số PDF bằng FALCON-512, tạo QR xác thực
online và xuất verification package để kiểm tra offline. Backend dùng FastAPI,
PostgreSQL và `liboqs-python`; frontend dùng React + Vite.

## 1. Kiến trúc

```text
React/Vite
   |
   | JWT Bearer token
   v
FastAPI -------------------- PostgreSQL
   |                            |
   |                            +-- users, documents, audit_log
   |
   +-- storage/uploads/<uuid>.pdf
   +-- keys/falcon_private.enc.json  (AES-256-GCM)
   +-- keys/falcon_public.bin
```

Luồng chính:

```text
Citizen login -> Upload PDF -> Admin signs -> QR generated
              -> Online verify -> Offline package -> CLI verify
```

## 2. Quyết định QR

QR online encode trực tiếp URL để camera điện thoại mở ổn định:

```text
/verify?d=<document_uuid>
```

Backend lưu metadata `qr_issued_at` và `qr_expires_at`. Endpoint public `/verify`
đọc PDF hiện tại, kiểm tra expiry và verify FALCON bằng public key đã gắn với
tài liệu tại thời điểm ký.

Offline package được xuất từ:

```text
GET /documents/{id}/verification-package
```

Package chứa public key và payload JSON minified:

```json
{"v":1,"id":"...","h":"...","s":"...","ts":1700000000,"ex":1800000000,"alg":"FALCON-512"}
```

## 3. Chuẩn bị local

Yêu cầu:

- Python 3.11+
- PostgreSQL 14+
- Node.js và npm
- `liboqs-python` cùng FALCON-512 mechanism

Tạo database local:

```bash
sudo -u postgres psql
```

```sql
CREATE USER portal_user WITH PASSWORD 'CHANGE_ME';
CREATE DATABASE citizen_portal OWNER portal_user;
```

Tạo virtual environment và cài dependency:

```bash
python3 -m venv .venv
PATH=.venv/bin:$PATH pip install -r backend/requirements.txt pytest
```

Tạo file môi trường local nhưng không commit:

```bash
cp backend/.env.example backend/.env
```

Các biến quan trọng:

| Biến | Mục đích |
|---|---|
| `DATABASE_URL` | PostgreSQL async connection string |
| `JWT_SECRET` | Khóa ký JWT; sinh bằng `openssl rand -hex 32` |
| `KEY_PASSPHRASE` | Passphrase mã hóa private key FALCON bằng AES-256-GCM |
| `UPLOAD_DIR` | Thư mục PDF, mặc định `./storage/uploads` tính từ `backend/` |
| `QR_VALIDITY_DAYS` | Thời hạn QR online và offline package |

Không commit `.env`, file key, PDF upload hoặc generated key material.

## 4. Chạy backend

```bash
cd backend
PATH=../.venv/bin:$PATH uvicorn app.main:app --reload --port 8000
```

Lần đầu backend khởi động, SQLAlchemy tạo bảng cho database mới. Nếu database
đã tồn tại từ phiên bản cũ, chạy migration thủ công:

```bash
cd backend
psql -h 127.0.0.1 -U portal_user -d citizen_portal \
  -f migrations/001_add_document_verification_metadata.sql
```

Tạo admin demo:

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"AdminPass123"}'
```

```sql
UPDATE users SET role='ADMIN' WHERE email='admin@example.com';
```

Health check:

```bash
curl http://localhost:8000/ping
curl http://localhost:8000/ping/db
```

## 5. Chạy frontend

```bash
npm ci
npm run dev
```

Mở `http://localhost:5173`.

Frontend giữ `access_token` trong `localStorage` để demo thuận tiện, nhưng không
lưu toàn bộ user object. Production nên chuyển sang cookie `HttpOnly` với cấu
hình CSRF phù hợp.

## 6. Demo online

1. Đăng ký hoặc login citizen.
2. Upload PDF tại `/documents`.
3. Login admin và ký tài liệu pending bằng nút `Ký FALCON`.
4. Mở chi tiết tài liệu và chọn `Xem QR`.
5. Scan QR bằng camera điện thoại hoặc mở `/verify?d=<document_uuid>`.
6. Kết quả hợp lệ hiển thị `valid: true`.

Demo tampering:

```bash
printf 'tampered' >> backend/storage/uploads/<document_uuid>.pdf
```

Refresh `/verify?d=<document_uuid>`. Kết quả phải là `valid: false`. Chỉ dùng
file demo và khôi phục file sau khi trình bày.

## 7. Demo offline CLI

Tại trang chi tiết, chọn `Tải verification package`, hoặc tải bằng API:

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8000/documents/$DOC_ID/verification-package \
  -o verification-package.json
```

Verify PDF mà không cần database:

```bash
PATH=.venv/bin:$PATH python scripts/verify_qr.py \
  --pdf document.pdf \
  --package verification-package.json
```

CLI cũ với payload và raw public key vẫn được hỗ trợ:

```bash
PATH=.venv/bin:$PATH python scripts/verify_qr.py \
  --pdf document.pdf \
  --payload offline-payload.json \
  --public-key falcon-public.bin
```

## 8. Test và security demo

Unit test:

```bash
PATH=.venv/bin:$PATH python -m pytest -q
```

Integration test cần backend local, PostgreSQL, admin demo và FALCON:

```bash
RUN_API_INTEGRATION=1 \
API_ADMIN_EMAIL=admin@example.com \
API_ADMIN_PASSWORD=AdminPass123 \
API_STORAGE_DIR="$PWD/backend/storage/uploads" \
PATH=.venv/bin:$PATH python -m pytest tests/test_api.py -q
```

Attack demo:

```bash
PATH=.venv/bin:$PATH python scripts/attack_forgery.py
PATH=.venv/bin:$PATH python scripts/attack_replay.py
```

Security Analysis:

```bash
PATH=.venv/bin:$PATH python scripts/security_analysis.py --samples 100
```

Script sinh:

- `report_inputs/security_analysis_summary.md`
- `report_inputs/security_analysis_frequency.csv`

## 9. Benchmark

```bash
PATH=.venv/bin:$PATH python scripts/benchmark.py --iterations 20
PATH=.venv/bin:$PATH python scripts/benchmark_falcon_ecdsa.py --iterations 20 --warmup 3
```

`scripts/benchmark.py` đo FALCON-512, FALCON-1024, ML-DSA-44/Dilithium2 và
ECDSA-P256 khi mechanism tương ứng khả dụng. Artifact report:

- `report_inputs/full_benchmark.csv`
- `report_inputs/full_benchmark_summary.md`

## 10. API chính

| Method | Route | Quyền |
|---|---|---|
| `POST` | `/auth/register` | Public |
| `POST` | `/auth/login` | Public |
| `GET` | `/auth/me` | Authenticated |
| `POST` | `/documents/upload` | Authenticated |
| `GET` | `/documents` | Authenticated |
| `POST` | `/documents/{id}/sign` | Admin |
| `POST` | `/documents/{id}/qr` | Owner hoặc admin |
| `GET` | `/documents/{id}/verification-package` | Owner hoặc admin |
| `GET` | `/verify?d=<uuid>` | Public |
| `GET` | `/audit` | Admin |

## 11. Security Notes

- FALCON ký SHA-256 digest của PDF, không tự implement crypto primitive.
- Private key mã hóa at rest bằng AES-256-GCM; key derivation dùng
  PBKDF2-HMAC-SHA256 và `KEY_PASSPHRASE`.
- Endpoint sign tính lại SHA-256 và từ chối nếu file đã đổi sau upload.
- Mỗi document giữ public key đã dùng lúc ký để key rotation không làm hỏng tài
  liệu cũ.
- Login, upload, sign và verify đều ghi audit outcome.
- Citizen không thể sign và không thể đọc `/audit`.

Threat model chi tiết: `docs/threat-model.md`.

## 12. Deploy EC2

Runbook bare-metal Ubuntu 22.04:

```text
deploy/DEPLOY.md
```

Trước feature freeze cần xác nhận PostgreSQL, `citizen-portal-api`, Nginx và TLS
đều chạy; đồng thời bootstrap keypair một lần trước khi bật nhiều Uvicorn
workers để tránh race condition lúc sinh key lần đầu.
