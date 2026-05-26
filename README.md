# HutepVPN Telegram Bot 🤖

Telegram-бот для управления VPN-подписками с личным кабинетом, платежами (Telegram Stars + криптовалюта) и реферальной системой.

## Возможности

- 🖥 **Личный кабинет** — управление подпиской и профилем
- 🔐 **VPN профили** — автоматическая выдача VLESS-конфигов через X-UI API
- 💳 **Оплата** — Telegram Stars (XTR) и криптовалюта (NOWPayments)
- 👥 **Реферальная система** — +7 дней каждому за приглашение друга
- 📊 **Подписки** — 4 тарифных плана (30/90/180/360 дней)

## Тарифы

| Период | Цена | Цена/день |
|--------|------|-----------|
| 30 дней | 70₽ | 2.33₽ |
| 90 дней | 190₽ | 2.11₽ |
| 180 дней | 350₽ | 1.94₽ |
| 360 дней | 600₽ | 1.67₽ |

## Стек

- **Python 3.11+**
- **Aiogram 3** — асинхронный Telegram Bot Framework
- **SQLAlchemy + aiosqlite** — база данных
- **FastAPI/uvicorn** — webhook-сервер
- **X-UI API** — управление VPN

## Установка

### 1. Клонирование и зависимости

```bash
cd hutep_vpnbot
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 2. Конфигурация

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
BOT_TOKEN=your_telegram_bot_token
XUI_API_URL=http://your_vps_ip:20561
XUI_API_KEY=your_xui_api_key
XUI_USE_TLS=false
DATABASE_URL=sqlite+aiosqlite:///./data/hutep_vpn.db
NOWPAYMENTS_API_KEY=your_nowpayments_api_key
NOWPAYMENTS_WEBHOOK_SECRET=your_webhook_secret
ADMIN_IDS=123456789
REFERRAL_BONUS_DAYS=7
```

### 3. Запуск

**Режим разработки (polling):**
```bash
python -m bot.main
```

**Production (webhook):**
```env
WEBHOOK_HOST=https://your_domain.com
WEBHOOK_PATH=/webhook
WEBAPP_HOST=0.0.0.0
WEBAPP_PORT=8080
```
```bash
python -m bot.main
```

## Структура проекта

```
hutep_vpnbot/
├── bot/
│   ├── __init__.py
│   ├── main.py              # Точка входа
│   ├── config.py            # Конфигурация
│   ├── db/
│   │   ├── database.py
│   │   └── models.py        # SQLAlchemy модели
│   ├── handlers/
│   │   ├── start.py         # /start
│   │   ├── menu.py          # Меню и профиль
│   │   ├── subscription.py  # Оформление подписки
│   │   ├── payment.py       # Платежи (Stars)
│   │   └── referral.py      # Реферальная система
│   ├── keyboards/
│   │   └── inline.py        # Inline-клавиатуры
│   └── services/
│       ├── xui_service.py   # X-UI API клиент
│       ├── payment_service.py
│       ├── vpn_service.py
│       └── referral_service.py
├── data/                    # База данных SQLite
├── .env.example
├── requirements.txt
└── README.md
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Приветствие и регистрация |
| `/menu` | Главное меню |
| `/help` | Справка |
| `/subscribe` | Оформление подписки |
| `/referral` | Реферальная программа |

## Платежи

### Telegram Stars
Автоматическая интеграция через Bot API. При оплате:
1. Бот отправляет invoice
2. Пользователь оплачивает Stars
3. Подписка активируется автоматически

### Криптовалюта (NOWPayments)
1. Пользователь выбирает крипту
2. Бот создаёт invoice в NOWPayments
3. Пользователь оплачивает
4. NOWPayments отправляет webhook → подписка активируется

## Реферальная система

- Каждый пользователь получает уникальный код при регистрации
- При покупке реферала → оба получают **+7 дней**
- Бонус начисляется автоматически через webhook или после оплаты

## X-UI Integration

Бот взаимодействует с X-UI панелью для:
- Создания VPN-клиентов (VLESS)
- Генерации ссылок для подключения
- Удаления клиентов при деактивации

## Деплой

### Systemd (Linux)

```ini
[Unit]
Description=HutepVPN Bot
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/hutep_vpnbot
ExecStart=/opt/hutep_vpnbot/venv/bin/python -m bot.main
Restart=always

[Install]
WantedBy=multi-user.target
```

### Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "-m", "bot.main"]
```

## Поддержка

- Telegram: @HutepVPNSupport
- Email: support@hutervpn.example.com

---

**HutepVPN** 🛡️ — Надёжная защита вашего интернета