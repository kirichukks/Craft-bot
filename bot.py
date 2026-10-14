import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton
import json
import os

# Токен вашего бота
TOKEN = "8701487976:AAGCfF3R539D4Q3il0DpXStrEi3APfMOw8U"
bot = telebot.TeleBot(TOKEN)

# Список всех администраторов с полными правами (вы и Lili)
ADMIN_IDS = [
    8449487962,  # Ваш ID
    399806055,   # ID Lili
]

# БЕЛЫЙ СПИСОК (все администраторы автоматически имеют доступ)
ALLOWED_USERS = list(ADMIN_IDS)

# Файл для сохранения данных (склад и техкарты)
DATA_FILE = "craft_data.json"

# Временные состояния для пошагового ввода
user_states = {}

# --- Работа с базой данных (JSON) ---
def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "stock": {"Зерно кофе (кг)": 5.5, "Молоко 2.5% (л)": 12.0, "Стаканы 300мл (шт)": 150},
        "recipes": {
            "Капучино": "Эспрессо: 1 порц, Молоко: 180 мл, Стакан 300мл: 1 шт",
            "Эспрессо": "Кофе в зернах: 18 г"
        }
    }

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"[ERROR] Не удалось сохранить данные: {e}")

db = load_data()


# --- Главное меню ---
def get_main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    btn_stock = KeyboardButton("📦 Склад")
    btn_add_stock = KeyboardButton("➕ Добавить товар")
    btn_recipes = KeyboardButton("📋 Техкарты")
    btn_add_recipe = KeyboardButton("➕ Добавить техкарту")
    btn_help = KeyboardButton("ℹ️ Помощь")
    markup.add(btn_stock, btn_add_stock)
    markup.add(btn_recipes, btn_add_recipe)
    markup.add(btn_help)
    return markup


