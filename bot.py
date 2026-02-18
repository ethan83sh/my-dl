from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
import threading
import time

# اطلاعات تلگرام (از my.telegram.org)
API_ID = 32585381
API_HASH = "9309e4bd6128d74e7189caa91d899153"

# توکن ربات از BotFather
BOT_TOKEN = "8587432432:AAGuMfvFVzjMrlr3Bs1I39nQRiwKLpaYXOY"

app = Client(
    "video_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# حذف فایل بعد از 24 ساعت
def delete_after(filename, delay_seconds=86400):
    def _delete():
        time.sleep(delay_seconds)
        if os.path.exists(filename):
            os.remove(filename)
            print(f"{filename} پاک شد")
    threading.Thread(target=_delete, daemon=True).start()

# لینک‌های کاربران
user_links = {}

# وقتی لینک فرستاده شد
@app.on_message(filters.private & filters.text)
def choose_quality(client, message):
    url = message.text
    user_links[message.from_user.id] = url

    buttons = [
        [InlineKeyboardButton("144p", "144"), InlineKeyboardButton("360p", "360")],
        [InlineKeyboardButton("720p", "720"), InlineKeyboardButton("1080p", "1080")],
        [InlineKeyboardButton("🎧 Audio Only", "audio")]
    ]

    message.reply(
        "کیفیت مورد نظر رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# وقتی کاربر دکمه می‌زند
@app.on_callback_query()
def download_video(client, callback_query):
    user_id = callback_query.from_user.id
    quality = callback_query.data
    url = user_links.get(user_id)

    if not url:
        callback_query.answer("لینکی پیدا نشد!", show_alert=True)
        return

    msg = callback_query.message.edit_text(f"در حال دانلود {quality}... 0% ⏳")

    # Progress hook
    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = downloaded / total * 100
                try:
                    msg.edit(f"در حال دانلود {quality}... {percent:.1f}% ⏳")
                except:
                    pass

    # تنظیمات yt-dlp
    if quality == "audio":
        ydl_opts = {
            "format": "bestaudio",
            "outtmpl": "video.%(ext)s",
            "progress_hooks": [progress_hook]
        }
    else:
        ydl_opts = {
            "format": f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
            "outtmpl": "video.%(ext)s",
            "progress_hooks": [progress_hook]
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filename = ydl.prepare_filename(info)

        callback_query.message.reply_video(filename)
        msg.edit("دانلود و ارسال کامل شد ✅")

        delete_after(filename)
        user_links.pop(user_id, None)

    except Exception as e:
        msg.edit(f"خطا در دانلود:\n{e}")
        print(e)

print("BOT STARTED")
app.run()
