from pyrogram import Client, filters
import yt_dlp
import os
import threading
import time

# توکن رباتت از BotFather
BOT_TOKEN = "8587432432:AAGuMfvFVzjMrlr3Bs1I39nQRiwKLpaYXOY"

app = Client("video_bot", bot_token=BOT_TOKEN)

# تابع حذف فایل بعد از زمان مشخص
def delete_after(filename, delay_seconds=86400):  # 86400 ثانیه = 24 ساعت
    def _delete():
        time.sleep(delay_seconds)
        if os.path.exists(filename):
            os.remove(filename)
            print(f"{filename} پاک شد")
    threading.Thread(target=_delete, daemon=True).start()

@app.on_message(filters.private & filters.text)
def downloader(client, message):
    url = message.text
    msg = message.reply("در حال دانلود...")

    ydl_opts = {
        "format": "best",
        "outtmpl": "video.%(ext)s"  # فایل داخل فولدر پروژه ذخیره می‌شود
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filename = ydl.prepare_filename(info)

        message.reply_video(filename)
        msg.edit("دانلود و ارسال کامل شد ✅")

        # پاک کردن فایل بعد از 24 ساعت
        delete_after(filename)

    except Exception as e:
        msg.edit(f"خطا در دانلود: {e}")
        print(e)  # خطا در ترمینال VPS نمایش داده می‌شود

app.run()
