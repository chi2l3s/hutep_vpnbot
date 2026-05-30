#!/usr/bin/env bash
# HutepVPN Bot — Deploy Script
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

fix_ports() {
    local http_port=80
    local https_port=443

    if ss -tlnp 2>/dev/null | grep -q ':80\s'; then
        for svc in AdGuardHome apache2 nginx; do
            if systemctl is-active --quiet $svc 2>/dev/null; then
                warn "$svc using port 80. Stopping..."
                systemctl stop $svc 2>/dev/null || true
                systemctl disable $svc 2>/dev/null || true
            fi
        done
        sleep 1
    fi

    if ss -tlnp 2>/dev/null | grep -q ':80\s'; then
        warn "Port 80 still occupied. Using 8080/8443."
        http_port=8080
        https_port=8443
        sed -i "s/- \"80:80\"/- \"${http_port}:80\"/" docker-compose.yml 2>/dev/null || true
        sed -i "s/- \"443:443\"/- \"${https_port}:443\"/" docker-compose.yml 2>/dev/null || true
    fi
}

check() {
    if ! command -v docker &>/dev/null; then
        error "Docker not installed. Run: curl -fsSL https://get.docker.com | sh"
    fi
    if ! $DC version &>/dev/null; then
        error "Docker Compose not found."
    fi
    if ! docker info &>/dev/null; then
        error "Docker daemon not running. Run: systemctl start docker"
    fi
    if [ ! -f .env ]; then
        error ".env not found. Run: ./scripts/install.sh"
    fi
}

build() {
    info "Building images..."
    $DC build --no-cache bot
    success "Bot image built"
}

start() {
    info "Starting containers..."
    fix_ports
    $DC up -d --remove-orphans
    sleep 2
    if $DC ps | grep -q "Up"; then
        success "Bot is running!"
    else
        error "Bot failed. Check: $DC logs bot"
    fi
}

restart_bot() {
    info "Restarting bot..."
    $DC restart bot
    success "Bot restarted"
}

logs() {
    $DC logs --tail=100 -f bot
}

status_cmd() {
    $DC ps
    echo
    $DC logs --tail=10 bot
}

stop_cmd() {
    info "Stopping containers..."
    $DC down
    success "Containers stopped"
}

pull_update() {
    info "Pulling updates..."
    git pull
    $DC build --pull bot
    $DC up -d --remove-orphans
    success "Update applied"
}

usage() {
    cat <<EOF
Usage: ./scripts/deploy.sh <command>

Commands:
  start     Build (if needed) and start containers
  build     Build bot image
  restart   Restart bot container
  stop      Stop and remove containers
  logs      Follow bot logs (Ctrl+C to exit)
  status    Container status + last logs
  shell     Enter bot container (bash)
  pull      git pull + rebuild + restart

Examples:
  ./scripts/deploy.sh start
  ./scripts/deploy.sh logs
EOF
}

COMMAND="${1:-}"

case "$COMMAND" in
    start)   check; build; start ;;
    build)   check; build ;;
    restart)  check; restart_bot ;;
    stop)    stop_cmd ;;
    logs)    logs ;;
    status)  status_cmd ;;
    shell)   $DC exec bot /bin/bash ;;
    pull)    check; pull_update ;;
    help|--help|-h|"") usage ;;
    *)       error "Unknown command: $COMMAND. Run: ./scripts/deploy.sh help" ;;
esac