# DEPLOY.md — Triển khai Citizen Services Portal lên AWS EC2

Runbook deploy 1 instance EC2 Ubuntu 22.04. Backend (FastAPI) + PostgreSQL + Nginx + frontend (Vite build), same-origin.

## 0. Chuẩn bị AWS EC2

- Launch instance: **Ubuntu Server 22.04 LTS**, **t3.micro** (Free Tier).
- Security Group — mở inbound:
  - **22** (SSH) — chỉ từ IP của bạn
  - **80** (HTTP)
  - **443** (HTTPS)
- Tạo + tải key pair `.pem`.
- SSH vào: `ssh -i key.pem ubuntu@<EC2_PUBLIC_IP>`

## 1. Đưa code lên EC2

Cách A — clone từ Git (nếu nhóm có repo chung):
```bash
cd ~
git clone <repo-url> citizen-portal
```

Cách B — copy từ máy local (scp):
```bash
# Trên máy Trung
scp -i key.pem citizen-portal-backend.tar.gz ubuntu@<EC2_IP>:~/
# Trên EC2
tar -xzf citizen-portal-backend.tar.gz
# (đảm bảo giải nén ra ~/citizen-portal/)
```

**Quan trọng:** code phải nằm ở `/home/ubuntu/citizen-portal/` (các config đều hard-code path này).

## 2. Bootstrap (cài deps + DB + .env)

```bash
cd ~/citizen-portal
chmod +x deploy/*.sh
./deploy/setup-ec2.sh
```

Script tự: cài python3.11/postgres/nginx + **liboqs build deps** (cmake/ninja-build/libssl-dev), tạo DB + user, venv + pip install, **pre-build liboqs** (lần import oqs đầu, ~2-5 phút), sinh `.env` (random DB pass + JWT secret + **KEY_PASSPHRASE**), tạo tables, tạo storage dir.

> ⚠ **FALCON-512 thật (liboqs):** backend giờ dùng crypto thật, không còn mock. `setup-ec2.sh` đã cài sẵn liboqs deps + pre-build. Lần `import oqs` đầu build C lib mất ~2-5 phút (script chờ sẵn). Nếu build lỗi → check `cmake ninja-build libssl-dev` đã cài.
>
> ⚠ **KEY_PASSPHRASE:** dùng để mã hoá private key admin (AES-256-GCM at-rest). `setup-ec2.sh` sinh random vào `.env`. **Không đổi sau khi đã ký doc** — đổi là key cũ giải mã fail (phải xoá `backend/keys/` sinh lại, doc cũ thành invalid).

## 3. Tạo admin user đầu tiên

```bash
cd ~/citizen-portal/backend
source .venv/bin/activate

# Đăng ký admin qua API tạm thời chạy 1 lần, hoặc seed script.
# Cách nhanh: chạy uvicorn tạm, register rồi promote:
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
sleep 3
curl -s -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@portal.vn","password":"ChangeMe123","full_name":"Admin"}'
# Promote thành admin (enum lưu UPPERCASE trong DB):
sudo -u postgres psql -d citizen_portal -c \
  "UPDATE users SET role='ADMIN' WHERE email='admin@portal.vn';"
kill %1   # tắt uvicorn tạm
```

## 4. systemd — chạy backend như service

```bash
sudo cp ~/citizen-portal/deploy/citizen-portal-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now citizen-portal-api
sudo systemctl status citizen-portal-api      # phải thấy active (running)
sudo journalctl -u citizen-portal-api -n 30   # xem log nếu lỗi
```

Test backend cục bộ:
```bash
curl -s http://127.0.0.1:8000/ping
curl -s http://127.0.0.1:8000/ping/db
```

## 5. Build + deploy frontend

Trên máy C (hoặc trên EC2 nếu cài node):
```bash
# C build với API base URL rỗng (same-origin qua nginx)
echo "VITE_API_BASE_URL=" > .env.production
npm run build      # tạo dist/
```

Copy `dist/` lên EC2:
```bash
scp -i key.pem -r dist ubuntu@<EC2_IP>:~/frontend-dist
# Trên EC2:
sudo mkdir -p /var/www/citizen-portal
sudo cp -r ~/frontend-dist/* /var/www/citizen-portal/
```

## 6. Nginx

```bash
sudo cp ~/citizen-portal/deploy/nginx-citizen-portal.conf \
  /etc/nginx/sites-available/citizen-portal
sudo ln -sf /etc/nginx/sites-available/citizen-portal \
  /etc/nginx/sites-enabled/citizen-portal
sudo rm -f /etc/nginx/sites-enabled/default
```

## 7. TLS

Không có domain (chỉ IP) → self-signed:
```bash
sudo ~/citizen-portal/deploy/tls-selfsigned.sh
```

Có domain (vd DuckDNS) → Let's Encrypt:
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d <your-domain>
```

Rồi:
```bash
sudo nginx -t                    # test config OK
sudo systemctl reload nginx
```

## 8. Verify end-to-end

Từ browser máy bạn:
- `https://<EC2_IP>/` → frontend login page (bỏ qua cảnh báo self-signed)
- Login admin → upload → sign → QR → scan QR (phone) → `/verify` hiển thị ✅

Từ terminal:
```bash
curl -k https://<EC2_IP>/ping
curl -k https://<EC2_IP>/verify?d=<doc_id>
```

## 9. Cập nhật code sau này

```bash
cd ~/citizen-portal && git pull        # hoặc scp tar mới
sudo systemctl restart citizen-portal-api
# nếu đổi frontend: rebuild + copy dist + reload nginx
```

---

## Troubleshooting

| Triệu chứng | Nguyên nhân | Fix |
|---|---|---|
| `502 Bad Gateway` | uvicorn không chạy | `sudo systemctl status citizen-portal-api` + xem journalctl |
| `/ping/db` lỗi 503 | DB chưa chạy / sai pass | `sudo systemctl status postgresql`, check `.env` DATABASE_URL |
| Frontend trắng trang | dist/ chưa copy / sai path | check `/var/www/citizen-portal/index.html` tồn tại |
| API 404 từ frontend | nginx location regex thiếu prefix | thêm prefix vào `location ~ ^/(...)` |
| CORS error | đang gọi cross-origin | đảm bảo frontend build với `VITE_API_BASE_URL=` rỗng (same-origin) |
| Upload PDF fail 413 | nginx `client_max_body_size` thấp | đã set 12M, tăng nếu cần |

## Checklist deploy hoàn tất

- [ ] EC2 chạy, Security Group mở 22/80/443
- [ ] `setup-ec2.sh` chạy xong, DB + .env OK
- [ ] liboqs build OK (log thấy "Falcon-512 available")
- [ ] `.env` có `KEY_PASSPHRASE` (random, chmod 600)
- [ ] Admin user tạo + promote
- [ ] `citizen-portal-api` service active (running)
- [ ] `/ping` + `/ping/db` trả ok
- [ ] Sign 1 doc test → verify ✅ valid (xác nhận FALCON + key giải mã chạy trên EC2)
- [ ] Frontend dist/ copy vào /var/www
- [ ] Nginx config + symlink + `nginx -t` pass
- [ ] TLS cert tạo, reload nginx
- [ ] Browser vào `https://<IP>/` thấy login
- [ ] Full demo flow chạy được trên EC2
