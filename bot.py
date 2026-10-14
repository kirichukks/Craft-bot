import datetime
import os
import telebot
from telebot import types
from supabase import create_client, Client

# Получаем ключи и настройки из переменных окружения Render
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
WEBAPP_URL = os.environ.get("WEBAPP_URL", "https://craft-pos-mobile.vercel.app")
SUPER_ADMIN_ID = 8449487962  # Ваш hardcoded super-admin ID

bot = telebot.TeleBot(TELEGRAM_TOKEN)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def is_admin(user_id):
  if user_id == SUPER_ADMIN_ID:
    return True
  try:
    res = (
        supabase.table("users")
        .select("role")
        .eq("telegram_id", user_id)
        .execute()
    )
    if res.data and res.data[0].get("role") in ["admin", "owner"]:
      return True
  except Exception as e:
    print(f"Error checking admin: {e}")
  return False


@bot.message_handler(commands=["start"])
def handle_start(message):
  user = message.from_user
  telegram_id = user.id
  username = user.username or user.first_name

  # Автоочистка неактивных пользователей (старше 7 дней, у которых статус pending)
  try:
    limit_date = (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(days=7)
    ).isoformat()
    supabase.table("users").delete().eq("status", "pending").lt(
        "last_active", limit_date
    ).execute()
  except Exception as e:
    print(f"Cleanup error: {e}")

  # Проверяем наличие пользователя в базе
  try:
    res = (
        supabase.table("users")
        .select("*")
        .eq("telegram_id", telegram_id)
        .execute()
    )

    if telegram_id == SUPER_ADMIN_ID:
      # Супер-админ всегда имеет полный доступ
      if not res.data:
        supabase.table("users").insert({
            "telegram_id": telegram_id,
            "username": username,
            "status": "approved",
            "role": "owner",
            "last_active": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat(),
        }).execute()
      else:
        supabase.table("users").update({
            "last_active": datetime.datetime.now(
                datetime.timezone.utc
            ).isoformat()
        }).eq("telegram_id", telegram_id).execute()

      markup = types.InlineKeyboardMarkup()
      markup.add(
          types.InlineKeyboardButton(
              "📱 Открыть CRAFT POS (Склад и Техкарты)",
              web_app=types.WebAppInfo(url=WEBAPP_URL),
          )
      )
      bot.send_message(
          message.chat.id,
          "👋 Приветствую, Шеф! Доступ полный ✅.\n\nКоманды для управления:\n/users"
          " — меню управления пользователями",
          reply_markup=markup,
      )
      return

    if not res.data:
      # Новий користувач — додаємо зі статусом pending
      supabase.table("users").insert({
          "telegram_id": telegram_id,
          "username": username,
          "status": "pending",
          "role": "staff",
          "last_active": datetime.datetime.now(
              datetime.timezone.utc
          ).isoformat(),
      }).execute()

      # Сповіщаємо адміна
      admin_markup = types.InlineKeyboardMarkup()
      admin_markup.row(
          types.InlineKeyboardButton(
              "✅ Разрешить", callback_data=f"approve_{telegram_id}"
          ),
          types.InlineKeyboardButton(
              "❌ Отклонить", callback_data=f"reject_{telegram_id}"
          ),
      )
      bot.send_message(
          SUPER_ADMIN_ID,
          f"🔔 **Новая заявка на доступ!**\nПользователь: @{username}"
          f" (ID: `{telegram_id}`)",
          reply_markup=admin_markup,
          parse_mode="Markdown",
      )

      bot.send_message(
          message.chat.id,
          "⏳ Ваша заявка отправлена администратору. Ожидайте подтверждения.",
      )
    else:
      user_data = res.data[0]
      status = user_data.get("status")

      # Оновлюємо час останньої активності
      supabase.table("users").update({
          "last_active": datetime.datetime.now(datetime.timezone.utc).isoformat()
      }).eq("telegram_id", telegram_id).execute()

      if status == "approved":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "📱 Открыть CRAFT POS (Склад и Техкарты)",
                web_app=types.WebAppInfo(url=WEBAPP_URL),
            )
        )
        bot.send_message(
            message.chat.id,
            "✅ Доступ подтвержден! Нажмите кнопку ниже для открытия системы:",
            reply_markup=markup,
        )
      elif status == "pending":
        bot.send_message(
            message.chat.id,
            "⏳ Ваша заявка находится на рассмотрении у администратора.",
        )
      else:
        bot.send_message(message.chat.id, "❌ Доступ к системе отклонен.")

  except Exception as e:
    print(f"Start command error: {e}")
    bot.send_message(
        message.chat.id, "⚠️ Произошла ошибка при подключении к базе данных."
    )


