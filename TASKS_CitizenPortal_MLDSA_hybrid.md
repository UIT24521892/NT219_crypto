# Task list cho Claude Code — CitizenPortal: ML-DSA-44 + QR hybrid offline (Ed25519)

> **Cách dùng:** mở file này trong Claude Code tại thư mục gốc repo, làm tuần tự theo từng PHASE. Mỗi task có **Việc cần làm**, **File liên quan**, **Tiêu chí nghiệm thu (DoD)**. Xong tick `[x]`.

---

## 0. Bối cảnh & mục tiêu

Codebase hiện ở trạng thái **v3** (FALCON-512, 1 tài khoản admin làm hết, QR chứa URL). Đích cần đạt = **v4 + hybrid offline QR**:

1. Thêm **ML-DSA-44** (FIPS 204) làm chữ ký **chính** (online verify, lớp hậu lượng tử).
2. Thêm **Ed25519** làm chữ ký **nhỏ nhúng trong QR** (offline verify tại chỗ).
3. Tách quyền `admin` → `reviewer` + `signer`.
4. Trust Registry công khai (`GET /public-keys`) cho **cả 2 key** ml-dsa-44 và ed25519.
5. Nhúng QR (tự chứa) + 2 chữ ký vào file PDF (pikepdf).
6. Trang verifier **offline** đóng gói sẵn public key Ed25519.

### Vì sao 2 lớp chữ ký (câu chốt cho buổi bảo vệ)
- **ML-DSA-44** (signature ~2420 B): chữ ký **chính**, chuẩn NIST FIPS 204, dựa trên Module-LWE, chống được máy tính lượng tử. Verify online qua `/verify?d=` và nhúng trong metadata PDF. Quá to để nhét QR.
- **Ed25519** (signature 64 B): chữ ký **nhỏ** nhét vừa QR để quét verify **offline tại chỗ** giống mẫu "Giấy đi đường", không cần mạng.

> **⚠️ Lưu ý trung thực cho báo cáo/bảo vệ:** Ed25519 là thuật toán **cổ điển** (không hậu lượng tử). Phải nói rõ trong báo cáo: lớp Ed25519 chỉ là **tiện ích xác minh nhanh offline (UX)**; **toàn vẹn & chống lượng tử thật sự do ML-DSA-44 đảm bảo** (verify online / trong metadata PDF). Nếu giám khảo hỏi "sao đề tài PQC mà QR lại dùng chữ ký cổ điển?" → trả lời: vì chữ ký PQC (ML-DSA 2420 B) không nhét vừa QR; lớp QR offline là tiện lợi, và **có thể nâng cấp lên FALCON-512 (PQC, 652 B)** mà không đổi kiến trúc. Đây là trade-off kích thước có chủ đích, không phải lỗ hổng.

---

## ⚠️ QUY TẮC AN TOÀN — đọc trước khi đụng server

- **KHÔNG reboot/stop EC2 (54.169.147.134).** Swap 2GB chưa nằm trong `/etc/fstab` → reboot mất swap; stop instance đổi public IP → hỏng cert `54.169.147.134.nip.io`. Chỉ `systemctl restart citizen-portal-api`, không restart máy.
- **Backup DB trước mỗi migration:** `pg_dump citizen_portal > ~/backup_$(date +%F_%H%M).sql`.
- **`ALTER TYPE ... ADD VALUE` chạy NGOÀI transaction** → tách khỏi `BEGIN/COMMIT` trong file migration.
- **Migration idempotent:** `ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`, check enum value tồn tại trước khi add.
- Làm trên nhánh `feat/mldsa-hybrid`, không push thẳng `main`. Mỗi PHASE = 1 commit.
- **Trước mỗi PHASE: `grep`/đọc code xác nhận trạng thái thật** thay vì tin báo cáo — repo có thể đã đi trước/sau báo cáo ở vài chỗ.

---

## PHASE 1 — Thêm ML-DSA-44 (chính) + Ed25519 (QR)

> Hệ thống chạy **song song 2 crypto service**. FALCON-512 cũ có thể xoá vì không còn dùng (xem 1.4).

