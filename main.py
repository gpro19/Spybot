import logging
import random
import os
import threading
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, ContextTypes, filters

# Konfigurasi logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Status permainan untuk setiap grup
games = {}

# Daftar kata yang akan digunakan
word_pairs = {
    "bot": "botanic",
    "game": "gamer",
    "spy": "spying",
    "secret": "secrete",
    "describe": "describing",
    "computer": "computation",
    "telegram": "telegraph",
    "python": "pythonic",
    "algorithm": "algorithms",
    "network": "networks"
}

# Inisialisasi Flask
app = Flask(__name__)

# Fungsi untuk menjalankan Flask
def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    logger.info(f"Received update: {update}")

    # Menangani pesan baru
    if "message" in update and "text" in update["message"]:
        asyncio.create_task(handle_message(update))

    return '', 200

async def handle_message(update: dict):
    # Implementasikan logika penanganan pesan di sini
    pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Received /start command")
    await update.message.reply_text("Selamat datang di permainan Spy! Gunakan /join untuk bergabung.")

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    chat_id = update.message.chat.id
    logger.info(f"{user.username} is trying to join the game in chat {chat_id}")

    if chat_id not in games:
        games[chat_id] = {
            "players": {},
            "spy_count": 0,
            "descriptions": {},
            "votes": {}
        }

    if user.id not in games[chat_id]["players"]:
        games[chat_id]["players"][user.id] = {"username": user.username, "role": None}
        await update.message.reply_text(f"{user.username} telah bergabung! Ketik /startgame untuk memulai permainan.")
    else:
        await update.message.reply_text("Anda sudah bergabung.")

async def start_game(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat.id
    logger.info(f"Starting game in chat {chat_id}")

    if chat_id not in games or len(games[chat_id]["players"]) < 3:
        await update.message.reply_text("Minimal 3 pemain diperlukan untuk memulai permainan.")
        return

    players = list(games[chat_id]["players"].keys())
    games[chat_id]["spy_count"] = 1 if len(players) <= 4 else 2
    spies = random.sample(players, games[chat_id]["spy_count"])

    for player_id in players:
        if player_id in spies:
            games[chat_id]["players"][player_id]["role"] = "spy"
            await context.bot.send_message(chat_id=player_id, text="Anda adalah spy! Kata rahasia Anda: " + random.choice(list(word_pairs.values())))
        else:
            games[chat_id]["players"][player_id]["role"] = "civilian"
            await context.bot.send_message(chat_id=player_id, text="Kata rahasia Anda: " + random.choice(list(word_pairs.keys())))

    await update.message.reply_text("Kata rahasia telah dikirim. Sekarang, silakan deskripsikan kata ini di chat pribadi dalam 40 detik!")

    # Mengatur waktu deskripsi
    context.job_queue.run_once(send_descriptions, 40, context=chat_id)

async def send_descriptions(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = context.job.context
    players = games[chat_id]["players"]
    group_chat_id = chat_id
    logger.info(f"Sending descriptions for chat {chat_id}")

    for player_id in players:
        if player_id in games[chat_id]["descriptions"]:
            await context.bot.send_message(chat_id=group_chat_id, text=f"{players[player_id]['username']} mendeskripsikan: {games[chat_id]['descriptions'][player_id]}")
        else:
            await context.bot.send_message(chat_id=group_chat_id, text=f"{players[player_id]['username']} ketiduran.")

    await start_voting(chat_id, context)

async def describe_word(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.message.from_user
    chat_id = update.message.chat.id

    if chat_id in games and user.id in games[chat_id]["players"]:
        description = ' '.join(context.args)
        if description:
            games[chat_id]["descriptions"][user.id] = description
            await update.message.reply_text("Deskripsi Anda berhasil dikirim.")
        else:
            await update.message.reply_text("Silakan berikan deskripsi setelah perintah ini.")
    else:
        await update.message.reply_text("Anda belum bergabung dalam permainan.")

async def start_voting(chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    players = games[chat_id]["players"]
    games[chat_id]["votes"] = {player_id: 0 for player_id in players.keys()}

    keyboard = [[InlineKeyboardButton(players[player_id]["username"], callback_data=f'vote_{player_id}') for player_id in players.keys()]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=chat_id, text="Voting dimulai! Pilih siapa yang Anda curigai sebagai spy:", reply_markup=reply_markup)

async def vote(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    selected_player_id = query.data.split('_')[1]

    if user_id in games[chat_id]["players"]:
        games[chat_id]["votes"][selected_player_id] += 1
        await query.answer()
        await query.edit_message_text(text=f"Anda telah memilih {games[chat_id]['players'][selected_player_id]['username']}.")

        if len(games[chat_id]["votes"]) == sum(1 for v in games[chat_id]["votes"].values() if v > 0):
            await end_voting(chat_id, context)

async def end_voting(chat_id, context: ContextTypes.DEFAULT_TYPE) -> None:
    voted_player = max(games[chat_id]["votes"], key=games[chat_id]["votes"].get)
    vote_count = games[chat_id]["votes"][voted_player]

    await context.bot.send_message(chat_id=chat_id, text=f"Pemain {games[chat_id]['players'][voted_player]['username']} terpilih dengan {vote_count} suara.")

    if vote_count > 0:
        await context.bot.send_message(chat_id=chat_id, text=f"{games[chat_id]['players'][voted_player]['username']} telah dieliminasi.")
        del games[chat_id]["players"][voted_player]

        if len(games[chat_id]["players"]) <= games[chat_id]["spy_count"]:
            await context.bot.send_message(chat_id=chat_id, text="Spy menang!")
            reset_game(chat_id)
            return

        await start_game(context.job.context, context)

    else:
        await context.bot.send_message(chat_id=chat_id, text="Tidak ada pemain yang dieliminasi. Melanjutkan ke putaran berikutnya.")
        await start_game(context.job.context, context)

def reset_game(chat_id):
    if chat_id in games:
        del games[chat_id]

async def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "6921935430:AAG2kC2tp6e86CKL0Q_n0beqYMUxNY-nIRk")
    if not bot_token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set.")
        return

    application = ApplicationBuilder().token(bot_token).build()
    
    # Menambahkan handler
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("join", join))
    application.add_handler(CommandHandler("startgame", start_game))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, describe_word))
    application.add_handler(CallbackQueryHandler(vote, pattern='^vote_'))

    await application.initialize()
    
    # Mulai polling
    await application.run_polling()

if __name__ == '__main__':
    # Menggunakan threading untuk menjalankan Flask
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()
    
    # Menjalankan main async function untuk bot
    asyncio.run(main())
