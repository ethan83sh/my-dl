from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
import threading
import time
import subprocess

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

def delete_after(filename, delay_seconds=86400):
    def _delete():
        time.sleep(delay_seconds)
        if os.path.exists(filename):
            os.remove(filename)
    threading.Thread(target=_delete, daemon=True).start()

user_links = {}

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
        "کیفیت رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

@app.on_callback_query()
def download_video(client, callback_query):
    user_id = callback_query.from_user.id
    quality = callback_query.data
    url = user_links.get(user_id)

    msg = callback_query.message.edit_text("در حال دانلود... 0%")

    def progress_hook(d):
        if d['status'] == 'downloading':
            total = d.get('total_bytes') or d.get('total_bytes_estimate')
            downloaded = d.get('downloaded_bytes', 0)
            if total:
                percent = downloaded / total * 100
                try:
                    msg.edit(f"دانلود... {percent:.1f}%")
                except:
                    pass

    if quality == "audio":
        ydl_opts = {
            "format": "bestaudio",
            "outtmpl": "input.%(ext)s",
            "progress_hooks": [progress_hook]
        }
    else:
        ydl_opts = {
            "format": f"bestvideo[height<={quality}]+bestaudio/best",
            "outtmpl": "input.%(ext)s",
            "progress_hooks": [progress_hook]
        }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            input_file = ydl.prepare_filename(info)

        output_file = "output.mp4"

        msg.edit("در حال تبدیل به MP4... 🎬")

        subprocess.run([
            "ffmpeg", "-y",
            "-i", input_file,
            "-c:v", "libx264",
            "-c:a", "aac",
            output_file
        ])

        callback_query.message.reply_video(output_file)
        msg.edit("ارسال شد ✅")

        delete_after(output_file)
        os.remove(input_file)
        user_links.pop(user_id, None)

    except Exception as e:
        msg.edit(f"خطا:\n{e}")
        print(e)

print("BOT STARTED")
app.run()
