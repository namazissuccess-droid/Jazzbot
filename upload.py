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
    bot.infinity_polling()
