import requests
import json
import os
import logging
import random
import threading
from flask import Flask, request
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from pymongo import MongoClient

from start import start_game, new_chat_members, send_donation_info, send_help_info, send_game_rules, top_grup  # Mengimpor fungsi dari start.py
from game_stats import player_stats, top_players

# Inisialisasi Flask
app = Flask(__name__)

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL Google Apps Script untuk mengambil pertanyaan
TOKEN = '7386179157:AAHcq5JrAxYjlTcULZlbvXR1YX5ygfvyrYY'  # Ganti dengan token bot Telegram Anda
GOOGLE_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbxBSMAruuH0lPIzQNE2L0JyCuSCVHPb85Ua1RHdEq6CCOu7ZVrlgsBFe2ZR8rFBmt4H/exec'  # Ganti dengan URL Google Apps Script Anda


# Inisialisasi MongoDB
mongo_client = MongoClient('mongodb+srv://ilham:galeh@cluster0.bsr41.mongodb.net/?retryWrites=true&w=majority')  # Ganti dengan URI MongoDB Anda jika perlu
db = mongo_client['game_db']  # Ganti dengan nama database yang diinginkan
users_collection = db['users']  # Koleksi untuk menyimpan data pengguna

# Inisialisasi variabel untuk menyimpan pertanyaan
questions = []

# Nama file lokal untuk menyimpan pertanyaan
QUESTIONS_FILE = 'questions.json'

# Fungsi untuk menyimpan pertanyaan ke file lokal
def save_questions_to_file(questions):
    with open(QUESTIONS_FILE, 'w') as f:
        json.dump(questions, f)

# Fungsi untuk memuat pertanyaan dari file lokal
def load_questions_from_file():
    global questions
    if os.path.exists(QUESTIONS_FILE):
        with open(QUESTIONS_FILE, 'r') as f:
            questions = json.load(f)
    else:
        questions = fetch_questions()  # Ambil dari Google Apps Script jika file tidak ada
        save_questions_to_file(questions)  # Simpan ke file lokal

# Fungsi untuk mengambil data pertanyaan dan jawaban
def fetch_questions():
    try:
        response = requests.get(GOOGLE_SCRIPT_URL)
        response.raise_for_status()  # Raise an error for bad responses
        return response.json()
    except Exception as e:
        logger.error(f"Failed to fetch questions: {e}")
        return []



# Fungsi untuk menyimpan skor ke Google Sheets
def add_score(scores):
        

    if not scores:
        logger.info("Skor kosong untuk chat_id ini.")
        return
        
    score_message = [
        {
            "playerId": user_id,
            "playerName": score['nama'],
            "score": score['poin']
        }
        for user_id, score in scores.items()
    ]

    if not score_message:
        #logger.info("Tidak ada skor untuk dikirim.")
        return

    # Mengirim data ke Google Apps Script
    try:
        response = requests.post(
            "https://script.google.com/macros/s/AKfycbwKfk6UoHCKdbG8YQXqRXBH8UbDQ6fSWSOkKMXfRMTpuTZ8KZLYz_bMC0DP6JTYqFMqDQ/exec",
            headers={"Content-Type": "application/json"},
            json=score_message
        )

        if response.status_code == 200:
            print("Data berhasil dikirim!")
        else:
            print("Terjadi kesalahan saat mengirim data.")

    except Exception as e:
        print(f"Error: {e}")



# Fungsi untuk mengirim pesan peringatan jika bot bukan administrator
def send_admin_alert(update: Update, context: CallbackContext) -> None:
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="<b>⚠️ Alert ⚠️</b>\n<i>Jadikan bot sebagai <b>admin</b> dan beri bot hak untuk <b>menghapus pesan.</b></i>",
        reply_to_message_id=update.message.message_id,
        parse_mode='HTML',
        disable_web_page_preview=True
    )

# Fungsi untuk memeriksa apakah bot adalah administrator
def is_bot_admin(update: Update, context: CallbackContext) -> bool:
    bot_id = context.bot.id
    adm = context.bot.get_chat_member(update.effective_chat.id, bot_id)
    return adm.status == "administrator"






