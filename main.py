import time
import os
import requests
import threading
from flask import Flask
from datetime import datetime, timedelta
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from PIL import Image
from io import BytesIO

# === Config ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

WALKABOUT_URL = "https://singaporegp.sg/en/tickets/general-tickets/walkabouts/sunday"
GRANDSTAND_URL = "https://singaporegp.sg/en/tickets/general-tickets/grandstands/sunday"

app = Flask(__name__)

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        res = requests.post(url, data=payload)
        print("✅ Telegram alert sent.")
    except Exception as e:
        print("❌ Telegram error:", e)

def send_telegram_photo(image_bytes, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    files = {"photo": ("screenshot.png", image_bytes)}
    data = {"chat_id": CHAT_ID, "caption": caption}
    try:
        res = requests.post(url, files=files, data=data)
        print("📷 Screenshot sent to Telegram.")
    except Exception as e:
        print("❌ Telegram photo error:", e)

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def check_ticket_status():
    driver = create_driver()
    try:
        messages = []

        # Zone 4 Walkabout Ticket Check
        driver.get(WALKABOUT_URL)
        time.sleep(3)
        try:
            walk_btn = driver.find_element(By.ID, "btn-buy-2025-zone-4-walkabout-sunday")
            btn_text = walk_btn.text.strip().lower()
            btn_class = walk_btn.get_attribute("class")

            if "buy" in btn_text or "stat-active" in btn_class:
                messages.append("✅ Zone 4 Walkabout Sunday: AVAILABLE")
            else:
                messages.append("❌ Zone 4 Walkabout Sunday: SOLD OUT")
        except NoSuchElementException:
            messages.append("⚠️ Zone 4 Walkabout button not found")

        # Tooltip backup check for Zone 4
        try:
            soldout_icon = driver.find_element(By.CLASS_NAME, "currently-sold-out-info")
            if "active" in soldout_icon.get_attribute("class"):
                messages.append("🔴 Tooltip Check: Zone 4 Walkabout shows Sold Out icon.")
            else:
                messages.append("🟢 Tooltip Check: Zone 4 Walkabout has no Sold Out icon.")
        except NoSuchElementException:
            messages.append("🟢 Tooltip Check: No sold-out span found for Zone 4 Walkabout.")

        # Zone 4 Visual Backup
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(BytesIO(screenshot))
        zone4_crop = img.crop((220, 1300, 400, 1350))
        colors = zone4_crop.getcolors(10000)
        if colors:
            most_common_color = sorted(colors, key=lambda x: x[0], reverse=True)[0][1]
            r, g, b = most_common_color[:3]
            if g > 150 and r < 100:
                messages.append("🟢 (Visual Backup) Zone 4 Walkabout: GREEN (Available)")
            elif r > 150 and g < 100:
                messages.append("🔴 (Visual Backup) Zone 4 Walkabout: RED (Sold Out)")
            else:
                messages.append("⚠️ (Visual Backup) Zone 4 Walkabout color unclear")

        # Stamford Grandstand Ticket Check
        driver.get(GRANDSTAND_URL)
        time.sleep(3)
        try:
            stam_btn = driver.find_element(By.ID, "btn-buy-2025-stamford-grandstand-sunday")
            btn_text = stam_btn.text.strip().lower()
            btn_class = stam_btn.get_attribute("class")

            if "buy" in btn_text or "stat-active" in btn_class:
                messages.append("✅ Stamford Grandstand Sunday: AVAILABLE")
            else:
                messages.append("❌ Stamford Grandstand Sunday: SOLD OUT")
        except NoSuchElementException:
            messages.append("⚠️ Stamford Grandstand button not found")

        # Tooltip backup check for Stamford
        try:
            soldout_icon = driver.find_element(By.CLASS_NAME, "currently-sold-out-info")
            if "active" in soldout_icon.get_attribute("class"):
                messages.append("🔴 Tooltip Check: Stamford Grandstand shows Sold Out icon.")
            else:
                messages.append("🟢 Tooltip Check: Stamford Grandstand has no Sold Out icon.")
        except NoSuchElementException:
            messages.append("🟢 Tooltip Check: No sold-out span found for Stamford Grandstand.")

        # Stamford Visual Backup
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(BytesIO(screenshot))
        stam_crop = img.crop((220, 960, 400, 1010))
        colors = stam_crop.getcolors(10000)
        if colors:
            most_common_color = sorted(colors, key=lambda x: x[0], reverse=True)[0][1]
            r, g, b = most_common_color[:3]
            if g > 150 and r < 100:
                messages.append("🟢 (Visual Backup) Stamford Grandstand: GREEN (Available)")
            elif r > 150 and g < 100:
                messages.append("🔴 (Visual Backup) Stamford Grandstand: RED (Sold Out)")
            else:
                messages.append("⚠️ (Visual Backup) Stamford Grandstand color unclear")

        status_msg = "\n".join(messages)
        send_telegram_message(f"📡 Ticket Check Status:\n{status_msg}")
        send_telegram_photo(screenshot, "🖼️ Screenshot at time of check")

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

        try:
            print(f"🔁 Running ticket check at SGT {datetime.now(sgt).strftime('%H:%M:%S')}")
            check_ticket_status()
        except Exception as e:
            print("❌ Error in hourly check:", e)

@app.route("/")
def home():
    return "✅ Bot is running and checking tickets every hour (SGT)."

@app.route("/run-now")
def run_now():
    try:
        check_ticket_status()
        return "✅ Manual ticket check completed and sent to Telegram."
    except Exception as e:
        return f"❌ Error: {e}"

threading.Thread(target=run_checker, daemon=True).start()

if TELEGRAM_TOKEN and CHAT_ID:
    print("🚀 Bot started. Monitoring will run at the start of every hour (SGT).")
    send_telegram_message("🚀 Bot started. Monitoring will run at the start of every hour (SGT).")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
