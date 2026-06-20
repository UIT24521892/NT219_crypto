# NT219 Topic 11 - Danh sach can chinh sua sau khi review

Ngay review: 2026-05-30  
Nguon doi chieu: `Copy of Topic11_Timeline_VN.xlsx`  
Pham vi: crypto, backend, frontend, test, tai lieu va deploy.

## 1. Ket luan hien tai

Du an dang o muc **W8 dang thuc hien**, chua du dieu kien dong **Cot moc 3 - Verify QR online + offline**.

## Cap nhat trien khai 2026-05-30

Da trien khai cac patch de dong flow W8:

- [x] Chon QR online dang URL va them offline verification package.
- [x] Luu public key theo tung document de ho tro key rotation.
- [x] Them pre-sign SHA-256 mismatch guard.
- [x] Them audit log cho login, upload, sign va verify.
- [x] Them expiry metadata cho QR online va offline payload.
- [x] Sua Register page, Admin redirect va xoa `localStorage.user`.
- [x] Xoa frontend mock legacy va dependency `qrcode.react`.
- [x] Them live integration test opt-in, attack tests va security analysis script.
- [x] Them threat model, migration SQL va viet lai README.
- [x] Them Nginx rate limit cho `/verify`.
- [x] Bootstrap keypair truoc khi systemd start nhieu Uvicorn workers.

Con can chay tren moi truong day du dependency va PostgreSQL:

- [ ] Chay toan bo pytest va live integration test.
- [ ] Chay `npm ci`, lint va frontend build.
- [ ] Chay benchmark va security analysis de sinh artifact report thuc te.
- [ ] Apply migration SQL tren DB cu neu da tung khoi tao.
- [ ] Deploy EC2 va thu thap screenshot/log bang chung.

| Giai doan | Trang thai | Ghi chu |
|---|---|---|
| W1-W3 | Phan lon da co | JWT, RBAC, upload PDF, SHA-256, ML-DSA-44 (PQC) + Ed25519 (QR offline) va AES-256-GCM da duoc trien khai |
| W4 - Cot moc 2 | Gan hoan tat | Flow upload va sign da co, nhung sign chua ghi `AuditLog` |
| W5-W7 | Da trien khai phan lon | QR PNG, CLI offline verifier va PDF tampering attack da co |
| W8 - Cot moc 3 | Dang lam do | Replay demo va `/audit` da co; online/offline QR chua noi thanh mot flow hoan chinh |
| W9-W10 | Moi co scaffold | Co benchmark script va deploy config, chua co bang chung EC2 live hoac feature freeze |

## 2. Viec can chot truoc khi sua

### DEC-01 - Chon mot contract QR chinh thuc

Timeline va code hien tai dang mo ta hai huong khac nhau:

| Noi dung | Timeline Excel | Code va `README.md` hien tai |
|---|---|---|
| QR online | Scanner camera doc payload, gui `POST /verify/qr` | QR chua URL, dien thoai mo `GET /verify?d=<id>` |
| QR offline | Payload co `v,id,h,s,ts,ex,alg` | CLI da dung schema nay, nhung backend chua xuat payload nay cho tai lieu that |
| Frontend scanner | Bat buoc co `QRScanner.jsx` dung camera API | `README.md` yeu cau dung camera app cua dien thoai, khong scan trong web |

Can chon mot trong hai phuong an:

- [ ] **Phuong an A - Bam timeline:** them `POST /verify/qr`, scanner camera tren frontend va QR payload day du.
- [ ] **Phuong an B - Giu flow URL hien tai:** cap nhat timeline, rubric demo va tai lieu kien truc; van phai them verification package rieng cho offline.

Khuyen nghi cho demo: giu QR online dang URL de scan on dinh, dong thoi sinh mot verification package day du cho CLI offline.

### DEC-02 - Chot cach luu JWT

Workbook yeu cau JWT chi luu trong React context in-memory. `README.md` cho phep luu `access_token` trong `localStorage`, nhung khong cho luu user data. Code hien tai luu ca token va user.

