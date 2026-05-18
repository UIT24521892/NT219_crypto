# Template Frontend — CitizenPortal (NT219)

Template này thay thế hoàn toàn `src/` cũ. Đã tích hợp đúng với backend của Trung (Member B).

## 1. Cách áp dụng

```bash
# Trong folder repo frontend hiện tại của C
cd <path>/NT219_crypto

# Backup src/ cũ nếu muốn xem lại
mv src src_old

# Giải nén template (mình gửi kèm file zip này)
unzip template_for_c.zip
# → src/ mới + .env.development mới sẽ xuất hiện
```

Sau đó:

```bash
npm install                 # cài nốt nếu chưa
npm run dev                 # khởi động Vite, mặc định port 5173
```

Mở `http://localhost:5173` → phải thấy login page.

**Lưu ý:** template KHÔNG đụng vào `package.json`, `vite.config.js`, `index.html` của C — giữ nguyên những file đó.

## 2. Cấu trúc

```
src/
├── main.jsx                         entry point
├── App.jsx                          ★ routes definition
├── index.css                        global styles tối giản
├── services/
│   ├── api.js                       axios instance + interceptors (token tự động)
│   ├── auth.js                      registerApi, loginApi, meApi
│   ├── documents.js                 list/get/upload/sign/qr/download
│   └── verify.js                    verifyDocument (public, không cần auth)
├── contexts/
│   └── AuthContext.jsx              ★ provider quản lý user + login/logout
├── components/
│   ├── ProtectedRoute.jsx           guard cho route cần auth
│   └── Layout.jsx                   navbar + content wrapper
└── pages/
    ├── LoginPage.jsx                ★ MẪU 1 — đăng nhập (đã có)
    └── VerifyPage.jsx               ★ MẪU 2 — verify QR target (đã có)
```

## 3. Việc của C — viết 4 page còn thiếu

C cần tạo 4 file mới trong `src/pages/`:

### 3.1 `RegisterPage.jsx`

Form đăng ký. Gọi `registerApi({ email, password, full_name })`.

Tham khảo `LoginPage.jsx` (cùng pattern: form + submit + error handling). Sau khi đăng ký thành công → redirect về `/login`.

### 3.2 `DocumentsListPage.jsx`

- Gọi `listDocuments()` lúc mount → hiển thị table
- Có form upload PDF → gọi `uploadDocument(file)`
- Mỗi row có link `<Link to={\`/documents/\${doc.id}\`}>`

### 3.3 `DocumentDetailPage.jsx`

- `useParams()` lấy `id`
- Gọi `getDocument(id)` để có metadata
- Nút "Tải xuống" → `downloadDocument(id)` rồi mở URL
- Nếu `doc.status === 'signed'` → nút "Xem QR" → gọi `getQrCode(id)` → hiển thị `<img src={qrUrl} />`

### 3.4 `AdminPage.jsx`

- Chỉ admin vào được (đã guard ở App.jsx)
- Gọi `listDocuments()` → tất cả docs trong hệ thống
- Filter `status === 'pending'` → mỗi row có nút "Ký FALCON" → `signDocument(id)` → reload list

## 4. Quan trọng — KHÔNG làm những việc sau

❌ **KHÔNG** dùng `qrcode.react` để tự sinh QR client-side
→ Backend đã sinh QR PNG sẵn. C gọi `getQrCode(id)` rồi `<img src={blob} />`.

❌ **KHÔNG** verify chữ ký phía client
→ Backend dùng FALCON-512 thật. Frontend chỉ hiển thị kết quả `valid: true/false` trả từ backend.

❌ **KHÔNG** dùng camera scan QR trong app
→ User scan QR bằng app camera của điện thoại. URL trong QR sẽ tự mở browser tới `/verify?d=<id>`. Việc của C là làm trang `/verify` đẹp (đã có sẵn `VerifyPage.jsx`).

❌ **KHÔNG** lưu user data dưới `localStorage` ngoài `access_token`
→ User info luôn fetch từ `/auth/me`. AuthContext đã tự lo.

❌ **KHÔNG** đổi `.env.development` về `VITE_USE_MOCK=true`
→ Mock mode bị xoá hoàn toàn. Template chạy thẳng với backend thật.

## 5. Test workflow demo

Yêu cầu backend của Trung đang chạy ở `http://localhost:8000`. Test users đã có sẵn trong DB:

| Email | Password | Role |
|---|---|---|
| `alice@example.com` | `SecurePass123` | citizen |
| `bob@example.com` | `BobPass123` | citizen |
| `admin@example.com` | `AdminPass123` | **admin** |

**Demo flow:**

1. Login bằng `alice@example.com` → vào `/documents`
2. Upload 1 file PDF → thấy doc xuất hiện với status "pending"
3. Logout, login lại bằng `admin@example.com` → vào `/admin`
4. Tìm doc của alice trong list → click "Ký FALCON" → status đổi thành "signed"
5. Vào `/documents/:id` của doc đó (admin xem được tất cả) → click "Xem QR" → thấy ảnh QR
6. Lưu QR vào điện thoại, hoặc copy URL trong QR (dùng app QR reader bất kỳ) → mở URL bằng browser khác / incognito → vào trang `/verify?d=...` → thấy ✅ "Tài liệu hợp lệ" + thông tin signer

**Demo tamper:**

7. Trên máy Trung, vào folder `backend/storage/uploads/<doc_id>.pdf` → mở bằng text editor → thêm 1 ký tự bất kỳ → save
8. Refresh trang `/verify?d=<id>` đó → bây giờ thấy ⚠️ "Tài liệu KHÔNG hợp lệ — Signature verification failed"

→ Đây là **highlight demo** chứng minh FALCON-512 thật sự chống chỉnh sửa.

## 6. CORS

Nếu chạy `npm run dev` mà console thấy lỗi CORS → báo Trung. Backend đã enable CORS cho `localhost:5173`, nhưng nếu C đổi port hoặc dùng IP LAN → cần thêm origin.

## 7. Câu hỏi gửi lại Trung

- [ ] Có cần thêm endpoint `GET /users` (admin xem list users)?
- [ ] Có cần `DELETE /documents/:id`?
- [ ] Có cần `PATCH /auth/me`?
- [ ] Có cần `GET /audit` (admin xem audit log)?
- [ ] Khi nào C có thể demo thử local với backend chạy thực tế?

---

## 8. Tóm tắt thay đổi so với code cũ của C

| Cũ | Mới |
|---|---|
| `VITE_USE_MOCK=true` | xoá hoàn toàn, chạy thẳng với backend |
| `mockDb.js` (localStorage fake) | xoá, gọi API thật |
| baseURL `http://localhost:5000/api` | `http://localhost:8000` (env var) |
| App.jsx monolith, state-based nav | App.jsx routes, react-router-dom |
| QR tự sinh client (`qrcode.react`) | dùng PNG từ backend |
| Verify camera scan + so chuỗi base64 | mở URL → backend verify FALCON thật |
| Field `documentHash`, `documentId` | `file_hash`, `doc_id` (snake_case khớp backend) |
| Login response `{user, accessToken}` | `{access_token}` → fetch `/auth/me` riêng |
| `pages/` và `components/` không xài | dùng đúng pattern modular |

Mọi vấn đề khi áp dụng template — báo Trung ngay, đừng tự fix lung tung làm sai contract với backend.
