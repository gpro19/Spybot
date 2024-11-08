import requests
from telegram import Update
from telegram.ext import CallbackContext
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# URL Google Apps Script untuk mengambil data pemain
STATS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbwDqdrHOTxS9cj8dTEHI0alLQHxQKZ4McDPrLBjh_IN3S4b23DrLsEm7OBx7DnykMgg/exec'  # Ganti dengan URL Anda

# Fungsi untuk menampilkan statistik pemain
def player_stats(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id  # Ambil ID pengguna dari pesan
    try:
        # Mengambil data dari Google Sheets
        response = requests.get(f"{STATS_SCRIPT_URL}?action=stats&userId={user_id}")
        response.raise_for_status()  # Memastikan respons yang baik
        data = response.json()  # Mengambil data dalam format JSON

        logger.info(f"Data received: {data}")  # Menampilkan data yang diterima

        if not data:
            update.message.reply_text("Data tidak tersedia untuk pemain ini.")
            return
        
        # Mengirim pesan dengan statistik pemain
        update.message.reply_text(
            f"<b>Your Game Stats</b>\n\n"
            f"🆔 <b>ID:</b> <code>{data['id']}</code>\n"
            f"🌟 <b>Point:</b> {data['score']}\n"
            f"🌏 <b>Global Rank:</b> {data.get('rank', 'N/A')}",  # Sesuaikan jika ada peringkat
            parse_mode='HTML'
        )

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching player stats: {e}")
        update.message.reply_text("Terjadi kesalahan saat mengambil statistik pemain.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        update.message.reply_text("Terjadi kesalahan yang tidak terduga.")

# Fungsi untuk menampilkan top player
def top_players(update: Update, context: CallbackContext) -> None:
    try:
        # Mengambil data dari Google Sheets
        response = requests.get(f"{STATS_SCRIPT_URL}?action=top&limit=20")
        response.raise_for_status()  # Memastikan respons yang baik
        data = response.json()  # Mengambil data dalam format JSON

        logger.info(f"Data received: {data}")  # Menampilkan data yang diterima

        if not data:
            update.message.reply_text("Data pemain teratas tidak tersedia.")
            return

        pesan = "<b>🏆 Top Player Global</b>\n\n"  # Judul leaderboard
        for i, player in enumerate(data):
            user_id = player['id']  # ID pengguna
            user_name = player['name']  # Nama pengguna
            user_score = player['score']  # Skor pengguna
            urlku = f'tg://user?id={user_id}'  # URL untuk menghubungkan ke pengguna di Telegram
            
            # Menambahkan gaya berdasarkan peringkat
            medal = ''
            if i == 0:
                medal = '🥇'  # Emas untuk peringkat 1
            elif i == 1:
                medal = '🥈'  # Perak untuk peringkat 2
            elif i == 2:
                medal = '🥉'  # Perunggu untuk peringkat 3
            else:
                medal = '▫️'  # Simbol untuk peringkat lainnya

            pesan += f'<b>{medal} {i + 1}.</b> <a href="{urlku}">{user_name}</a> - <b>{user_score}</b> Points\n'  # Format pesan

        # Mengirim pesan ke pengguna
        update.message.reply_text(pesan, parse_mode='HTML', disable_web_page_preview=True)

    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching top players: {e}")
        update.message.reply_text("Terjadi kesalahan saat mengambil data pemain teratas.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        update.message.reply_text("Terjadi kesalahan yang tidak terduga.")
