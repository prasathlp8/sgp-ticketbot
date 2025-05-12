import time
import os
import requests
import threading
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from flask import Flask
from datetime import datetime, timedelta
import pytz

# === Config ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# === URLs ===
WALKABOUT_URL = "https://singaporegp.sg/en/tickets/general-tickets/walkabouts/sunday"
GRANDSTAND_URL = "https://singaporegp.sg/en/tickets/general-tickets/grandstands/sunday"


# === Send Telegram Message ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        res = requests.post(url, data=payload)
        if res.status_code == 200:
            print("✅ Telegram alert sent.")
        else:
            print("❌ Telegram error:", res.text)
    except Exception as e:
        print("❌ Telegram exception:", e)


# === Ticket Checking Logic ===
def check_ticket_status():
    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = uc.Chrome(options=options, use_subprocess=True)

    try:
        messages = []

        # Zone 4 Walkabout
        driver.get(WALKABOUT_URL)
        time.sleep(3)
        try:
            walk_btn = driver.find_element(
                By.ID, "btn-buy-2025-zone-4-walkabout-sunday")
            if "stat-active" in walk_btn.get_attribute("class"):
                messages.append("✅ Zone 4 Walkabout Sunday: AVAILABLE")
            else:
                messages.append("❌ Zone 4 Walkabout Sunday: SOLD OUT")
        except NoSuchElementException:
            messages.append("⚠️ Walkabout button not found")

        # Stamford Grandstand
        driver.get(GRANDSTAND_URL)
        time.sleep(3)
        try:
            stam_btn = driver.find_element(
                By.ID, "btn-buy-2025-stamford-grandstand-sunday")
            if "stat-active" in stam_btn.get_attribute("class"):
                messages.append("✅ Stamford Grandstand Sunday: AVAILABLE")
            else:
                messages.append("❌ Stamford Grandstand Sunday: SOLD OUT")
        except NoSuchElementException:
            messages.append("⚠️ Stamford Grandstand button not found")

        # Send Telegram update
        status_msg = "\n".join(messages)
        send_telegram_message(f"📡 Ticket Check Status:\n{status_msg}")

    finally:
        driver.quit()


# === Hourly Checker Based on SGT ===
def run_checker():
    sgt = pytz.timezone('Asia/Singapore')

    while True:
        now = datetime.now(sgt)
        next_hour = (now + timedelta(hours=1)).replace(minute=0,
                                                       second=0,
                                                       microsecond=0)
        sleep_duration = (next_hour - now).total_seconds()

        print(
            f"🕒 SGT now: {now.strftime('%Y-%m-%d %H:%M:%S')} | Sleeping {int(sleep_duration)} sec until next hour..."
        )
        time.sleep(sleep_duration)

        print(
            f"🔁 Running ticket check at SGT {datetime.now(sgt).strftime('%H:%M:%S')}"
        )
        check_ticket_status()


# === Flask Server to Stay Awake ===
app = Flask(__name__)


@app.route("/")
def home():
    return "✅ Bot is running and checking tickets every hour (SGT)."


# === Start Thread + Flask ===
threading.Thread(target=run_checker, daemon=True).start()

# Startup Telegram message
if TELEGRAM_TOKEN and CHAT_ID:
    print("🚀 Bot started. SGT-hourly monitoring begins.")
    send_telegram_message(
        "🚀 Bot started. Monitoring will run at the start of every hour (SGT).")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
