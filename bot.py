from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
import threading
import time
import subprocess
import uuid

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")

app = Client(
    "video_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_links = {}


def delete_after(filename, delay_seconds=86400):
    def _delete():
        time.sleep(delay_seconds)
        if os.path.exists(filename):
            try:
                os.remove(filename)
            except:
                pass

    threading.Thread(target=_delete, daemon=True).start()


@app.on_message(filters.private & filters.text)
def choose_quality(client, message):
    url = message.text.strip()

    if not url.startswith("http"):
        message.reply("لینک معتبر ارسال کن ❌")
        return

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

    if not url:
        callback_query.answer("لینک پیدا نشد ❌", show_alert=True)
        return

    msg = callback_query.message.edit_text("در حال دانلود...")

    def run_download():
        try:
            unique_id = str(uuid.uuid4())
            input_template = f"{unique_id}.%(ext)s"
            output_file = f"{unique_id}.mp4"

            last_update = 0

            def progress_hook(d):
                nonlocal last_update
                if d['status'] == 'downloading':
                    now = time.time()
                    if now - last_update < 2:
                        return  # جلوگیری از flood
                    last_update = now

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
                    "outtmpl": input_template,
                    "progress_hooks": [progress_hook]
                }
            else:
                ydl_opts = {
                    "format": f"bestvideo[height<={quality}]+bestaudio/best",
                    "outtmpl": input_template,
                    "progress_hooks": [progress_hook]
                }

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url)
                input_file = ydl.prepare_filename(info)

            msg.edit("در حال تبدیل به MP4... 🎬")

            subprocess.run([
                "ffmpeg", "-y",
                "-i", input_file,
                "-c:v", "libx264",
                "-c:a", "aac",
                output_file
            ], check=True)

            callback_query.message.reply_video(output_file)
            msg.edit("ارسال شد ✅")

            delete_after(output_file)

            try:
                os.remove(input_file)
            except:
                pass

            user_links.pop(user_id, None)

        except Exception as e:
            try:
                msg.edit(f"خطا:\n{e}")
            except:
                pass
            print(e)

    threading.Thread(target=run_download).start()


print("BOT STARTED")
app.run()
