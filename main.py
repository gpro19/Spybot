import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, CallbackContext
from telegram.ext import filters  # Mengimpor filters dari telegram.ext

from flask import Flask, request
import random
import threading

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

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Selamat datang di permainan Spy! Gunakan /join untuk bergabung.")

def join(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    chat_id = update.message.chat_id

    if chat_id not in games:
        games[chat_id] = {
            "players": {},
            "spy_count": 0,
            "descriptions": {},
            "votes": {}
        }

    if user.id not in games[chat_id]["players"]:
        games[chat_id]["players"][user.id] = {"username": user.username, "role": None}
        update.message.reply_text(f"{user.username} telah bergabung! Ketik /startgame untuk memulai permainan.")
    else:
        update.message.reply_text("Anda sudah bergabung.")

def start_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    if chat_id not in games or len(games[chat_id]["players"]) < 3:
        update.message.reply_text("Minimal 3 pemain diperlukan untuk memulai permainan.")
        return

    # Menentukan jumlah spy
    players = list(games[chat_id]["players"].keys())
    games[chat_id]["spy_count"] = 1 if len(players) <= 4 else 2
    spies = random.sample(players, games[chat_id]["spy_count"])

    for player_id in players:
        if player_id in spies:
            games[chat_id]["players"][player_id]["role"] = "spy"
            context.bot.send_message(chat_id=player_id, text="Anda adalah spy! Kata rahasia Anda: " + random.choice(list(word_pairs.values())))
        else:
            games[chat_id]["players"][player_id]["role"] = "civilian"
            context.bot.send_message(chat_id=player_id, text="Kata rahasia Anda: " + random.choice(list(word_pairs.keys())))

    update.message.reply_text("Kata rahasia telah dikirim. Sekarang, silakan deskripsikan kata ini di chat pribadi dalam 40 detik!")

    # Mengatur waktu deskripsi
    context.job_queue.run_once(send_descriptions, 40, context=chat_id)

def send_descriptions(context: CallbackContext) -> None:
    chat_id = context.job.context
    players = games[chat_id]["players"]
    group_chat_id = chat_id

    for player_id in players.keys():
        if player_id in games[chat_id]["descriptions"]:
            context.bot.send_message(chat_id=group_chat_id, text=f"{players[player_id]['username']} mendeskripsikan: {games[chat_id]['descriptions'][player_id]}")
        else:
            context.bot.send_message(chat_id=group_chat_id, text=f"{players[player_id]['username']} ketiduran.")

    start_voting(chat_id, context)

def describe_word(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    chat_id = update.message.chat_id

    if chat_id in games and user.id in games[chat_id]["players"]:
        description = ' '.join(context.args)
        if description:
            games[chat_id]["descriptions"][user.id] = description
            update.message.reply_text("Deskripsi Anda berhasil dikirim.")
        else:
            update.message.reply_text("Silakan berikan deskripsi setelah perintah ini.")
    else:
        update.message.reply_text("Anda belum bergabung dalam permainan.")

def start_voting(chat_id, context: CallbackContext) -> None:
    players = games[chat_id]["players"]
    games[chat_id]["votes"] = {player_id: 0 for player_id in players.keys()}

    keyboard = []
    for player_id in players.keys():
        keyboard.append([InlineKeyboardButton(players[player_id]["username"], callback_data=f'vote_{player_id}')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=chat_id, text="Voting dimulai! Pilih siapa yang Anda curigai sebagai spy:", reply_markup=reply_markup)

def vote(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    selected_player_id = query.data.split('_')[1]

    if user_id in games[chat_id]["players"]:
        games[chat_id]["votes"][selected_player_id] += 1
        query.answer()
        query.edit_message_text(text=f"Anda telah memilih {games[chat_id]['players'][selected_player_id]['username']}.")

        # Cek apakah semua pemain sudah memilih
        if len(games[chat_id]["votes"]) == sum(1 for v in games[chat_id]["votes"].values() if v > 0):
            end_voting(chat_id, context)

def end_voting(chat_id, context: CallbackContext) -> None:
    voted_player = max(games[chat_id]["votes"], key=games[chat_id]["votes"].get)
    vote_count = games[chat_id]["votes"][voted_player]

    context.bot.send_message(chat_id=chat_id, text=f"Pemain {games[chat_id]['players'][voted_player]['username']} terpilih dengan {vote_count} suara.")

    if vote_count > 0:
        context.bot.send_message(chat_id=chat_id, text=f"{games[chat_id]['players'][voted_player]['username']} telah dieliminasi.")
        del games[chat_id]["players"][voted_player]

        if len(games[chat_id]["players"]) <= games[chat_id]["spy_count"]:  # Cek apakah spy menang
            context.bot.send_message(chat_id=chat_id, text="Spy menang!")
            reset_game(chat_id)
            return
        
        # Melanjutkan ke putaran berikutnya
        start_game(context.job.context, context)

    else:
        context.bot.send_message(chat_id=chat_id, text="Tidak ada pemain yang dieliminasi. Melanjutkan ke putaran berikutnya.")
        start_game(context.job.context, context)

def reset_game(chat_id):
    if chat_id in games:
        del games[chat_id]

def start_bot(token: str):
    # Buat updater dan dispatcher
    updater = Updater(token)
    dispatcher = updater.dispatcher

    # Tambahkan handler
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("join", join))
    dispatcher.add_handler(CommandHandler("startgame", start_game))
    dispatcher.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, describe_word))  
    dispatcher.add_handler(CallbackQueryHandler(vote, pattern='^vote_'))

    # Mulai bot
    updater.start_polling()
    updater.idle()

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    if update:
        # Proses update dengan dispatcher
        updater.dispatcher.process_update(Update.de_json(update))
    return 'ok'

if __name__ == '__main__':
    # Token bot Anda
    TOKEN = '6921935430:AAGmSrcmn7Jc5_egkDjqeLXVhHjkPUoXu-4'
    
    # Jalankan bot di thread terpisah
    bot_thread = threading.Thread(target=start_bot, args=(TOKEN,))
    bot_thread.start()

    # Jalankan aplikasi Flask
    app.run(port=8000)
