# Crypto A Workflow And Secrets Guide

Tài liệu này tóm tắt toàn bộ luồng Crypto/Security mà Member A đang phụ trách:
FALCON-512 signing, encrypted key storage, QR payload, offline verifier, attack demos,
benchmark, và các file nhạy cảm liên quan.

## 1. Trạng Thái File Nhạy Cảm Trong Workspace

Kết quả kiểm tra hiện tại:

- Có `.env.development`.
- Không có `.env`.
- Không có `.pem`.
- Không có `.key`.
- Không có `.key.enc`.
- Không có private key material mới trong workspace.

`.env.development` hiện là file frontend Vite, không phải nơi lưu private key:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_USE_MOCK=false
```

Không đưa `KEY_PASSPHRASE`, private key, hoặc key material vào frontend env vì biến Vite
có thể bị bundle sang frontend nếu đặt sai prefix hoặc dùng sai cách.

## 2. Vai Trò Từng File Crypto

### `backend/app/crypto/falcon_service.py`

File lõi cho chữ ký FALCON-512:

- Resolve tên thuật toán `FALCON-512` sang tên thật trong liboqs, ví dụ `Falcon-512`.
- `generate_keypair()` sinh public/private key bằng `oqs.Signature`.
- `hash_document(pdf_bytes)` tính SHA-256 hex của PDF/document bytes.
- `sign_document(pdf_bytes, private_key)` ký SHA-256 digest 32 bytes, không ký trực tiếp toàn bộ PDF.
- `verify_signature(doc_hash_hex, signature, public_key)` verify chữ ký trên hash.
- `verify_document(pdf_bytes, signature, public_key, expected_hash_hex)` tính lại hash PDF rồi verify.

### `backend/app/crypto/key_manager.py`

File quản lý key storage:

- Private key không lưu plaintext.
- Passphrase lấy từ biến môi trường `KEY_PASSPHRASE`.
- Dùng PBKDF2-HMAC-SHA256 để derive AES-256 key từ passphrase.
- Dùng AES-256-GCM để mã hóa private key.
- `save_encrypted_private_key()` ghi private key đã mã hóa vào `.key.enc`.
- `load_encrypted_private_key()` đọc và giải mã `.key.enc`.
- `save_public_key()` ghi public key raw bytes vào `.key`.
- `load_public_key()` đọc public key raw bytes.
- `ensure_admin_keypair(private_path, public_path)`:
  - Nếu cả 2 key đã tồn tại: load public key + decrypt private key.
  - Nếu chưa có cả 2: sinh keypair mới, mã hóa private key, lưu public key.
  - Nếu chỉ thiếu 1 trong 2 file: báo lỗi, không overwrite nửa còn lại.

### `backend/app/crypto/qr_builder.py`

File tạo và parse QR payload:

```python
payload = {
    "v": 1,
    "id": doc_id,
    "h": sha256_hex,
    "s": sig_base64url_no_padding,
    "ts": issued_at_unix,
    "ex": expires_at_unix,
    "alg": "FALCON-512",
}
```

Chức năng chính:

- `build_payload()` tạo JSON compact để nhúng vào QR.
- `parse_payload()` validate đúng schema.
- `b64url_encode()` và `b64url_decode()` xử lý signature trong QR.
- `is_expired()` kiểm tra QR đã hết hạn chưa.

### `scripts/verify_qr.py`

CLI offline verifier:

```bash
python scripts/verify_qr.py --pdf document.pdf --payload payload.json --public-key admin_public.key
```

Luồng verify:

1. Đọc PDF bytes.
2. Đọc QR payload JSON.
3. Đọc raw public key bytes.
4. Parse payload bằng `parse_payload()`.
5. Reject nếu `alg != "FALCON-512"`.
6. Reject nếu payload đã expired.
7. Decode signature từ `payload["s"]`.
8. Gọi `verify_document()` với PDF bytes, signature, public key, và expected hash.

Exit code:

- `0`: hợp lệ.
- `1`: chữ ký/hash sai, expired, unsupported algorithm.
- `2`: lỗi input hoặc payload không parse được.

Output JSON:

```json
{"valid":true,"reason":"valid","doc_id":"...","algorithm":"FALCON-512"}
```

### `scripts/attack_forgery.py`

Demo PDF tampering:

1. Sinh keypair tạm trong RAM.
2. Ký PDF gốc.
3. Tạo QR payload cho PDF gốc.
4. Sửa nội dung PDF.
5. Verify PDF đã sửa với payload cũ.
6. Kết quả đúng: PDF gốc valid, PDF tampered fail với `signature_or_hash_mismatch`.

### `scripts/attack_replay.py`

Demo QR expired replay:

1. Sinh keypair tạm trong RAM.
2. Tạo payload có `issued_at=100`, `expires_at=200`.
3. Verify tại `now=199`: valid.
4. Verify tại `now=200`: fail với `expired`.

### `scripts/benchmark_falcon_ecdsa.py`

Benchmark cuối cho report:

- Chỉ benchmark `FALCON-512` và `ECDSA-P256`.
- Đo keygen/sign/verify bằng `time.perf_counter_ns()`.
- FALCON ký SHA-256 digest 32 bytes để khớp logic hệ thống ký hash PDF.
- ECDSA dùng `SECP256R1` và `utils.Prehashed(hashes.SHA256())`.
- Ghi output vào `report_inputs/benchmark_results.csv` và `report_inputs/benchmark_summary.md`.

## 3. Luồng Hoạt Động Từ Đầu Đến Cuối

### Bước 1: Cài dependency

Python code import FALCON qua module:

```python
import oqs
```

Dependency chính:

- `liboqs-python`
- `cryptography`
- `pytest`

Kiểm tra liboqs:

```bash
python -c "import oqs; print(oqs.get_enabled_sig_mechanisms())"
```

### Bước 2: Cấu hình passphrase cho private key

Chỉ cần nhập thủ công một thứ cho backend crypto:

```bash
export KEY_PASSPHRASE="replace-with-a-long-random-secret"
```

PowerShell:

```powershell
$env:KEY_PASSPHRASE="replace-with-a-long-random-secret"
```

Không hardcode passphrase vào source code. Không commit `.env` nếu tạo file local.

### Bước 3: Sinh hoặc load admin keypair

Backend gọi:

```python
public_key, private_key = ensure_admin_keypair(
    private_path="backend/keys/admin_private.key.enc",
    public_path="backend/keys/admin_public.key",
)
```

Nếu chưa có key:

- `generate_keypair()` sinh keypair bằng FALCON-512.
- Private key được mã hóa AES-256-GCM.
- Public key được lưu raw bytes.

Nếu đã có key:

- Public key được đọc từ `.key`.
- Private key được decrypt từ `.key.enc` bằng `KEY_PASSPHRASE`.

### Bước 4: Ký PDF

Backend nhận PDF bytes, sau đó:

1. `hash_document(pdf_bytes)` tính SHA-256 hex.
2. `sign_document(pdf_bytes, private_key)` ký SHA-256 digest 32 bytes.
3. `build_payload()` tạo QR payload chứa document id, hash, signature, timestamp, expiry, algorithm.
4. QR payload được embed vào QR code hoặc gửi cho frontend/backend adapter.

Private key chỉ tồn tại trong RAM trong lúc ký.

### Bước 5: Verify online/offline

Verifier nhận:

- PDF bytes.
- QR payload JSON.
- Public key raw bytes.

Sau đó:

1. Parse payload.
2. Check algorithm.
3. Check expiry.
4. Decode signature.
5. Tính lại SHA-256 của PDF.
6. So hash PDF hiện tại với hash trong QR.
7. Verify FALCON signature.

Nếu PDF bị sửa, hash thay đổi nên verify fail.
Nếu QR hết hạn, verifier reject trước khi verify chữ ký.

## 4. File Nào Chứa Gì Và Có Cần Nhập Thủ Công Không

| Loại file | Có trong workspace hiện tại? | Chứa gì | Có nhập thủ công không? | Có commit không? |
|---|---:|---|---|---|
| `.env.development` | Có | Config frontend Vite: API URL, mock flag | Không cần thêm crypto secret | Đang là file project |
| `.env` | Không | Nếu backend loader dùng `.env`, chỉ chứa `KEY_PASSPHRASE=...` | Có thể tạo local thủ công | Không commit |
| `.pem` | Không | Project crypto hiện không dùng PEM cho FALCON | Không tạo nếu không có nhu cầu TLS/service khác | Không commit private PEM |
| `.key` | Không | Raw public key bytes từ `save_public_key()` | Không tự gõ tay, để code sinh | Không commit theo rule project |
| `.key.enc` | Không | JSON private key đã mã hóa AES-256-GCM | Không tự gõ tay, để code sinh | Không commit |
| private key raw bytes | Không ghi file plaintext | Secret key FALCON do liboqs sinh | Không bao giờ paste thủ công | Không commit |
| QR payload JSON | Có thể sinh runtime | `v,id,h,s,ts,ex,alg` | Backend/script sinh | Có thể lưu làm demo, không chứa private key |
| benchmark CSV/MD | Có | Số liệu benchmark | Script sinh | Có thể gửi report |

## 5. `.key.enc` Sẽ Có Dạng Gì

File encrypted private key là JSON do code sinh, ví dụ cấu trúc:

```json
{
  "algorithm": "Falcon-512",
  "ciphertext": "base64-aes-gcm-ciphertext",
  "created_at": 1700000000,
  "kdf": "PBKDF2HMAC-SHA256",
  "kdf_iterations": 1200000,
  "nonce": "base64-random-nonce",
  "salt": "base64-random-salt",
  "version": 1
}
```

Không sửa tay các field này. Nếu sửa `salt`, `nonce`, `ciphertext`, `algorithm`, hoặc dùng sai
`KEY_PASSPHRASE`, decrypt sẽ fail.

## 6. Thứ Cần Nhập Thủ Công

Chỉ cần nhập thủ công:

```bash
KEY_PASSPHRASE=<một passphrase dài, random, không commit>
```

Khuyến nghị:

- Dài ít nhất 32 ký tự.
- Không dùng tên nhóm, MSSV, password dễ đoán.
- Dùng cùng passphrase để decrypt lại `.key.enc` cũ.
- Nếu đổi passphrase mà chưa re-encrypt key cũ, file `.key.enc` cũ sẽ không decrypt được.

Không nhập thủ công:

- Private key FALCON.
- Public key raw bytes.
- `.key.enc` JSON.
- Signature trong QR.
- SHA-256 hash nếu backend đang tự tính từ PDF.

## 7. Lệnh Chạy Nhanh

Trong workspace này `.venv/bin/python` đang là symlink hỏng, nên dùng:

```bash
PYTHONPATH=.venv/lib/python3.12/site-packages python3 -m pytest -q
PYTHONPATH=.venv/lib/python3.12/site-packages python3 scripts/attack_forgery.py
PYTHONPATH=.venv/lib/python3.12/site-packages python3 scripts/attack_replay.py
PYTHONPATH=.venv/lib/python3.12/site-packages python3 scripts/benchmark_falcon_ecdsa.py --iterations 20 --warmup 3
```

Nếu venv hoạt động bình thường trên máy khác, dùng dạng chuẩn:

```bash
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH python scripts/benchmark_falcon_ecdsa.py --iterations 20 --warmup 3
```

## 8. Lỗi Thường Gặp

- Thiếu `KEY_PASSPHRASE`: `key_manager.py` báo RuntimeError.
- Sai `KEY_PASSPHRASE`: decrypt `.key.enc` fail.
- Thiếu `oqs`: FALCON signing/verify không chạy, tests liên quan FALCON sẽ skip nếu được cấu hình skip.
- PDF bị sửa sau khi ký: verifier trả `signature_or_hash_mismatch`.
- QR hết hạn: verifier trả `expired`.
- Payload sai schema: verifier trả `invalid_payload`.
- Algorithm khác `FALCON-512`: verifier trả `unsupported_algorithm`.

## 9. Kết Luận Cho GPT/Reviewer

Member A không tự implement crypto primitive. Hệ thống dùng `liboqs-python` qua `import oqs`
để ký FALCON-512, ký trên SHA-256 hash của PDF, lưu private key bằng AES-256-GCM với passphrase
từ môi trường, và đưa signature vào QR payload dạng base64url. File cần nhập thủ công duy nhất là
biến môi trường local `KEY_PASSPHRASE`; các key file phải do code sinh và không được commit.
