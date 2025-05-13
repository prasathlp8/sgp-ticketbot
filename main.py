import time
import os
import requests
import threading
import chromedriver_autoinstaller
from flask import Flask
from datetime import datetime, timedelta
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException\

# === Config ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

WALKABOUT_URL = "https://singaporegp.sg/en/tickets/general-tickets/walkabouts/sunday"
GRANDSTAND_URL = "https://singaporegp.sg/en/tickets/general-tickets/grandstands/sunday"

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        res = requests.post(url, data=payload)
        print("✅ Telegram alert sent.")
    except Exception as e:
        print("❌ Telegram error:", e)

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)  # No chromedriver path needed

def check_ticket_status():
    driver = create_driver()
    try:
        messages = []

        driver.get(WALKABOUT_URL)
        time.sleep(3)
        try:
            walk_btn = driver.find_element(By.ID, "btn-buy-2025-zone-4-walkabout-sunday")
            if "stat-active" in walk_btn.get_attribute("class"):
                messages.append("✅ Zone 4 Walkabout Sunday: AVAILABLE")
            else:
                messages.append("❌ Zone 4 Walkabout Sunday: SOLD OUT")
        except NoSuchElementException:
            messages.append("⚠️ Walkabout button not found")

        driver.get(GRANDSTAND_URL)
        time.sleep(3)
        try:
            stam_btn = driver.find_element(By.ID, "btn-buy-2025-stamford-grandstand-sunday")
            if "stat-active" in stam_btn.get_attribute("class"):
                messages.append("✅ Stamford Grandstand Sunday: AVAILABLE")
            else:
                messages.append("❌ Stamford Grandstand Sunday: SOLD OUT")
        except NoSuchElementException:
            messages.append("⚠️ Stamford button not found")

        status_msg = "\n".join(messages)
        send_telegram_message(f"📡 Ticket Check Status:\n{status_msg}")
    finally:
        driver.quit()

def run_checker():
    sgt = pytz.timezone('Asia/Singapore')
    while True:
        now = datetime.now(sgt)
        next_time = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
        sleep_duration = (next_time - now).total_seconds()
        print(f"🕒 SGT now: {now.strftime('%Y-%m-%d %H:%M:%S')} | Sleeping {int(sleep_duration)} sec until next hour...")
        time.sleep(sleep_duration)
        print(f"🔁 Running ticket check at SGT {datetime.now(sgt).strftime('%H:%M:%S')}")
        check_ticket_status()

# Flask App for Render
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is running and checking tickets every hour (SGT)."

threading.Thread(target=run_checker, daemon=True).start()

if TELEGRAM_TOKEN and CHAT_ID:
    print("🚀 Bot started. Monitoring will run at the start of every hour (SGT).")
    send_telegram_message("🚀 Bot started. Monitoring will run at the start of every hour (SGT).")

if __name__ == "__main__":
    #check_ticket_status()
    app.run(host="0.0.0.0", port=8080)
