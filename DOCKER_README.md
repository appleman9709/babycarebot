# 🐳 Docker развертывание BabyCareBot

## 📋 Требования

- Docker
- Docker Compose (для локального тестирования)
- Telegram Bot API credentials

## 🚀 Быстрый старт

### 1. Локальное тестирование с Docker Compose

```bash
# Клонируйте репозиторий
git clone <your-repo-url>
cd BabyCareBot-1.1

# Создайте файл .env с вашими данными
cp .env.example .env
# Отредактируйте .env файл

# Запустите контейнер
docker-compose up --build
```

### 2. Развертывание на Render

1. **Подключите репозиторий** к Render
2. **Создайте новый Web Service**
3. **Укажите переменные окружения:**
   - `API_ID` - ваш Telegram API ID
   - `API_HASH` - ваш Telegram API Hash
   - `BOT_TOKEN` - токен вашего бота
4. **Build Command:** `pip install -r requirements.txt`
5. **Start Command:** `python main.py`

## 🔧 Переменные окружения

Создайте файл `.env` в корне проекта:

```env
# Telegram Bot API credentials
API_ID=your_api_id_here
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here

# Database settings
DATABASE_URL=sqlite:///data/babybot.db

# Logging
LOG_LEVEL=INFO
```

## 📁 Структура проекта

```
BabyCareBot-1.1/
├── main.py                 # Основной код бота
├── requirements.txt        # Python зависимости
├── Dockerfile             # Docker образ
├── docker-compose.yml     # Локальное тестирование
├── render.yaml            # Конфигурация Render
├── docker-entrypoint.sh   # Скрипт запуска
├── .dockerignore          # Исключения для Docker
├── data/                  # Данные (советы, база)
│   └── advice.csv        # CSV с советами
└── DOCKER_README.md       # Эта документация
```

## 🐳 Docker команды

### Сборка образа
```bash
docker build -t babycare-bot .
```

### Запуск контейнера
```bash
docker run -d \
  --name babycare-bot \
  --env-file .env \
  -v $(pwd)/data:/app/data \
  babycare-bot
```

### Просмотр логов
```bash
docker logs -f babycare-bot
```

### Остановка контейнера
```bash
docker stop babycare-bot
docker rm babycare-bot
```

## 🔍 Отладка

### Проверка переменных окружения
```bash
docker exec babycare-bot env | grep -E "(API_|BOT_)"
```

### Проверка файлов в контейнере
```bash
docker exec babycare-bot ls -la /app
docker exec babycare-bot ls -la /app/data
```

### Подключение к контейнеру
```bash
docker exec -it babycare-bot /bin/bash
```

## ⚠️ Важные замечания

1. **База данных** создается в контейнере и монтируется в `./data/`
2. **Файл advice.csv** должен быть в директории `data/`
3. **Переменные окружения** обязательны для работы бота
4. **Порт 8000** открыт для совместимости с Render

## 🚀 Развертывание на Render

1. **Подключите GitHub репозиторий**
2. **Выберите ветку** (обычно `main` или `master`)
3. **Укажите переменные окружения** в настройках сервиса
4. **Дождитесь автоматической сборки и развертывания**

## 📊 Мониторинг

- **Логи** доступны в Render Dashboard
- **Статус** сервиса отображается в реальном времени
- **Автоматический перезапуск** при сбоях

## 🆘 Устранение неполадок

### Бот не отвечает
- Проверьте переменные окружения
- Убедитесь, что API_ID и API_HASH корректны
- Проверьте токен бота

### Ошибки базы данных
- Проверьте права доступа к директории `data/`
- Убедитесь, что SQLite может создавать файлы

### Проблемы с зависимостями
- Проверьте `requirements.txt`
- Убедитесь, что все пакеты совместимы

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи в Render Dashboard
2. Убедитесь в корректности переменных окружения
3. Проверьте статус Telegram Bot API
