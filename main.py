import requests
import os
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import logging
import random

# Inisialisasi Flask
app = Flask(__name__)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Konfigurasi bot Telegram
TOKEN = '6921935430:AAG2kC2tp6e86CKL0Q_n0beqYMUxNY-nIRk'  # Ganti dengan token bot Telegram Anda
GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbxBSMAruuH0lPIzQNE2L0JyCuSCVHPb85Ua1RHdEq6CCOu7ZVrlgsBFe2ZR8rFBmt4H/exec'  # Ganti dengan URL Google Apps Script Anda
user_scores = {}
leaderboard = []

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

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text("Game sudah dimulai. Ketik /next untuk pertanyaan berikutnya.")

def next_question(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_scores:
        user_scores[user_id] = 0

    if 'answered_questions' not in context.user_data:
        context.user_data['answered_questions'] = []
    
    # Pilih pertanyaan acak yang belum dijawab
    available_questions = [q for q in questions if q not in context.user_data['answered_questions']]
    
    if available_questions:
        question_data = random.choice(available_questions)
        context.user_data['current_question'] = question_data
        question_text = question_data["question"]
        
        # Buat placeholder berdasarkan jumlah jawaban yang ada
        num_placeholders = len(question_data["answers"])
        placeholders = ["_______" for _ in range(num_placeholders)]  # Placeholder sesuai jumlah jawaban
        display_question = f"{question_text}\n" + "\n".join([f"{i + 1}. {placeholders[i]}" for i in range(num_placeholders)])
        
        update.message.reply_text(display_question)
    else:
        update.message.reply_text("Semua pertanyaan sudah dijawab! Ketik /poin untuk melihat skor Anda.")

def answer(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in user_scores:
        user_scores[user_id] = 0
    
    question_data = context.user_data.get('current_question', None)
    if question_data:
        answer_text = update.message.text.lower()
        
        # Cek apakah jawaban sudah terisi
        if answer_text in question_data["answers"]:
            # Cek apakah jawaban sudah dijawab
            if 'answered' not in context.user_data:
                context.user_data['answered'] = [False] * len(question_data["answers"])
            
            answer_index = question_data["answers"].index(answer_text)
            if context.user_data['answered'][answer_index]:
                update.message.reply_text("Jawaban ini sudah diberikan sebelumnya. Coba jawaban lain.")
                return
            
            user_scores[user_id] += 1  # Setiap jawaban benar mendapatkan 1 poin
            
            # Ganti jawaban yang benar di tampilan
            context.user_data['answered'][answer_index] = True  # Tandai jawaban sebagai sudah terisi
            
            num_placeholders = len(question_data["answers"])
            placeholders = ["_______" if not answered else f"{question_data['answers'][i]} (+1) [{update.message.from_user.first_name}]" for i, answered in enumerate(context.user_data['answered'])]
            
            # Menampilkan kembali pertanyaan dengan jawaban yang sudah terisi
            question_text = question_data["question"]
            display_question = f"{question_text}\n" + "\n".join([f"{i + 1}. {placeholders[i]}" for i in range(num_placeholders)])
            update.message.reply_text(display_question)
            
            # Cek jika semua jawaban sudah terisi
            if all(context.user_data['answered']):
                # Tampilkan papan poin dan pesan akhir
                display_leaderboard(update)
                context.user_data['answered_questions'].append(question_data)  # Tandai pertanyaan sebagai dijawab
                next_question(update, context)
        else:
            update.message.reply_text("Jawaban tidak valid. Coba lagi.")
    else:
        update.message.reply_text("Tidak ada pertanyaan yang sedang aktif.")

def points(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    score = user_scores.get(user_id, 0)
    update.message.reply_text(f"Skor Anda: {score}")

def display_leaderboard(update):
    global leaderboard
    leaderboard = sorted(user_scores.items(), key=lambda x: x[1], reverse=True)[:10]  # Ambil 10 pemain teratas
    leaderboard_message = "Papan Poin (Top 10) :\n" + "\n".join([f"{i + 1}. {user[0]}: {user[1]} poin" for i, user in enumerate(leaderboard)])
    update.message.reply_text(leaderboard_message + "\n\nGunakan perintah /poin untuk melihat detail poin kamu, Ketik /mulai untuk Pertanyaan Lainnya.")

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
