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



# Menyimpan skor dan pertanyaan berdasarkan ID grup
user_scores = {}
group_data = {}  # Menyimpan data grup termasuk pertanyaan dan jawaban

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
    user_name = update.message.from_user.first_name
    chat_id = update.message.chat.id  # Dapatkan ID grup

    if chat_id not in group_data:
        group_data[chat_id] = {
            'scores': {},
            'questions': questions.copy(),
            'current_question': None,
            'answered_questions': []
        }

    if user_id not in group_data[chat_id]['scores']:
        group_data[chat_id]['scores'][user_id] = (user_name, 0)  # Simpan nama dan skor awal

    # Pilih pertanyaan acak yang belum dijawab
    available_questions = [q for q in group_data[chat_id]['questions'] if q not in group_data[chat_id]['answered_questions']]
    
    if available_questions:
        question_data = random.choice(available_questions)
        group_data[chat_id]['current_question'] = question_data  # Simpan pertanyaan yang sedang aktif
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
    chat_id = update.message.chat.id  # Dapatkan ID grup

    # Ambil data grup berdasarkan chat_id
    group_info = group_data.get(chat_id, None)
    
    if group_info is None or group_info['current_question'] is None:
        update.message.reply_text("Tidak ada pertanyaan yang sedang aktif. Silakan ketik /next untuk mendapatkan pertanyaan.")
        return

    question_data = group_info['current_question']
    answer_text = update.message.text.lower().strip()  # Normalisasi jawaban
    
    logger.info(f"User answer: {answer_text}, Valid answers: {question_data['answers']}")
    
    if answer_text in question_data["answers"]:
        # Update skor
        current_score = group_info['scores'][user_id][1] + 1  
        group_info['scores'][user_id] = (user_name, current_score)  
        
        # Tandai jawaban sebagai sudah diberikan
        group_info['answered_questions'].append(question_data)
        
        # Menampilkan hasil
        display_results(update, group_info, question_data)
        next_question(update, context)  # Mengambil pertanyaan berikutnya
    else:
        update.message.reply_text("Jawaban tidak valid. Coba lagi.")

def display_results(update, group_info, question_data):
    num_placeholders = len(question_data["answers"])
    placeholders = ["_______" if q not in group_info['answered_questions'] else f"{q['answer']} (+1)" for q in group_info['answered_questions']]
    
    question_text = question_data["question"]
    display_question = f"{question_text}\n" + "\n".join([f"{i + 1}. {placeholders[i]}" for i in range(num_placeholders)])
    
    update.message.reply_text(display_question)

def points(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    chat_id = update.message.chat.id  # Dapatkan ID grup

    group_info = group_data.get(chat_id, None)
    if group_info:
        user_data = group_info['scores'].get(user_id, (None, 0))  # Ambil tuple, default ke (None, 0)
        score = user_data[1]  # Ambil skor dari tuple
        update.message.reply_text(f"Skor Anda: {score}")
    else:
        update.message.reply_text("Tidak ada data skor untuk grup ini.")

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