- [ ] **1.1 ML-DSA service**
  - Việc: tạo `backend/app/crypto/mldsa_service.py` dùng `oqs.Signature("ML-DSA-44")` (nếu liboqs cũ chỉ có "Dilithium2" thì fallback + ghi chú). Hàm `sign(data)->bytes`, `verify(data,sig,pub)->bool`.
  - DoF: ký + verify 1 chuỗi test bằng ML-DSA-44.

- [ ] **1.2 Ed25519 service cho QR**
  - Việc: tạo `backend/app/crypto/ed25519_qr_service.py` dùng thư viện `cryptography`:
    `from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey`.
    Hàm `sign_qr(canonical: bytes)->bytes` (ra 64 B), `verify_qr(canonical, sig, pub)->bool`. Public key export được dạng raw 32 B và PEM.
  - DoF: ký + verify 1 chuỗi test bằng Ed25519; sig đúng 64 byte.

- [ ] **1.3 Key manager cho 2 key**
  - Việc: `key_manager.py` quản lý **2 keypair**: `keys/mldsa_private.enc.json` và `keys/ed25519_private.enc.json`. Cả hai mã hoá AES-256-GCM, khoá dẫn xuất từ `KEY_PASSPHRASE` qua PBKDF2. Sinh mới nếu chưa có.
  - DoF: chạy backend lần đầu tạo đủ 2 file key mã hoá, giải mã được bằng passphrase.

- [ ] **1.4 Dọn FALCON cũ**
  - Việc: gỡ `falcon_service.py`, `falcon_primitives.py` và mọi import liên quan (không còn dùng). `grep -ri "falcon" backend/app` chỉ còn comment lịch sử (nếu muốn giữ) — không còn code chạy.
  - DoF: backend khởi động không lỗi import sau khi gỡ FALCON.

---

## PHASE 2 — Migration 003: role + cột chữ ký + signed_pdf

- [ ] **2.1 Viết `backend/migrations/003_role_separation_and_hybrid.sql`**
  - Việc:
    - Mở rộng enum `user_role`: `(citizen, admin)` → thêm `reviewer`, `signer` (`ALTER TYPE ... ADD VALUE IF NOT EXISTS`, ngoài transaction).
    - `documents` thêm cột (đều `IF NOT EXISTS`):
      - `mldsa_signature` BYTEA — ML-DSA-44 ký trên SHA-256(PDF).
      - `qr_signature` BYTEA — Ed25519 ký trên **chuỗi canonical** của QR (xem 5.1).
      - `qr_payload` JSONB — chuỗi data đã đưa vào QR (truy vết).
      - `signed_pdf_path` VARCHAR — đường dẫn PDF đã nhúng QR.
      - `public_key_ref` VARCHAR — key_id ML-DSA (nếu chưa có từ migration 002).
      - `qr_public_key_ref` VARCHAR — key_id Ed25519 dùng cho QR.
    - Migrate dữ liệu cũ: cột `falcon_signature` cũ (nếu có) → drop hoặc giữ làm lịch sử; user `role=admin` → map sang `signer` (ghi rõ quy ước trong comment).
  - DoF: apply `001 → 002 → 003` trên DB sạch không lỗi; chạy lại lần 2 không lỗi.

- [ ] **2.2 Apply trên EC2 (không reboot)**
  - Việc: `pg_dump` backup → apply 003 → kiểm tra `\d documents` và `\dT+ user_role`.
  - DoF: có đủ cột mới; enum có 4 giá trị.

---

## PHASE 3 — RBAC: Reviewer vs Signer

- [ ] **3.1 Dependency phân quyền:** thêm `require_reviewer`, `require_signer`, giữ `require_admin` (đọc role từ JWT qua `get_current_user`).
- [ ] **3.2 Gắn quyền vào endpoint:**
  - `/documents/{id}/approve` & `/reject` → `require_reviewer`.
  - `/documents/{id}/sign` → `require_signer` **và** kiểm tra `status==APPROVED`, chưa thì 409 `document_not_approved`.
  - Đảm bảo **1 tài khoản không vừa approve vừa sign cùng 1 document**.
  - DoF: reviewer-sign→403, signer-approve→403, sign-chưa-approved→409, citizen-sign→403.
- [ ] **3.3 Audit log:** ghi đúng `reviewed_by` / `signed_by` + actor + role cho từng thao tác.

