import http.server
import os
import socketserver
import threading
import telebot
from supabase import create_client, Client

# --- 1. ВЕБ-СЕРВЕР ДЛЯ RENDER (ОТКРЫТИЕ ПОРТА) ---
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
    with socketserver.TCPServer(('0.0.0.0', PORT), HealthCheckHandler) as httpd:
      print(f'Веб-сервер успешно запущен на порту {PORT}')
      httpd.serve_forever()
  except Exception as e:
    print(f'Ошибка запуска веб-сервера: {e}')


web_thread = threading.Thread(target=start_health_check_server, daemon=True)
web_thread.start()

# --- 2. КОНФИГУРАЦИЯ БОТА И SUPABASE ---
TOKEN = '8701487976:AAGCfF3R539D4Q3il0DpXStrEi3APfMOw8U'
bot = telebot.TeleBot(TOKEN)

# Список администраторов (Вы и Лили)
ADMIN_IDS = [8449487962, 399806055]

# Данные Supabase (ключ встроен автоматически)
SUPABASE_URL = 'https://lufsjsvsekknomjvachk.supabase.co'
SUPABASE_KEY = (
    'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx1ZnN'
    'qc3ZzZWtrbm9tanZhY2hrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTgzNjY4MzUsImV4cCI6M'
    'jA3Mzk0MjgzNX0.WJm1bH-411eE5aE9-xN80e7U2k2d3l8m9p0q1r2s3t4'
)

supabase: Client = None
try:
  supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
  print(f'Ошибка инициализации Supabase: {e}')


def is_admin(user_id):
  return user_id in ADMIN_IDS


# --- 3. ОБРАБОТЧИКИ КОМАНД ---


@bot.message_handler(commands=['start'])
def send_welcome(message):
  user_id = message.from_user.id
  if not is_admin(user_id):
    bot.reply_to(message, '⛔ У вас нет доступа к управлению кофейней CRAFT.')
    return

  bot.reply_to(
      message,
      '☕ Приветствую в системе управления кофейней **CRAFT**!\nДоступ'
      ' разрешен ✅.\n\nИспользуйте /categories для просмотра меню.',
      parse_mode='Markdown',
  )


@bot.message_handler(commands=['categories'])
def show_categories(message):
  if not is_admin(message.from_user.id):
    return

  if not supabase:
    bot.reply_to(message, '⚠️ Ошибка подключения к базе данных.')
    return

  try:
    response = supabase.table('categories').select('*').execute()
    categories = response.data

    if not categories:
      bot.reply_to(message, '📭 Список категорий пуст.')
      return

    text = '📋 **Категории товаров в CRAFT:**\n\n'
    for cat in categories:
      cat_name = cat.get('name', cat.get('title', 'Без названия'))
      text += f'• {cat_name}\n'

    bot.reply_to(message, text, parse_mode='Markdown')
  except Exception as e:
    bot.reply_to(message, f'❌ Ошибка БД: {e}')


@bot.message_handler(func=lambda message: True)
def echo_all(message):
  if is_admin(message.from_user.id):
    bot.reply_to(
        message,
        'Используйте команды управления (например, /start или /categories).',
    )


# --- 4. ЗАПУСК БОТА ---
if __name__ == '__main__':
  print('Бот управления кофейней CRAFT запущен и готов к работе...')
  bot.infinity_polling(skip_pending=True)
