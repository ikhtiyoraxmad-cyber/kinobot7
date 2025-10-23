import os
import json
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Konfiguratsiya
BOT_TOKEN = "SIZNING_BOT_TOKEN"  # @BotFather dan olingan token
ADMIN_ID = 123456789  # Admin Telegram ID

# Ma'lumotlar bazasi (JSON fayllar)
USERS_FILE = "users.json"
MOVIES_FILE = "movies.json"
PREMIUM_REQUESTS_FILE = "premium_requests.json"

# Global o'zgaruvchilar
FREE_LIMIT = 3


# Ma'lumotlarni yuklash
def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def save_data(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


users = load_data(USERS_FILE)
movies = load_data(MOVIES_FILE)
premium_requests = load_data(PREMIUM_REQUESTS_FILE)


# Foydalanuvchi ma'lumotlarini yangilash
def update_user(user_id, username):
    user_id_str = str(user_id)
    if user_id_str not in users:
        users[user_id_str] = {
            "username": username,
            "used_codes": 0,
            "is_premium": False,
            "joined_date": datetime.now().isoformat()
        }
    else:
        users[user_id_str]["username"] = username
    save_data(USERS_FILE, users)


# /start komandasi
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    update_user(user.id, user.username or "username_yoq")

    keyboard = [
        [InlineKeyboardButton("🎬 Kino kodini kiritish", callback_data="enter_code")],
        [InlineKeyboardButton("💎 Premium obuna bilan tanishish", callback_data="premium_info")],
        [InlineKeyboardButton("📊 Mening statistikam", callback_data="my_stats")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 Assalomu aleykum, {user.first_name}!\n\n"
        "🎬 Kino bot xizmatiga xush kelibsiz!\n\n"
        "Kino kodini kiriting va kinolardan bahramand bo'ling.\n"
        "Bepul foydalanuvchilar 3 ta kinoni ko'rishlari mumkin.",
        reply_markup=reply_markup
    )


# Tugmachalar uchun callback handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)

    if query.data == "enter_code":
        await query.edit_message_text("🔢 Iltimos, kino kodini kiriting:")
        context.user_data['waiting_for'] = 'code'

    elif query.data == "premium_info":
        await show_premium_info(query)

    elif query.data == "my_stats":
        await show_user_stats(query, user_id)

    elif query.data == "subscribe_premium":
        await query.edit_message_text(
            "💎 Premium obunaga a'zo bo'lish uchun:\n\n"
            "📢 Kanal yoki guruh silkasini yuboring.\n"
            "Silkangiz ko'rib chiqilgandan so'ng, sizga premium bot va kanallar linklari yuboriladi."
        )
        context.user_data['waiting_for'] = 'channel_link'

    elif query.data == "back_to_main":
        keyboard = [
            [InlineKeyboardButton("🎬 Kino kodini kiritish", callback_data="enter_code")],
            [InlineKeyboardButton("💎 Premium obuna bilan tanishish", callback_data="premium_info")],
            [InlineKeyboardButton("📊 Mening statistikam", callback_data="my_stats")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🏠 Asosiy menyu",
            reply_markup=reply_markup
        )


# Premium ma'lumotini ko'rsatish
async def show_premium_info(query):
    keyboard = [
        [InlineKeyboardButton("✅ Premium obunaga a'zo bo'lish", callback_data="subscribe_premium")],
        [InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        "💎 PREMIUM OBUNA\n\n"
        "✨ Premium obuna afzalliklari:\n\n"
        "🎬 Cheksiz kino ko'rish\n"
        "🚀 Tezkor yuklanish\n"
        "🎯 Yangi kinolarga birinchi bo'lib kirish\n"
        "📺 Premium bot va kanallarga kirish\n"
        "🎁 Maxsus bonuslar\n\n"
        "Premium obuna olish uchun:\n"
        "👉 O'zingizning kanal yoki guruh silkasini yuboring\n"
        "👉 Adminlar ko'rib chiqadi\n"
        "👉 Tasdiqlangandan so'ng premium statusga ega bo'lasiz",
        reply_markup=reply_markup
    )


# Foydalanuvchi statistikasi
async def show_user_stats(query, user_id):
    user_data = users.get(user_id, {})
    used_codes = user_data.get("used_codes", 0)
    is_premium = user_data.get("is_premium", False)

    keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_to_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    status = "💎 Premium" if is_premium else f"🆓 Bepul ({FREE_LIMIT - used_codes} ta qoldi)"

    await query.edit_message_text(
        f"📊 SIZNING STATISTIKANGIZ\n\n"
        f"👤 Username: @{user_data.get('username', 'noma\'lum')}\n"
        f"🎬 Foydalanilgan kodlar: {used_codes}\n"
        f"📌 Status: {status}",
        reply_markup=reply_markup
    )


# Xabarlarni qayta ishlash
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    username = update.effective_user.username or "username_yoq"
    text = update.message.text

    update_user(update.effective_user.id, username)

    waiting_for = context.user_data.get('waiting_for')

    if waiting_for == 'code':
        await process_movie_code(update, context, user_id, text)
        context.user_data['waiting_for'] = None

    elif waiting_for == 'channel_link':
        await process_channel_link(update, context, user_id, username, text)
        context.user_data['waiting_for'] = None
    else:
        await update.message.reply_text(
            "Iltimos, /start buyrug'ini yuboring yoki tugmalardan foydalaning."
        )


# Kino kodini qayta ishlash
async def process_movie_code(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, code):
    user_data = users.get(user_id, {})
    used_codes = user_data.get("used_codes", 0)
    is_premium = user_data.get("is_premium", False)

    # Limitni tekshirish
    if not is_premium and used_codes >= FREE_LIMIT:
        await update.message.reply_text(
            "⚠️ Sizning limitingiz tugadi!\n\n"
            "Premium bot va kanallardan foydalanish uchun, o'zingizning kanal yoki guruh silkasini yuboring.\n\n"
            "Yuborilgan guruh va kanal silkalari tez fursat ichida ko'rib chiqiladi va sizga premium bot va kanallar linki yuboriladi.\n\n"
            "💎 Premium obuna haqida ma'lumot olish uchun 'Premium obuna bilan tanishish' tugmasini bosing."
        )
        return

    # Kinoni qidirish
    movie = movies.get(code)

    if not movie:
        await update.message.reply_text(
            "❌ Bunday kod topilmadi!\n\n"
            "Iltimos, to'g'ri kodni kiriting."
        )
        return

    # Kinoni yuborish
    await send_movie(update, context, user_id, movie)

    # Hisoblagichni yangilash
    if not is_premium:
        users[user_id]["used_codes"] = used_codes + 1
        save_data(USERS_FILE, users)


# Kinoni yuborish
async def send_movie(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, movie):
    # Video yoki rasmni yuborish
    if movie.get("type") == "video":
        message = await update.message.reply_video(
            video=movie["file_id"],
            caption=f"🎬 {movie['title']}\n\n⏱️ Bu xabar 10 sekunddan keyin o'chadi..."
        )
    elif movie.get("type") == "photo":
        message = await update.message.reply_photo(
            photo=movie["file_id"],
            caption=f"🖼️ {movie['title']}\n\n⏱️ Bu xabar 10 sekunddan keyin o'chadi..."
        )
    else:
        await update.message.reply_text(f"🎬 {movie['title']}")
        return

    # 10 sekund kutish va teskari sanoq
    for i in range(10, 0, -1):
        await asyncio.sleep(1)
        try:
            if i <= 5:  # Faqat oxirgi 5 sekundda yangilash
                await message.edit_caption(
                    caption=f"🎬 {movie['title']}\n\n⏱️ Xabar {i} sekunddan keyin o'chadi..."
                )
        except:
            pass

    # Xabarni o'chirish
    try:
        await message.delete()
        await update.message.reply_text("✅ Xabar o'chirildi.")
    except:
        pass


# Kanal/guruh silkasini qayta ishlash
async def process_channel_link(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id, username, link):
    # Premium so'rovni saqlash
    request_id = f"{user_id}_{datetime.now().timestamp()}"
    premium_requests[request_id] = {
        "user_id": user_id,
        "username": username,
        "link": link,
        "date": datetime.now().isoformat(),
        "status": "pending"
    }
    save_data(PREMIUM_REQUESTS_FILE, premium_requests)

    # Adminga xabar yuborish
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📩 YANGI PREMIUM SO'ROV\n\n"
                 f"👤 User ID: {user_id}\n"
                 f"📝 Username: @{username}\n"
                 f"🔗 Silka: {link}\n"
                 f"📅 Sana: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
    except:
        pass

    await update.message.reply_text(
        "✅ Sizning so'rovingiz qabul qilindi!\n\n"
        "Tez orada adminlar sizning silkangizni ko'rib chiqadi va premium bot va kanallar linklari yuboriladi.\n\n"
        "Sabr qiling! 🙏"
    )


# Admin komandasi - foydalanuvchilar ro'yxati
async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda ruxsat yo'q!")
        return

    if not users:
        await update.message.reply_text("📭 Hali foydalanuvchilar yo'q.")
        return

    user_list = "👥 FOYDALANUVCHILAR RO'YXATI\n\n"
    for user_id, data in users.items():
        status = "💎" if data.get("is_premium", False) else "🆓"
        user_list += f"{status} @{data['username']} (ID: {user_id})\n"
        user_list += f"   Kodlar: {data.get('used_codes', 0)}\n\n"

    await update.message.reply_text(user_list)


# Admin komandasi - kinolar ro'yxati
async def admin_movies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda ruxsat yo'q!")
        return

    if not movies:
        await update.message.reply_text("📭 Hali kinolar yo'q.")
        return

    movie_list = "🎬 KINOLAR RO'YXATI\n\n"
    for code, movie in movies.items():
        movie_list += f"Kod: {code}\n"
        movie_list += f"Nomi: {movie['title']}\n\n"

    await update.message.reply_text(movie_list)


# Admin komandasi - premium so'rovlar
async def admin_requests(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Sizda ruxsat yo'q!")
        return

    pending = [r for r in premium_requests.values() if r['status'] == 'pending']

    if not pending:
        await update.message.reply_text("📭 Yangi so'rovlar yo'q.")
        return

    request_list = "📩 PREMIUM SO'ROVLAR\n\n"
    for req in pending:
        request_list += f"👤 @{req['username']} (ID: {req['user_id']})\n"
        request_list += f"🔗 {req['link']}\n"
        request_list += f"📅 {req['date']}\n\n"

    await update.message.reply_text(request_list)


# Asosiy funksiya
def main():
    # Bot ilovasini yaratish
    application = Application.builder().token(BOT_TOKEN).build()

    # Handlerlarni qo'shish
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("users", admin_users))
    application.add_handler(CommandHandler("movies", admin_movies))
    application.add_handler(CommandHandler("requests", admin_requests))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Botni ishga tushirish
    print("🤖 Bot ishga tushdi...")
    application.run_polling()


if __name__ == "__main__":
    main()