- [ ] Chon requirement chinh thuc.
- [ ] Toi thieu: xoa `localStorage.user`.
- [ ] Neu bam workbook: chuyen token sang memory va chap nhan logout khi refresh trang, hoac dung cookie `HttpOnly` neu muon session ben vung.

## 3. P0 - Bat buoc sua de dong Cot moc 3

### QR-01 - Noi QR offline vao flow tai lieu that

**Hien trang**

- `backend/app/crypto/qr_builder.py:47` co hai kieu payload trong cung `build_payload()`.
- Backend online chi sinh dict `{v, doc_id, hash, url}` tai `backend/app/api/documents.py:254`.
- CLI `scripts/verify_qr.py:47` chi doc payload offline `{v,id,h,s,ts,ex,alg}`.
- Chua co bo sinh `verification_package.json`.

**Can sua**

- [ ] Tach ro `build_online_payload()` va `build_offline_payload()` thay vi mot ham tra ve `dict | str`.
- [ ] Them endpoint hoac script xuat verification package gom PDF hoac hash, payload offline va public key.
- [ ] Them expiry thuc te cho payload offline, vi du `signed_at + 365 ngay`.
- [ ] Bo sung huong dan demo CLI bang package sinh tu tai lieu da ky tren he thong.
- [ ] Them test integration: sign tai lieu -> xuat package -> CLI verify thanh cong.

### QR-02 - Replay protection moi chi ton tai trong script demo

**Hien trang**

- `scripts/attack_replay.py` chung minh CLI offline tu choi payload het han.
- QR online khong co expiry va `GET /verify?d=<id>` khong kiem tra timestamp.

**Can sua**

- [ ] Ghi ro threat model: replay online duoc chap nhan hay bi chan.
- [ ] Neu can chan replay online, luu `issued_at`, `expires_at` va validate tren endpoint verify.
- [ ] Xuat CSV ket qua attack thay vi chi in JSON.

### KEY-01 - Tai lieu cu se hong khi rotate key

**Hien trang**

- Khi sign, DB chi luu `public_key_ref`: `backend/app/api/documents.py:219`.
- Khi verify, backend luon lay public key hien tai: `backend/app/api/verify.py:119`.
- Q&A du kien noi public key cu van o DB de verify tai lieu cu, nhung code chua lam dieu do.

**Can sua**

- [ ] Tao bang key metadata hoac luu public key theo tung document.
- [ ] Luu key ID/reference on dinh khi sign.
- [ ] Verify bang public key gan voi tai lieu, khong mac dinh dung key hien tai.
- [ ] Them test: ky bang key A -> rotate sang key B -> tai lieu cu van verify duoc bang key A.

### SIGN-01 - Can phat hien file bi thay doi truoc khi admin ky

**Hien trang**

- Hash duoc tinh luc upload tai `backend/app/api/documents.py:112`.
- Luc sign, adapter tinh lai hash trong primitive nhung endpoint bo qua hash moi: `backend/app/api/documents.py:212`.
- Neu file tren disk bi sua sau upload va truoc sign, he thong ky file moi nhung DB va QR van co the hien hash cu.

**Can sua**

- [ ] Truoc khi sign, tinh lai SHA-256 va so sanh voi `doc.file_hash`.
- [ ] Neu khac nhau, tu choi sign va ghi audit outcome `hash_mismatch_before_sign`.
- [ ] Them test integration cho tinh huong nay.

### AUDIT-01 - Audit log chua du cho non-repudiation

**Hien trang**

- Chi endpoint verify ghi log tai `backend/app/api/verify.py:25`.
- Sign, upload va login chua ghi log du comment trong `backend/app/api/audit.py:6`.

**Can sua**

- [ ] Ghi audit cho login thanh cong/that bai.
- [ ] Ghi audit cho upload.
- [ ] Ghi audit cho sign thanh cong/that bai.
- [ ] Ghi audit cho verify online.
- [ ] Them test RBAC: citizen khong doc duoc `/audit`.

