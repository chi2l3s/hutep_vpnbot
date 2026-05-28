#!/bin/bash
# HutepVPN Bot - Setup Script
# Usage: bash setup.sh

set -e

echo "=========================================="
echo "  HutepVPN Bot - Setup Script"
echo "=========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root (sudo bash setup.sh)${NC}"
    exit 1
fi

# Vars
BOT_DIR="/opt/hutep_vpnbot"
BOT_PORT=8080
NGINX_PORT=2087

echo -e "${GREEN}[1/8] Updating system...${NC}"
apt update && apt install -y python3 python3-pip python3-venv git nginx certbot python3-certbot-nginx curl

echo -e "${GREEN}[2/8] Stopping existing services...${NC}"
systemctl stop hutep-vpn-bot 2>/dev/null || true
systemctl stop nginx 2>/dev/null || true

echo -e "${GREEN}[3/8] Cloning repo...${NC}"
if [ -d "$BOT_DIR" ]; then
    echo "Repo already exists, pulling latest..."
    cd $BOT_DIR && git pull
else
    git clone https://github.com/chi2l3s/hutep_vpnbot.git $BOT_DIR
fi

echo -e "${GREEN}[4/8] Setting up venv and installing deps...${NC}"
cd $BOT_DIR
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt -q

echo -e "${GREEN}[5/8] Creating .env file...${NC}"
if [ ! -f "$BOT_DIR/.env" ]; then
    cat > $BOT_DIR/.env << 'EOF'
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
XUI_API_URL=http://localhost:20561
XUI_API_KEY=YOUR_XUI_API_KEY_HERE
DATABASE_URL=sqlite+aiosqlite:///./data/hutep_vpn.db
NOWPAYMENTS_API_KEY=
NOWPAYMENTS_WEBHOOK_SECRET=
REFERRAL_BONUS_DAYS=7
ADMIN_IDS=
WEBHOOK_HOST=https://bot.mylumina.ru
WEBHOOK_PATH=/webhook
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=8080
EOF
    echo -e "${YELLOW}Please edit $BOT_DIR/.env with your actual values!${NC}"
fi

echo -e "${GREEN}[6/8] Initializing database...${NC}"
mkdir -p $BOT_DIR/data
source venv/bin/activate
python3 -c "import asyncio; from bot.db import init_db; asyncio.run(init_db())" 2>/dev/null || true

echo -e "${GREEN}[7/8] Setting up nginx...${NC}"
# Temporary nginx config (no SSL yet)
cat > /etc/nginx/sites-available/bot << 'EOF'
server {
    server_name bot.mylumina.ru;
    listen 80;

    location /webhook {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
EOF

rm -f /etc/nginx/sites-enabled/default
ln -sf /etc/nginx/sites-available/bot /etc/nginx/sites-enabled/
nginx -t && systemctl start nginx

echo -e "${GREEN}[8/8] Getting SSL certificate...${NC}"
certbot --nginx -d bot.mylumina.ru --non-interactive --redirect --agree-tos -m admin@mylumina.ru 2>/dev/null || echo "SSL failed, will retry later"

# Update nginx config to use SSL on port 2087
cat > /etc/nginx/sites-available/bot << 'EOF'
server {
    server_name bot.mylumina.ru;

    location /webhook {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        return 404;
    }

    listen 2087 ssl;
    ssl_certificate /etc/letsencrypt/live/bot.mylumina.ru/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/bot.mylumina.ru/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}
EOF

# Add iptables redirect 443 -> nginx (2087)
if ! iptables -t nat -C PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 2087 2>/dev/null; then
    iptables -t nat -A PREROUTING -p tcp --dport 443 -j REDIRECT --to-port 2087
fi
if ! iptables -t nat -C PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 2087 2>/dev/null; then
    iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 2087
fi

# Save iptables rules
iptables-save > /etc/iptables/rules.v4 2>/dev/null || true

# Create systemd service
cat > /etc/systemd/system/hutep-vpn-bot.service << 'EOF'
[Unit]
Description=HutepVPN Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/hutep_vpnbot
ExecStart=/opt/hutep_vpnbot/venv/bin/python -m bot.main
Restart=always

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable hutep-vpn-bot
systemctl start hutep-vpn-bot

echo ""
echo -e "${GREEN}=========================================="
echo "  Setup Complete!"
echo "=========================================="
echo ""
echo -e "${GREEN}Next steps:${NC}"
echo "1. Edit $BOT_DIR/.env with your actual values"
echo "2. Restart bot: systemctl restart hutep-vpn-bot"
echo "3. Check status: systemctl status hutep-vpn-bot"
echo "4. Check webhook: curl -s https://bot.mylumina.ru/webhook"
echo ""