@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    username = message.from_user.username or "Без юзернейма"
    first_name = message.from_user.first_name or "Имя скрыто"
    
    if user_id not in ALLOWED_USERS:
        bot.reply_to(
            message, 
            "🔒 Эта система управления CRAFT BAR закрыта.\n"
            "Ваш запрос на доступ отправлен администраторам. Ожидайте подтверждения."
        )
        
        alert_text = (
            f"🚨 **Попытка доступа к боту!**\n\n"
            f"👤 Имя: {first_name}\n"
            f"🔗 Юзернейм: @{username}\n"
            f"🆔 ID: `{user_id}`\n\n"
            f"👉 **Чтобы РАЗРЕШИТЬ:** сделайте Reply (ответ) на это сообщение цифрой `1`\n"
            f"👉 **Чтобы ЗАПРЕТИТЬ:** сделайте Reply цифрой `0`"
        )
        
        # Рассылаем уведомление ВСЕМ администраторам
        for adm_id in ADMIN_IDS:
            try:
                bot.send_message(adm_id, alert_text, parse_mode="Markdown")
            except Exception as e:
                print(f"[ERROR] Ошибка отправки админу {adm_id}: {e}")
        return

    bot.send_message(
        message.chat.id, 
        "👋 Добро пожаловать в систему управления кофейней **CRAFT**!\n"
        "Выберите нужное действие на клавиатуре ниже:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )


# --- 1. Обработка Reply-ответов администраторов (выдача доступа) ---
@bot.message_handler(func=lambda message: message.from_user.id in ADMIN_IDS and message.reply_to_message is not None)
def handle_admin_reply(message):
    reply_text = message.reply_to_message.text
    if not reply_text or "Попытка доступа к боту!" not in reply_text:
        return
        
    try:
        lines = reply_text.split("\n")
        target_id = None
        for line in lines:
            if "🆔 ID:" in line:
                target_id = int(line.replace("🆔 ID:", "").replace("`", "").strip())
                break
                
        if not target_id:
            bot.reply_to(message, "⚠️ Не удалось распознать ID пользователя в сообщении.")
            return

        command = message.text.strip()
        
        if command == "1":
            if target_id not in ALLOWED_USERS:
                ALLOWED_USERS.append(target_id)
                print(f"[OK] Пользователь {target_id} добавлен в ALLOWED_USERS. Список: {ALLOWED_USERS}")
            
            bot.reply_to(message, f"✅ Доступ для ID `{target_id}` **разрешен**.", parse_mode="Markdown")
            try:
                bot.send_message(
                    target_id, 
                    "🎉 Администратор одобрил ваш запрос! Добро пожаловать в систему CRAFT.", 
                    reply_markup=get_main_menu()
                )
            except Exception as e:
                print(f"[WARNING] Не удалось отправить сообщение пользователю: {e}")
                
        elif command == "0":
            bot.reply_to(message, f"❌ Доступ для ID `{target_id}` **запрещен**.", parse_mode="Markdown")
            try:
                bot.send_message(target_id, "⛔ К сожалению, администратор отклонил ваш запрос на доступ.")
            except Exception:
                pass
        else:
            bot.reply_to(message, "⚠️ Отправьте `1` чтобы разрешить, или `0` чтобы запретить.", parse_mode="Markdown")
            
    except Exception as e:
        print(f"[ERROR] Ошибка обработки ответа админа: {e}")
        bot.reply_to(message, "⚠️ Произошла ошибка при обработке команды.")


# --- 2. Обработка команд /users и /remove (доступно всем админам) ---
@bot.message_handler(commands=['users'])
def list_users(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    users_list_str = "\n".join([f"• `{uid}`" for uid in ALLOWED_USERS])
    bot.reply_to(message, f"📋 **Активные пользователи:**\n{users_list_str}", parse_mode="Markdown")


@bot.message_handler(commands=['remove'])
def remove_user(message):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.reply_to(message, "⚠️ Укажите ID. Пример: `/remove 123456789`", parse_mode="Markdown")
            return
            
        target_id = int(parts[1])
        if target_id in ADMIN_IDS:
            bot.reply_to(message, "⛔ Нельзя удалить администратора из белого списка через эту команду!")
            return
            
        if target_id in ALLOWED_USERS:
            ALLOWED_USERS.remove(target_id)
            bot.reply_to(message, f"✅ Пользователь с ID `{target_id}` удален.", parse_mode="Markdown")
            try:
                bot.send_message(target_id, "⛔ Администратор ограничил ваш доступ к системе CRAFT.")
            except Exception:
                pass
        else:
            bot.reply_to(message, "⚠️ Такого ID нет в списке.")
    except ValueError:
        bot.reply_to(message, "⚠️ Неверный формат ID.")


# --- 3. Обработка всех остальных текстовых сообщений и кнопок меню ---
@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    user_id = message.from_user.id
    
    if user_id not in ALLOWED_USERS:
        return

    text = message.text.strip()
    state = user_states.get(user_id)

    # Процесс добавления товара на склад
    if state == "waiting_stock_name":
        user_states[user_id] = {"name": text, "step": "waiting_stock_qty"}
        bot.reply_to(message, f"📦 Товар: **{text}**.\nТеперь отправьте его количество (например: `10` или `5.5`):", parse_mode="Markdown")
        return

    elif isinstance(state, dict) and state.get("step") == "waiting_stock_qty":
        try:
            qty = float(text.replace(",", "."))
            item_name = state["name"]
            db["stock"][item_name] = qty
            save_data(db)
            user_states.pop(user_id, None)
            bot.reply_to(message, f"✅ Товар **{item_name}** в количестве **{qty}** успешно добавлен/обновлен!", reply_markup=get_main_menu(), parse_mode="Markdown")
        except ValueError:
            bot.reply_to(message, "⚠️ Пожалуйста, введите число (например: `10` или `2.5`).")
        return

    # Процесс добавления техкарты
    if state == "waiting_recipe_name":
        user_states[user_id] = {"recipe_name": text, "step": "waiting_recipe_ingredients"}
        bot.reply_to(message, f"📋 Напиток: **{text}**.\nТеперь введите состав и граммовки (например: *Эспрессо 30мл, Молоко 150мл*):", parse_mode="Markdown")
        return

    elif isinstance(state, dict) and state.get("step") == "waiting_recipe_ingredients":
        recipe_name = state["recipe_name"]
        db["recipes"][recipe_name] = text
        save_data(db)
        user_states.pop(user_id, None)
        bot.reply_to(message, f"✅ Техкарта для **{recipe_name}** успешно сохранена!", reply_markup=get_main_menu(), parse_mode="Markdown")
        return

    # Кнопки меню
    if text == "📦 Склад":
        stock_items = db.get("stock", {})
        if not stock_items:
            msg = "📦 Склад пуст."
        else:
            msg = "📦 **Текущие остатки на складе:**\n\n"
            for item, qty in stock_items.items():
                msg += f"• {item}: **{qty}**\n"
        bot.reply_to(message, msg, parse_mode="Markdown")

    elif text == "➕ Добавить товар":
        user_states[user_id] = "waiting_stock_name"
        bot.reply_to(message, "✍️ Введите название нового товара или ингредиента (например: *Сироп ванильный*):")

    elif text == "📋 Техкарты":
        recipes = db.get("recipes", {})
        if not recipes:
            msg = "📋 Техкарты пока не добавлены."
        else:
            msg = "📋 **Технологические карты напитков:**\n\n"
            for name, ingr in recipes.items():
                msg += f"☕ **{name}**\n   Состав: {ingr}\n\n"
        bot.reply_to(message, msg, parse_mode="Markdown")

    elif text == "➕ Добавить техкарту":
        user_states[user_id] = "waiting_recipe_name"
        bot.reply_to(message, "✍️ Введите название нового напитка (например: *Латте*):")

    elif text == "ℹ️ Помощь":
        bot.reply_to(
            message, 
            "ℹ️ **Справка по системе CRAFT:**\n\n"
            "• Используйте кнопки меню для просмотра склада и техкарт.\n"
            "• Нажимайте «➕ Добавить товар» или «➕ Добавить техкарту» для изменения базы данных.\n"
            "• Команда `/users` — список доступов (админ).\n"
            "• Команда `/remove ID` — забрать доступ (админ).",
            parse_mode="Markdown"
        )


if __name__ == "__main__":
    try:
        print("Бот управления кофейней CRAFT запущен и готов к работе...")
        bot.infinity_polling()
    except Exception as e:
        print(f"\n❌ ПРОИЗОШЛА ОШИБКА: {e}")
        input("\nНажмите Enter, чтобы закрыть окно...")