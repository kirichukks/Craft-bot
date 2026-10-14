import os
from threading import Thread
from flask import Flask
import telebot
from telebot.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    WebAppInfo,
)

# ----------------------------------------------------
# 1. Веб-сервер Flask для бесплатного тарифа Render
# ----------------------------------------------------
app = Flask('')


@app.route('/')
def home():
  return 'CRAFT POS Bot is alive!'


def run():
  # Render автоматически передает порт через переменную PORT
  port = int(os.environ.get('PORT', 8080))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = Thread(target=run)
  t.daemon = True
  t.start()


# Запускаем фоновый веб-сервер, чтобы Render видел открытый порт
keep_alive()

# ----------------------------------------------------
# 2. Инициализация Telegram Бота
# ----------------------------------------------------
TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEBAPP_URL = os.environ.get(
    'WEBAPP_URL', 'https://craft-pos-mobile.vercel.app'
)

if not TOKEN:
  raise ValueError('Ошибка: Переменная TELEGRAM_TOKEN не задана!')

bot = telebot.TeleBot(TOKEN)


# ----------------------------------------------------
# 3. Обработчики команд Telegram
# ----------------------------------------------------
@bot.message_handler(commands=['start'])
def send_welcome(message):
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

  bot.reply_to(message, welcome_text, reply_markup=markup, parse_mode='Markdown')


# ----------------------------------------------------
# 4. Запуск Long Polling
# ----------------------------------------------------
if __name__ == '__main__':
  print('Бот успешно запущен...')
  bot.infinity_polling(timeout=10, long_polling_timeout=5)
