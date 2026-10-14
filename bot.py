import os
import sys
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

print('Инициализация вебхук-бота...', flush=True)

TOKEN = os.environ.get('TELEGRAM_TOKEN')
WEBAPP_URL = os.environ.get(
    'WEBAPP_URL', 'https://craft-pos-mobile.vercel.app'
)
RENDER_EXTERNAL_URL = os.environ.get('RENDER_EXTERNAL_URL')  # Render сам подставит URL

if not TOKEN:
  print('КРИТИЧЕСКАЯ ОШИБКА: TELEGRAM_TOKEN не найден!', flush=True)
  sys.exit(1)

bot = telebot.TeleBot(TOKEN)
app = Flask('')


@app.route('/')
def home():
  return 'CRAFT POS Bot is alive (Webhook mode)!'


# Маршрут, на который Telegram будет присылать сообщения
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
  if request.headers.get('content-type') == 'application/json':
    json_string = request.get_data().decode('utf-8')
    update = telebot.types.Update.de_json(json_string)
    bot.process_new_updates([update])
    return '', 200
  else:
    return 'Forbidden', 403


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
  except Exception as e:
    print(f'Ошибка при обработке /start: {e}', flush=True)


if __name__ == '__main__':
  # Автоматически устанавливаем вебхук на адрес вашего сервиса в Render
  if RENDER_EXTERNAL_URL:
    webhook_url = f'{RENDER_EXTERNAL_URL}/{TOKEN}'
    bot.remove_webhook()
    bot.set_webhook(url=webhook_url)
    print(f'Вебхук успешно установлен на: {webhook_url}', flush=True)

  # Запуск Flask-сервера на порту Render
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)
