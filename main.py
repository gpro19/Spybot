import logging
import random
import os
import threading
import time
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters

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

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    logger.info(f"Received update: {update}")

    # Menangani pesan baru
    if "message" in update and "text" in update["message"]:
        handle_message(update)

    return '', 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

def handle_message(update):
    # Implementasikan logika penanganan pesan di sini
    pass

def start(update: Update, context: CallbackContext) -> None:
    logger.info("Received /start command")
    update.message.reply_text("Selamat datang di permainan Spy! Gunakan /join untuk bergabung.")

def join(update: Update, context: CallbackContext) -> None:
    user = update.message.from_user
    chat_id = update.message.chat.id

    username = user.username if user.username else user.first_name
    logger.info(f"{username} is trying to join the game in chat {chat_id}")

    if chat_id not in games:
        games[chat_id] = {
            "players": {},
            "spy_count": 0,
            "descriptions": {},
            "votes": {},
            "has_described": {}  # Menyimpan status deskripsi pemain
        }

    if user.id not in games[chat_id]["players"]:
        games[chat_id]["players"][user.id] = {"username": username, "role": None}
        games[chat_id]["has_described"][user.id] = False  # Set status deskripsi awal untuk pemain
        update.message.reply_text(f"{username} telah bergabung! Ketik /startgame untuk memulai permainan.")
    else:
        update.message.reply_text("Anda sudah bergabung.")

def start_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    players = games[chat_id]["players"]

    if len(players) < 3:
        update.message.reply_text("Tidak cukup pemain untuk memulai permainan.")
        return

    # Cek apakah permainan sudah dimulai
    if "spy_count" in games[chat_id] and games[chat_id]["spy_count"] > 0:
        update.message.reply_text("Permainan sudah dimulai!")
        return

    # Menetapkan peran
    spy_count = 1 if len(players) <= 5 else 2
    games[chat_id]["spy_count"] = spy_count
    spy_players = random.sample(list(players.keys()), spy_count)

    for player_id in players:
        if player_id in spy_players:
            games[chat_id]["players"][player_id]["role"] = "spy"
            context.bot.send_message(chat_id=player_id, text="Anda adalah SPY!")
        else:
            games[chat_id]["players"][player_id]["role"] = "civilian"
            context.bot.send_message(chat_id=player_id, text="Anda adalah WARGA BIASA!")

    # Mengirim kata kepada pemain
    words = random.sample(list(word_pairs.keys()), len(players))
    for player_id, word in zip(players.keys(), words):
        games[chat_id]["descriptions"][player_id] = word
        context.bot.send_message(chat_id=player_id, text=f"Anda mendapatkan kata: {word}")

    update.message.reply_text("Permainan dimulai! Setiap pemain memiliki 40 detik untuk mendiskripsikan kata mereka.")

    # Memulai fase deskripsi
    threading.Thread(target=description_phase, args=(chat_id, context)).start()

def description_phase(chat_id, context):
    time.sleep(40)  # Tunggu selama 40 detik untuk deskripsi

    # Mengumpulkan deskripsi
    descriptions = []
    for player_id in games[chat_id]["players"]:
        username = games[chat_id]['players'][player_id]['username']
        word = games[chat_id]["descriptions"][player_id]
        
        # Kirim pesan ke grup jika deskripsi sudah ada
        if games[chat_id]["has_described"].get(player_id, False):
            descriptions.append(f"{username} mendeskripsikan: {word}")
        else:
            # Jika pemain tidak mendeskripsikan, kirim pesan
            context.bot.send_message(chat_id=player_id, text="Anda sedang tidur, jangan diganggu.")

    # Kirim semua deskripsi ke grup
    if descriptions:
        context.bot.send_message(chat_id=chat_id, text="\n".join(descriptions))
    else:
        context.bot.send_message(chat_id=chat_id, text="Tidak ada deskripsi yang dikirim.")

    context.bot.send_message(chat_id=chat_id, text="Waktu deskripsi telah habis! Sekarang waktunya untuk diskusi selama 60 detik.")

    # Memulai fase diskusi
    time.sleep(60)  # Tunggu selama 60 detik untuk diskusi

    # Memulai fase voting
    voting_phase(chat_id, context)