---

## PHASE 4 — Trust Registry công khai (2 key)

- [ ] **4.1 Router public-keys**
  - Việc: `backend/app/routers/public_keys.py`:
    - `GET /public-keys` → liệt kê key `status=ACTIVE` (key_id, algorithm, fingerprint, valid_from/until). Trả **cả 2**: `ml-dsa-44:...` (algorithm `ml-dsa-44`) và `ed25519:...` (algorithm `ed25519`).
    - `GET /public-keys/{key_id}` → chi tiết kèm `public_key_pem` + `fingerprint`.
    - **Không yêu cầu auth.**
  - DoF: gọi không cần token, thấy đủ 2 key.
- [ ] **4.2 Đăng ký router vào `main.py`** → kiểm tra Swagger `/docs` + `curl /public-keys`.
- [ ] **4.3 Seed 2 key khi ký lần đầu**
  - Việc: lần đầu sign, backend tính fingerprint cho cả ML-DSA pubkey và Ed25519 pubkey, tạo 2 bản ghi `public_keys` status=ACTIVE; document lưu `public_key_ref` (ML-DSA) + `qr_public_key_ref` (Ed25519).
  - DoF: bảng `public_keys` có 2 dòng sau document đầu tiên.

---

## PHASE 5 — Luồng ký hybrid: sinh 2 chữ ký + payload QR tự chứa

> **Phần lõi.** Lúc Signer ký (1 lần), backend tạo **2 chữ ký** và **1 payload QR tự chứa**.

- [ ] **5.1 Hàm tạo chuỗi canonical cho QR**
  - Việc: viết `build_qr_canonical(doc) -> bytes` sinh chuỗi **xác định, cố định thứ tự**, ví dụ:
    `doc_id|file_hash|signer_email|signed_at_iso|valid_from|valid_until`
    Đây là chuỗi Ed25519 sẽ ký. **Sign và verify (kể cả phía client JS) phải dùng CHUNG đúng định dạng này** — sai 1 ký tự/khoảng trắng/encoding là verify fail. Chốt rõ: UTF-8, không space thừa, ngày ISO-8601.
  - DoF: gọi 2 lần trên cùng document ra **đúng cùng 1 chuỗi byte**.

- [ ] **5.2 Sinh 2 chữ ký lúc sign**
  - Việc: trong `/documents/{id}/sign`:
    1. `mldsa_signature` = ML-DSA-44 ký trên `SHA-256(PDF)` → lưu DB.
    2. `canonical` = `build_qr_canonical(doc)`; `qr_signature` = Ed25519 ký trên `canonical` → lưu DB.
    3. (self-check) verify ngay 2 chữ ký vừa tạo trước khi commit.
  - DoF: document signed có cả `mldsa_signature` và `qr_signature`; self-check pass.

- [ ] **5.3 Đóng gói payload QR tự chứa (KHÔNG còn là URL)**
  - Việc: nội dung QR = chuỗi pipe-delimited kiểu giấy đi đường:
    `base64(qr_signature)|doc_id|file_hash_prefix|signer_email|signed_at|valid_until|qr_public_key_ref`
    Render QR PNG từ chuỗi này, mức sửa lỗi **M** (vẫn dư chỗ).
  - DoF: quét QR ra đúng chuỗi pipe-delimited đọc được; KHÔNG ra URL.
  - Kích thước: Ed25519 sig 64 B → base64 ~88 ký tự; tổng payload ~160–200 ký tự → **QR version ~7–9, gọn, in nhỏ vẫn quét tốt** (như mẫu giấy đi đường).

---

## PHASE 6 — Nhúng QR + 2 chữ ký vào PDF (pikepdf)

- [ ] **6.1 `pdf_embedder.py`**
  - Việc: cài `pikepdf` (thêm `requirements.txt`). Hàm nhận (PDF gốc, ảnh QR PNG, `mldsa_signature`, `qr_signature`, `public_key_ref`, `qr_public_key_ref`, `signed_at`) → tạo PDF mới: chèn QR vào trang đầu/góc (giống vị trí QR mẫu giấy đi đường) + ghi 2 chữ ký + 2 key_ref + signed_at vào **metadata ẩn** của PDF. Lưu `<filename>_signed.pdf`.
  - DoF: mở `_signed.pdf` thấy QR trên trang; đọc metadata ra đủ các trường.