### FE-01 - Trang dang ky van la mock

**Hien trang**

- `src/pages/RegisterPage.jsx:17` chi hien `alert("Register mock thanh cong")`.
- `src/services/auth.js` da co `registerApi()` nhung chua duoc dung.
- Frontend gui `full_name`, trong khi backend schema khong co field nay.

**Can sua**

- [ ] Goi `registerApi()` that, xu ly loading/error va redirect ve `/login`.
- [ ] Chot co can luu ho ten khong.
- [ ] Neu can ho ten: them column DB, schema, migration va response.
- [ ] Neu khong can: xoa field khoi UI va request.

### FE-02 - Route admin hien tai bi hong

**Hien trang**

- `src/pages/AdminPage.jsx:22` goi cung `signDocument(1)`.
- Document ID trong backend la UUID.
- Flow sign dung hon dang nam trong `src/pages/DocumentsListPage.jsx:83`.

**Can sua**

- [ ] Thay Admin page bang danh sach tai lieu pending va nut sign theo UUID.
- [ ] Hoac redirect `/admin` sang `/documents` neu dung chung mot bang.
- [ ] Them error handling cho upload va sign.

### TEST-01 - Thieu integration test full chain

- [ ] Them backend test: register/login -> upload -> admin sign -> tao QR -> verify valid.
- [ ] Them backend test: sua PDF sau sign -> verify invalid.
- [ ] Them backend test: citizen khong duoc sign.
- [ ] Them backend test: tai lieu cua citizen A khong lo cho citizen B.
- [ ] Them test attack replay va forgery.

## 4. P1 - Can sua truoc feature freeze W10

### SEC-01 - Thieu Security Analysis W8-W10

- [ ] Viet script avalanche effect cho SHA-256: thay doi 1 bit dau vao va do so bit hash thay doi.
- [ ] Viet script entropy cua signature bytes.
- [ ] Viet script frequency distribution cua signature bytes.
- [ ] Xuat CSV ket qua.
- [ ] Ve bieu do matplotlib.
- [ ] Viet nhan xet vao phan Security Features va Testing & Security Analysis.

### BENCH-01 - Benchmark day du chua co artifact report

**Hien trang**

- `scripts/benchmark.py:183` da ho tro FALCON-512, FALCON-1024, ML-DSA-44/Dilithium2 va ECDSA-P256 de so sanh giua cac ho.
- `report_inputs/benchmark_summary.md` hien co ML-DSA-44 (PQC chinh), Ed25519 (QR offline) va ECDSA-P256 (baseline) tu `scripts/benchmark_mldsa_ed25519_ecdsa.py`.

**Can sua**

- [ ] Chay full benchmark tren dev va EC2.
- [ ] Luu `full_benchmark.csv`.
- [ ] Ve chart keygen/sign/verify time va key/signature size.
- [ ] Ghi ro OS, CPU, Python, liboqs version va so iteration.

### ATTACK-01 - Attack script chua co CSV va test tong hop

- [ ] Them output CSV cho `scripts/attack_forgery.py`.
- [ ] Them output CSV cho `scripts/attack_replay.py`.
- [ ] Them `tests/test_attacks.py`.
- [ ] Ghi ket qua va ti le block vao report.

### API-01 - Public verify chua co rate limit

- [ ] Them rate limit cho endpoint verify public.
- [ ] Ghi outcome rate-limited vao log neu can.
- [ ] Them test hoac demo script cho rate limit.

### AUTH-01 - Password bcrypt dang bi cat ngam

**Hien trang**

- `backend/app/security.py` cat password ve 72 bytes truoc khi bcrypt.
- Hai password khac nhau sau byte 72 co the bi xem la giong nhau.

**Can sua**

- [ ] Tu choi password vuot gioi han byte, hoac dung chien luoc pre-hash duoc tai lieu hoa.
- [ ] Them unit test cho password Unicode va password vuot gioi han.

