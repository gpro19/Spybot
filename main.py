import requests
import logging
import random
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Inisialisasi Flask
app = Flask(__name__)

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL Google Apps Script untuk mengambil pertanyaan
TOKEN = '6921935430:AAG2kC2tp6e86CKL0Q_n0beqYMUxNY-nIRk'  # Ganti dengan token bot Telegram Anda
GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbxBSMAruuH0lPIzQNE2L0JyCuSCVHPb85Ua1RHdEq6CCOu7ZVrlgsBFe2ZR8rFBmt4H/exec'  # Ganti dengan URL Google Apps Script Anda



# Inisialisasi data untuk menyimpan informasi game
user_data = {}
correct_answers_status = {}

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

# Fungsi untuk memulai permainan
def play_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id

    # Cek apakah game sudah dimulai
    if chat_id not in user_data:
        user_data[chat_id] = {
            "current_question": None,
            "score": {}
        }

    # Pilih pertanyaan secara acak
    question = random.choice(questions)
    user_data[chat_id]["current_question"] = question
    correct_answers_status[question["question"]] = [False] * len(question["answers"])  # Inisialisasi status jawaban benar

    # Kirim pertanyaan ke grup
    question_text = f"{question['question']}\n" + "\n".join([f"{i + 1}. _________" for i in range(len(question["answers"]))])
    update.message.reply_text(question_text)

# Fungsi untuk memproses jawaban
def answer(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    answer_text = update.message.text.lower().strip()
    
    # Cek apakah permainan sudah dimulai
    if chat_id not in user_data:
        update.message.reply_text("Belum ada permainan yang dimulai. Ketik /play untuk memulai.")
        return

    current_question = user_data[chat_id]["current_question"]

    # Cek apakah ada pertanyaan aktif
    if current_question is None:
        update.message.reply_text("Tidak ada pertanyaan aktif.")
        return

    answers = current_question["answers"]

    # Mencari jawaban yang benar
    correct_answer_found = False
    for i, answer in enumerate(answers):
        if answer_text == answer.lower():  # Membandingkan dengan lowercase
            correct_index = i
            correct_answer_found = True
            break

    if not correct_answer_found:
        update.message.reply_text("Jawaban tidak valid. Coba lagi.")
        return

    if correct_answers_status[current_question["question"]][correct_index]:
        update.message.reply_text("Jawaban ini sudah dijawab dengan benar oleh pemain lain. Coba jawaban lain.")
        return

    # Tandai jawaban ini sebagai benar
    correct_answers_status[current_question["question"]][correct_index] = True
    
    # Update skor untuk pemain yang menjawab
    if user_id not in user_data[chat_id]["score"]:
        user_data[chat_id]["score"][user_id] = {"nama": user_name, "poin": 0}
    
    user_data[chat_id]["score"][user_id]["poin"] += 1  # Tambahkan poin

    # Update pesan dengan jawaban yang benar
    response_message = f"{current_question['question']}\n"
    for i, answer in enumerate(answers):
        if correct_answers_status[current_question["question"]][i]:
            response_message += f"{i + 1}. {answer} (+1) [{user_name}]\n"
        else:
            response_message += f"{i + 1}. _________\n"

    if all(correct_answers_status[current_question["question"]]):
        response_message += "\nSemua jawaban sudah terjawab. Ketik /play untuk pertanyaan berikutnya."
        del user_data[chat_id]  # Hapus data game setelah semua terjawab
        del correct_answers_status[current_question["question"]]
    
    update.message.reply_text(response_message)

# Fungsi untuk melihat skor pemain
def view_score(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id

    if chat_id not in user_data or "score" not in user_data[chat_id]:
        update.message.reply_text("Belum ada permainan yang dimulai atau belum ada pemain yang memiliki skor.")
        return

    scores = user_data[chat_id]["score"]
    score_message = "Skor Pemain:\n"

    for user_id, score in scores.items():
        score_message += f"{score['nama']}: {score['poin']}\n"

    update.message.reply_text(score_message)

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    logger.info(f"Received update: {update}")

    if "message" in update and "text" in update["message"]:
        # Panggil fungsi yang memproses pesan
        handle_message(update)

    return '', 200

def run_flask():
    app.run(host='0.0.0.0', port='8000')

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("play", play_game))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, answer))
    dp.add_handler(CommandHandler("score", view_score))  # Tambahkan handler untuk melihat skor

    updater.start_polling()

    # Jalankan Flask pada thread terpisah
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

if __name__ == '__main__':
    main()
