# NT219 Crypto — AGENTS.md
# OpenAI Codex custom instructions cho Member A, đồ án NT219 Topic 11

## Dự án là gì
Cổng Dịch vụ Công cho Công dân — ký số PDF theo sơ đồ hybrid: ML-DSA-44
(CRYSTALS-Dilithium, FIPS 204) là chữ ký hậu lượng tử chính (online/PDF
metadata), kèm chữ ký Ed25519 cổ điển 64 byte trong QR tự chứa để verify offline.
Member A phụ trách toàn bộ module Crypto/Security.

## Stack của Member A
- Python 3.11 + liboqs-python (oqs.Signature)
- pytest cho unit test
- Backend tích hợp: FastAPI (Member B), port 4000

## Venv
```bash
# Chạy với venv local
PATH=.venv/bin:$PATH python -m pytest -q
PATH=.venv/bin:$PATH python scripts/benchmark.py
```

## File đã hoàn thành (pass hết pytest)
- backend/app/crypto/mldsa_service.py — ML-DSA-44 primary: generate_keypair, hash_document, sign_document, verify_signature, verify_document
- backend/app/crypto/ed25519_qr_service.py — Ed25519 (classical) cho QR offline: generate_keypair, sign_qr, verify_qr
- backend/app/crypto/key_manager.py — AES-256-GCM, PBKDF2HMAC, KEY_PASSPHRASE từ env
- backend/app/crypto/qr_builder.py — build_payload, parse_payload, b64url_decode, is_expired
- scripts/benchmark.py — Falcon-512/1024, ML-DSA-44, ECDSA-P256 → results/benchmark.csv
- tests/test_mldsa.py, test_qr_hybrid.py, test_key_manager.py, test_qr_builder.py, test_benchmark.py

## File CẦN làm
- scripts/verify_qr.py — CLI offline verifier (W6)
- scripts/attack_forgery.py — PDF tampering attack (W7)
- scripts/attack_replay.py — QR replay attack (W8)
- Security Analysis: avalanche, entropy, frequency (W8–W9)

## QR Payload Schema (đang dùng)
```python
payload = {
    "v":   1,
    "id":  doc_id,           # UUID tài liệu
    "h":   sha256_hex,       # SHA-256(pdf_bytes).hexdigest()
    "s":   sig_base64url,    # ML-DSA-44 sig, base64url no-padding
    "ts":  int(time.time()), # Unix timestamp lúc ký
    "ex":  int(time.time()) + 365 * 86400,
    "alg": "ML-DSA-44",
}
# Minified: json.dumps(payload, separators=(",", ":"))
```

## Benchmark thực tế (đã đo)
| Algorithm  | keygen(ms) | sign(ms) | verify(ms) | pubkey(B) | privkey(B) | sig(B) |
|------------|-----------|----------|------------|-----------|------------|--------|
| Falcon-512 | 5.904     | 0.224    | 0.047      | 897       | 1281       | 655    |
| Falcon-1024| 18.570    | 0.415    | 0.080      | 1793      | 2305       | 1267   |
| ML-DSA-44  | 0.046     | 0.063    | 0.019      | 1312      | 2560       | 2420   |
| ECDSA-P256 | 0.169     | 0.093    | 0.064      | 91        | 138        | 70     |

## Quy tắc bắt buộc
- Dùng oqs.Signature("ML-DSA-44") từ liboqs-python — không tự implement crypto
- KHÔNG lưu private key vào DB hoặc hardcode
- Private key mã hóa AES-256-GCM, passphrase lấy từ env KEY_PASSPHRASE
- KHÔNG commit .env hoặc file key
- KHÔNG chạy DROP/TRUNCATE/DELETE trừ khi được yêu cầu rõ
- Sau khi sửa, báo cáo file đã sửa + cách chạy test lại

## Câu hỏi Q&A defense hay gặp

**Tại sao ML-DSA-44 làm chữ ký chính (thay vì FALCON-512)?**
ML-DSA-44 (CRYSTALS-Dilithium) là chuẩn NIST FIPS 204 đã được chuẩn hóa chính
thức, dựa trên Module-LWE/SIS lattice; ký/verify nhanh và triển khai ổn định trên
liboqs (C library đã audit của Open Quantum Safe), không tự implement. Đây là lớp
bảo đảm hậu lượng tử cho tài liệu, verify online / từ metadata PDF.

**Vậy QR offline ký bằng gì? Chữ ký ML-DSA-44 ~2420B quá lớn cho QR mà?**
Đúng. Chữ ký ML-DSA-44 ~2420 byte và public key ~1312 byte quá lớn để nhét vào
một QR scan được. Nên QR tự chứa dùng Ed25519 — chữ ký cổ điển chỉ 64 byte,
public key 32 byte — để verify offline ngay tại chỗ bằng Web Crypto. Lưu ý trung
thực: Ed25519 KHÔNG phải hậu lượng tử, chỉ là lớp tiện ích UX offline; bảo đảm
hậu lượng tử thật sự vẫn là ML-DSA-44 (FALCON-512 trước đây từng được cân nhắc
cho QR vì sig nhỏ ~652B, nhưng vẫn lớn hơn nhiều so với Ed25519 và không phải
chuẩn FIPS).

**Nếu private key bị lộ thì sao?**
Sinh keypair mới, update KEY_PASSPHRASE, re-sign tài liệu cần thiết. Public key cũ vẫn
trong DB để verify tài liệu cũ. Production dùng HSM hoặc AWS KMS.

**Tại sao ký trên hash thay vì ký trực tiếp PDF?**
Hash SHA-256 luôn là 32 bytes cố định, không phụ thuộc kích thước PDF. Verification chỉ
cần tính lại hash, không cần truyền toàn bộ PDF — phù hợp cho offline verify và QR payload.
