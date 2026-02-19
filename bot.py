from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import yt_dlp
import os
import threading
import time
import subprocess
import uuid
import glob

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

if not API_ID or not API_HASH or not BOT_TOKEN:
    raise RuntimeError("ENV vars missing: API_ID, API_HASH, BOT_TOKEN")

app = Client(
    "video_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

user_links = {}


def delete_after(filepath, delay_seconds=86400):
    def _delete():
        time.sleep(delay_seconds)
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except:
            pass

    threading.Thread(target=_delete, daemon=True).start()


def safe_edit(msg, text):
    try:
        msg.edit(text)
    except:
        pass


def find_downloaded_files(unique_id: str):
    # هرچی با این uuid شروع شده را پیدا می‌کنیم (برای حالت merge یا چند فایل)
    return sorted(glob.glob(f"{unique_id}.*"))


def is_video_file(path: str):
    ext = os.path.splitext(path)[1].lower()
    return ext in [".mp4", ".mkv", ".webm", ".mov", ".m4v"]


def is_audio_file(path: str):
    ext = os.path.splitext(path)[1].lower()
    return ext in [".m4a", ".mp3", ".aac", ".opus", ".ogg", ".wav", ".flac"]


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

    msg = callback_query.message.edit_text("در حال آماده‌سازی...")

    def run_download():
        unique_id = str(uuid.uuid4())
        # فایل‌های دانلودی را با uuid شروع می‌کنیم تا بعداً بتوانیم پیدا/پاک کنیم
        outtmpl = f"{unique_id}.%(ext)s"

        last_update = 0

        def progress_hook(d):
            nonlocal last_update
            if d.get("status") == "downloading":
                now = time.time()
                if now - last_update < 2:
                    return
                last_update = now

                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                downloaded = d.get("downloaded_bytes", 0)
                if total:
                    percent = downloaded / total * 100
                    safe_edit(msg, f"دانلود... {percent:.1f}%")
                else:
                    safe_edit(msg, "دانلود...")

        try:
            # تنظیمات yt-dlp:
            # - merge_output_format=mp4: تا جای ممکن خروجی merge نهایی mp4 باشد
            # - noplaylist: جلوگیری از دانلود پلی‌لیست
            # - progress_hooks: برای درصد
            # نکته: تبدیل اجباری با ffmpeg را اینجا انجام نمی‌دهیم مگر لازم شود
            if quality == "audio":
                ydl_opts = {
                    "format": "bestaudio/best",
                    "outtmpl": outtmpl,
                    "merge_output_format": "mp4",
                    "noplaylist": True,
                    "progress_hooks": [progress_hook],
                    "quiet": True,
                    "no_warnings": True,
                }
            else:
                ydl_opts = {
                    "format": f"bestvideo[height<={quality}]+bestaudio/best",
                    "outtmpl": outtmpl,
                    "merge_output_format": "mp4",
                    "noplaylist": True,
                    "progress_hooks": [progress_hook],
                    "quiet": True,
                    "no_warnings": True,
                }

            safe_edit(msg, "در حال دانلود...")

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # دانلود
                ydl.download([url])

            # پیدا کردن فایل(ها)ی تولید شده
            files = find_downloaded_files(unique_id)
            video_candidates = [f for f in files if is_video_file(f)]
            audio_candidates = [f for f in files if is_audio_file(f)]

            if quality == "audio":
                # اگر فقط صداست، اولین فایل صوتی را بفرست
                if audio_candidates:
                    final_path = audio_candidates[0]
                    safe_edit(msg, "در حال ارسال فایل صوتی...")
                    callback_query.message.reply_document(final_path)
                    safe_edit(msg, "ارسال شد ✅")
                    delete_after(final_path)
                else:
                    # بعضی سایت‌ها ممکن است خروجی را mp4 بدهند (صدا داخل mp4)
                    if video_candidates:
                        final_path = video_candidates[0]
                        safe_edit(msg, "در حال ارسال...")
                        callback_query.message.reply_video(final_path, supports_streaming=True)
                        safe_edit(msg, "ارسال شد ✅")
                        delete_after(final_path)
                    else:
                        raise RuntimeError("فایل خروجی پیدا نشد.")
            else:
                if not video_candidates:
                    raise RuntimeError("فایل ویدیو پیدا نشد.")

                input_file = video_candidates[0]

                # اگر خروجی همین الان mp4 است، لازم نیست ffmpeg اجرا کنیم
                if input_file.lower().endswith(".mp4"):
                    safe_edit(msg, "در حال ارسال...")
                    callback_query.message.reply_video(input_file, supports_streaming=True)
                    safe_edit(msg, "ارسال شد ✅")
                    delete_after(input_file)
                else:
                    # تبدیل به MP4 با نام متفاوت (برای جلوگیری از in-place)
                    safe_edit(msg, "در حال تبدیل به MP4... 🎬")
                    output_tmp = f"{unique_id}.converted.mp4"

                    subprocess.run([
                        "ffmpeg", "-y",
                        "-i", input_file,
                        "-c:v", "libx264",
                        "-c:a", "aac",
                        output_tmp
                    ], check=True)

                    callback_query.message.reply_video(output_tmp, supports_streaming=True)
                    safe_edit(msg, "ارسال شد ✅")

                    delete_after(output_tmp)

            # پاکسازی بقیه فایل‌های این uuid (به‌جز اونکه زمان‌بندی حذف دارد)
            # هرچی باقی مانده و غیر از فایل ارسال‌شده را حذف می‌کنیم
            for f in find_downloaded_files(unique_id):
                try:
                    # اگر فایل زمان‌بندی حذف دارد، باز هم حذف فوری نکن
                    if os.path.exists(f) and not f.endswith(".converted.mp4"):
                        # اگر همین فایل ارسال شده بوده (mp4 مستقیم)، باز حذف فوری نکن
                        pass
                except:
                    pass

            user_links.pop(user_id, None)

        except Exception as e:
            safe_edit(msg, f"خطا:\n{e}")
            print(e)

            # اگر دانلود نصفه فایل ساخته، پاکش کن
            try:
                for f in find_downloaded_files(unique_id):
                    try:
                        if os.path.exists(f):
                            os.remove(f)
                    except:
                        pass
            except:
                pass

    threading.Thread(target=run_download, daemon=True).start()


print("BOT STARTED")
app.run()
