#!/bin/bash

# Ждем, пока база данных будет готова
echo "🚀 Запуск BabyCareBot..."

# Проверяем наличие переменных окружения
if [ -z "$API_ID" ] || [ -z "$API_HASH" ] || [ -z "$BOT_TOKEN" ]; then
    echo "❌ Ошибка: Не установлены переменные окружения API_ID, API_HASH или BOT_TOKEN"
    exit 1
fi

echo "✅ Переменные окружения настроены"
echo "🔧 Инициализация базы данных..."

# Запускаем бота
exec python main.py
