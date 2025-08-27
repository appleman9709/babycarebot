# BabyCareBot - Telegram Bot для ухода за малышом

## 🔐 Настройка безопасности

### Важно! Никогда не храните секретные данные в коде!

Все API ключи и токены должны храниться только в переменных окружения или `.env` файле.

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone <your-repo-url>
cd BabyCareBot
```

### 2. Настройка переменных окружения
Скопируйте `env.example` в `.env` и заполните вашими данными:

```bash
cp env.example .env
```

Отредактируйте `.env` файл:
```env
# Telegram Bot API credentials
API_ID=YOUR_API_ID_HERE
API_HASH=YOUR_API_HASH_HERE
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# Database settings
DATABASE_URL=sqlite:///data/babybot.db

# Logging
LOG_LEVEL=INFO

# Scheduler settings
FEEDING_CHECK_INTERVAL=30
TIPS_CHECK_INTERVAL=1
```

### 3. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 4. Запуск бота
```bash
python main.py
```

## 🔑 Получение Telegram API данных

### 1. API_ID и API_HASH
1. Перейдите на [my.telegram.org](https://my.telegram.org)
2. Войдите в свой аккаунт
3. Перейдите в "API development tools"
4. Создайте новое приложение
5. Скопируйте `api_id` и `api_hash`

### 2. BOT_TOKEN
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

## 🛡️ Безопасность

### ✅ Что делать:
- Хранить секреты в `.env` файле
- Добавить `.env` в `.gitignore`
- Использовать переменные окружения на сервере

### ❌ Что НЕ делать:
- Хранить секреты в коде
- Коммитить `.env` файл в репозиторий
- Публиковать токены в открытом доступе

## 🌍 Развертывание

### Render
1. Создайте новый Web Service
2. Подключите GitHub репозиторий
3. Установите переменные окружения в Render Dashboard
4. Убедитесь, что `.env` не попадает в репозиторий

### Docker
```bash
docker build -t babycarebot .
docker run -e API_ID=xxx -e API_HASH=xxx -e BOT_TOKEN=xxx babycarebot
```

## 📁 Структура проекта

```
BabyCareBot/
├── main.py              # Основной код бота
├── requirements.txt      # Зависимости Python
├── .env                 # Переменные окружения (НЕ в репозитории!)
├── env.example          # Пример переменных окружения
├── .gitignore          # Исключения Git
├── README.md           # Этот файл
└── data/               # Данные и советы
    └── advice.csv      # CSV с советами
```

## 🆘 Устранение неполадок

### Ошибка "Не все необходимые переменные окружения установлены"
- Проверьте наличие `.env` файла
- Убедитесь, что все переменные заполнены
- Проверьте правильность значений

### Ошибка "API_ID должен быть числом"
- Убедитесь, что API_ID содержит только цифры
- Уберите кавычки вокруг значения

### Ошибка "Bot token expired"
- Получите новый токен у @BotFather
- Обновите переменную BOT_TOKEN

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи бота
2. Убедитесь в правильности переменных окружения
3. Проверьте статус бота в @BotFather

---

**⚠️ ВАЖНО: Никогда не публикуйте секретные данные!**
