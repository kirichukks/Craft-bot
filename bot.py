import os
import sys
from threading import Thread
from flask import Flask
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

print("Инициализация скрипта бота...", flush=True)

# ----------------------------------------------------
# 1. Веб-сервер Flask для бесплатного тарифа Render
# ----------------------------------------------------
app = Flask('')


@app.route('/')
def home():
  return 'CRAFT POS Bot is alive!'


def run():
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = Thread(target=run)
  t.daemon = True
  t.start()
  print('Веб-сервер Flask запущен в фоне.', flush=True)


# Запускаем фоновый веб-сервер
keep_alive()

# ----------------------------------------------------
# 2. Инициализация Telegram Бота
# ----------------------------------------------------
TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEBAPP_URL = os.environ.get(
    'WEBAPP_URL', 'https://craft-pos-mobile.vercel.app'
)

if not TOKEN:
  print('КРИТИЧЕСКАЯ ОШИБКА: TELEGRAM_TOKEN не найден!', flush=True)
  sys.exit(1)

bot = telebot.TeleBot(TOKEN)

# Принудительно сбрасываем любые зависшие вебхуки при старте
try:
  bot.remove_webhook()
except Exception:
  pass


@bot.message_handler(commands=['start'])
def send_welcome(message):
  try:
    markup = InlineKeyboardMarkup()
    web_app_button = InlineKeyboardButton(
        text='Открыть CRAFT POS 🚀', web_app=WebAppInfo(url=WEBAPP_URL)
    )
    markup.add(web_app_button)

    welcome_text = (
        f'Приветствую, {message.from_user.first_name}!\n\n'
        'Добро пожаловать в рабочую систему **CRAFT Bar**.\n'
        'Нажмите кнопку ниже для запуска терминала POS:'
    )

    bot.reply_to(
        message, welcome_text, reply_markup=markup, parse_mode='Markdown'
    )
    print(
        f'Успешно отправлен ответ на /start пользователю {message.from_user.id}',
        flush=True,
    )
  except Exception as e:
    print(f'Ошибка при обработке /start: {e}', flush=True)


# ----------------------------------------------------
# 3. Запуск Long Polling
# ----------------------------------------------------
if __name__ == '__main__':
  print('Запуск polling Telegram API...', flush=True)
  try:
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
  except Exception as e:
    print(f'Ошибка в polling: {e}', flush=True)