### CONFIG-01 - `upload_dir` dang khong duoc dung

**Hien trang**

- Settings co `upload_dir`.
- `backend/app/api/documents.py` hardcode `Path("storage/uploads")`.

**Can sua**

- [ ] Dung `settings.upload_dir`.
- [ ] Dam bao path duoc resolve on dinh theo backend directory.
- [ ] Cleanup file neu DB commit upload that bai.

### KEY-02 - Khoi tao key co nguy co race khi chay nhieu worker

**Hien trang**

- systemd chay `uvicorn --workers 2`.
- Moi process co cache va lock rieng.
- Neu hai worker cung tao key lan dau, co the tranh chap ghi file.

**Can sua**

- [ ] Sinh keypair mot lan trong bootstrap deploy truoc khi start service.
- [ ] Hoac dung file lock cross-process va atomic write cho ca cap key.
- [ ] Them health check xac nhan keypair load duoc.

### QR-03 - Tang quiet zone cua QR

- [ ] Doi `border=2` thanh `border=4` tai `backend/app/crypto/qr_builder.py:169` de dung quiet zone toi thieu cua QR spec va tang do on dinh khi scan.
- [ ] Test scan tren man hinh va tren anh chup tu dien thoai.

### DOC-01 - Thieu threat model

- [ ] Tao `docs/threat-model.md`.
- [ ] Bao gom STRIDE va it nhat JWT forgery, PDF tampering, QR replay, key leakage, DB tampering.
- [ ] Map tung threat sang mitigation va bang chung test/demo.

## 5. P2 - Don dep va hoan thien truoc khi nop

### FE-03 - Xu ly localStorage va code frontend cu

- [ ] Xoa `localStorage.user` tai `src/contexts/AuthContext.jsx`.
- [ ] Sua `src/components/Navbar.jsx`: dang dung key `accessToken`, khong khop `access_token`.
- [ ] Xoa hoac danh dau legacy cac page/service cu khong con dung.
- [ ] Xoa `src/services/mockDb.js` neu mock mode da bo.
- [ ] Xoa dependency `qrcode.react` neu frontend khong sinh QR client-side.
- [ ] Revoke object URL cua QR khi component unmount hoac khi load QR moi.

### FE-04 - Frontend test va responsive

- [ ] Them Vitest va React Testing Library.
- [ ] Test login flow.
- [ ] Test register flow.
- [ ] Test upload flow.
- [ ] Test sign flow admin.
- [ ] Test verify page valid/invalid.
- [ ] Neu bam timeline, test QR scanner camera flow.
- [ ] Kiem tra responsive tren mobile.

### DOC-02 - README goc dang la template noi bo

**Hien trang**

- `README.md` dang mo ta cach giai nen template frontend thay vi huong dan du an.

**Can sua**

- [ ] Viet lai README: tong quan, kien truc, setup local, env vars, test, benchmark, demo flow va deploy.
- [ ] Ghi ro contract QR da chot o `DEC-01`.
- [ ] Ghi quy tac feature freeze.
- [ ] Khong dua secret, file key hoac `.env` that vao repo.

### DEPLOY-01 - Deploy moi co scaffold, chua co bang chung live

- [ ] Chot instance type: timeline ghi `t3.medium`, `deploy/DEPLOY.md` ghi `t3.micro`.
- [ ] Sua request register trong `deploy/DEPLOY.md`: backend hien khong nhan `full_name`, tru khi da them field.
- [ ] Chay bootstrap EC2.
- [ ] Xac nhan liboqs co ML-DSA-44 (FIPS 204).
- [ ] Xac nhan `.env` co `KEY_PASSPHRASE`, permission `600`.
- [ ] Xac nhan PostgreSQL, backend systemd va Nginx deu `active (running)`.
- [ ] Xac nhan TLS.
- [ ] Chay full demo flow tren EC2.
- [ ] Luu screenshot va log lam bang chung.

