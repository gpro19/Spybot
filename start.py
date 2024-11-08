from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram import Update
from telegram.ext import CallbackContext

# Fungsi untuk menangani perintah /start
def start_game(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat.id
    user_name = update.message.from_user.first_name
    if update.message.from_user.last_name:
        user_name += ' ' + update.message.from_user.last_name

    # Membersihkan nama dari karakter khusus HTML jika perlu
    user_name = user_name

    # Menyiapkan keyboard
    keyboard = [
        [InlineKeyboardButton("Support", url='https://t.me/Mazekubot'),
         InlineKeyboardButton("Dev", url='https://t.me/MzCoder')]
    ]

    # Mengirim pesan sambutan
    welcome_message = (
        f"Hai! {user_name}, saya host-bot game Family100 di grup Telegram. "
        "Tambahkan saya ke grup untuk mulai bermain game!\n\n"
        "/play : mulai game\n"
        "/nyerah : menyerah dari game\n"
        "/next : Pertanyaan berikutnya\n"
        "/help : membuka pesan bantuan\n"
        "/stats : melihat statistik kamu\n"
        "/top : lihat top skor global\n"
        "/topgrup : lihat top global grup\n"
        "/peraturan : aturan bermain\n"
        "/donasi : dukung bot ini agar tetap aktif"
    )
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(welcome_message, reply_markup=reply_markup)



# Fungsi untuk menangani anggota baru
def new_chat_members(update: Update, context: CallbackContext) -> None:
    new_user = update.message.new_chat_members[0]  # Ambil anggota baru
    id_user = new_user.id  # ID pengguna baru
    id_group = update.chat.id  # ID grup
    username = f"@{update.chat.username}" if update.chat.username else "No data"  # Username grup

    # Cek apakah ID pengguna baru sama dengan ID bot Anda
    if new_user.id == context.bot.id:
        # Mengirim pesan sambutan ke grup
        update.message.reply_html(
            "Halo semua, terima kasih sudah mengundang saya ke grup ini.\n\n"
            "/play : mulai game\n"
            "/nyerah : menyerah dari game\n"
            "/next : Pertanyaan berikutnya\n"
            "/help : membuka pesan bantuan\n"
            "/stats : melihat statistik kamu\n"
            "/top : lihat top skor global\n"
            "/topgrup : lihat top global grup\n"
            "/peraturan : aturan bermain\n"
            "/donasi : dukung bot ini agar tetap aktif"
        )

        # Membuat pesan untuk dikirim ke admin atau grup lain
        pesan = "#Family100Robot"
        pesan += f"\nadded to <b>{update.chat.title}</b> (<code>{id_group}</code>)\n{username}"
        pesan += f"\n\nby [#id{update.message.from_user.id}]"

        # Kirim pesan ke grup admin atau grup tertentu
        context.bot.send_message(chat_id='-1002043233293', text=pesan, parse_mode='HTML')