- [ ] **6.2 Gọi trong luồng sign** → lưu `signed_pdf_path`.
- [ ] **6.3 Endpoint `GET /documents/{id}/signed-download`** trả `_signed.pdf` cho citizen sở hữu document.

---

## PHASE 7 — Trang verifier OFFLINE (Ed25519 client-side)

> Nơi thể hiện "quét ra nội dung + verify chữ ký không cần mạng" như giấy đi đường. **Với Ed25519, verify trong trình duyệt rất dễ — không cần WASM.**

- [ ] **7.1 Đóng gói public key Ed25519 vào verifier**
  - Việc: build-time, nhúng `ed25519_public_key` (raw 32 B / hoặc SPKI) vào app verifier dưới dạng hằng số/asset. Đây là **trust anchor offline** — verifier tin key này sẵn, không hỏi server.
  - DoF: verifier có sẵn public key Ed25519 kể cả khi tắt mạng.

- [ ] **7.2 Logic verify offline (client-side)**
  - Việc: trang verifier nhận chuỗi QR (quét/paste) → tách theo `|` → dựng lại `canonical` bằng **đúng định dạng `build_qr_canonical`** (port sang JS, cẩn thận khớp byte-for-byte) → verify `qr_signature` bằng public key đã đóng gói.
    - Ưu tiên **Web Crypto API**: `crypto.subtle.importKey('raw', pub, {name:'Ed25519'}, ...)` rồi `crypto.subtle.verify('Ed25519', key, sig, canonical)` (Chrome/Edge/Safari mới hỗ trợ).
    - Fallback nếu trình duyệt cũ: lib `tweetnacl` (`nacl.sign.detached.verify(canonical, sig, pub)`) — chỉ ~8KB, không cần build phức tạp.
  - DoF: **tắt mạng** vẫn verify được 1 QR thật → hợp lệ; sửa 1 ký tự trong chuỗi → không hợp lệ.

- [ ] **7.3 Giữ verify online song song**
  - Việc: nếu có mạng, vẫn cho gọi `GET /verify?d=` để check ML-DSA-44 trên hash hiện tại + hạn QR (lớp PQC mạnh hơn). Nút "Xem khóa công khai" gọi `GET /public-keys/{key_id}`.
  - DoF: cả 2 đường (offline Ed25519, online ML-DSA) đều chạy.

---

## PHASE 8 — Frontend

- [ ] **8.1 Tách `AdminPage` → `ReviewerPage` + `SignerPage`** (điều hướng theo role từ `/auth/me`).
- [ ] **8.2 VerifyPage:** hỗ trợ cả quét QR tự chứa (offline Ed25519) lẫn verify online; nút "Xem khóa công khai".
- [ ] **8.3 DocumentDetailPage:** `signed` → link tải `_signed.pdf`; `rejected` → hiện `review_note`.
- [ ] **8.4 Dọn dead code:** xoá `mockDb.js`, `authService.js`, `documentService.js`, `CitizenPage`, `DashboardPage`, `QrPage` nếu không còn import; tắt `VITE_USE_MOCK` cho prod.
  - DoF: `npm run build` pass.

---

## PHASE 9 — Benchmark & đồng bộ báo cáo

- [ ] **9.1 ⚠️ Sửa bảng benchmark sai trong báo cáo v4**
  - Vấn đề: bảng benchmark (mục III.4.b) **vẫn để số FALCON-512** (public key 897 B, signature 652 B) trong khi mục II.2.c nói ML-DSA-44 là public key 1312 B, signature 2420 B → mâu thuẫn. Chạy lại lấy số thật.
- [ ] **9.2 Benchmark 3 thuật toán:** ML-DSA-44 vs Ed25519 vs ECDSA-P256 (100 iter, 10 warmup). Bảng này minh hoạ rõ lý do kiến trúc: ML-DSA sig ~2420 B (PQC, online) vs Ed25519 64 B (nhỏ → nhét QR offline). Xuất PNG biểu đồ.
  - File: `scripts/benchmark_mldsa_ed25519_ecdsa.py`.
