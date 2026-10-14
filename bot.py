import os
from threading import Thread
import telebot
from flask import Flask
from supabase import create_client, Client

# --- 1. МИНИ-СЕРВЕР ДЛЯ RENDER (ЧТОБЫ БОТ НЕ ЗАСЫПАЛ) ---
app = Flask('')


@app.route('/')
def home():
  return 'CRAFT POS Bot is alive and running!', 200


def run_web():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


Thread(target=run_web).daemon = True
# ---------------------------------------------------------

# --- 2. КОНФИГУРАЦИЯ БОТА И БАЗЫ ДАННЫХ ---
TOKEN = '8701487976:AAGCfF3R539D4Q3il0DpXStrEi3APfMOw8U'
bot = telebot.TeleBot(TOKEN)

# Список ID администраторов (Вы и Лили)
ADMIN_IDS = [8449487962, 399806055]

# Данные Supabase (замените на ваши актуальные ключи, если они отличаются)
SUPABASE_URL = os.environ.get('SUPABASE_URL', 'https://lufsjsvsekknomjvachk.supabase.co')
SUPABASE_KEY = os.environ.get(
    'SUPABASE_KEY',
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...',  # Укажите ваш секретный ключ Supabase, если не задан в переменных окружения Render
)

# Инициализация клиента Supabase (если ключи заданы)
supabase: Client = None
try:
  if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
  print(f'Ошибка подключения к Supabase: {e}')


# Проверка на администратора
def is_admin(user_id):
  return user_id in ADMIN_IDS


# --- 3. ОБРАБОТЧИКИ КОМАНД ---


@bot.message_handler(commands=['start'])
def send_welcome(user_message):
  user_id = user_message.from_user.id
  if not is_admin(user_id):
    bot.reply_to(
        user_message,
        '⛔ У вас нет доступа к управлению кофейней CRAFT. Запрос на доступ'
        ' отправлен администраторам.',
    )
    # Можно отправить уведомление админам о попытке входа
    for admin_id in ADMIN_IDS:
      try:
        bot.send_message(
            admin_id,
            f'⚠️ Пользователь @{user_message.from_user.username} (ID:'
            f' `{user_id}`) попытался запустить бота.',
            parse_mode='Markdown',
        )
      except:
        pass
    return

  bot.reply_to(
      user_message,
      '☕ Приветствую в системе управления кофейней **CRAFT**!\nДоступ'
      ' разрешен ✅.\n\nИспользуйте команды для работы с категориями и товарами.',
      parse_mode='Markdown',
  )


@bot.message_handler(commands=['categories'])
def show_categories(user_message):
  if not is_admin(user_message.from_user.id):
    return

  if not supabase:
    bot.reply_to(user_message, '❌ База данных Supabase не подключена.')
    return

  try:
    response = supabase.table('categories').select('*').execute()
    categories = response.data

    if not categories:
      bot.reply_to(user_message, '📭 Список категорий пока пуст.')
      return

    text = '📋 **Категории товаров в CRAFT:**\n\n'
    for cat in categories:
      # Настройте поля под структуру вашей таблицы (например, name или title)
      cat_name = cat.get('name', cat.get('title', 'Без названия'))
      text += f'• {cat_name}\n'

    bot.reply_to(user_message, text, parse_mode='Markdown')
  except Exception as e:
    bot.reply_to(user_message, f'❌ Ошибка при получении категорий: {e}')


@bot.message_handler(func=lambda message: True)
def echo_all(user_message):
  if not is_admin(user_message.from_user.id):
    return
  bot.reply_to(
      user_message,
      'Используйте команды для управления, например /categories',
  )


# --- 4. ЗАПУСК БОТА ---
if __name__ == '__main__':
  print('Бот управления кофейней CRAFT запущен и готов к работе...')
  bot.infinity_polling(skip_pending=True)