# Fungsi untuk memulai permainan
def play_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.effective_chat.id
    
     # ID grup yang diizinkan
    allowed_group_id = -1001651683956

    if update.effective_chat.id != allowed_group_id:
        return update.message.reply_html('<i>Bot hanya dapat digunakan di support grup</i>')

    
    if update.effective_chat.type == 'private':
        return update.message.reply_html('<i>Bot hanya dapat dimainkan pada grup</i>')

    # Cek apakah bot adalah administrator
    #if not is_bot_admin(update, context):
        #send_admin_alert(update, context)
        #return
        
    user_data = users_collection.find_one({"chat_id": chat_id})
    
    # Cek apakah game sudah dimulai
    if user_data and user_data.get("current_question") is not None:
        current_question = user_data["current_question"]
        question_text = f"{current_question['question']}\n" + "\n".join([f"{i + 1}. {user_data['answers_record'][i]}" for i in range(len(current_question["answers"]))])
        full_message = f"{question_text}\n\nGame sudah dimulai, Ketik /next untuk berganti soal permainan."
        update.message.reply_text(full_message)
        return
    
    # Cek apakah game sudah dimulai
    if user_data is None:
        users_collection.insert_one({
            "chat_id": chat_id,
            "current_question": None,
            "score": {},
            "correct_answers_status": [],
            "answers_record": []
        })

    # Pilih pertanyaan secara acak
    question = random.choice(questions)
    users_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "current_question": question,
            "correct_answers_status": [False] * len(question["answers"]),  # Inisialisasi status jawaban benar
            "answers_record": ["_______"] * len(question["answers"])  # Inisialisasi penyimpanan jawaban yang sudah diberikan
        }}
    )

    # Kirim pertanyaan ke grup
    question_text = f"{question['question']}\n" + "\n".join([f"{i + 1}. _______" for i in range(len(question['answers']))])
    update.message.reply_text(question_text)

# Fungsi untuk memproses jawaban
def answer(update: Update, context: CallbackContext) -> None:
    
    if update.message is None:
        return
    
    chat_id = update.message.chat.id
    user_id = update.message.from_user.id
    user_name = update.message.from_user.first_name
    answer_text = update.message.text.lower().strip()
    
    
    user_data = users_collection.find_one({"chat_id": chat_id})

    # Cek apakah permainan sudah dimulai
    if user_data is None:
        #update.message.reply_text("Belum ada permainan yang dimulai. Ketik /play untuk memulai.")
        return
    
    scores = user_data["score"]
    current_question = user_data.get("current_question")

    # Cek apakah ada pertanyaan aktif
    if current_question is None:
        #update.message.reply_text("Tidak ada pertanyaan aktif.")
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
        #update.message.reply_text("Jawaban tidak valid. Coba lagi.")
        return

    if user_data["correct_answers_status"][correct_index]:
        #update.message.reply_text("Jawaban ini sudah dijawab dengan benar oleh pemain lain. Coba jawaban lain.")
        return

    # Tandai jawaban ini sebagai benar
    user_data["correct_answers_status"][correct_index] = True
    
    # Update skor untuk pemain yang menjawab
    if str(user_id) not in user_data["score"]:
        user_data["score"][str(user_id)] = {"nama": user_name, "poin": 0}

    pts = random.randint(1, 10)
    user_data["score"][str(user_id)]["poin"] += pts  # Tambahkan poin
    
    # Simpan jawaban ke dalam answers_record pada posisi yang sesuai
    user_data["answers_record"][correct_index] = f"{answers[correct_index]} (+{pts}) [{user_name}]"

    # Update pesan dengan jawaban yang benar
    response_message = f"{current_question['question']}\n"
    for i in range(len(answers)):
        response_message += f"{i + 1}. {user_data['answers_record'][i]}\n"

    if all(user_data["correct_answers_status"]):
        response_message += "\nSemua jawaban sudah terjawab. Ketik /play untuk pertanyaan berikutnya."        
        
        update.message.reply_text(response_message)
        
        # Simpan skor ke Google Sheets
        add_score(scores)
        
        users_collection.delete_one({"chat_id": chat_id})  # Hapus data game setelah semua terjawab
        
    else:
        users_collection.update_one({"chat_id": chat_id}, {"$set": user_data})
        update.message.reply_text(response_message)


