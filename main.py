import logging
import random
import os
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

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
        update.message.reply_text(f"{user.username} telah bergabung! Ketik /startgame untuk memulai permainan.")
    else:
        update.message.reply_text("Anda sudah bergabung.")

def start_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    players = games[chat_id]["players"]

    if len(players) < 3:
        update.message.reply_text("Tidak cukup pemain untuk memulai permainan.")
        return

    if "spy_count" in games[chat_id]:  # Cek apakah permainan sudah dimulai
        update.message.reply_text("Permainan sudah dimulai!")
        return

    # Menetapkan peran
    spy_count = 1 if len(players) <= 5 else 2
    games[chat_id]["spy_count"] = spy_count
    spy_players = random.sample(list(players.keys()), spy_count)

    for player_id in players:
        if player_id in spy_players:
            games[chat_id]["players"][player_id]["role"] = "spy"
        else:
            games[chat_id]["players"][player_id]["role"] = "civilian"

    # Mengirim kata kepada pemain
    words = random.sample(list(word_pairs.keys()), len(players))
    for player_id, word in zip(players.keys(), words):
        games[chat_id]["descriptions"][player_id] = word
        context.bot.send_message(chat_id=player_id, text=f"Anda mendapatkan kata: {word}")

    update.message.reply_text("Permainan dimulai! Setiap pemain memiliki 40 detik untuk menggambarkan kata mereka.")

    # Memulai fase deskripsi
    threading.Thread(target=description_phase, args=(chat_id, context)).start()

def description_phase(chat_id, context):
    time.sleep(40)  # Tunggu selama 40 detik untuk deskripsi
    context.bot.send_message(chat_id=chat_id, text="Waktu deskripsi telah habis! Sekarang waktunya untuk voting.")
    
    # Memulai fase voting
    voting_phase(chat_id, context)

def voting_phase(chat_id, context):
    players = games[chat_id]["players"]
    keyboard = []
    
    for player_id, info in players.items():
        button = InlineKeyboardButton(info["username"], callback_data=f"vote_{player_id}")
        keyboard.append(button)

    reply_markup = InlineKeyboardMarkup(build_menu(keyboard, n_cols=1))
    context.bot.send_message(chat_id=chat_id, text="Silakan pilih pemain yang ingin Anda eliminasi:", reply_markup=reply_markup)

def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat.id
    selected_player_id = query.data.split("_")[1]

    if chat_id in games and user_id in games[chat_id]["players"]:
        if "votes" not in games[chat_id]:
            games[chat_id]["votes"] = {}
        
        games[chat_id]["votes"][user_id] = selected_player_id
        query.edit_message_text(text=f"Anda telah memilih {games[chat_id]['players'][selected_player_id]['username']}.")

        if len(games[chat_id]["votes"]) == len(games[chat_id]["players"]):
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
    eliminated = max(vote_counts, key=vote_counts.get)
    context.bot.send_message(chat_id=chat_id, text=f"Pemain {games[chat_id]['players'][eliminated]['username']} telah dieliminasi.")

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
    
# Menambahkan handler perintah
def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "6921935430:AAG2kC2tp6e86CKL0Q_n0beqYMUxNY-nIRk")  # Ganti dengan token bot Anda
    updater = Updater(bot_token)
    dp = updater.dispatcher
    
    # Menambahkan handler
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("join", join))
    dp.add_handler(CommandHandler("startgame", start_game))
    dp.add_handler(MessageHandler(Filters.callback_query, button))
    
    # Mulai polling
    updater.start_polling()

    # Jalankan Flask di thread terpisah
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

if __name__ == '__main__':
    main()
