import os
import re
import time
import threading
import queue
import subprocess
import requests
import telebot
from telebot import types
from playwright.sync_api import sync_playwright

# ═══════════════════════════════════════
# 🔑 Configuration
# ═══════════════════════════════════════
TOKEN = "8640761166:AAF3Qjpt8xsH4r-M1Vaai6oBXwUcwmMl2Ww"
CHAT_ID = 7737151421
bot = telebot.TeleBot(TOKEN)

task_queue = queue.Queue()
is_working = False
worker_lock = threading.Lock()
user_context = {
    "state": "IDLE",
    "number": None,
    "otp": None,
    "pending_link": None,
}

BROWSER_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"]
YOUTUBE_DOMAINS = ["youtube.com", "youtu.be", "youtube-nocookie.com"]

# ═══════════════════════════════════════
# 🛠️ Helper Functions
# ═══════════════════════════════════════
def is_youtube(link):
    return any(d in link for d in YOUTUBE_DOMAINS)

def safe_filename(title):
    title = re.sub(r'[\\/*?:"<>|]', '', title)
    return title.strip().replace(' ', '_')[:80]

def msg(text, **kwargs):
    try:
        bot.send_message(CHAT_ID, text, parse_mode="Markdown", **kwargs)
    except Exception as e:
        print(f"Send error: {e}")

def take_screenshot(page, caption="📸"):
    try:
        page.screenshot(path="s.png")
        with open("s.png", 'rb') as f:
            bot.send_photo(CHAT_ID, f, caption=caption)
        os.remove("s.png")
    except: pass

# ═══════════════════════════════════════
# 🔑 Jazz Drive Login Logic
# ═══════════════════════════════════════
def do_login(page, context):
    global user_context
    msg("🔐 *LOGIN REQUIRED*\n\n📱 Apna Jazz number bhejein\nFormat: `03XXXXXXXXX`")
    user_context["state"] = "WAITING_FOR_NUMBER"

    # Wait for number (timeout 5 mins)
    for _ in range(300):
        if user_context["state"] == "NUMBER_RECEIVED": break
        time.sleep(1)
    else:
        msg("⏰ *Timeout!* Number nahi aaya.")
        return False

    page.locator("#msisdn").fill(user_context["number"])
    page.locator("#signinbtn").first.click()
    time.sleep(3)
    
    msg("✅ Number accept hua!\n🔢 *OTP bhejein*:")
    user_context["state"] = "WAITING_FOR_OTP"

    for _ in range(300):
        if user_context["state"] == "OTP_RECEIVED": break
        time.sleep(1)
    else:
        msg("⏰ *Timeout!* OTP nahi aaya.")
        return False

    otp = user_context["otp"].strip()
    for i, digit in enumerate(otp[:6], 1):
        try:
            page.locator(f"input[aria-label='Digit {i}']").fill(digit)
        except: pass

    time.sleep(5)
    context.storage_state(path="state.json")
    msg("✅ *LOGIN SUCCESSFUL*")
    user_context["state"] = "IDLE"
    return True

# ═══════════════════════════════════════
# ⬇️ Downloader Logic
# ═══════════════════════════════════════
def process_file(link, height=None, label=""):
    yt = is_youtube(link)
    video_title = "downloaded_file"
    
    if yt:
        try:
            video_title = subprocess.check_output(f"yt-dlp --get-title '{link}'", shell=True).decode().strip()
            video_title = safe_filename(video_title)
        except: pass

    OUT = f"{video_title}.mp4"
    msg(f"⬇️ *Downloading:* {video_title}")

    # yt-dlp command
    q_fmt = f"bestvideo[height<={height}][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" if height else "best"
    cmd = f"yt-dlp -f '{q_fmt}' --merge-output-format mp4 -o '{OUT}' '{link}'"
    
    os.system(cmd)

    if os.path.exists(OUT) and os.path.getsize(OUT) > 1000:
        msg(f"✅ Download Complete ({os.path.getsize(OUT)//1048576} MB). Uploading...")
        jazz_drive_upload(OUT)
    else:
        msg("❌ Download Failed.")

