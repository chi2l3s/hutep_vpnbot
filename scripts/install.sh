#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# HutepVPN Bot — Interactive Installer
# One-command deployment for fresh VPS
# Usage: ./scripts/install.sh
# ─────────────────────────────────────────────────────────────
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

get_dc() {
    docker compose version &>/dev/null && echo "docker compose" || echo "docker-compose"
}
DC=$(get_dc)

prompt() {
    local var="$1"
    local label="$2"
    local default="${3:-}"
    local value

    if [ -n "$default" ]; then
        read -p "$(echo -e "${CYAN}${label}${NC} [$default]: ")" value
        value="${value:-$default}"
    else
        read -p "$(echo -e "${CYAN}${label}${NC}: ")" value
    fi
    export "$var=$value"
}

prompt_pass() {
    local var="$1"
    local label="$2"
    local value
    read -sp "$(echo -e "${CYAN}${label}${NC}: ")" value
    echo
    export "$var=$value"
}

yesno() {
    local label="$1"
    local default="${2:-n}"
    local yn

    if [ "$default" = "y" ]; then
        read -p "$(echo -e "${CYAN}${label}${NC} [Y/n]: ")" yn
        yn="${yn:-y}"
    else
        read -p "$(echo -e "${CYAN}${label}${NC} [y/N]: ")" yn
        yn="${yn:-n}"
    fi

    [ "$yn" = "y" ] || [ "$yn" = "Y" ]
}

check_docker() {
    info "Checking prerequisites..."

    if ! command -v docker &>/dev/null; then
        warn "Docker not installed. Installing..."
        curl -fsSL https://get.docker.com | sh
        systemctl start docker
        systemctl enable docker
    fi

    if ! $DC version &>/dev/null; then
        apt-get update -qq
        apt-get install -y -qq docker-compose-plugin 2>/dev/null || \
        apt-get install -y -qq docker-compose 2>/dev/null || true
    fi

    if ! docker info &>/dev/null; then
        error "Docker daemon not running. Run: systemctl start docker"
    fi

    success "Docker: OK"
}

stop_conflicts() {
    info "Checking for conflicting services..."

    for svc in AdGuardHome apache2 nginx; do
        if systemctl is-active --quiet $svc 2>/dev/null; then
            if yesno "$svc detected on port 80. Stop it?" "y"; then
                systemctl stop $svc 2>/dev/null || true
                systemctl disable $svc 2>/dev/null || true
                success "$svc stopped"
            fi
        fi
    done

    if ss -tlnp 2>/dev/null | grep -q ':80\s'; then
        warn "Port 80 still in use. Will use 8080/8443."
        HTTP_PORT=8080
        HTTPS_PORT=8443
    else
        HTTP_PORT=80
        HTTPS_PORT=443
    fi
}

collect_settings() {
    info "Collecting settings..."
    echo

    echo -e "${YELLOW}=== Telegram ===${NC}"
    prompt BOT_TOKEN "Telegram Bot Token (from @BotFather)"

    echo
    echo -e "${YELLOW}=== X-UI Panel ===${NC}"
    prompt XUI_API_URL "X-UI URL (e.g. https://vpn.example.com:48291/cPQ3oKGCuGtngvqGOx/panel/api)"
    prompt XUI_API_KEY "X-UI API Key (Settings → Security → API Token)"

    IP=$(hostname -I 2>/dev/null | awk '{print $1}')
    prompt XUI_SUB_BASE_URL "Subscription Base URL" "https://${IP}:2096"

    echo
    echo -e "${YELLOW}=== Admin ===${NC}"
    prompt ADMIN_IDS "Your Telegram ID (from @userinfobot)" ""

    echo
    echo -e "${YELLOW}=== NOWPayments (optional) ===${NC}"
    prompt NOWPAYMENTS_API_KEY "NOWPayments API Key (leave empty to skip)" ""

    echo
    echo -e "${YELLOW}=== Domain / SSL ===${NC}"
    prompt DOMAIN "Domain name (leave empty to skip SSL)" ""

    if [ -n "$DOMAIN" ]; then
        prompt EMAIL "Email for Let's Encrypt" "admin@$DOMAIN"
        HAS_DOMAIN="yes"
    else
        HAS_DOMAIN="no"
    fi
}

