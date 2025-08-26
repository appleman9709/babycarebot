
from telethon import TelegramClient, events, Button
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import asyncio
import sqlite3
import random
import threading
import time
import http.server
import socketserver
import pytz

# Конфигурация (замените на ваши данные)
import os
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

# Получаем данные из переменных окружения или используем значения по умолчанию
API_ID = int(os.getenv('API_ID', '25723882'))
API_HASH = os.getenv('API_HASH', '151124efbbbe8c1b47db84955e4f1ae5')
BOT_TOKEN = os.getenv('BOT_TOKEN', '8481307424:AAEX7XN6DtLxra3vR1Y2Q60NZ6AgvxQJ96k')  # Новый токен

# Проверяем наличие токена
if not BOT_TOKEN:
    print("❌ ОШИБКА: BOT_TOKEN не установлен!")
    print("📝 Получите новый токен у @BotFather и установите переменную окружения BOT_TOKEN")
    print("🔧 Или добавьте токен прямо в код (не рекомендуется для продакшена)")
    exit(1)

# Функция для получения тайского времени
def get_thai_time():
    """Получить текущее время в тайском часовом поясе"""
    thai_tz = pytz.timezone('Asia/Bangkok')
    utc_now = datetime.now(pytz.UTC)
    thai_now = utc_now.astimezone(thai_tz)
    return thai_now

def get_thai_date():
    """Получить текущую дату в тайском часовом поясе"""
    return get_thai_time().date()

