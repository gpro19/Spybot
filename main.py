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

    if "message" in update and "text" in update["message"]:
        handle_message(update)

    return '', 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

def handle_message(update):
    # Implementasikan logika penanganan pesan di sini
    pass

# Konstanta untuk pengaturan permainan
DESCRIPTION_TIME = 40
VOTING_TIME = 20

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
            "has_described": {},
            "round": 1,
            "scores": {},
            "current_words": {},
            "current_roles": {}
        }

    if user.id not in games[chat_id]["players"]:
        games[chat_id]["players"][user.id] = {"username": username, "role": None}
        games[chat_id]["has_described"][user.id] = False
        update.message.reply_text(f"{username} telah bergabung! Ketik /startgame untuk memulai permainan.")
    else:
        update.message.reply_text("Anda sudah bergabung.")

def start_game(chat_id, context) -> None:
    players = games[chat_id]["players"]

    if len(players) < 3:
        context.bot.send_message(chat_id=chat_id, text="Tidak cukup pemain untuk memulai permainan.")
        return

    if "spy_count" in games[chat_id] and games[chat_id]["spy_count"] > 0:
        context.bot.send_message(chat_id=chat_id, text="Permainan sudah dimulai!")
        return

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

    words = random.sample(list(word_pairs.keys()), len(players))
    for player_id, word in zip(players.keys(), words):
        games[chat_id]["descriptions"][player_id] = word
        context.bot.send_message(chat_id=player_id, text=f"Anda mendapatkan kata: {word}")

    context.bot.send_message(chat_id=chat_id, text=f"Putaran deskripsi ke-{games[chat_id]['round']} dimulai! Setiap pemain memiliki {DESCRIPTION_TIME} detik untuk mendiskripsikan kata mereka.")
    threading.Thread(target=description_phase, args=(chat_id, context)).start()

def description_phase(chat_id, context):
    games[chat_id]["is_description_phase"] = True
    time.sleep(DESCRIPTION_TIME)

    descriptions = []
    for player_id in games[chat_id]["players"]:
        if games[chat_id]["has_described"].get(player_id):
            description_text = games[chat_id]["descriptions"].get(player_id, "Tidak ada deskripsi.")
            descriptions.append(f"{games[chat_id]['players'][player_id]['username']} mendeskripsikan: {description_text}")

    context.bot.send_message(chat_id=chat_id, text="Fase deskripsi selesai! Berikut adalah deskripsi dari pemain:\n" + "\n".join(descriptions))
    context.bot.send_message(chat_id=chat_id, text="Sekarang waktunya untuk diskusi selama 60 detik.")
    
    voting_phase(chat_id, context)

