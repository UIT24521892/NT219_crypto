#!/usr/bin/env bash
#
# setup-ec2.sh — bootstrap fresh Ubuntu 22.04 EC2 cho Citizen Services Portal.
#
# CHẠY VỚI QUYỀN sudo, user 'ubuntu', sau khi đã copy/clone code vào
#   /home/ubuntu/citizen-portal
#
# Usage:
#   chmod +x deploy/setup-ec2.sh
#   ./deploy/setup-ec2.sh
#
# Script này KHÔNG tự chạy backend — chỉ cài deps + DB. Phần systemd + nginx
# + TLS làm thủ công theo DEPLOY.md (để Trung kiểm soát từng bước).
set -euo pipefail

PROJECT_DIR=/home/ubuntu/citizen-portal
BACKEND_DIR="$PROJECT_DIR/backend"
DB_NAME=citizen_portal
DB_USER=portal_user

echo "════════════════════════════════════════════"
echo " Citizen Portal — EC2 bootstrap"
echo "════════════════════════════════════════════"

# ── 1. System packages ──
echo "==> [1/6] apt update + cài packages (gồm liboqs build deps)"
sudo apt-get update -y
sudo apt-get install -y \
    python3 python3-venv python3-dev \
    postgresql postgresql-contrib \
    nginx \
    git curl build-essential \
    cmake ninja-build libssl-dev
# cmake/ninja-build/libssl-dev: cần để liboqs (FALCON-512) tự build lúc import oqs lần đầu.

# ── 2. PostgreSQL: tạo DB + user ──
echo "==> [2/6] Setup PostgreSQL"
sudo systemctl enable --now postgresql

# Sinh password ngẫu nhiên cho DB
DB_PASS=$(openssl rand -hex 24)

# Tạo user + DB (idempotent — bỏ qua nếu đã có)
sudo -u postgres psql <<SQL
DO \$\$
BEGIN
   IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '$DB_USER') THEN
      CREATE ROLE $DB_USER LOGIN PASSWORD '$DB_PASS';
   ELSE
      ALTER ROLE $DB_USER PASSWORD '$DB_PASS';
   END IF;
END
\$\$;
SQL

sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname = '$DB_NAME'" \
    | grep -q 1 || sudo -u postgres createdb -O "$DB_USER" "$DB_NAME"

echo "    DB '$DB_NAME' + user '$DB_USER' ready."

# ── 3. Python venv + deps ──
echo "==> [3/6] Tạo venv + pip install"
cd "$BACKEND_DIR"
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

# Pre-build liboqs: lần `import oqs` đầu tiên tự build C lib (~2-5 phút).
# Làm ngay đây để request /sign đầu tiên không bị chậm/timeout.
echo "    Building liboqs (first import, ~2-5 phút, kiên nhẫn)..."
./.venv/bin/python -c "import oqs; assert 'Falcon-512' in oqs.get_enabled_sig_mechanisms(); print('    liboqs OK — Falcon-512 available')" \
    || echo "    ⚠ liboqs build/import lỗi — check cmake/ninja-build/libssl-dev đã cài đủ."

# ── 4. Tạo .env ──
echo "==> [4/6] Sinh .env"
JWT_SECRET=$(openssl rand -hex 32)
KEY_PASSPHRASE=$(openssl rand -hex 32)
cat > "$BACKEND_DIR/.env" <<ENV
DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASS@127.0.0.1:5432/$DB_NAME
JWT_SECRET=$JWT_SECRET
JWT_ALGORITHM=HS256
JWT_EXPIRES_MINUTES=60
UPLOAD_DIR=./storage/uploads
MAX_UPLOAD_SIZE_MB=10
QR_VALIDITY_DAYS=365
KEY_PASSPHRASE=$KEY_PASSPHRASE
ENV
chmod 600 "$BACKEND_DIR/.env"
echo "    .env tạo xong (DB pass + JWT secret + KEY_PASSPHRASE random, chmod 600)."
echo "    ⚠ KEY_PASSPHRASE dùng để mã hoá private key admin (AES-256-GCM)."
echo "      ĐỪNG đổi sau khi đã ký doc — đổi là key cũ giải mã không được."

# ── 5. Tạo schema (tables) ──
echo "==> [5/6] Tạo bảng DB"
# Backend tạo bảng tự động lúc startup (Base.metadata.create_all) HOẶC
# chạy thủ công nếu có script. Ở đây import models để tạo schema:
cd "$BACKEND_DIR"
./.venv/bin/python -c "
import asyncio
from app.database import Base, engine
from app import models  # noqa: F401  (đăng ký models)

async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('    Tables created.')

asyncio.run(init())
" || echo "    ⚠ Tạo bảng thất bại — check app.database có expose Base + engine."

# Sinh keypair trước khi systemd khởi động nhiều worker để tránh race lần đầu.
./.venv/bin/python -c "
from app.crypto.falcon_service import get_public_key
print(f'    FALCON server key ready ({len(get_public_key())} public-key bytes).')
"

# ── 6. Storage dir ──
echo "==> [6/6] Tạo storage/uploads"
mkdir -p "$BACKEND_DIR/storage/uploads"

echo ""
echo "════════════════════════════════════════════"
echo " ✅ Bootstrap xong. Bước tiếp (xem DEPLOY.md):"
echo "   1. Tạo admin user đầu tiên"
echo "   2. systemd: cp citizen-portal-api.service → enable"
echo "   3. nginx: cp config + symlink + reload"
echo "   4. TLS: chạy tls-selfsigned.sh"
echo "   5. Build frontend → copy dist/ vào /var/www/citizen-portal"
echo "════════════════════════════════════════════"