client = TelegramClient('babybot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    
    # Создание таблиц (если их нет)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS families (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS family_members (
            family_id INTEGER,
            user_id INTEGER,
            role TEXT DEFAULT 'Родитель',
            name TEXT DEFAULT 'Неизвестно',
            FOREIGN KEY (family_id) REFERENCES families (id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS feedings (
            id INTEGER PRIMARY KEY,
            family_id INTEGER,
            author_id INTEGER,
            timestamp TEXT NOT NULL,
            author_role TEXT DEFAULT 'Родитель',
            author_name TEXT DEFAULT 'Неизвестно',
            FOREIGN KEY (family_id) REFERENCES families (id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS diapers (
            id INTEGER PRIMARY KEY,
            family_id INTEGER,
            author_id INTEGER,
            timestamp TEXT NOT NULL,
            author_role TEXT DEFAULT 'Родитель',
            author_name TEXT DEFAULT 'Неизвестно',
            FOREIGN KEY (family_id) REFERENCES families (id)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            family_id INTEGER,
            feed_interval INTEGER DEFAULT 3,
            diaper_interval INTEGER DEFAULT 2,
            tips_enabled INTEGER DEFAULT 1,
            tips_time_hour INTEGER DEFAULT 9,
            tips_time_minute INTEGER DEFAULT 0,
            FOREIGN KEY (family_id) REFERENCES families (id)
        )
    """)
    
    # Добавляем новые колонки к существующей таблице settings, если их нет
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN tips_time_hour INTEGER DEFAULT 9")
        print("✅ Добавлена колонка tips_time_hour")
    except sqlite3.OperationalError:
        print("ℹ️ Колонка tips_time_hour уже существует")
    
    try:
        cur.execute("ALTER TABLE settings ADD COLUMN tips_time_minute INTEGER DEFAULT 0")
        print("✅ Добавлена колонка tips_time_minute")
    except sqlite3.OperationalError:
        print("ℹ️ Колонка tips_time_minute уже существует")
    
    # Обновляем существующие записи, устанавливая значения по умолчанию
    cur.execute("UPDATE settings SET tips_time_hour = 9 WHERE tips_time_hour IS NULL")
    cur.execute("UPDATE settings SET tips_time_minute = 0 WHERE tips_time_minute IS NULL")
    
    # Миграция таблиц feedings и diapers
    try:
        # Проверяем, есть ли колонка family_id в таблице feedings
        cur.execute("PRAGMA table_info(feedings)")
        columns = [col[1] for col in cur.fetchall()]
        
        if 'family_id' not in columns:
            print("🔄 Мигрируем таблицу feedings...")
            # Создаем временную таблицу с новой структурой
            cur.execute("""
                CREATE TABLE feedings_new (
                    id INTEGER PRIMARY KEY,
                    family_id INTEGER,
                    author_id INTEGER,
                    timestamp TEXT NOT NULL,
                    author_role TEXT DEFAULT 'Родитель',
                    author_name TEXT DEFAULT 'Неизвестно',
                    FOREIGN KEY (family_id) REFERENCES families (id)
                )
            """)
            
            # Копируем данные из старой таблицы
            cur.execute("SELECT id, user_id, timestamp FROM feedings")
            old_data = cur.fetchall()
            
            for row in old_data:
                # Для каждой записи создаем временную семью
                temp_family_id = create_family(f"Миграция {row[0]}", row[1])
                cur.execute("INSERT INTO feedings_new (family_id, author_id, timestamp, author_role, author_name) VALUES (?, ?, ?, ?, ?)",
                           (temp_family_id, row[1], row[2], 'Родитель', 'Неизвестно'))
            
            # Удаляем старую таблицу и переименовываем новую
            cur.execute("DROP TABLE feedings")
            cur.execute("ALTER TABLE feedings_new RENAME TO feedings")
            print("✅ Таблица feedings мигрирована")
        else:
            print("ℹ️ Таблица feedings уже имеет правильную структуру")
            
    except sqlite3.OperationalError as e:
        print(f"ℹ️ Миграция feedings: {e}")
    
    try:
        # Проверяем, есть ли колонка family_id в таблице diapers
        cur.execute("PRAGMA table_info(diapers)")
        columns = [col[1] for col in cur.fetchall()]
        
        if 'family_id' not in columns:
            print("🔄 Мигрируем таблицу diapers...")
            # Создаем временную таблицу с новой структурой
            cur.execute("""
                CREATE TABLE diapers_new (
                    id INTEGER PRIMARY KEY,
                    family_id INTEGER,
                    author_id INTEGER,
                    timestamp TEXT NOT NULL,
                    author_role TEXT DEFAULT 'Родитель',
                    author_name TEXT DEFAULT 'Неизвестно',
                    FOREIGN KEY (family_id) REFERENCES families (id)
                )
            """)
            
            # Копируем данные из старой таблицы
            cur.execute("SELECT id, user_id, timestamp FROM diapers")
            old_data = cur.fetchall()
            
            for row in old_data:
                # Для каждой записи создаем временную семью
                temp_family_id = create_family(f"Миграция {row[0]}", row[1])
                cur.execute("INSERT INTO diapers_new (family_id, author_id, timestamp, author_role, author_name) VALUES (?, ?, ?, ?, ?)",
                           (temp_family_id, row[1], row[2], 'Родитель', 'Неизвестно'))
            
            # Удаляем старую таблицу и переименовываем новую
            cur.execute("DROP TABLE diapers")
            cur.execute("ALTER TABLE diapers_new RENAME TO diapers")
            print("✅ Таблица diapers мигрирована")
        else:
            print("ℹ️ Таблица diapers уже имеет правильную структуру")
            
    except sqlite3.OperationalError as e:
        print(f"ℹ️ Миграция diapers: {e}")
    
    conn.commit()
    conn.close()
    print("✅ База данных инициализирована/обновлена")

# Функции для работы с базой данных
def get_family_id(user_id):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("SELECT family_id FROM family_members WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    family_id = result[0] if result else None
    print(f"DEBUG: get_family_id({user_id}) = {family_id}")
    return family_id

def create_family(name, user_id):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    
    cur.execute("INSERT INTO families (name) VALUES (?)", (name,))
    family_id = cur.lastrowid
    
    cur.execute("INSERT INTO family_members (family_id, user_id) VALUES (?, ?)", (family_id, user_id))
    cur.execute("INSERT INTO settings (family_id) VALUES (?)", (family_id,))
    
    conn.commit()
    conn.close()
    return family_id

def invite_code_for(family_id):
    # В существующей базе нет колонки invite_code, возвращаем ID семьи
    return str(family_id)

def get_family_name(family_id):
    """Получить название семьи по ID"""
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("SELECT name FROM families WHERE id = ?", (family_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else "Неизвестная семья"

def get_member_info(user_id):
    """Получить информацию о члене семьи"""
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("SELECT role, name FROM family_members WHERE user_id = ?", (user_id,))
    result = cur.fetchone()
    conn.close()
    if result:
        return result[0], result[1]  # role, name
    return "Родитель", "Неизвестно"

def set_member_role(user_id, role, name):
    """Установить роль и имя для члена семьи"""
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("UPDATE family_members SET role = ?, name = ? WHERE user_id = ?", (role, name, user_id))
    conn.commit()
    conn.close()

def get_family_members_with_roles(family_id):
    """Получить всех членов семьи с ролями"""
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("SELECT user_id, role, name FROM family_members WHERE family_id = ?", (family_id,))
    members = cur.fetchall()
    conn.close()
    return members

def add_feeding(user_id, minutes_ago=0):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    
    # Получаем family_id пользователя
    family_id = get_family_id(user_id)
    if not family_id:
        # Если пользователь не в семье, создаем временную семью
        family_id = create_family("Временная семья", user_id)
    
    # Получаем информацию об авторе
    role, name = get_member_info(user_id)
    
    timestamp = get_thai_time() - timedelta(minutes=minutes_ago)
    cur.execute("INSERT INTO feedings (family_id, author_id, timestamp, author_role, author_name) VALUES (?, ?, ?, ?, ?)", 
                (family_id, user_id, timestamp.isoformat(), role, name))
    conn.commit()
    conn.close()

def add_diaper_change(user_id, minutes_ago=0):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    
    # Получаем family_id пользователя
    family_id = get_family_id(user_id)
    if not family_id:
        # Если пользователь не в семье, создаем временную семью
        family_id = create_family("Временная семья", user_id)
    
    # Получаем информацию об авторе
    role, name = get_member_info(user_id)
    
    timestamp = get_thai_time() - timedelta(minutes=minutes_ago)
    cur.execute("INSERT INTO diapers (family_id, author_id, timestamp, author_role, author_name) VALUES (?, ?, ?, ?, ?)", 
                (family_id, user_id, timestamp.isoformat(), role, name))
    conn.commit()
    conn.close()

def get_last_feeding_time(user_id):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    
    # Получаем family_id пользователя
    family_id = get_family_id(user_id)
    if not family_id:
        return None
    
    cur.execute("SELECT timestamp FROM feedings WHERE family_id = ? ORDER BY timestamp DESC LIMIT 1", (family_id,))
    result = cur.fetchone()
    conn.close()
    if result:
        return datetime.fromisoformat(result[0])
    return None

def get_user_intervals(family_id):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("SELECT feed_interval, diaper_interval FROM settings WHERE family_id = ?", (family_id,))
    result = cur.fetchone()
    conn.close()
    if result:
        return result[0], result[1]
    return 3, 2

def set_user_interval(family_id, feed_interval=None, diaper_interval=None):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    if feed_interval is not None:
        cur.execute("UPDATE settings SET feed_interval = ? WHERE family_id = ?", (feed_interval, family_id))
    if diaper_interval is not None:
        cur.execute("UPDATE settings SET diaper_interval = ? WHERE family_id = ?", (diaper_interval, family_id))
    conn.commit()
    conn.close()

def is_tips_enabled(family_id):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("SELECT tips_enabled FROM settings WHERE family_id = ?", (family_id,))
    result = cur.fetchone()
    conn.close()
    return result[0] if result else 1

def toggle_tips(family_id):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("UPDATE settings SET tips_enabled = CASE WHEN tips_enabled = 1 THEN 0 ELSE 1 END WHERE family_id = ?", (family_id,))
    conn.commit()
    conn.close()

def set_tips_time(family_id, hour, minute):
    """Установить время рассылки советов"""
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("UPDATE settings SET tips_time_hour = ?, tips_time_minute = ? WHERE family_id = ?", (hour, minute, family_id))
    conn.commit()
    conn.close()

def get_tips_time(family_id):
    """Получить время рассылки советов"""
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("SELECT tips_time_hour, tips_time_minute FROM settings WHERE family_id = ?", (family_id,))
    result = cur.fetchone()
    conn.close()
    if result:
        return result[0], result[1]
    return 9, 0  # значения по умолчанию

def get_feedings_by_day(user_id, date):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    
    # Получаем family_id пользователя
    family_id = get_family_id(user_id)
    if not family_id:
        return []
    
    start_date = datetime.combine(date, datetime.min.time()).isoformat()
    end_date = datetime.combine(date, datetime.max.time()).isoformat()
    cur.execute("SELECT id, timestamp, author_role, author_name FROM feedings WHERE family_id = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp", 
                (family_id, start_date, end_date))
    result = cur.fetchall()
    conn.close()
    return result

def get_diapers_by_day(user_id, date):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    
    # Получаем family_id пользователя
    family_id = get_family_id(user_id)
    if not family_id:
        return []
    
    start_date = datetime.combine(date, datetime.min.time()).isoformat()
    end_date = datetime.combine(date, datetime.max.time()).isoformat()
    cur.execute("SELECT id, timestamp, author_role, author_name FROM diapers WHERE family_id = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp", 
                (family_id, start_date, end_date))
    result = cur.fetchall()
    conn.close()
    return result

def delete_entry(table, entry_id):
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute(f"DELETE FROM {table} WHERE id = ?", (entry_id,))
    conn.commit()
    conn.close()

# Функция для получения случайного совета
def get_random_tip():
    try:
        import csv
        tips = []
        
        # Читаем советы из CSV файла
        with open("data/advice.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                tips.append(row["tip"])
        
        if tips:
            return random.choice(tips)
        else:
            return "Пока нет доступных советов."
            
    except Exception as e:
        print(f"Ошибка при чтении советов: {e}")
        # Возвращаем запасной совет в случае ошибки
        return "Помните, что каждый ребенок уникален и развивается в своем темпе."



# Инициализация
init_db()
scheduler = AsyncIOScheduler()

# Состояния ожидания
family_creation_pending = {}
manual_feeding_pending = {}
join_pending = {}
edit_pending = {}
edit_role_pending = {}

@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    buttons = [
        [Button.text("🍽 Кормление"), Button.text("🧷 Смена подгузника")],
        [Button.text("🍼 Статус кормления"), Button.text("📜 История")],
        [Button.text("💡 Совет"), Button.text("⚙ Настройки")]
    ]
    await event.respond("👶 Привет! Я помогу следить за малышом:", buttons=buttons)

@client.on(events.NewMessage(pattern='🍽 Кормление'))
async def feeding_menu(event):
    buttons = [
        [Button.inline("Сейчас", b"feed_now")],
        [Button.inline("15 мин назад", b"feed_15")],
        [Button.inline("30 мин назад", b"feed_30")],
        [Button.inline("🕒 Указать вручную", b"feed_manual")],
    ]
    await event.respond("🍼 Когда было кормление?", buttons=buttons)

@client.on(events.NewMessage(pattern='🧷 Смена подгузника'))
async def diaper_menu(event):
    buttons = [
        [Button.inline("Сейчас", b"diaper_now")],
        [Button.inline("🕒 Указать вручную", b"diaper_manual")],
    ]
    await event.respond("🧷 Когда была смена подгузника?", buttons=buttons)

@client.on(events.NewMessage(pattern='⏰ Когда ел?'))
async def last_feed(event):
    time = get_last_feeding_time(event.sender_id)
    if time:
        delta = datetime.now() - time
        h, m = divmod(int(delta.total_seconds() // 60), 60)
        await event.respond(f"🍼 Последнее кормление было {h}ч {m}м назад.")
    else:
        await event.respond("❌ Пока нет записей о кормлении.")

@client.on(events.NewMessage(pattern='💡 Совет'))
async def tip_command(event):
    tip = get_random_tip()
    await event.respond(tip)

@client.on(events.NewMessage(pattern='👤 Моя роль'))
async def my_role_command(event):
    """Показать и изменить роль пользователя"""
    uid = event.sender_id
    fid = get_family_id(uid)
    
    if not fid:
        await event.respond("❌ Сначала создайте семью.")
        return
    
    role, name = get_member_info(uid)
    
    message = (
        f"👤 **Ваша роль в семье:**\n\n"
        f"🎭 Роль: {role}\n"
        f"📝 Имя: {name}\n\n"
        f"💡 Нажмите кнопку ниже, чтобы изменить"
    )
    
    buttons = [
        [Button.inline("✏️ Изменить роль", b"edit_role")],
        [Button.inline("🔙 Назад", b"back_to_main")]
    ]
    
    await event.respond(message, buttons=buttons)



@client.on(events.NewMessage(pattern='⚙ Настройки'))
async def settings_menu(event):
    fid = get_family_id(event.sender_id)
    if not fid:
        # Если пользователь не в семье, показываем кнопку создания семьи
        buttons = [
            [Button.inline("👨‍👩‍👧 Создать семью", b"create_family")]
        ]
        await event.respond("⚙ Настройки:\n\n❗ Сначала создайте семью:", buttons=buttons)
        return
    
    feed_i, diaper_i = get_user_intervals(fid)
    tips_on = is_tips_enabled(fid)
    tips_label = "🔕 Отключить советы" if tips_on else "🔔 Включить советы"
    tips_hour, tips_minute = get_tips_time(fid)
    
    buttons = [
        [Button.inline(f"🍽 Интервал кормления: {feed_i}ч", b"set_feed")],
        [Button.inline(f"🧷 Интервал подгузника: {diaper_i}ч", b"set_diaper")],
        [Button.inline(tips_label, b"toggle_tips")],
        [Button.inline(f"🕐 Время советов: {tips_hour:02d}:{tips_minute:02d}", b"set_tips_time")],
        [Button.inline("👤 Моя роль", b"my_role")],
        [Button.inline("👨‍👩‍👧 Управление семьей", b"family_management")]
    ]
    await event.respond("⚙ Настройки:", buttons=buttons)

async def create_family_cmd(event):
    await event.respond("👨‍👩‍👧 Введите название новой семьи:")
    family_creation_pending[event.sender_id] = True

async def family_management_cmd(event):
    fid = get_family_id(event.sender_id)
    if fid:
        code = invite_code_for(fid)
        buttons = [
            [Button.inline("👥 Члены семьи", b"family_members")],
            [Button.inline("🔙 Назад к настройкам", b"back_to_settings")]
        ]
        await event.respond(
            f"👨‍👩‍👧 **Управление семьей**\n\n"
            f"Название: {get_family_name(fid)}\n"
            f"Код для приглашения: `{code}`\n\n"
            f"Выберите действие:",
            buttons=buttons
        )
    else:
        await event.respond("❌ Ошибка: семья не найдена.")

async def family_members_cmd(event):
    fid = get_family_id(event.sender_id)
    if fid:
        conn = sqlite3.connect("babybot.db")
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM family_members WHERE family_id = ?", (fid,))
        members = cur.fetchall()
        conn.close()
        
        if members:
            text = "👥 **Члены семьи:**\n\n"
            for i, (user_id, role, name) in enumerate(members, 1):
                text += f"{i}. {role} {name} (ID: {user_id})\n"
        else:
            text = "👥 В семье пока нет членов."
        
        buttons = [
            [Button.inline("🔙 Назад к управлению семьей", b"back_to_family_management")]
        ]
        await event.respond(text, buttons=buttons)
    else:
        await event.respond("❌ Ошибка: семья не найдена.")



@client.on(events.NewMessage(pattern='📜 История'))
async def history_menu(event):
    print(f"DEBUG: Обработка команды '📜 История' для пользователя {event.sender_id}")
    today = get_thai_date()
    buttons = [
        [Button.inline(f"📅 {today - timedelta(days=i)}", f"hist_{i}".encode())] for i in range(3)
    ]
    await event.respond("📖 Выберите день для просмотра истории:", buttons=buttons)

@client.on(events.NewMessage(pattern='🍼 Статус кормления'))
async def feeding_status(event):
    """Показать текущий статус кормления"""
    uid = event.sender_id
    fid = get_family_id(uid)
    
    if not fid:
        await event.respond("❌ Сначала создайте семью.")
        return
    
    # Получаем интервал кормления
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    cur.execute("SELECT feed_interval FROM settings WHERE family_id = ?", (fid,))
    interval_result = cur.fetchone()
    feed_interval = interval_result[0] if interval_result else 3
    
    # Получаем время последнего кормления
    last_feeding = get_last_feeding_time_for_family(fid)
    
    if last_feeding:
        time_since_last = get_thai_time() - last_feeding
        hours_since_last = time_since_last.total_seconds() / 3600
        minutes_since_last = time_since_last.total_seconds() / 60
        
        # Определяем статус
        if hours_since_last < feed_interval:
            status = "✅ Время кормления еще не подошло"
            remaining = feed_interval - hours_since_last
            status_emoji = "🟢"
        elif hours_since_last < (feed_interval + 0.5):
            status = "⚠️ Пора кормить!"
            remaining = 0
            status_emoji = "🟡"
        else:
            status = "🚨 Долго не кормили!"
            remaining = 0
            status_emoji = "🔴"
        
        message = (
            f"{status_emoji} **Статус кормления**\n\n"
            f"⏰ Последнее кормление: {last_feeding.strftime('%H:%M')}\n"
            f"🕐 Прошло: {hours_since_last:.1f} ч. ({minutes_since_last:.0f} мин.)\n"
            f"🔄 Интервал: {feed_interval} ч.\n"
            f"📊 Статус: {status}\n"
        )
        
        if remaining > 0:
            message += f"⏳ До следующего кормления: {remaining:.1f} ч."
        else:
            message += f"💡 Рекомендуется покормить сейчас!"
    else:
        message = (
            f"🍼 **Статус кормления**\n\n"
            f"👶 Кормлений еще не было\n"
            f"🔄 Рекомендуемый интервал: {feed_interval} ч.\n"
            f"💡 Запишите первое кормление!"
        )
    
    conn.close()
    
    # Добавляем кнопки для быстрых действий
    buttons = [
        [Button.inline("🍼 Кормить сейчас", b"feed_now")],
        [Button.inline("🕒 Указать время", b"feed_manual")]
    ]
    
    await event.respond(message, buttons=buttons)

@client.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode()

    if data == "feed_now":
        add_feeding(event.sender_id)
        await event.edit("🍼 Кормление зафиксировано.")
    elif data == "feed_15":
        add_feeding(event.sender_id, 15)
        await event.edit("🍼 Кормление (15 мин назад) зафиксировано.")
    elif data == "feed_30":
        add_feeding(event.sender_id, 30)
        await event.edit("🍼 Кормление (30 мин назад) зафиксировано.")
    elif data == "feed_manual":
        manual_feeding_pending[event.sender_id] = True
        await event.respond("🕒 Введите время кормления в формате ЧЧ:ММ (например, 14:30):")

    elif data == "diaper_now":
        add_diaper_change(event.sender_id)
        await event.edit("🧷 Смена подгузника зафиксирована.")
    elif data == "diaper_manual":
        manual_feeding_pending[event.sender_id] = "diaper"
        await event.respond("🕒 Введите время смены подгузника в формате ЧЧ:ММ (например, 14:30):")

    elif data == "set_feed":
        buttons = [[Button.inline(f"{i} ч", f"feed_{i}".encode())] for i in range(1, 7)]
        await event.edit("🍽 Выберите интервал кормления:", buttons=buttons)
    elif data == "set_diaper":
        buttons = [[Button.inline(f"{i} ч", f"diaper_{i}".encode())] for i in range(1, 7)]
        await event.edit("🧷 Выберите интервал смены подгузника:", buttons=buttons)
    elif data.startswith("feed_yesterday_"):
        minutes_ago = int(data.split("_")[-1])
        uid = event.sender_id
        
        print(f"DEBUG: Обработка feed_yesterday_ для пользователя {uid}")
        print(f"DEBUG: manual_feeding_pending[{uid}] = {manual_feeding_pending.get(uid, 'не найдено')}")
        
        if uid in manual_feeding_pending and isinstance(manual_feeding_pending[uid], dict):
            time_str = manual_feeding_pending[uid]["time"]
            add_feeding(uid, minutes_ago=minutes_ago)
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%d.%m')
            await event.edit(f"✅ Кормление за вчера ({yesterday}) в {time_str} зафиксировано.")
            del manual_feeding_pending[uid]
        else:
            await event.edit("❌ Ошибка: данные о времени не найдены.")
    
    elif data.startswith("diaper_yesterday_"):
        minutes_ago = int(data.split("_")[-1])
        uid = event.sender_id
        
        print(f"DEBUG: Обработка diaper_yesterday_ для пользователя {uid}")
        print(f"DEBUG: manual_feeding_pending[{uid}] = {manual_feeding_pending.get(uid, 'не найдено')}")
        
        if uid in manual_feeding_pending and isinstance(manual_feeding_pending[uid], dict):
            time_str = manual_feeding_pending[uid]["time"]
            add_diaper_change(uid, minutes_ago=minutes_ago)
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%d.%m')
            await event.edit(f"✅ Смена подгузника за вчера ({yesterday}) в {time_str} зафиксирована.")
            del manual_feeding_pending[uid]
        else:
            await event.edit("❌ Ошибка: данные о времени не найдены.")
    
    elif data.startswith("feed_"):
        hours = int(data.split("_")[1])
        fid = get_family_id(event.sender_id)
        set_user_interval(fid, feed_interval=hours)
        await event.edit(f"✅ Интервал кормления установлен на {hours} ч.")
    elif data.startswith("diaper_"):
        hours = int(data.split("_")[1])
        fid = get_family_id(event.sender_id)
        set_user_interval(fid, diaper_interval=hours)
        await event.edit(f"✅ Интервал смены подгузника установлен на {hours} ч.")
    elif data == "toggle_tips":
        fid = get_family_id(event.sender_id)
        toggle_tips(fid)
        await settings_menu(event)
    
    elif data == "my_role":
        uid = event.sender_id
        role, name = get_member_info(uid)
        
        message = (
            f"👤 **Ваша роль в семье:**\n\n"
            f"🎭 Роль: {role}\n"
            f"📝 Имя: {name}\n\n"
            f"💡 Нажмите кнопку ниже, чтобы изменить"
        )
        
        buttons = [
            [Button.inline("✏️ Изменить роль", b"edit_role")],
            [Button.inline("🔙 Назад к настройкам", b"back_to_settings")]
        ]
        
        await event.edit(message, buttons=buttons)
    
    elif data == "edit_role":
        await event.edit("👤 Выберите вашу роль:")
        buttons = [
            [Button.inline("👨‍👩‍👧 Родитель", b"role_parent")],
            [Button.inline("👨‍👩‍👧 Мама", b"role_mom")],
            [Button.inline("👨‍👩‍👧 Папа", b"role_dad")],
            [Button.inline("👨‍👩‍👧 Бабушка", b"role_grandma")],
            [Button.inline("👨‍👩‍👧 Дедушка", b"role_grandpa")],
            [Button.inline("👨‍👩‍👧 Няня", b"role_nanny")],
            [Button.inline("🔙 Назад к настройкам", b"back_to_settings")]
        ]
        await event.edit("👤 Выберите вашу роль:", buttons=buttons )
    
    elif data.startswith("role_"):
        role_map = {
            "role_parent": "Родитель",
            "role_mom": "Мама",
            "role_dad": "Папа",
            "role_grandma": "Бабушка",
            "role_grandpa": "Дедушка",
            "role_nanny": "Няня"
        }
        role = role_map.get(data, "Родитель")
        uid = event.sender_id
        
        # Запрашиваем имя
        await event.edit(f"👤 Роль установлена: {role}\n\n📝 Теперь введите ваше имя:")
        edit_role_pending[uid] = {"role": role, "step": "waiting_name"}
    
    elif data == "back_to_main":
        await start(event)
    
    elif data == "set_tips_time":
        await event.edit("🕐 Выберите время для рассылки советов:")
        # Показываем кнопки для выбора часа
        buttons = []
        for hour in range(0, 24, 2):  # Каждые 2 часа
            buttons.append([Button.inline(f"{hour:02d}:00", f"tips_hour_{hour}".encode())])
        buttons.append([Button.inline("🔙 Назад", b"back_to_settings")])
        await event.edit("🕐 Выберите час для рассылки советов:", buttons=buttons)

    elif data.startswith("tips_hour_"):
        hour = int(data.split("_")[-1])
        # Показываем кнопки для выбора минуты
        buttons = []
        for minute in range(0, 60, 15):  # Каждые 15 минут
            buttons.append([Button.inline(f"{hour:02d}:{minute:02d}", f"tips_time_{hour}_{minute}".encode())])
        buttons.append([Button.inline("🔙 Назад", b"set_tips_time")])
        await event.edit(f"🕐 Выберите минуту для времени {hour:02d}:XX:", buttons=buttons)
    
    elif data.startswith("tips_time_"):
        parts = data.split("_")
        hour = int(parts[-2])
        minute = int(parts[-1])
        fid = get_family_id(event.sender_id)
        set_tips_time(fid, hour, minute)
        await event.edit(f"✅ Время рассылки советов установлено на {hour:02d}:{minute:02d}")
        # Возвращаемся к настройкам через 2 секунды
        await asyncio.sleep(2)
        await settings_menu(event)
    
    elif data.startswith("hist_"):
        print(f"DEBUG: Обработка истории для пользователя {event.sender_id}, data: {data}")
        try:
            index = int(data.split("_")[1])
            target_date = get_thai_date() - timedelta(days=index)
            print(f"DEBUG: Целевая дата: {target_date}")
            
            feedings = get_feedings_by_day(event.sender_id, target_date)
            diapers = get_diapers_by_day(event.sender_id, target_date)
            
            print(f"DEBUG: Найдено кормлений: {len(feedings) if feedings else 0}")
            print(f"DEBUG: Найдено смен подгузников: {len(diapers) if diapers else 0}")
            
            if feedings:
                print(f"DEBUG: Первое кормление: {feedings[0]}")
            if diapers:
                print(f"DEBUG: Первая смена: {diapers[0]}")
        except Exception as e:
            print(f"DEBUG: Ошибка при обработке истории: {e}")
            await event.answer(f"❌ Ошибка: {str(e)}", alert=True)
            return

        text = f"📅 История за {target_date}:\n\n"

        if feedings:
            text += "🍼 Кормления:\n"
            for f in feedings:
                time_str = datetime.fromisoformat(f[1]).strftime("%H:%M")
                # Проверяем, есть ли информация об авторе
                if len(f) >= 4 and f[3] and f[4]:  # author_role и author_name
                    author_info = f"{f[3]} {f[4]}"
                else:
                    author_info = "Неизвестно"
                text += f"  • {time_str} - {author_info} [ID {f[0]}]\n"
        else:
            text += "🍼 Кормлений нет\n"

        if diapers:
            text += "\n🧷 Подгузники:\n"
            for d in diapers:
                time_str = datetime.fromisoformat(d[1]).strftime("%H:%M")
                # Проверяем, есть ли информация об авторе
                if len(d) >= 4 and d[3] and d[4]:  # author_role и author_name
                    author_info = f"{d[3]} {d[4]}"
                else:
                    author_info = "Неизвестно"
                text += f"  • {time_str} - {author_info} [ID {d[0]}]\n"
        else:
            text += "\n🧷 Смен нет\n"

        # Кнопки удаления и редактирования
        buttons = []
        for f in feedings:
            buttons.append([Button.inline(f"🍼 {f[0]} ✏️", f"edit_feed_{f[0]}".encode()),
                            Button.inline("🗑", f"del_feed_{f[0]}".encode())])
        for d in diapers:
            buttons.append([Button.inline(f"🧷 {d[0]} ✏️", f"edit_diaper_{d[0]}".encode()),
                            Button.inline("🗑", f"del_diaper_{d[0]}".encode())])

        # Проверяем, есть ли кнопки
        if buttons:
            await event.edit(text, buttons=buttons)
        else:
            # Если кнопок нет, просто обновляем текст
            await event.edit(text)
        return

    elif data.startswith("del_feed_"):
        entry_id = int(data.split("_")[-1])
        delete_entry("feedings", entry_id)
        await event.answer("🗑 Удалено", alert=True)

    elif data.startswith("del_diaper_"):
        entry_id = int(data.split("_")[-1])
        delete_entry("diapers", entry_id)
        await event.answer("🗑 Удалено", alert=True)

    elif data.startswith("edit_feed_") or data.startswith("edit_diaper_"):
        entry_id = int(data.split("_")[-1])
        table = "feedings" if "feed" in data else "diapers"
        edit_pending[event.sender_id] = (table, entry_id)
        await event.respond(f"✏️ Введите новое время в формате ЧЧ:ММ для записи ID {entry_id}")
    
    elif data == "create_family":
        await event.respond("👨‍👩‍👧 Введите название новой семьи:")
        family_creation_pending[event.sender_id] = True
    
    elif data == "family_management":
        await family_management_cmd(event)
    
    elif data == "family_members":
        await family_members_cmd(event)
    
    elif data == "back_to_family_management":
        await family_management_cmd(event)
    
    elif data == "back_to_settings":
        await settings_menu(event)
    
    elif data == "feed_cancel":
        uid = event.sender_id
        if uid in manual_feeding_pending:
            del manual_feeding_pending[uid]
        await event.edit("❌ Запись кормления отменена.")
    
    elif data == "diaper_cancel":
        uid = event.sender_id
        if uid in manual_feeding_pending:
            del manual_feeding_pending[uid]
        await event.edit("❌ Запись смены подгузника отменена.")

@client.on(events.NewMessage)
async def handle_text(event):
    uid = event.sender_id

    if uid in manual_feeding_pending:
        user_input = event.raw_text.strip()
        action_type = manual_feeding_pending[uid]
        
        # Проверяем, что это за действие
        if action_type == "diaper":
            print(f"DEBUG: Пользователь {uid} ввел время для смены подгузника: '{user_input}'")
            action_name = "смена подгузника"
            add_func = add_diaper_change
            callback_prefix = "diaper_yesterday_"
            cancel_callback = "diaper_cancel"
        else:
            print(f"DEBUG: Пользователь {uid} ввел время для кормления: '{user_input}'")
            action_name = "кормление"
            add_func = add_feeding
            callback_prefix = "feed_yesterday_"
            cancel_callback = "feed_cancel"
        
        try:
            # Парсим введенное время
            t = datetime.strptime(user_input, "%H:%M")
            print(f"DEBUG: Парсинг времени успешен: {t}")
            
            # Создаем datetime объект для сегодняшнего дня с введенным временем (в тайском времени)
            today = get_thai_date()
            # Создаем datetime объект с тайским часовым поясом
            thai_tz = pytz.timezone('Asia/Bangkok')
            dt = thai_tz.localize(datetime.combine(today, t.time()))
            now = get_thai_time()
            
            print(f"DEBUG: Сегодня (Таиланд): {today}")
            print(f"DEBUG: Введенное время: {dt}")
            print(f"DEBUG: Текущее время (Таиланд): {now}")
            print(f"DEBUG: UTC время: {datetime.now(pytz.UTC)}")
            
            # Вычисляем разницу в минутах
            diff = int((now - dt).total_seconds() // 60)
            print(f"DEBUG: Разница в минутах: {diff}")
            
            # Проверяем, что время не в будущем и не слишком далеко в прошлом
            if diff < 0:
                print(f"DEBUG: Время в будущем, разница: {diff}")
                # Предлагаем сделать запись за прошлый день
                yesterday = today - timedelta(days=1)
                yesterday_dt = thai_tz.localize(datetime.combine(yesterday, t.time()))
                yesterday_diff = int((now - yesterday_dt).total_seconds() // 60)
                
                if yesterday_diff >= 0 and yesterday_diff <= 1440:
                    # Создаем кнопки для выбора дня
                    buttons = [
                        [Button.inline("✅ Да, за вчера", f"{callback_prefix}{yesterday_diff}".encode())],
                        [Button.inline("❌ Нет, отменить", cancel_callback.encode())]
                    ]
                    await event.respond(
                        f"🕒 Время {user_input} больше текущего времени.\n"
                        f"Хотите сделать запись {action_name} за вчера ({yesterday.strftime('%d.%m')})?",
                        buttons=buttons)
                    # Сохраняем введенное время для возможного использования
                    manual_feeding_pending[uid] = {"type": action_type, "time": user_input, "minutes_ago": yesterday_diff}
                    print(f"DEBUG: Сохранили данные в manual_feeding_pending[{uid}] = {manual_feeding_pending[uid]}")
                    return
                else:
                    await event.respond("❌ Нельзя указать время в будущем. Введите прошедшее время.")
                    return
            elif diff > 1440:  # больше 24 часов
                print(f"DEBUG: Время слишком далеко в прошлом, разница: {diff}")
                # Проверяем, может ли это быть время за вчера
                yesterday = today - timedelta(days=1)
                yesterday_dt = thai_tz.localize(datetime.combine(yesterday, t.time()))
                yesterday_diff = int((now - yesterday_dt).total_seconds() // 60)
                
                if yesterday_diff >= 0 and yesterday_diff <= 1440:
                    print(f"DEBUG: Время подходит для вчерашнего дня, разница: {yesterday_diff}")
                    # Автоматически предлагаем записать за вчера
                    buttons = [
                        [Button.inline("✅ Да, за вчера", f"{callback_prefix}{yesterday_diff}".encode())],
                        [Button.inline("❌ Нет, отменить", cancel_callback.encode())]
                    ]
                    await event.respond(
                        f"🕒 Время {user_input} слишком далеко в прошлом для сегодняшнего дня.\n"
                        f"Хотите сделать запись {action_name} за вчера ({yesterday.strftime('%d.%m')})?",
                        buttons=buttons)
                    manual_feeding_pending[uid] = {"type": action_type, "time": user_input, "minutes_ago": yesterday_diff}
                    print(f"DEBUG: Сохранили данные в manual_feeding_pending[{uid}] = {manual_feeding_pending[uid]}")
                    return
                else:
                    await event.respond("❌ Время слишком далеко в прошлом. Максимум 24 часа назад.")
                    return
            
            # Если время в прошлом, но не слишком далеко
            if diff >= 0:
                print(f"DEBUG: Добавляем {action_name}, minutes_ago: {diff}")
                add_func(uid, minutes_ago=diff)
                await event.respond(f"✅ {action_name.capitalize()} в {user_input} зафиксировано.")
            else:
                await event.respond("❌ Ошибка: неожиданное значение времени.")
            
            # Удаляем данные только после успешного добавления
            if uid in manual_feeding_pending:
                del manual_feeding_pending[uid]
        except ValueError as e:
            print(f"DEBUG: Ошибка парсинга времени: {e}")
            await event.respond("❌ Неверный формат. Введите время в формате ЧЧ:ММ (например: 14:30)")
            # Удаляем данные при ошибке парсинга
            if uid in manual_feeding_pending:
                del manual_feeding_pending[uid]
        except Exception as e:
            print(f"DEBUG: Неожиданная ошибка: {e}")
            await event.respond(f"❌ Ошибка: {str(e)}")
            # Удаляем данные при неожиданной ошибке
            if uid in manual_feeding_pending:
                del manual_feeding_pending[uid]
        return

    if uid in family_creation_pending:
        name = event.raw_text.strip()
        fid = create_family(name, uid)
        del family_creation_pending[uid]
        code = invite_code_for(fid)
        await event.respond(f"✅ Семья создана. Код приглашения: `{code}`")
        return
    
    if uid in edit_role_pending:
        user_input = event.raw_text.strip()
        role_data = edit_role_pending[uid]
        
        if role_data["step"] == "waiting_name":
            # Устанавливаем роль и имя
            set_member_role(uid, role_data["role"], user_input)
            del edit_role_pending[uid]
            
            await event.respond(
                f"✅ Роль обновлена!\n\n"
                f"🎭 Роль: {role_data['role']}\n"
                f"📝 Имя: {user_input}\n\n"
                f"💡 Теперь в истории будет отображаться, кто именно ухаживает за малышом!"
            )
        return



def get_last_feeding_time_for_family(family_id):
    """Получить время последнего кормления для семьи"""
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    
    # Получаем всех членов семьи
    cur.execute("SELECT user_id FROM family_members WHERE family_id = ?", (family_id,))
    members = cur.fetchall()
    
    if not members:
        conn.close()
        return None
    
    # Получаем последнее кормление среди всех членов семьи
    member_ids = [str(member[0]) for member in members]
    placeholders = ','.join(['?' for _ in member_ids])
    
    cur.execute(f"""
        SELECT timestamp FROM feedings 
        WHERE family_id = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (family_id,))
    
    result = cur.fetchone()
    conn.close()
    
    if result:
        return datetime.fromisoformat(result[0])
    return None

def should_send_feeding_reminder(family_id):
    """Проверить, нужно ли отправить напоминание о кормлении"""
    conn = sqlite3.connect("babybot.db")
    cur = conn.cursor()
    
    # Получаем интервал кормления для семьи
    cur.execute("SELECT feed_interval FROM settings WHERE family_id = ?", (family_id,))
    result = cur.fetchone()
    
    if not result:
        conn.close()
        return False
    
    feed_interval = result[0]  # в часах
    last_feeding = get_last_feeding_time_for_family(family_id)
    
    if not last_feeding:
        # Если кормлений еще не было, напоминаем через 2 часа после создания семьи
        return True
    
    # Вычисляем, сколько времени прошло с последнего кормления
    time_since_last = datetime.now() - last_feeding
    hours_since_last = time_since_last.total_seconds() / 3600
    
    # Если прошло больше интервала + 30 минут (буфер), отправляем напоминание
    return hours_since_last >= (feed_interval + 0.5)
    
    conn.close()

@scheduler.scheduled_job('interval', minutes=30)
async def check_feeding_reminders():
    """Проверять каждые 30 минут, нужно ли отправить напоминания о кормлении"""
    try:
        conn = sqlite3.connect("babybot.db")
        cur = conn.cursor()
        
        # Получаем все семьи с включенными уведомлениями
        cur.execute("SELECT family_id FROM settings WHERE tips_enabled = 1")
        families = cur.fetchall()
        
        for (family_id,) in families:
            if should_send_feeding_reminder(family_id):
                # Получаем всех членов семьи
                cur.execute("SELECT user_id FROM family_members WHERE family_id = ?", (family_id,))
                members = cur.fetchall()
                
                # Получаем интервал кормления
                cur.execute("SELECT feed_interval FROM settings WHERE family_id = ?", (family_id,))
                interval_result = cur.fetchone()
                feed_interval = interval_result[0] if interval_result else 3
                
                # Получаем время последнего кормления
                last_feeding = get_last_feeding_time_for_family(family_id)
                
                if last_feeding:
                    time_since_last = datetime.now() - last_feeding
                    hours_since_last = time_since_last.total_seconds() / 3600
                    message = (
                        f"🍼 **Напоминание о кормлении!**\n\n"
                        f"⏰ Прошло: {hours_since_last:.1f} ч. с последнего кормления\n"
                        f"📅 Последнее кормление: {last_feeding.strftime('%H:%M')}\n"
                        f"🔄 Рекомендуемый интервал: {feed_interval} ч.\n\n"
                        f"💡 Не забудьте покормить малыша!"
                    )
                else:
                    message = (
                        f"🍼 **Первое кормление!**\n\n"
                        f"👶 Пора начать отслеживать кормления\n"
                        f"🔄 Рекомендуемый интервал: {feed_interval} ч.\n\n"
                        f"💡 Запишите первое кормление!"
                    )
                
                # Отправляем уведомление всем членам семьи
                for (user_id,) in members:
                    try:
                        await client.send_message(user_id, message)
                        print(f"✅ Отправлено напоминание о кормлении пользователю {user_id}")
                    except Exception as e:
                        print(f"❌ Ошибка отправки напоминания пользователю {user_id}: {e}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка в check_feeding_reminders: {e}")

@scheduler.scheduled_job('interval', minutes=1)
async def send_scheduled_tips():
    """Отправлять советы по расписанию для каждой семьи"""
    try:
        current_time = datetime.now()
        current_hour = current_time.hour
        current_minute = current_time.minute
        
        conn = sqlite3.connect("babybot.db")
        cur = conn.cursor()
        
        # Получаем все семьи с включенными советами
        cur.execute("SELECT family_id, tips_time_hour, tips_time_minute FROM settings WHERE tips_enabled = 1")
        families = cur.fetchall()
        
        for (family_id, tips_hour, tips_minute) in families:
            # Проверяем, пора ли отправлять советы для этой семьи
            if current_hour == tips_hour and current_minute == tips_minute:
                tip = get_random_tip()
                
                # Получаем всех членов семьи
                cur.execute("SELECT user_id FROM family_members WHERE family_id = ?", (family_id,))
                members = cur.fetchall()
                
                # Отправляем совет всем членам семьи
                for (user_id,) in members:
                    try:
                        await client.send_message(user_id, tip)
                        print(f"✅ Отправлен совет пользователю {user_id} в {current_hour:02d}:{current_minute:02d}")
                    except Exception as e:
                        print(f"❌ Ошибка отправки совета пользователю {user_id}: {e}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка в send_scheduled_tips: {e}")

@scheduler.scheduled_job('interval', minutes=15)
async def send_scheduled_feeding_reminders():
    """Отправлять регулярные напоминания о кормлении по расписанию"""
    try:
        conn = sqlite3.connect("babybot.db")
        cur = conn.cursor()
        
        # Получаем все семьи с включенными уведомлениями
        cur.execute("SELECT family_id FROM settings WHERE tips_enabled = 1")
        families = cur.fetchall()
        
        for (family_id,) in families:
            # Получаем интервал кормления
            cur.execute("SELECT feed_interval FROM settings WHERE family_id = ?", (family_id,))
            interval_result = cur.fetchone()
            feed_interval = interval_result[0] if interval_result else 3
            
            # Получаем время последнего кормления
            last_feeding = get_last_feeding_time_for_family(family_id)
            
            if last_feeding:
                # Вычисляем, сколько времени прошло
                time_since_last = datetime.now() - last_feeding
                hours_since_last = time_since_last.total_seconds() / 3600
                
                # Если прошло примерно интервал кормления, отправляем напоминание
                if abs(hours_since_last - feed_interval) <= 0.25:  # ±15 минут
                    # Получаем всех членов семьи
                    cur.execute("SELECT user_id FROM family_members WHERE family_id = ?", (family_id,))
                    members = cur.fetchall()
                    
                    message = (
                        f"🍼 **Время кормления!**\n\n"
                        f"⏰ Прошло: {hours_since_last:.1f} ч. с последнего кормления\n"
                        f"📅 Последнее кормление: {last_feeding.strftime('%H:%M')}\n"
                        f"🔄 Интервал: {feed_interval} ч.\n\n"
                        f"💡 Пора покормить малыша!"
                    )
                    
                    # Отправляем уведомление всем членам семьи
                    for (user_id,) in members:
                        try:
                            await client.send_message(user_id, message)
                            print(f"✅ Отправлено регулярное напоминание о кормлении пользователю {user_id}")
                        except Exception as e:
                            print(f"❌ Ошибка отправки регулярного напоминания пользователю {user_id}: {e}")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка в send_scheduled_feeding_reminders: {e}")

class HealthCheckHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            response = f"""
            <html>
            <head><title>BabyCareBot Health Check</title></head>
            <body>
                <h1>🍼 BabyCareBot</h1>
                <p>Status: ✅ Running</p>
                <p>Time: {time.strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p>Bot is working in background</p>
            </body>
            </html>
            """
            self.wfile.write(response.encode())
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            response = '{"status": "healthy", "service": "babycare-bot"}'
            self.wfile.write(response.encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server(port=8000):
    """Запуск HTTP сервера для health checks"""
    try:
        with socketserver.TCPServer(("", port), HealthCheckHandler) as httpd:
            print(f"🌐 Health check server started on port {port}")
            httpd.serve_forever()
    except Exception as e:
        print(f"❌ Health check server error: {e}")

async def start_bot():
    # Запускаем health сервер в отдельном потоке
    health_thread = threading.Thread(target=start_health_server, daemon=True)
    health_thread.start()
    print("🌐 Health check server started")
    
    scheduler.start()
    print("✅ Бот запущен!")
    await client.run_until_disconnected()

# Запуск бота
if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(start_bot())
