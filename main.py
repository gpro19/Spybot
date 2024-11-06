import requests
from flask import Flask, request
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging

# Inisialisasi Flask
app = Flask(__name__)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi bot Telegram
TOKEN = '6921935430:AAG2kC2tp6e86CKL0Q_n0beqYMUxNY-nIRk'
updater = Updater(TOKEN, use_context=True)
dispatcher = updater.dispatcher

# URL Google Apps Script
GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbxBSMAruuH0lPIzQNE2L0JyCuSCVHPb85Ua1RHdEq6CCOu7ZVrlgsBFe2ZR8rFBmt4H/exec'  # Ganti dengan URL Web App Anda

# Ambil data dari Google Apps Script
def fetch_questions():
    response = requests.get(GOOGLE_SCRIPT_URL)
    if response.status_code == 200:
        return response.json()
    else:
        logger.error("Failed to fetch questions from Google Apps Script")
        return []

# Mengambil data pertanyaan dan jawaban
questions = fetch_questions()
user_scores = {}

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Game sudah dimulai. Ketik /next untuk pertanyaan berikutnya.")

def next_question(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_scores:
        user_scores[user_id] = 0

    if 'current_question' not in context.user_data:
        context.user_data['current_question'] = 0
    
    question_index = context.user_data['current_question']
    
    if question_index < len(questions):
        question_data = questions[question_index]
        question_text = question_data["question"]
        update.message.reply_text(question_text)
    else:
        update.message.reply_text("Game selesai! Ketik /poin untuk melihat skor Anda.")

def answer(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_scores:
        user_scores[user_id] = 0
    
    question_index = context.user_data.get('current_question', 0)
    if question_index < len(questions):
        answer = update.message.text.lower()
        question_data = questions[question_index]
        
        if answer in question_data["answers"]:
            user_scores[user_id] += 1  # Setiap jawaban benar mendapatkan 1 poin
            update.message.reply_text(f"{answer} (+1) [Anda]")
        else:
            update.message.reply_text("Jawaban tidak valid. Coba lagi.")
        
        # Increment question index
        context.user_data['current_question'] += 1
        next_question(update, context)
    else:
        update.message.reply_text("Game sudah selesai. Ketik /poin untuk melihat skor.")

def points(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    score = user_scores.get(user_id, 0)
    update.message.reply_text(f"Skor Anda: {score}")

def main():
    # Menambahkan handler ke dispatcher
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("next", next_question))
    dispatcher.add_handler(CommandHandler("poin", points))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, answer))

    # Mulai polling
    updater.start_polling()
    logger.info("Bot is polling...")

if __name__ == '__main__':
    main()
    app.run(port=8000)  # Jalankan Flask di port 8000