def handle_player_description(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id

    if chat_id in games and user_id in games[chat_id]["players"]:
        description_text = update.message.text
        games[chat_id]["descriptions"][user_id] = description_text
        games[chat_id]["has_described"][user_id] = True
        update.message.reply_text("Deskripsi Anda telah disimpan.")
    else:
        update.message.reply_text("Anda tidak dapat mendeskripsikan karena Anda belum bergabung dalam permainan.")

def voting_phase(chat_id, context):
    players = games[chat_id]["players"]
    keyboard = []
    
    for player_id, info in players.items():
        button_text = f"{info['username']} (Voted)" if player_id in games[chat_id].get("votes", {}) else info["username"]
        button = InlineKeyboardButton(text=button_text, callback_data=f"vote_{player_id}")  
        keyboard.append(button)

    reply_markup = InlineKeyboardMarkup(build_menu(keyboard, n_cols=1))
    context.bot.send_message(chat_id=chat_id, text="Silakan pilih pemain yang ingin Anda eliminasi:", reply_markup=reply_markup)

    time.sleep(VOTING_TIME)
    determine_votes(chat_id, context)

def button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()

    user_id = query.from_user.id
    chat_id = query.message.chat.id
    selected_player_id = query.data.split("_")[1]

    if chat_id in games and user_id in games[chat_id]["players"]:
        if selected_player_id in games[chat_id]["players"]:
            if "votes" not in games[chat_id]:
                games[chat_id]["votes"] = {}

            if user_id not in games[chat_id]["votes"]:
                games[chat_id]["votes"][user_id] = selected_player_id
                
                buttons = []
                for player_id, info in games[chat_id]["players"].items():
                    button_text = f"{info['username']} (Voted)" if player_id in games[chat_id]["votes"] else info["username"]
                    buttons.append(InlineKeyboardButton(text=button_text, callback_data=f"vote_{player_id}"))

                reply_markup = InlineKeyboardMarkup(build_menu(buttons, n_cols=1))
                context.bot.edit_message_reply_markup(chat_id=chat_id, message_id=query.message.message_id, reply_markup=reply_markup)

                context.bot.send_message(chat_id=chat_id, text=f"{games[chat_id]['players'][user_id]['username']} telah memilih {games[chat_id]['players'][selected_player_id]['username']}.")

                if len(games[chat_id]["votes"]) == len(games[chat_id]["players"]):
                    context.bot.send_message(chat_id=chat_id, text="Voting selesai!")
                    determine_elimination(chat_id, context)
            else:
                context.bot.send_message(chat_id=chat_id, text="Anda sudah memberikan suara!")
        else:
            logger.error(f"Selected player ID {selected_player_id} tidak ditemukan dalam daftar pemain.")
    else:
        logger.error(f"Chat ID {chat_id} atau User ID {user_id} tidak ditemukan dalam permainan.")

def determine_votes(chat_id, context):
    if "votes" not in games[chat_id]:
        games[chat_id]["votes"] = {}

    context.bot.send_message(chat_id=chat_id, text="Voting selesai!")
    determine_elimination(chat_id, context)

def determine_elimination(chat_id, context):
    vote_counts = {}
    for vote in games[chat_id]["votes"].values():
        if vote in vote_counts:
            vote_counts[vote] += 1
        else:
            vote_counts[vote] = 1

    if vote_counts:
        eliminated = max(vote_counts, key=vote_counts.get)

        if eliminated in games[chat_id]['players']:
            context.bot.send_message(chat_id=chat_id, text=f"Pemain {games[chat_id]['players'][eliminated]['username']} telah dieliminasi.")
            
            if games[chat_id]['players'][eliminated]['role'] == 'spy':
                context.bot.send_message(chat_id=chat_id, text="Dia adalah SPY.")
            else:
                context.bot.send_message(chat_id=chat_id, text="Dia adalah WARGA BIASA.")
            
            check_game_end(chat_id, context)
        else:
            context.bot.send_message(chat_id=chat_id, text="Pemain yang akan dieliminasi tidak ditemukan.")
            check_game_end(chat_id, context)
    else:
        context.bot.send_message(chat_id=chat_id, text="Tidak ada suara yang dihitung.")
        check_game_end(chat_id, context)

def check_game_end(chat_id, context):
    spies = [player_id for player_id, info in games[chat_id]["players"].items() if info["role"] == "spy"]
    civilians = [player_id for player_id, info in games[chat_id]["players"].items() if info["role"] == "civilian"]
    
    if len(spies) == 0:
        context.bot.send_message(chat_id=chat_id, text="Warga biasa menang!")
    elif len(spies) >= len(civilians):
        context.bot.send_message(chat_id=chat_id, text="Spy menang!")
    else:
        games[chat_id]["round"] += 1
        context.bot.send_message(chat_id=chat_id, text=f"Putaran deskripsi ke-{games[chat_id]['round']} dimulai!")
        games[chat_id]["current_roles"] = {player_id: info["role"] for player_id, info in games[chat_id]["players"].items()}
        games[chat_id]["descriptions"] = games[chat_id]["current_words"]
        for player_id in games[chat_id]["players"]:
            if player_id in games[chat_id]["current_roles"]:
                games[chat_id]["players"][player_id]["role"] = games[chat_id]["current_roles"][player_id]

        start_game(chat_id, context)

def reset_game(chat_id):
    if chat_id in games:
        del games[chat_id]

def kill_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    if chat_id in games:
        del games[chat_id]
        update.message.reply_text("Permainan telah dihentikan!")
    else:
        update.message.reply_text("Tidak ada permainan yang sedang berlangsung.")

def build_menu(buttons, n_cols, header_buttons=None, footer_buttons=None):
    menu = [buttons[i:i + n_cols] for i in range(0, len(buttons), n_cols)]
    if header_buttons:
        menu.insert(0, header_buttons)
    if footer_buttons:
        menu.append(footer_buttons)
    return menu

def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "6921935430:AAG2kC2tp6e86CKL0Q_n0beqYMUxNY-nIRk")  # Ganti dengan token bot Anda
    updater = Updater(bot_token)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("join", join))
    dp.add_handler(CommandHandler("startgame", start_game))
    dp.add_handler(CommandHandler("killgame", kill_game))
    dp.add_handler(CallbackQueryHandler(button))
    dp.add_handler(MessageHandler(Filters.text & Filters.chat_type.private, handle_player_description))
    
    updater.start_polling()

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

if __name__ == '__main__':
    main()