def voting_phase(chat_id, context):
    players = games[chat_id]["players"]
    keyboard = []
    
    for player_id, info in players.items():
        # Memastikan text ada dan tidak kosong
        button = InlineKeyboardButton(text=info["username"], callback_data=f"vote_{player_id}")  
        keyboard.append(button)

    reply_markup = InlineKeyboardMarkup(build_menu(keyboard, n_cols=1))
    context.bot.send_message(chat_id=chat_id, text="Silakan pilih pemain yang ingin Anda eliminasi:", reply_markup=reply_markup)

    # Menunggu 20 detik untuk voting
    time.sleep(20)  # Tunggu selama 20 detik untuk voting
    determine_votes(chat_id, context)

def determine_votes(chat_id, context):
    if "votes" not in games[chat_id]:
        games[chat_id]["votes"] = {}

    # Proses voting
    context.bot.send_message(chat_id=chat_id, text="Voting selesai!")
    determine_elimination(chat_id, context)

def determine_elimination(chat_id, context):
    vote_counts = {}
    for vote in games[chat_id]["votes"].values():
        if vote in vote_counts:
            vote_counts[vote] += 1
        else:
            vote_counts[vote] = 1

    # Menemukan pemain dengan suara terbanyak
    if vote_counts:
        eliminated = max(vote_counts, key=vote_counts.get)
        context.bot.send_message(chat_id=chat_id, text=f"Pemain {games[chat_id]['players'][eliminated]['username']} telah dieliminasi.")
    else:
        context.bot.send_message(chat_id=chat_id, text="Tidak ada suara yang dihitung.")

    # Memeriksa kondisi akhir permainan
    check_game_end(chat_id, context)

def check_game_end(chat_id, context):
    spies = [player_id for player_id, info in games[chat_id]["players"].items() if info["role"] == "spy"]
    civilians = [player_id for player_id, info in games[chat_id]["players"].items() if info["role"] == "civilian"]
    
    if len(spies) == 0:
        context.bot.send_message(chat_id=chat_id, text="Warga biasa menang!")
    elif len(spies) >= len(civilians):
        context.bot.send_message(chat_id=chat_id, text="Spy menang!")
    
    # Reset permainan untuk putaran berikutnya
    reset_game(chat_id)

def reset_game(chat_id):
    # Mengatur ulang status permainan
    if chat_id in games:
        del games[chat_id]

# Tambahkan perintah untuk menghentikan permainan
def kill_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    if chat_id in games:
        del games[chat_id]
        update.message.reply_text("Permainan telah dihentikan!")
    else:
        update.message.reply_text("Tidak ada permainan yang sedang berlangsung.")

# Menambahkan handler untuk pesan di chat privat
def handle_private_messages(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    # Pastikan pengguna adalah pemain dalam permainan
    for game_chat_id, game in games.items():
        if user_id in game["players"]:
            # Menandai bahwa pemain telah mendeskripsikan
            game["has_described"][user_id] = True
            break

# Menambahkan handler perintah
def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "6921935430:AAG2kC2tp6e86CKL0Q_n0beqYMUxNY-nIRk")  # Ganti dengan token bot Anda
    updater = Updater(bot_token)
    dp = updater.dispatcher
    
    # Menambahkan handler
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("join", join))
    dp.add_handler(CommandHandler("startgame", start_game))
    dp.add_handler(CommandHandler("killgame", kill_game))  # Menambahkan handler untuk /killgame
    dp.add_handler(CallbackQueryHandler(button))  # Menggunakan CallbackQueryHandler untuk menangani tombol
    dp.add_handler(MessageHandler(Filters.text & Filters.private, handle_private_messages))  # Menambahkan handler untuk pesan di chat privat
    
    # Mulai polling
    updater.start_polling()

    # Jalankan Flask di thread terpisah
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

if __name__ == '__main__':
    main()
