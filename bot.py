from pyrogram import Client, filters
import yt_dlp
import os

# توکن رباتت از BotFather
BOT_TOKEN = "YOUR_BOT_TOKEN"

app = Client("video_bot", bot_token=BOT_TOKEN)

@app.on_message(filters.private & filters.text)
def downloader(client, message):
    url = message.text
    msg = message.reply("در حال دانلود...")

    ydl_opts = {
        "format": "best",
        "outtmpl": "video.%(ext)s"  # فایل داخل فولدر پروژه ذخیره می‌شه
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url)
            filename = ydl.prepare_filename(info)

        message.reply_video(filename)
        msg.edit("دانلود و ارسال کامل شد ✅")
        os.remove(filename)  # بعد از ارسال فایل پاک می‌شه

    except Exception as e:
        msg.edit(f"خطا در دانلود: {e}")
        print(e)  # خطا در ترمینال VPS نمایش داده می‌شه

app.run()

