#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
# HutepVPN Bot — Deploy Script
# Быстрый деплой на VPS: собирает и запускает Docker-стек
# ─────────────────────────────────────────────────────────────
set -euo pipefail

# ── Цвета ────────────────────────────────────────────────────
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
CYAN='\\033[0;36m'
NC='\\033[0m' # No Color

info()    { echo -e \"${CYAN}[INFO]${NC} $1\"; }
success() { echo -e \"${GREEN}[OK]${NC} $1\"; }
warn()    { echo -e \"${YELLOW}[WARN]${NC} $1\"; }
error()   { echo -e \"${RED}[ERROR]${NC} $1\"; exit 1; }

# ── Проверки ──────────────────────────────────────────────────
check() {
    command -v docker &>/dev/null || error \"Docker не установлен. Установите Docker: https://docs.docker.com/engine/install/\"
    command -v docker compose &>/dev/null || error \"Docker Compose не найден. Установите Docker Compose Plugin.\"
    [[ -f .env ]] || error \".env не найден. Скопируйте .env.example в .env и заполните переменные.\"
    grep -q \"BOT_TOKEN=\" .env && grep -q \"WEBHOOK_HOST=\" .env \
        || error \".env должен содержать BOT_TOKEN и WEBHOOK_HOST\"
}

# ── Docker-слой ───────────────────────────────────────────────
build() {
    info \"Сборка образов...\"
    docker compose build --no-cache bot
    success \"Образ бота собран\"
}

start() {
    info \"Запуск контейнеров...\"
    docker compose up -d --remove-orphans
    success \"Контейнеры запущены\"
}

restart_bot() {
    info \"Перезапуск бота...\"
    docker compose restart bot
    success \"Бот перезапущен\"
}

logs() {
    info \"Последние 100 строк логов бота:\"
    docker compose logs --tail=100 bot
}

status() {
    info \"Статус контейнеров:\"
    docker compose ps
    echo
    info \"Статус бота:\"
    docker compose logs --tail=5 bot
}

shell() {
    docker compose exec bot /bin/bash
}

stop() {
    info \"Остановка контейнеров...\"
    docker compose down
    success \"Стоп. Данные сохранены в Docker volume.\"
}

pull_update() {
    info \"Pull + rebuild...\"
    git pull
    docker compose build --pull bot
    docker compose up -d --remove-orphans
    success \"Обновление применено\"
}

# ── Help ──────────────────────────────────────────────────────
usage() {
    cat <<EOF
Использование: ./scripts/deploy.sh <команда>

Команды:
  build      Собрать Docker-образы
  start      Собрать (если нужно) и запустить
  restart    Перезапустить бота
  stop       Остановить контейнеры
  logs       Показать логи бота
  status     Статус контейнеров
  shell      Зайти в контейнер бота (bash)
  pull       git pull + rebuild + restart
  help       Показать эту справку

Пример:
  ./scripts/deploy.sh start
EOF
}

# ── Main ───────────────────────────────────────────────────────
COMMAND="${1:-help}"

case "$COMMAND" in
    build)   check; build ;;
    start)   check; build; start ;;
    restart) check; restart_bot ;;
    stop)    stop ;;
    logs)    logs ;;
    status)  status ;;
    shell)   shell ;;
    pull)    pull_update ;;
    help)    usage ;;
    *)       error \"Неизвестная команда: $COMMAND. Используйте: ./scripts/deploy.sh help\" ;;
esac
