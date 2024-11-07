import requests
import os
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging
import random
import json

# Inisialisasi Flask
app = Flask(__name__)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi bot Telegram
TOKEN = '6921935430:AAG2kC2tp6e86CKL0Q_n0beqYMUxNY-nIRk'  # Ganti dengan token bot Telegram Anda
GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbxBSMAruuH0lPIzQNE2L0JyCuSCVHPb85Ua1RHdEq6CCOu7ZVrlgsBFe2ZR8rFBmt4H/exec'  # Ganti dengan URL Google Apps Script Anda


# Menyimpan skor dan pertanyaan berdasarkan ID grup
user_scores = {}
group_questions = {}

# Ambil data dari Google Apps Script
def fetch_questions():
    try:
        response = requests.get(GOOGLE_SCRIPT_URL)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch questions: {e}")
        return []

# Mengambil data pertanyaan dan jawaban
questions = fetch_questions()

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Game sudah dimulai. Ketik /next untuk pertanyaan berikutnya.")

def next_question(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    chat_id = update.message.chat.id

    if user_id not in user_scores:
        user_scores[user_id] = (user_name, 0)

    if chat_id not in group_questions:
        group_questions[chat_id] = questions.copy()

    if 'answered_questions' not in context.user_data:
        context.user_data['answered_questions'] = []

    available_questions = [q for q in group_questions[chat_id] if q not in context.user_data['answered_questions']]
    
    if available_questions:
        question_data = random.choice(available_questions)
        context.user_data['current_question'] = question_data
        question_text = question_data["question"]
        
        num_placeholders = len(question_data["answers"])
        placeholders = ["_______" for _ in range(num_placeholders)]
        
        display_question = f"{question_text}\n" + "\n".join([f"{i + 1}. {placeholders[i]}" for i in range(num_placeholders)])
        
        update.message.reply_text(display_question)
    else:
        update.message.reply_text("Semua pertanyaan sudah dijawab! Ketik /poin untuk melihat skor Anda.")

def answer(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    chat_id = update.message.chat.id

    question_data = context.user_data.get('current_question', None)

    if question_data is None:
        update.message.reply_text("Tidak ada pertanyaan yang sedang aktif. Silakan ketik /next untuk mendapatkan pertanyaan.")
        return

    answer_text = update.message.text.lower()

    if answer_text in map(str.lower, question_data["answers"]):
        if 'answered' not in context.user_data:
            context.user_data['answered'] = [False] * len(question_data["answers"])

        answer_index = question_data["answers"].index(next(ans for ans in question_data["answers"] if ans.lower() == answer_text))
        if context.user_data['answered'][answer_index]:
            update.message.reply_text("Jawaban ini sudah diberikan sebelumnya. Coba jawaban lain.")
            return
        
        current_score = user_scores[user_id][1] + 1
        user_scores[user_id] = (user_name, current_score)
        
        context.user_data['answered'][answer_index] = True
        
        num_placeholders = len(question_data["answers"])
        placeholders = ["_______" if not answered else f"{question_data['answers'][i]} (+1) [{user_name}]" for i, answered in enumerate(context.user_data['answered'])]
        
        question_text = question_data["question"]
        display_question = f"{question_text}\n" + "\n".join([f"{i + 1}. {placeholders[i]}" for i in range(num_placeholders)])
        
        if all(context.user_data['answered']):
            leaderboard_message = display_leaderboard()
            combined_message = f"{display_question}\n\n{leaderboard_message}\n\nGunakan perintah /poin untuk melihat detail poin kamu, Ketik /next untuk Pertanyaan Lainnya."
            update.message.reply_text(combined_message)
            context.user_data['answered_questions'].append(question_data)
            next_question(update, context)
        else:
            update.message.reply_text(display_question)        
    else:
        update.message.reply_text("Jawaban tidak valid. Coba lagi.")

def display_leaderboard():
    sorted_users = sorted(user_scores.items(), key=lambda x: x[1][1], reverse=True)[:10]
    leaderboard_message = "Papan Poin (Top 10):\n" + "\n".join([f"{i + 1}. {user[1][0]}: {user[1][1]} poin" for i, user in enumerate(sorted_users)])
    return leaderboard_message

def points(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_data = user_scores.get(user_id, (None, 0))
    score = user_data[1]
    update.message.reply_text(f"Skor Anda: {score}")

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    logger.info(f"Received update: {update}")

    if "message" in update and "text" in update["message"]:
        handle_message(update)

    return '', 200

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8000)))

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("next", next_question))
    dp.add_handler(CommandHandler("poin", points))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, answer))

    updater.start_polling()

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

if __name__ == '__main__':
    main()
