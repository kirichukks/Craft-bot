import datetime
import http.server
import os
import socketserver
import threading
import telebot
from telebot import types
from supabase import create_client, Client

# --- 1. ВЕБ-СЕРВЕР ДЛЯ RENDER ---
PORT = int(os.environ.get('PORT', 10000))

class HealthCheckHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b'CRAFT POS Bot is alive and running!')
    def log_message(self, format, *args):
        return

def start_health_check_server():
    try:
        with socketserver.TCPServer(("0.0.0.0", PORT), HealthCheckHandler) as httpd:
            httpd.serve_forever()
    except Exception as e:
        print(f"Ошибка веб-сервера: {e}")

threading.Thread(target=start_health_check_server, daemon=True).start()

# --- 2. ИНИЦИАЛИЗАЦИЯ ---
TOKEN = '8701487976:AAGCfF3R539D4Q3il0DpXStrEi3APfMOw8U'
bot = telebot.TeleBot(TOKEN)

# Ваш Главный Telegram ID (вечный админ)
SUPER_ADMIN_ID = 8449487962 

SUPABASE_URL = 'https://lufsjsvsekknomjvachk.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx1ZnNqc3ZzZWtrbm9tanZhY2hrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgzNjY4MzUsImV4cCI6MjA3Mzk0MjgzNX0.WJm1bH-411eE5aE9-xN80e7U2k2d3l8m9p0q1r2s3t4'

supabase: Client = None
try:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    print(f"Ошибка Supabase: {e}")

# Функция автоочистки неактивных пользователей (> 7 дней)
def cleanup_inactive_users():
    if not supabase:
        return
    try:
        limit_date = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()
        supabase.table('users').delete().neq('telegram_id', SUPER_ADMIN_ID).lt('last_active', limit_date).execute()
    except Exception as e:
        print(f"Ошибка при автоочистке пользователей: {e}")

# --- 3. ОБРАБОТЧИКИ КОМАНД ---
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без юзернейма"
    full_name = f"{message.from_user.first_name or ''} {message.from_user.last_name or ''}".strip()

    cleanup_inactive_users()

    if user_id == SUPER_ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        web_app_url = 'https://craft-pos-mobile.vercel.app'
        markup.add(types.InlineKeyboardButton(text="📱 Открыть CRAFT POS (Склад и Техкарты)", web_app=types.WebAppInfo(url=web_app_url)))
        
        bot.send_message(message.chat.id, "👋 Приветствую, Шеф! Доступ полный ✅.\n\nКоманды для управления:\n/users — меню управления пользователями", reply_markup=markup)
        update_user_activity(user_id, username, full_name, 'approved')
        return

    if supabase:
        try:
            res = supabase.table('users').select('*').eq('telegram_id', user_id).execute()
            user_data = res.data
        except Exception:
            user_data = []

        if user_data and user_data[0].get('status') == 'approved':
            update_user_activity(user_id, username, full_name, 'approved')
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="📱 Открыть CRAFT POS", web_app=types.WebAppInfo(url='https://craft-pos-mobile.vercel.app')))
            bot.send_message(message.chat.id, "✅ Доступ разрешен.", reply_markup=markup)
        else:
            update_user_activity(user_id, username, full_name, 'pending')
            
            bot.send_message(
                message.chat.id, 
                "⏳ Вашего доступа нет в системе или срок его действия истек (не заходили более 7 дней).\nЗапрос отправлен главному администратору. Ожидайте подтверждения."
            )

            markup = types.InlineKeyboardMarkup(row_width=2)
            btn_allow = types.InlineKeyboardButton("✅ Разрешить", callback_data=f"allow_{user_id}")
            btn_deny = types.InlineKeyboardButton("❌ Отклонить", callback_data=f"deny_{user_id}")
            markup.add(btn_allow, btn_deny)

            bot.send_message(
                SUPER_ADMIN_ID, 
                f"🔔 **Новый запрос на доступ в CRAFT POS!**\n\nИмя: {full_name}\nUsername: @{username}\nID: `{user_id}`",
                reply_markup=markup,
                parse_mode="Markdown"
            )

