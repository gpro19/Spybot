import requests
import json
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
answers_record = {}  # Untuk menyimpan jawaban yang sudah diberikan

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


# Fungsi untuk menyimpan skor ke Google Sheets
def add_score(chat_id):
    # Memeriksa keberadaan skor untuk chat_id
    if chat_id not in user_data or "score" not in user_data[chat_id]:
        print("Tidak ada skor untuk chat_id ini.")
        return  

    scores = user_data[chat_id]["score"]
    score_message = [
        {
            "playerId": user_id,
            "playerName": score['nama'],
            "score": score['poin']
        }
        for user_id, score in scores.items()
    ]

    # Jika score_message kosong, tidak ada yang perlu dikirim
    if not score_message:
        print("Tidak ada skor untuk dikirim.")
        return

    # Menyimpan data dalam payload
    payload = score_message

    # Mengirim data ke Google Apps Script
    try:
        response = requests.post(
            "https://script.google.com/macros/s/AKfycbwKfk6UoHCKdbG8YQXqRXBH8UbDQ6fSWSOkKMXfRMTpuTZ8KZLYz_bMC0DP6JTYqFMqDQ/exec",
            headers={"Content-Type": "application/json"},
            json=payload  # Menggunakan parameter json untuk otomatis mengonversi ke JSON
        )

        # Memeriksa respons
        if response.status_code == 200:
            print("Data berhasil dikirim!")
        else:
            print("Terjadi kesalahan saat mengirim data.")

    except Exception as e:
        print(f"Error: {e}")




# Fungsi untuk memulai permainan
def play_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id

       # Cek apakah game sudah dimulai
    if chat_id in user_data and user_data[chat_id]["current_question"] is not None:
        current_question = user_data[chat_id]["current_question"]
        question_text = f"{current_question['question']}\n" + "\n".join([f"{i + 1}. {answers_record[chat_id][i]}" for i in range(len(current_question["answers"]))])
    
        # Gabungkan pertanyaan dan instruksi dalam satu pesan
        full_message = f"{question_text}\n\nGame sudah dimulai, Ketik /next untuk berganti soal permainan."
        update.message.reply_text(full_message)
        return
    
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
    answers_record[chat_id] = ["_______"] * len(question["answers"])  # Inisialisasi penyimpanan jawaban yang sudah diberikan

    # Kirim pertanyaan ke grup
    question_text = f"{question['question']}\n" + "\n".join([f"{i + 1}. {answers_record[chat_id][i]}" for i in range(len(question["answers"]))])
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
    
    
    
    # Simpan jawaban ke dalam answers_record pada posisi yang sesuai
    answers_record[chat_id][correct_index] = f"{answers[correct_index]} (+1) [{user_name}]"

    # Update pesan dengan jawaban yang benar
    response_message = f"{current_question['question']}\n"
    for i in range(len(answers)):
        response_message += f"{i + 1}. {answers_record[chat_id][i]}\n"

    if all(correct_answers_status[current_question["question"]]):
        response_message += "\nSemua jawaban sudah terjawab. Ketik /play untuk pertanyaan berikutnya."        
    
        # Simpan skor ke Google Sheets
        add_score(chat_id)
        
        del user_data[chat_id]  # Hapus data game setelah semua terjawab
        del correct_answers_status[current_question["question"]]
        del answers_record[chat_id] 
        
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


# Fungsi untuk menyerah pada pertanyaan
def give_up(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id

    # Cek apakah permainan sudah dimulai
    if chat_id not in user_data or user_data[chat_id]["current_question"] is None:
        update.message.reply_text("Game belum dimulai. Ketik /play untuk memulai permainan.")
        return

    current_question = user_data[chat_id]["current_question"]

    # Mencari jawaban yang belum dijawab
    answers = current_question["answers"]
    unanswered_answers = [i for i, answered in enumerate(correct_answers_status[current_question["question"]]) if not answered]

    if unanswered_answers:
        # Pilih satu jawaban yang belum dijawab secara acak
        random_index = random.choice(unanswered_answers)
        answer_to_show = answers[random_index]
        user_name = update.message.from_user.first_name
        
        # Tampilkan jawaban yang belum dijawab
        response_message = f"{user_name} menyerah pada pertanyaan:\n\n{current_question['question']}\n"
        for i in range(len(answers)):
            if i == random_index:
                response_message += f"{i + 1}. {answer_to_show} [🤖 bot]\n"  # Menambahkan nomor
            else:
                response_message += f"{i + 1}. {answers_record[chat_id][i]}\n"  # Menambahkan nomor
        
        response_message += "\nKetik /play untuk pertanyaan lain."
        update.message.reply_text(response_message)

        add_score(chat_id)
        
        del user_data[chat_id]  # Hapus data game setelah semua terjawab
        del correct_answers_status[current_question["question"]]
        del answers_record[chat_id] 
        
    else:
        update.message.reply_text("Semua jawaban sudah dijawab.")
        

# Fungsi untuk pertanyaan berikutnya
def next_question(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id

    # Cek apakah permainan sudah dimulai
    if chat_id not in user_data or user_data[chat_id]["current_question"] is None:
        update.message.reply_text("Game belum dimulai. Ketik /play untuk memulai permainan.")
        return

    # Hapus data pertanyaan sebelumnya
    add_score(chat_id)
    del correct_answers_status[user_data[chat_id]["current_question"]["question"]]
    del answers_record[chat_id]

    # Pilih pertanyaan baru
    question = random.choice(questions)
    user_data[chat_id]["current_question"] = question
    correct_answers_status[question["question"]] = [False] * len(question["answers"])  # Inisialisasi status jawaban benar
    answers_record[chat_id] = ["_______"] * len(question["answers"])  # Inisialisasi penyimpanan jawaban yang sudah diberikan

    # Kirim pertanyaan ke grup
    question_text = f"{question['question']}\n" + "\n".join([f"{i + 1}. {answers_record[chat_id][i]}" for i in range(len(question["answers"]))])
    update.message.reply_text(question_text)



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
    dp.add_handler(CommandHandler("nyerah", give_up))
    dp.add_handler(CommandHandler("next", next_question))  # Tambahkan handler untuk pertanyaan berikutnya
    
    updater.start_polling()

    # Jalankan Flask pada thread terpisah
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

if __name__ == '__main__':
    main()