generate_env() {
    info "Generating .env..."

    if [ "$HAS_DOMAIN" = "yes" ]; then
        WEBHOOK_HOST="https://$DOMAIN"
    elif [ -n "$IP" ]; then
        WEBHOOK_HOST="http://${IP}:${HTTP_PORT}"
    else
        WEBHOOK_HOST=""
    fi

    cat > .env <<EOF
# HutepVPN Bot Configuration

# === Telegram ===
BOT_TOKEN=$BOT_TOKEN

# === X-UI ===
XUI_API_URL=$XUI_API_URL
XUI_API_KEY=$XUI_API_KEY
XUI_USE_TLS=false

# === Subscription ===
XUI_SUB_BASE_URL=$XUI_SUB_BASE_URL
XUI_SUB_PATH=/sub/

# === Database ===
DATABASE_URL=sqlite+aiosqlite:///./data/hutep_vpn.db

# === NOWPayments ===
NOWPAYMENTS_API_KEY=$NOWPAYMENTS_API_KEY
NOWPAYMENTS_WEBHOOK_SECRET=
NOWPAYMENTS_SANDBOX=false

# === Referral ===
REFERRAL_BONUS_DAYS=7

# === Admin ===
ADMIN_IDS=$ADMIN_IDS

# === Webhook ===
WEBHOOK_HOST=$WEBHOOK_HOST
WEBHOOK_PATH=/webhook
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=8080
EOF

    success ".env created"
}

setup_ssl() {
    info "Setting up SSL..."

    mkdir -p nginx/ssl

    if [ "$HAS_DOMAIN" = "yes" ]; then
        if command -v certbot &>/dev/null; then
            certbot certonly --nginx -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" 2>/dev/null || \
            certbot certonly --webroot -w /var/www/certbot -d "$DOMAIN" --non-interactive --agree-tos -m "$EMAIL" 2>/dev/null || {
                warn "Certbot failed. Using HTTP only."
                HAS_DOMAIN="no"
            }
        else
            warn "Certbot not found. Install: apt install certbot python3-certbot-nginx"
            HAS_DOMAIN="no"
        fi
    fi

    if [ "$HAS_DOMAIN" = "yes" ]; then
        cp /etc/letsencrypt/live/$DOMAIN/fullchain.pem nginx/ssl/cert.pem 2>/dev/null || true
        cp /etc/letsencrypt/live/$DOMAIN/privkey.pem nginx/ssl/key.pem 2>/dev/null || true
    else
        if [ ! -f nginx/ssl/cert.pem ]; then
            openssl req -x509 -nodes -newkey rsa:2048 \
                -keyout nginx/ssl/key.pem \
                -out nginx/ssl/cert.pem \
                -subj "/CN=localhost" \
                -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" 2>/dev/null || true
        fi
    fi

    if [ "$HTTP_PORT" != "80" ]; then
        sed -i "s/- \"80:80\"/- \"${HTTP_PORT}:80\"/" docker-compose.yml 2>/dev/null || true
        sed -i "s/- \"443:443\"/- \"${HTTPS_PORT}:443\"/" docker-compose.yml 2>/dev/null || true
    fi

    success "SSL configured"
}

build_start() {
    info "Building Docker images..."
    $DC build --no-cache bot
    success "Image built"

    info "Starting containers..."
    $DC up -d --remove-orphans
    sleep 3

    if $DC ps | grep -q "Up"; then
        success "Bot is running!"
        echo
        $DC ps
        echo
        info "Last logs:"
        $DC logs --tail=20 bot
    else
        error "Bot failed. Check: $DC logs bot"
    fi
}

main() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════╗"
    echo "║       HutepVPN Bot — Interactive Installer      ║"
    echo "╚══════════════════════════════════════════════════╝"
    echo -e "${NC}"

    cd "$(dirname "$0")/.."

    if [ "$(id -u)" -ne 0 ]; then
        warn "Not running as root. Some operations may fail."
    fi

    if [ -f .env ]; then
        if yesno ".env already exists. Overwrite?" "n"; then
            cp .env .env.backup.$(date +%Y%m%d%H%M%S)
            info "Backup created"
        else
            info "Keeping existing .env"
            if yesno "Build and start bot?" "y"; then
                check_docker
                stop_conflicts
                build_start
            fi
            exit 0
        fi
    fi

    check_docker
    stop_conflicts
    collect_settings
    generate_env
    setup_ssl

    if yesno "Build and start bot now?" "y"; then
        build_start
    else
        success "Configuration saved to .env"
        info "Run: ./scripts/deploy.sh start"
    fi

    echo
    echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  HutepVPN Bot installed!${NC}"
    echo -e "${GREEN}══════════════════════════════════════════════════════════${NC}"
    echo
    echo -e "  ${CYAN}Manage:${NC}"
    echo -e "    ./scripts/deploy.sh logs     — View logs"
    echo -e "    ./scripts/deploy.sh restart  — Restart bot"
    echo -e "    ./scripts/deploy.sh stop     — Stop bot"
    echo
}

main "$@"