### DOC-03 - Bao cao va artifact cuoi ky

- [ ] Solution Architecture diagram.
- [ ] Algorithm Selection.
- [ ] Security Features.
- [ ] Testing & Security Analysis.
- [ ] Deployment Guide.
- [ ] Bao cao `.docx`.
- [ ] Slide deck 15-20 slide.
- [ ] Q&A prep sheet.
- [ ] Video demo 10 phut.
- [ ] Git tag `v1.0`.

## 6. Phan cong goi y

### Member A - Crypto/Security

- [ ] QR offline package va CLI integration.
- [ ] Key rotation design voi public key theo tai lieu.
- [ ] Attack CSV va `tests/test_attacks.py`.
- [ ] Avalanche, entropy, frequency va chart.
- [ ] Full benchmark CSV va chart.
- [ ] `docs/threat-model.md`.
- [ ] Noi dung Algorithm Selection, Security Features, Testing & Analysis.

### Member B - Backend/DevOps

- [ ] Audit log cho login/upload/sign/verify.
- [ ] Fix pre-sign hash mismatch.
- [ ] Public verify rate limit.
- [ ] Backend integration tests.
- [ ] Dung `settings.upload_dir`.
- [ ] Khoi tao key an toan truoc multi-worker.
- [ ] Deploy EC2 va thu thap bang chung.

### Member C - Frontend/Docs

- [ ] Register page goi API that.
- [ ] Sua Admin page.
- [ ] Xu ly JWT/localStorage theo quyet dinh chung.
- [ ] Xoa code mock va dependency thua.
- [ ] Them frontend tests.
- [ ] Viet lai README, tong hop report, slides va video.
- [ ] Them camera scanner neu nhom chon bam timeline.

## 7. Thu tu trien khai de dong W8

1. [ ] Chot `DEC-01` va `DEC-02`.
2. [ ] Sua key rotation va pre-sign hash mismatch.
3. [ ] Noi verification package offline vao tai lieu that.
4. [ ] Hoan thien audit log va rate limit.
5. [ ] Sua Register page va Admin page.
6. [ ] Them integration tests full chain.
7. [ ] Chay demo noi bo: valid, tampered, expired replay va offline CLI.
8. [ ] Hoan thien threat model va Security Analysis ban dau.

## 8. Lenh kiem tra sau khi sua

Checkout review hien tai chua co `.venv`, `pytest` hoac `node_modules`. Can cai dependency truoc khi chay.

```bash
# Python tests
PATH=.venv/bin:$PATH python -m pytest -q

# Attack demos
PATH=.venv/bin:$PATH python scripts/attack_forgery.py
PATH=.venv/bin:$PATH python scripts/attack_replay.py

# Benchmark
PATH=.venv/bin:$PATH python scripts/benchmark.py --iterations 20
PATH=.venv/bin:$PATH python scripts/benchmark_mldsa_ed25519_ecdsa.py --iterations 20 --warmup 3

# Frontend
npm ci
npm run lint
npm run build
```

Kiem tra toi thieu truoc khi dong W8:

- [ ] Tat ca pytest pass.
- [ ] Frontend lint va build pass.
- [ ] Upload -> sign -> QR -> online verify valid.
- [ ] Sua PDF sau sign -> online verify invalid.
- [ ] Verification package -> CLI offline verify valid.
- [ ] Payload het han -> CLI offline verify expired.
- [ ] Citizen khong the sign hoac doc audit log.
- [ ] Khong co `.env`, private key hoac generated key file bi commit.

## 9. Ket qua review tinh da co

- Git worktree sach: `main...origin/main`.
- Parse AST thanh cong cho 30 file Python.
- Bash syntax hop le cho `deploy/setup-ec2.sh` va `deploy/tls-selfsigned.sh`.
- Repo co 24 test pytest, nhung chua chay runtime duoc tren checkout review do thieu dependency local.
- `npm run lint` va `npm run build` chua chay duoc do chua co `node_modules`.