def update_user_activity(user_id, username, full_name, status):
    if not supabase:
        return
    try:
        supabase.table('users').upsert({
            'telegram_id': user_id,
            'username': username,
            'full_name': full_name,
            'status': status,
            'last_active': datetime.datetime.utcnow().isoformat()
        }).execute()
    except Exception as e:
        print(f"Ошибка обновления пользователя: {e}")

# Интерактивное меню пользователей: /users
@bot.message_handler(commands=['users'])
def list_users(message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    if not supabase:
        bot.reply_to(message, "⚠️ Ошибка БД.")
        return

    try:
        res = supabase.table('users').select('*').execute()
        users = res.data
        if not users:
            bot.reply_to(message, "📭 Список пользователей пуст.")
            return

        for u in users:
            uid = u.get('telegram_id')
            name = u.get('full_name') or "Без имени"
            uname = u.get('username') or "нет"
            status = u.get('status')

            # Пропускаем главного админа в списке на удаление
            if uid == SUPER_ADMIN_ID:
                continue

            text = f"👤 **{name}** (@{uname})\n🆔 ID: `{uid}`\n📌 Статус: `{status}`"
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(f"🗑 Удалить {name}", callback_data=f"del_{uid}"))
            
            bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode='Markdown')

        bot.send_message(message.chat.id, "📋 Выше представлен список всех сотрудников. Для удаления просто нажмите кнопку под карточкой пользователя.")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# Обработка нажатий на все кнопки (Разрешить, Отклонить, Удалить)
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    if call.from_user.id != SUPER_ADMIN_ID:
        bot.answer_callback_query(call.id, "У вас нет прав.")
        return

    data = call.data

    # 1. Разрешить доступ
    if data.startswith('allow_'):
        target_id = int(data.split('_')[1])
        try:
            supabase.table('users').update({'status': 'approved'}).eq('telegram_id', target_id).execute()
            bot.answer_callback_query(call.id, "Доступ разрешен!")
            bot.edit_message_text(f"✅ Доступ для пользователя `{target_id}` **разрешен**.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(text="📱 Открыть CRAFT POS", web_app=types.WebAppInfo(url='https://craft-pos-mobile.vercel.app')))
            bot.send_message(target_id, "🎉 Администратор одобрил ваш доступ! Нажмите кнопку ниже для входа:", reply_markup=markup)
        except Exception as e:
            bot.answer_callback_query(call.id, f"Ошибка: {e}")

    # 2. Отклонить доступ
    elif data.startswith('deny_'):
        target_id = int(data.split('_')[1])
        try:
            supabase.table('users').update({'status': 'blocked'}).eq('telegram_id', target_id).execute()
            bot.answer_callback_query(call.id, "Доступ отклонен.")
            bot.edit_message_text(f"❌ Доступ для пользователя `{target_id}` **отклонен**.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            bot.send_message(target_id, "⛔ Администратор отклонил ваш запрос на доступ.")
        except Exception as e:
            bot.answer_callback_query(call.id, f"Ошибка: {e}")

    # 3. Удалить пользователя через меню
    elif data.startswith('del_'):
        target_id = int(data.split('_')[1])
        try:
            supabase.table('users').delete().eq('telegram_id', target_id).execute()
            bot.answer_callback_query(call.id, "Пользователь удален.")
            bot.edit_message_text(f"🗑 Пользователь с ID `{target_id}` **удален** из системы.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
            
            try:
                bot.send_message(target_id, "⛔ Ваш доступ к CRAFT POS был отозван администратором.")
            except Exception:
                pass
        except Exception as e:
            bot.answer_callback_query(call.id, f"Ошибка: {e}")

@bot.message_handler(commands=['categories'])
def show_categories(message):
    if message.from_user.id != SUPER_ADMIN_ID:
        return
    if not supabase:
        bot.reply_to(message, "⚠️ Ошибка БД.")
        return

    try:
        response = supabase.table('categories').select('*').execute()
        categories = response.data
        if not categories:
            bot.reply_to(message, "📭 Список пуст.")
            return

        text = "📋 **Категории товаров в CRAFT:**\n\n"
        for cat in categories:
            text += f"• {cat.get('name', cat.get('title', 'Без названия'))}\n"
        bot.reply_to(message, text, parse_mode='Markdown')
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

if __name__ == '__main__':
    print("Бот с интерактивным меню запущен...")
    bot.infinity_polling(skip_pending=True)
