import requests
from telegram import Update
from telegram.ext import CallbackContext

# URL Google Apps Script untuk mengambil data pemain
STATS_SCRIPT_URL = 'https://script.google.com/macros/s/AKfycbwDqdrHOTxS9cj8dTEHI0alLQHxQKZ4McDPrLBjh_IN3S4b23DrLsEm7OBx7DnykMgg/exec'  # Ganti dengan URL Anda

# Fungsi untuk menampilkan statistik pemain
def player_stats(update: Update, context: CallbackContext) -> None:
    try:
        # Mengambil data dari Google Sheets
        response = requests.get(STATS_SCRIPT_URL)
        response.raise_for_status()  # Memastikan respons yang baik
        data = response.json()  # Mengambil data dalam format JSON

        # Mengurutkan data berdasarkan skor
        data.sort(key=lambda x: x[2], reverse=True)

        # Ambil ID pengguna dari pesan
        user_id = update.message.from_user.id
        
        # Mencari indeks pemain berdasarkan ID
        index = next((i for i, player in enumerate(data) if player[0] == user_id), -1)

        # Jika pemain tidak ditemukan
        if index == -1:
            update.message.reply_text(
                f"<b>Your Game Stats</b>\n\n"
                f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
                f"🌟 <b>Point:</b> 0\n"
                f"🌏 <b>Global Rank:</b> -", 
                parse_mode='HTML'
            )
            return
        
        # Jika pemain ditemukan
        player_score = data[index][2]  # Poin pemain
        global_rank = index + 1  # Peringkat global

        # Mengirim pesan dengan statistik pemain
        update.message.reply_text(
            f"<b>Your Game Stats</b>\n\n"
            f"🆔 <b>ID:</b> <code>{user_id}</code>\n"
            f"🌟 <b>Point:</b> {player_score}\n"
            f"🌏 <b>Global Rank:</b> {global_rank}",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error fetching player stats: {e}")
        update.message.reply_text("Terjadi kesalahan saat mengambil statistik pemain.")

# Fungsi untuk menampilkan top player
def top_players(update: Update, context: CallbackContext) -> None:
    try:
        # Mengambil data dari Google Sheets
        response = requests.get(STATS_SCRIPT_URL)
        response.raise_for_status()  # Memastikan respons yang baik
        data = response.json()  # Mengambil data dalam format JSON

        # Mengurutkan data berdasarkan skor
        data.sort(key=lambda x: x[2], reverse=True)

        pesan = "<b>Top Player Global</b>\n"
        rank_limit = 20  # Batasi jumlah pemain yang ditampilkan

        for i, player in enumerate(data):
            if i >= rank_limit:  # Hentikan setelah 20 pemain
                break
            
            mdl = ''
            top = ''
            if i == 0:
                mdl += '🥇'
                top += '🏆'
            elif i == 1:
                mdl += '🥈'
            elif i == 2:
                mdl += '🥉'
            else:
                mdl += '▫'

            user_id = player[0]  # ID pengguna
            user_name = player[1]  # Nama pengguna
            user_score = player[2]  # Skor pengguna
            urlku = f'tg://user?id={user_id}'  # URL untuk menghubungkan ke pengguna di Telegram
            
            pesan += f'\n{mdl}<b> {i + 1}.</b> <a href="{urlku}">{user_name}</a> - <b>({user_score})</b> {top}'

        # Mengirim pesan ke pengguna
        update.message.reply_text(pesan, parse_mode='HTML', disable_web_page_preview=True)

    except Exception as e:
        logger.error(f"Error fetching top players: {e}")
        update.message.reply_text("Terjadi kesalahan saat mengambil data pemain teratas.")
