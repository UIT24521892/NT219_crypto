#!/usr/bin/env bash
#
# tls-selfsigned.sh — sinh self-signed TLS cert cho demo.
#
# Dùng khi EC2 chỉ có IP công khai (không có domain → Let's Encrypt không cấp được).
# Browser sẽ cảnh báo "Not secure" — click "Advanced > Proceed" để vào (chấp nhận
# được cho demo môn học).
#
# Nếu CÓ domain (vd qua DuckDNS): dùng certbot thay vì script này:
#   sudo apt install certbot python3-certbot-nginx
#   sudo certbot --nginx -d your-domain.duckdns.org
#
# Chạy:
#   chmod +x deploy/tls-selfsigned.sh
#   sudo deploy/tls-selfsigned.sh
set -euo pipefail

CERT_DIR=/etc/ssl/citizen-portal
DAYS=365

# Lấy public IP của EC2 (để nhét vào SAN cho đỡ warning)
PUBLIC_IP=$(curl -s --max-time 3 http://169.254.169.254/latest/meta-data/public-ipv4 || echo "127.0.0.1")

echo "==> Sinh self-signed cert cho IP: $PUBLIC_IP"

sudo mkdir -p "$CERT_DIR"

sudo openssl req -x509 -nodes \
    -newkey rsa:2048 \
    -keyout "$CERT_DIR/privkey.pem" \
    -out "$CERT_DIR/fullchain.pem" \
    -days "$DAYS" \
    -subj "/C=VN/ST=HCM/L=HCMC/O=UIT/OU=NT219/CN=$PUBLIC_IP" \
    -addext "subjectAltName=IP:$PUBLIC_IP,DNS:localhost"

sudo chmod 600 "$CERT_DIR/privkey.pem"
sudo chmod 644 "$CERT_DIR/fullchain.pem"

echo "==> Done. Cert tại $CERT_DIR/"
echo "    fullchain.pem + privkey.pem"
echo "==> Reload nginx: sudo systemctl reload nginx"
