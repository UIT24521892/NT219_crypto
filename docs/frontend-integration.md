\# Frontend Integration Notes



\## Stack

\- React + Vite

\- Dev origin: http://localhost:5173



\## Env

VITE\_API\_BASE\_URL=http://127.0.0.1:8000/api

VITE\_USE\_MOCK=true



\## Auth

Frontend lưu token ở:

\- localStorage.accessToken



Header gửi backend:

Authorization: Bearer <token>



\## Expected APIs



\### POST /auth/login

Request:

{

&#x20; "email": "admin@demo.vn",

&#x20; "password": "admin123"

}



Response:

{

&#x20; "success": true,

&#x20; "accessToken": "...",

&#x20; "user": {

&#x20;   "id": 1,

&#x20;   "fullName": "Admin",

&#x20;   "email": "admin@demo.vn",

&#x20;   "role": "admin"

&#x20; }

}



\### GET /documents

Response:

\[

&#x20; {

&#x20;   "id": 1,

&#x20;   "fileName": "test.pdf",

&#x20;   "fileType": "application/pdf",

&#x20;   "fileSize": 12345,

&#x20;   "status": "pending",

&#x20;   "uploadedBy": "Nguyễn Văn A",

&#x20;   "uploadedAt": "2026-05-18T10:00:00Z",

&#x20;   "signedAt": null,

&#x20;   "qrCodeData": null

&#x20; }

]



\### POST /documents/upload

Content-Type:

multipart/form-data



Field:

file



\### POST /documents/{id}/sign

Response:

{

&#x20; "success": true,

&#x20; "message": "Ký tài liệu thành công",

&#x20; "documentHash": "...",

&#x20; "signature": "...",

&#x20; "algorithm": "FALCON-512",

&#x20; "qrCodeData": "..."

}



\### POST /verify

Request:

{

&#x20; "documentId": 1,

&#x20; "documentHash": "...",

&#x20; "signature": "...",

&#x20; "algorithm": "FALCON-512"

}



Response:

{

&#x20; "valid": true,

&#x20; "message": "Signature verified",

&#x20; "algorithm": "FALCON-512",

&#x20; "documentHash": "...",

&#x20; "checkedAt": "2026-05-18T10:00:00Z"

}

