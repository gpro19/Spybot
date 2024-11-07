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
        user_scores[user_id] = (update.message.from_user.first_name, 0)  # Simpan nama dan skor awal

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
    user_name = update.message.from_user.first_name  # Ambil nama pengguna

    # Inisialisasi skor untuk pengguna baru
    if user_id not in user_scores:
        user_scores[user_id] = (user_name, 0)  # Simpan nama dan skor sebagai tuple

    question_data = context.user_data.get('current_question', None)
    if question_data:
        answer_text = update.message.text.lower()
        
        # Cek apakah jawaban sudah terisi
        if answer_text in question_data["answers"]:
            # Cek apakah jawaban sudah dijawab
            if 'answered' not in context.user_data:
                context.user_data['answered'] = [False] * len(question_data["answers"])  # Inisialisasi jawaban
            
            answer_index = question_data["answers"].index(answer_text)
            if context.user_data['answered'][answer_index]:
                update.message.reply_text("Jawaban ini sudah diberikan sebelumnya. Coba jawaban lain.")
                return
            
            # Update skor
            current_score = user_scores[user_id][1] + 1  # Ambil skor yang ada dan tambahkan 1
            user_scores[user_id] = (user_name, current_score)  # Update dengan nama dan skor
            
            # Ganti jawaban yang benar di tampilan
            context.user_data['answered'][answer_index] = True  # Tandai jawaban sebagai sudah terisi
            
            num_placeholders = len(question_data["answers"])
            placeholders = ["_______" if not answered else f"{question_data['answers'][i]} (+1) [{user_name}]" for i, answered in enumerate(context.user_data['answered'])]
            
            # Menampilkan kembali pertanyaan dengan jawaban yang sudah terisi
            question_text = question_data["question"]
            display_question = f"{question_text}\n" + "\n".join([f"{i + 1}. {placeholders[i]}" for i in range(num_placeholders)])
            
            # Cek jika semua jawaban sudah terisi
            if all(context.user_data['answered']):
                # Gabungkan semua informasi dalam satu pesan
                leaderboard_message = display_leaderboard()  # Dapatkan papan poin
                combined_message = f"{display_question}\n\n{leaderboard_message}\n\nGunakan perintah /poin untuk melihat detail poin kamu, Ketik /mulai untuk Pertanyaan Lainnya."
                update.message.reply_text(combined_message)
                context.user_data['answered_questions'].append(question_data)  # Tandai pertanyaan sebagai dijawab
                next_question(update, context)
            else:
                update.message.reply_text(display_question)        
    else:
        update.message.reply_text("Tidak ada pertanyaan yang sedang aktif.")

def display_leaderboard():
    global leaderboard
    # Mengurutkan berdasarkan skor dan mengambil 10 pemain teratas
    sorted_users = sorted(user_scores.items(), key=lambda x: x[1][1], reverse=True)[:10]
    leaderboard_message = "Papan Poin (Top 10) :\n" + "\n".join([f"{i + 1}. {user[1][0]}: {user[1][1]} poin" for i, user in enumerate(sorted_users)])
    return leaderboard_message

def points(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    user_data = user_scores.get(user_id, (None, 0))  # Ambil tuple, default ke (None, 0)
    score = user_data[1]  # Ambil skor dari tuple
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