@bot.message_handler(commands=["users"])
def handle_users_menu(message):
  if not is_admin(message.from_user.id):
    bot.send_message(message.chat.id, "⛔ У вас нет прав для этой команды.")
    return

  try:
    res = supabase.table("users").select("*").execute()
    users = res.data
    if not users:
      bot.send_message(message.chat.id, "📭 Список пользователей пуст.")
      return

    for u in users:
      uid = u.get("telegram_id")
      uname = u.get("username", "Unknown")
      status = u.get("status", "unknown")
      role = u.get("role", "staff")

      text = (
          f"👤 **{uname}**\nID: `{uid}`\nСтатус: `{status}`\nРоль: `{role}`"
      )
      markup = types.InlineKeyboardMarkup()

      if status == "pending":
        markup.row(
            types.InlineKeyboardButton(
                "✅ Разрешить", callback_data=f"approve_{uid}"
            ),
            types.InlineKeyboardButton(
                "❌ Отклонить", callback_data=f"reject_{uid}"
            ),
        )
      else:
        markup.add(
            types.InlineKeyboardButton("🗑 Удалить", callback_data=f"delete_{uid}")
        )

      bot.send_message(
          message.chat.id, text, reply_markup=markup, parse_mode="Markdown"
      )
  except Exception as e:
    print(f"Users menu error: {e}")
    bot.send_message(message.chat.id, "⚠️ Ошибка при загрузке пользователей.")


# Универсальный обработчик всех нажатий инлайн-кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
  data = call.data
  try:
    if data.startswith("approve_"):
      target_id = int(data.split("_")[1])
      supabase.table("users").update({"status": "approved"}).eq(
          "telegram_id", target_id
      ).execute()
      bot.answer_callback_query(call.id, "Пользователь одобрен ✅")
      bot.edit_message_text(
          f"{call.message.text}\n\n✅ **СТАТУС: ОДОБРЕНО**",
          call.message.chat.id,
          call.message.message_id,
          parse_mode="Markdown",
      )
      # Уведомляем самого пользователя
      try:
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton(
                "📱 Открыть CRAFT POS (Склад и Техкарты)",
                web_app=types.WebAppInfo(url=WEBAPP_URL),
            )
        )
        bot.send_message(
            target_id,
            "🎉 Ваш доступ одобрен! Нажмите кнопку ниже для открытия склада:",
            reply_markup=markup,
        )
      except Exception:
        pass

    elif data.startswith("reject_"):
      target_id = int(data.split("_")[1])
      supabase.table("users").update({"status": "rejected"}).eq(
          "telegram_id", target_id
      ).execute()
      bot.answer_callback_query(call.id, "Доступ отклонен ❌")
      bot.edit_message_text(
          f"{call.message.text}\n\n❌ **СТАТУС: ОТКЛОНЕНО**",
          call.message.chat.id,
          call.message.message_id,
          parse_mode="Markdown",
      )
      try:
        bot.send_message(
            target_id, "❌ К сожалению, ваш запрос на доступ был отклонен."
        )
      except Exception:
        pass

    elif data.startswith("delete_"):
      target_id = int(data.split("_")[1])
      supabase.table("users").delete().eq(
          "telegram_id", target_id
      ).execute()
      bot.answer_callback_query(call.id, "Пользователь удален 🗑")
      bot.edit_message_text(
          f"{call.message.text}\n\n🗑 **УДАЛЕНО**",
          call.message.chat.id,
          call.message.message_id,
          parse_Mode="Markdown",
      )
  except Exception as e:
    print(f"Callback error: {e}")
    bot.answer_callback_query(call.id, "⚠️ Произошла ошибка.")


if __name__ == "__main__":
  print("Bot started successfully...")
  bot.infinity_polling()
