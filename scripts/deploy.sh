#!/usr/bin/env bash
# HutepVPN Bot — Deploy Script
set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
error()   { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# Check prerequisites
check() {
    if ! command -v docker &>/dev/null; then
        error "Docker not installed. See: https://docs.docker.com/engine/install/"
    fi
    if ! docker compose version &>/dev/null && ! docker-compose version &>/dev/null; then
        error "Docker Compose not found. Install Docker Compose Plugin."
    fi
    if [ ! -f .env ]; then
        error ".env not found. Copy .env.example to .env and fill it."
    fi
}

# Get docker compose command
get_docker_compose() {
    if docker compose version &>/dev/null; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

DC=$(get_docker_compose)

build() {
    info "Building images..."
    $DC build --no-cache bot
    success "Bot image built"
}

start() {
    info "Starting containers..."
    $DC up -d --remove-orphans
    success "Containers started"
}

restart_bot() {
    info "Restarting bot..."
    $DC restart bot
    success "Bot restarted"
}

logs() {
    info "Last 100 log lines:"
    $DC logs --tail=100 bot
}

status_cmd() {
    info "Container status:"
    $DC ps
}

shell_bot() {
    $DC exec bot /bin/bash
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
  build      Build Docker images
  start      Build (if needed) and start
  restart    Restart bot
  stop       Stop containers
  logs       Show bot logs
  status     Container status
  shell      Enter bot container (bash)
  pull       git pull + rebuild + restart
  help       Show this help

Examples:
  ./scripts/deploy.sh start
  ./scripts/deploy.sh logs
  ./scripts/deploy.sh restart
EOF
}

COMMAND="${1:-help}"

case "$COMMAND" in
    build)   check; build ;;
    start)   check; build; start ;;
    restart) check; restart_bot ;;
    stop)    stop_cmd ;;
    logs)    logs ;;
    status)  status_cmd ;;
    shell)   shell_bot ;;
    pull)    pull_update ;;
    help|--help|-h) usage ;;
    *)       error "Unknown command: $COMMAND. Use: ./scripts/deploy.sh help" ;;
esac