- [ ] **9.3 Đồng bộ chữ trong báo cáo:**
  - Mô tả kiến trúc 2 lớp: ML-DSA-44 (PQC chính, online) + Ed25519 (offline QR, **ghi rõ là cổ điển, lớp tiện lợi**).
  - Cập nhật mục III.3.c (luồng QR self-contained), bảng threat model thêm dòng "Sửa nội dung trong QR (offline forgery) → Ed25519 verify fail".
  - Thêm 1 câu thẳng thắn: vì sao QR dùng cổ điển + hướng nâng cấp lên FALCON-512.

---

## PHASE 10 — Test end-to-end & nghiệm thu

- [ ] **10.1 Smoke test đầy đủ (EC2, không reboot):** citizen upload → reviewer approve → signer sign (sinh 2 chữ ký) → nhúng QR vào PDF → tải `_signed.pdf` → **quét QR ra chuỗi tự chứa** → verify offline (tắt mạng) hợp lệ → bật mạng verify online ML-DSA cũng hợp lệ.
- [ ] **10.2 Attack scripts:**
  - `attack_forgery.py`: sửa nội dung PDF sau ký → ML-DSA verify fail (`signature_or_hash_mismatch`).
  - `attack_qr_tamper.py` (MỚI): sửa 1 field trong chuỗi QR → Ed25519 verify offline fail.
  - `attack_replay.py`: QR quá hạn → `expired`. Tất cả `attack_blocked=true`.
- [ ] **10.3 Test phân quyền:** reviewer-sign→403, signer-approve→403, sign-chưa-approved→409, citizen-sign→403.
- [ ] **10.4** `systemctl status citizen-portal-api` active; `journalctl` không traceback sau `restart`.

---

## Kiến trúc 2 lớp chữ ký — tóm tắt

| | ML-DSA-44 (chính, PQC) | Ed25519 (QR, cổ điển) |
|---|---|---|
| Ký trên | SHA-256(PDF) | chuỗi canonical của QR |
| Kích thước sig | ~2420 B | 64 B |
| Lưu ở | DB `mldsa_signature` + metadata PDF | DB `qr_signature` + **trong QR** |
| Verify | online `/verify?d=` | **offline**, key đóng gói sẵn (Web Crypto / tweetnacl) |
| Vai trò | toàn vẹn + chống lượng tử (chuẩn FIPS 204) | quét nhanh tại chỗ, không cần mạng (tiện ích) |
| Public key | `public_keys` (key_id `ml-dsa-44:`) | `public_keys` (key_id `ed25519:`) + bundle trong verifier |

## Bảng đối chiếu v3 → đích

| Hạng mục | v3 | Đích (hybrid) |
|---|---|---|
| Thuật toán | FALCON-512 (1 cái) | ML-DSA-44 (chính) + Ed25519 (QR) |
| Cột chữ ký | `falcon_signature` | `mldsa_signature` + `qr_signature` |
| Nội dung QR | URL `verify?d=` | chuỗi tự chứa `sig\|fields` |
| Verify | chỉ online | online (ML-DSA) + offline (Ed25519) |
| Phân quyền | 1 admin | reviewer + signer |
| Migration | 001, 002 | 001, 002, **003** |
| Trust Registry public | không | `GET /public-keys` (2 key) |
| Nhúng PDF | không | pikepdf, `signed_pdf_path` |

## Thứ tự chạy
PHASE 1 → 2 → 3 → 4 → 5 → 6 → 7 (lõi hybrid xong) → 8 (frontend) → 9 (benchmark + báo cáo) → 10 (test). Commit theo từng phase, cuối cùng PR `feat/mldsa-hybrid` → `main`.

## Nâng cấp tương lai (nếu muốn QR cũng PQC)
Đổi lớp Ed25519 → **FALCON-512** (PQC, 652 B): thay `ed25519_qr_service` bằng `falcon_qr_service` (liboqs), `qr_public_key_ref=falcon-512:`. QR sẽ dày hơn (version ~16–20) nhưng vẫn quét được, và lúc đó **cả 2 lớp đều hậu lượng tử**. Kiến trúc giữ nguyên, chỉ đổi thư viện ký/verify của lớp QR.