# ═══════════════════════════════════════
# ☁️ Jazz Drive Upload
# ═══════════════════════════════════════
def jazz_drive_upload(filename):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
        storage = "state.json" if os.path.exists("state.json") else None
        ctx = browser.new_context(storage_state=storage)
        page = ctx.new_page()
        
        try:
            page.goto("https://cloud.jazzdrive.com.pk/", timeout=60000)
            if page.locator("#msisdn").is_visible():
                if not do_login(page, ctx): return

            # Trigger Upload
            page.set_input_files("input[type='file']", os.path.abspath(filename))
            time.sleep(10) # Wait for upload progress
            msg("🚀 Uploading to Jazz Drive started...")
            
            # Wait for upload completion (simple sleep or check for success element)
            time.sleep(20) 
            msg("🏁 Upload process finished!")
        except Exception as e:
            msg(f"❌ Upload Error: {e}")
        finally:
            browser.close()
            if os.path.exists(filename): os.remove(filename)

# ═══════════════════════════════════════
# 🔄 Worker Loop
# ═══════════════════════════════════════
def worker_loop():
    global is_working
    while not task_queue.empty():
        item = task_queue.get()
        process_file(item["link"], item["height"], item["label"])
        task_queue.task_done()
    is_working = False

# ═══════════════════════════════════════
# 🤖 Bot Handlers
# ═══════════════════════════════════════
@bot.message_handler(commands=['start'])
def start(m):
    msg("🤖 *Jazz Drive Bot Active*\nSend me a link to start.")

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    global is_working
    text = message.text

    if user_context["state"] == "WAITING_FOR_NUMBER":
        user_context["number"] = text
        user_context["state"] = "NUMBER_RECEIVED"
        return
    
    if user_context["state"] == "WAITING_FOR_OTP":
        user_context["otp"] = text
        user_context["state"] = "OTP_RECEIVED"
        return

    if text.startswith("http"):
        task_queue.put({"link": text, "height": "720", "label": "720p"})
        msg("✅ Added to queue.")
        if not is_working:
            is_working = True
            threading.Thread(target=worker_loop, daemon=True).start()

# ═══════════════════════════════════════
# 🚀 START BOT (Crucial Missing Part)
# ═══════════════════════════════════════
if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()        f"💻 /cmd — Server command",
        reply_markup=types.ReplyKeyboardRemove()
    )

@bot.message_handler(commands=['checklogin'])
def cmd_checklogin(message):
    threading.Thread(target=check_login_status, daemon=True).start()

@bot.message_handler(commands=['status'])
def cmd_status(message):
    status_icon = "🟢" if is_working else "🔴"
    status_text = "Kaam chal raha hai" if is_working else "Khali (IDLE)"
    cookie = "✅ Active" if os.path.exists("state.json") else "❌ Nahi hai"
    msg(
        f"╔══════════════════════╗\n"
        f"║   📊  *BOT STATUS*      ║\n"
        f"╚══════════════════════╝\n\n"
        f"{status_icon} *State:* {status_text}\n"
        f"📋 *Queue:* {task_queue.qsize()} files pending\n"
        f"🍪 *Session:* {cookie}"
    )