# Fungsi untuk melihat skor pemain
def view_score(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id

    user_data = users_collection.find_one({"chat_id": chat_id})

    if user_data is None or "score" not in user_data:
        update.message.reply_text("Belum ada permainan yang dimulai atau belum ada pemain yang memiliki skor.")
        return

    scores = user_data["score"]
    score_message = "Skor Pemain:\n"

    for user_id, score in scores.items():
        score_message += f"{score['nama']}: {score['poin']}\n"

    update.message.reply_text(score_message)

# Fungsi untuk menyerah pada pertanyaan
def give_up(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    
    if update.effective_chat.type == 'private':
        return update.message.reply_html('<i>Bot hanya dapat dimainkan pada grup</i>')
        
    user_data = users_collection.find_one({"chat_id": chat_id})
    
    
    # Cek apakah permainan sudah dimulai
    if user_data is None or user_data["current_question"] is None:
        update.message.reply_text("Game belum dimulai. Ketik /play untuk memulai permainan.")
        return
    
    scores = user_data["score"]
    current_question = user_data["current_question"]

    # Mencari jawaban yang belum dijawab
    answers = current_question["answers"]
    unanswered_answers = [i for i, answered in enumerate(user_data["correct_answers_status"]) if not answered]

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
                response_message += f"{i + 1}. {user_data['answers_record'][i]}\n"  # Menambahkan nomor
        
        response_message += "\nKetik /play untuk pertanyaan lain."
        update.message.reply_text(response_message)
       
        add_score(scores)
        
        users_collection.delete_one({"chat_id": chat_id})  # Hapus data game setelah semua terjawab
        
    else:
        update.message.reply_text("Semua jawaban sudah dijawab.")

# Fungsi untuk pertanyaan berikutnya
def next_question(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    
    if update.effective_chat.type == 'private':
        return update.message.reply_html('<i>Bot hanya dapat dimainkan pada grup</i>')
        
    user_data = users_collection.find_one({"chat_id": chat_id})
    
    # Cek apakah permainan sudah dimulai
    if user_data is None or user_data["current_question"] is None:
        update.message.reply_text("Game belum dimulai. Ketik /play untuk memulai permainan.")
        return
     
    scores = user_data["score"]
    
    # Hapus data pertanyaan sebelumnya
    #users_collection.delete_one({"chat_id": chat_id})

    
    if user_data is None:
        users_collection.insert_one({
            "chat_id": chat_id,
            "current_question": None,
            "score": {},
            "correct_answers_status": [],
            "answers_record": []
        })
        
    # Pilih pertanyaan baru
    question = random.choice(questions)
    users_collection.update_one(
        {"chat_id": chat_id},
        {"$set": {
            "current_question": question,
            "score": {},
            "correct_answers_status": [False] * len(question["answers"]),  # Inisialisasi status jawaban benar
            "answers_record": ["_______"] * len(question["answers"]),  # Inisialisasi penyimpanan jawaban yang sudah diberikan
        }}
    )

    # Kirim pertanyaan ke grup
    question_text = f"{question['question']}\n" + "\n".join([f"{i + 1}. _______" for i in range(len(question["answers"]))])
    update.message.reply_text(question_text)
    add_score(scores)

@app.route('/webhook', methods=['POST'])
def webhook():
    update = request.get_json()
    logger.info(f"Received update: {update}")

    if "message" in update and "text" in update["message"]:
        # Panggil fungsi yang memproses pesan
        handle_message(update)

    return '', 200

def run_flask():
    app.run(host='0.0.0.0', port=8000)

def main():
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    
    load_questions_from_file()
    updater = Updater(TOKEN)

    updater.start_webhook(listen='0.0.0.0', port=8000, url_path='webhook')
    updater.bot.setWebhook('https://fair-berthe-grng-57915732.koyeb.app/webhook')  # Ganti dengan domain Anda

    
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start_game, Filters.chat_type.private))
    dp.add_handler(CommandHandler("play", play_game))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, answer))
    dp.add_handler(CommandHandler("score", view_score))  # Tambahkan handler untuk melihat skor
    dp.add_handler(CommandHandler("nyerah", give_up))
    dp.add_handler(CommandHandler("next", next_question))  # Tambahkan handler untuk pertanyaan berikutnya
    dp.add_handler(CommandHandler("stats", player_stats))  # Menambahkan handler untuk /stats
    dp.add_handler(CommandHandler("top", top_players))  # Menambahkan handler untuk /top
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, new_chat_members))
    dp.add_handler(CommandHandler('donasi', send_donation_info))
    dp.add_handler(CommandHandler('help', send_help_info))
    dp.add_handler(CommandHandler('peraturan', send_game_rules))
    dp.add_handler(CommandHandler("topgrup", top_grup))
    

    
    #updater.start_polling()

    # Jalankan Flask pada thread terpisah
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Jalankan updater
    updater.idle()
    
if __name__ == '__main__':
    main()