@bot.message_handler(commands=['cmd'])
def cmd_shell(message):
    try:
        cmd = message.text.replace("/cmd ", "", 1).strip()
        out = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode()
        out = out[:4000] or "✅ Done (no output)"
        bot.reply_to(message, f"💻 *Output:*\n```\n{out}\n```", parse_mode="Markdown")
    except subprocess.CalledProcessError as e:
        bot.reply_to(message, f"❌ *Error:*\n```\n{e.output.decode()[:3000]}\n```", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, f"❌ `{str(e)}`", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_msg(message):
    global is_working
    text = message.text.strip() if message.text else ""
    remove_kb = types.ReplyKeyboardRemove()

    # ── Login states ──
    if user_context["state"] == "WAITING_FOR_NUMBER":
        user_context["number"] = text
        user_context["state"] = "NUMBER_RECEIVED"
        bot.reply_to(message, "✅ Number receive hua...")
        return

    if user_context["state"] == "WAITING_FOR_OTP":
        user_context["otp"] = text
        user_context["state"] = "OTP_RECEIVED"
        bot.reply_to(message, "✅ OTP receive hua...")
        return

    # ── Quality select ──
    if user_context["state"] == "WAITING_FOR_QUALITY":
        label = text.replace("🎯","").replace("📱","").replace("💻","").replace("🖥️","").replace("⭐","").strip()
        height = get_height_from_label(label)
        link = user_context["pending_link"]
        user_context["state"] = "IDLE"
        user_context["pending_link"] = None

        msg(
            f"✅ *{label}* quality select!\n"
            f"📋 Queue mein add ho raha hai...",
            reply_markup=remove_kb
        )

        task_queue.put({"link": link, "height": height, "label": label})
        with worker_lock:
            if not is_working:
                is_working = True
                threading.Thread(target=worker_loop, daemon=True).start()
        return

    # ── Link ──
    if text.startswith("http"):
        if is_youtube(text):
            ask_quality(text)
        else:
            task_queue.put({"link": text, "height": None, "label": "Direct"})
            bot.reply_to(message,
                f"✅ *Queue mein add!*\n"
                f"📍 Position: *{task_queue.qsize()}*",
                parse_mode="Markdown")
            with worker_lock:
                if not is_working:
                    is_working = True
                    threading.Thread(target=worker_loop, daemon=True).start()
    else:
        bot.reply_to(message,
            f"ℹ️ Direct link bhejein\n"
            f"ya `/checklogin` try karein",
            parse_mode="Markdown")

# ═══════════════════════════════════════
# 🔄 Worker Loop
# ═══════════════════════════════════════
def worker_loop():
    global is_working
    try:
        while not task_queue.empty():
            item = task_queue.get()
            link  = item["link"]
            height = item["height"]
            label  = item["label"]
            short  = link[:55] + "..." if len(link) > 55 else link
            msg(
                f"╔══════════════════════╗\n"
                f"║   🎬  *PROCESSING...*   ║\n"
                f"╚══════════════════════╝\n\n"
                f"🔗 `{short}`"
            )
            try:
                process_file(link, height, label)
            except Exception as e:
                msg(f"❌ *Error:*\n`{str(e)[:150]}`")
            finally:
                task_queue.task_done()

        msg(
            f"╔══════════════════════╗\n"
            f"║  ✅  *QUEUE COMPLETE!*  ║\n"
            f"╚══════════════════════╝\n\n"
            f"📎 Agla link bhejein\n"
            f"ya rest karo! 😊"
        )
    except Exception as e:
        msg(f"⚠️ Worker crash:\n`{str(e)[:150]}`")
    finally:
        with worker_lock:
            is_working = False

# ═══════════════════════════════════════
# ⬇️ Universal Downloader
# ═══════════════════════════════════════
def file_ok(f, min_mb=2):
    if not os.path.exists(f): return False
    return os.path.getsize(f) / (1024*1024) >= min_mb

def clean(f):
    if os.path.exists(f): os.remove(f)

def get_yt_title(link):
    try:
        result = subprocess.check_output(
            f"yt-dlp --no-warnings --get-title '{link}'",
            shell=True, stderr=subprocess.DEVNULL
        ).decode().strip()
        return safe_filename(result) if result else None
    except:
        return None

def process_file(link, height=None, label=""):
    yt = is_youtube(link)
    min_size = 5 if yt else 2

    video_title = None
    if yt:
        msg(f"📝 *Video info fetch ho rahi hai...*")
        video_title = get_yt_title(link)
        if video_title:
            display = video_title.replace('_', ' ')
            msg(
                f"🎬 *{display}*\n"
                f"📐 Quality: *{label}*"
            )

    if video_title:
        q_suffix = f"_{label.replace(' ','')}" if label and label != "Best Quality" else "_best"
        OUT = f"{video_title}{q_suffix}.mp4"
    else:
        OUT = "downloaded_file.mp4"

    success = False

    try:
        msg(
            f"┌─────────────────────┐\n"
            f"│  ⬇️  *DOWNLOADING...*  │\n"
            f"└─────────────────────┘"
        )

        # ── Method 1: yt-dlp ──
        if not success:
            q_label = label if label else "Best"
            if yt and height:
                q_fmt = (
                    f"bestvideo[height<={height}][vcodec^=avc][ext=mp4]+"
                    f"bestaudio[acodec^=mp4a]/"
                    f"bestvideo[height<={height}][ext=mp4]+bestaudio/"
                    f"bestvideo[height<={height}]+bestaudio/"
                    f"best[height<={height}]/best"
                )
            elif yt:
                q_fmt = (
                    "bestvideo[vcodec^=avc][ext=mp4]+bestaudio[acodec^=mp4a]/"
                    "bestvideo[ext=mp4]+bestaudio/bestvideo+bestaudio/best"
                )
            else:
                q_fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

            msg(f"🔄 *Method 1/5* — yt-dlp `({q_label})`")
            clean(OUT)
            os.system(
                f"yt-dlp --no-warnings --no-playlist "
                f"--socket-timeout 60 --retries 5 "
                f"--fragment-retries 5 "
                f"--concurrent-fragments 4 "
                f"-f '{q_fmt}' "
                f"--merge-output-format mp4 "
                f"--add-header 'User-Agent:Mozilla/5.0 (Windows NT 10.0; Win64; x64)' "
                f"--no-check-certificates "
                f"-o '{OUT}' '{link}'"
            )
            if os.path.exists(OUT):
                sz = os.path.getsize(OUT) / (1024*1024)
                msg(f"📦 yt-dlp result: *{sz:.1f} MB*")
                if file_ok(OUT, min_size): success = True
                else:
                    msg(f"⚠️ Too small ({sz:.1f}MB) — next method...")
                    clean(OUT)

        # ── Method 2: aria2c ──
        if not success and not yt:
            msg("🔄 *Method 2/5* — aria2c")
            clean(OUT)
            os.system(
                f"aria2c -x 16 -s 16 -k 1M "
                f"--timeout=60 --retry-wait=3 --max-tries=3 "
                f"--user-agent='Mozilla/5.0' --allow-overwrite=true "
                f"-o '{OUT}' '{link}'"
            )
            if os.path.exists(OUT):
                sz = os.path.getsize(OUT) / (1024*1024)
                msg(f"📦 aria2c result: *{sz:.1f} MB*")
                if file_ok(OUT, min_size): success = True
                else: clean(OUT)

        # ── Method 3: wget ──
        if not success and not yt:
            msg("🔄 *Method 3/5* — wget")
            clean(OUT)
            os.system(
                f"wget -q --tries=3 --timeout=60 "
                f"--user-agent='Mozilla/5.0' --no-check-certificate "
                f"-O '{OUT}' '{link}'"
            )
            if os.path.exists(OUT):
                sz = os.path.getsize(OUT) / (1024*1024)
                msg(f"📦 wget result: *{sz:.1f} MB*")
                if file_ok(OUT, min_size): success = True
                else: clean(OUT)

        # ── Method 4: curl ──
        if not success and not yt:
            msg("🔄 *Method 4/5* — curl")
            clean(OUT)
            os.system(
                f"curl -L --retry 3 --max-time 300 "
                f"-H 'User-Agent: Mozilla/5.0' -H 'Accept: */*' "
                f"-H 'Referer: {link}' -o '{OUT}' '{link}'"
            )
            if os.path.exists(OUT):
                sz = os.path.getsize(OUT) / (1024*1024)
                msg(f"📦 curl result: *{sz:.1f} MB*")
                if file_ok(OUT, min_size): success = True
                else: clean(OUT)

        # ── Method 5: requests ──
        if not success and not yt:
            msg("🔄 *Method 5/5* — Python requests")
            clean(OUT)
            try:
                hdrs = {'User-Agent': 'Mozilla/5.0', 'Accept': '*/*', 'Referer': link}
                with requests.get(link, headers=hdrs, stream=True,
                                  allow_redirects=True, timeout=60) as r:
                    r.raise_for_status()
                    with open(OUT, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192):
                            if chunk: f.write(chunk)
                if os.path.exists(OUT):
                    sz = os.path.getsize(OUT) / (1024*1024)
                    msg(f"📦 requests result: *{sz:.1f} MB*")
                    if file_ok(OUT, min_size): success = True
                    else: clean(OUT)
            except Exception as e:
                msg(f"⚠️ Method 5 error: `{str(e)[:100]}`")

        # ── Final ──
        if not success:
            msg(
                f"╔══════════════════════╗\n"
                f"║  ❌  *DOWNLOAD FAILED*  ║\n"
                f"╚══════════════════════╝\n\n"
                f"Sab 5 methods fail ho gaye!\n\n"
                f"*Possible reasons:*\n"
                f"⏰ Link expire ho gaya\n"
                f"🔐 Login/auth chahiye\n"
                f"🚫 Site ne block kiya\n\n"
                f"📎 Fresh link bhejein."
            )
            return

        size_mb = os.path.getsize(OUT) / (1024*1024)
        display = OUT.replace('_', ' ').replace('.mp4', '')
        msg(
            f"╔══════════════════════╗\n"
            f"║  ✅  *DOWNLOAD DONE!*   ║\n"
            f"╚══════════════════════╝\n\n"
            f"🎬 *{display[:40]}*\n"
            f"📦 Size: *{size_mb:.1f} MB*\n\n"
            f"☁️ Jazz Drive pe upload\n"
            f"ho raha hai..."
        )

        jazz_drive_upload(OUT)

    except Exception as e:
        msg(f"❌ *Process Error:*\n`{str(e)[:200]}`")
        raise
    finally:
        clean(OUT)

# ═══════════════════════════════════════
# ☁️ Jazz Drive Upload
# ═══════════════════════════════════════
def jazz_drive_upload(filename):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=BROWSER_ARGS)
        ctx = browser.new_context(
            viewport={'width': 1280, 'height': 720},
            storage_state="state.json" if os.path.exists("state.json") else None
        )
        page = ctx.new_page()
        upload_success = False

        try:
            msg("🌐 *Jazz Drive* khul raha hai...")
            page.goto("https://cloud.jazzdrive.com.pk/", wait_until="networkidle", timeout=90000)
            time.sleep(3)

            if page.locator("#msisdn").is_visible():
                msg("⚠️ *Session expire ho gayi!*\nLogin karo pehle...")
                ok = do_login(page, ctx)
                if not ok:
                    msg("❌ Login fail — file skip kar raha hoon.")
                    return
                page.goto("https://cloud.jazzdrive.com.pk/", wait_until="networkidle", timeout=90000)
                time.sleep(3)

            ctx.storage_state(path="state.json")

            msg(
                f"┌─────────────────────┐\n"
                f"│  📤  *UPLOADING...*    │\n"
                f"└─────────────────────┘\n\n"
                f"File select ho rahi hai..."
            )
            time.sleep(2)

            try:
                page.evaluate("""
                    document.querySelectorAll('header button').forEach(b => {
                        if(b.innerHTML.includes('svg') || b.innerHTML.includes('upload')) b.click();
                    });
                """)
                time.sleep(2)
            except: pass

            try:
                dialog = page.locator("div[role='dialog']")
                if dialog.is_visible():
                    with page.expect_file_chooser() as fc:
                        dialog.locator("text=/upload/i").first.click()
                    fc.value.set_files(os.path.abspath(filename))
                else:
                    page.set_input_files("input[type='file']", os.path.abspath(filename))
            except:
                page.set_input_files("input[type='file']", os.path.abspath(filename))

            time.sleep(3)

            try:
                if page.get_by_text("Yes", exact=True).is_visible():
                    page.get_by_text("Yes", exact=True).click()
            except: pass
