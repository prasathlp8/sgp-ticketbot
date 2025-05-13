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

def create_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def analyze_color(crop_img, label):
    colors = crop_img.getcolors(10000)
    if not colors:
        return f"⚠️ 3. Visual Backup ({label}): No dominant color"
    sorted_colors = sorted(colors, key=lambda x: x[0], reverse=True)
    for count, color in sorted_colors[:10]:
        r, g, b = color[:3]
        if g > 120 and r < 100:
            return f"🟢 3. Visual Backup ({label}): GREEN (Available)"
        if r > 150 and g < 100:
            return f"🔴 3. Visual Backup ({label}): RED (Sold Out)"
    return f"⚠️ 3. Visual Backup ({label}): Color unclear"

def check_ticket_status():
    driver = create_driver()
    try:
        messages = ["\n📡 Ticket Check Status:"]

        # Zone 4 Walkabout
        walkabout_section = ["\n🔲 Zone 4 Walkabout"]
        driver.get(WALKABOUT_URL)
        time.sleep(3)

        # Screenshot for cropping
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(BytesIO(screenshot))

        # 1. Button check
        try:
            walk_btn = driver.find_element(By.ID, "btn-buy-2025-zone-4-walkabout-sunday")
            btn_text = walk_btn.text.strip().lower()
            btn_class = walk_btn.get_attribute("class")
            if "buy" in btn_text or "stat-active" in btn_class:
                walkabout_section.append("✅ 1. Button Check: AVAILABLE")
            else:
                walkabout_section.append("❌ 1. Button Check: SOLD OUT")
        except NoSuchElementException:
            walkabout_section.append("⚠️ 1. Button Check: Not Found")

        # 2. Tooltip check
        try:
            tooltip = driver.find_element(By.CLASS_NAME, "currently-sold-out-info")
            tooltip_text = tooltip.get_attribute("data-tippy-content") or ""
            if "no tickets available" in tooltip_text.lower():
                walkabout_section.append("🔴 2. Tooltip Check: Sold Out (via tooltip text)")
            else:
                walkabout_section.append("🟢 2. Tooltip Check: No sold-out text")
        except NoSuchElementException:
            walkabout_section.append("🟢 2. Tooltip Check: No sold-out span found")

        zone4_crop = img.crop((1120, 885, 1210, 920))  # Adjusted box
        walkabout_section.append(analyze_color(zone4_crop, "Zone 4 Walkabout"))

        # Stamford Grandstand
        stamford_section = ["\n🔲 Stamford Grandstand"]
        driver.get(GRANDSTAND_URL)
        time.sleep(3)

        # Screenshot for Stamford
        screenshot = driver.get_screenshot_as_png()
        img = Image.open(BytesIO(screenshot))

        # 1. Button check
        try:
            stam_btn = driver.find_element(By.ID, "btn-buy-2025-stamford-grandstand-sunday")
            btn_text = stam_btn.text.strip().lower()
            btn_class = stam_btn.get_attribute("class")
            if "buy" in btn_text or "stat-active" in btn_class:
                stamford_section.append("✅ 1. Button Check: AVAILABLE")
            else:
                stamford_section.append("❌ 1. Button Check: SOLD OUT")
        except NoSuchElementException:
            stamford_section.append("⚠️ 1. Button Check: Not Found")

        # 2. Tooltip check
        try:
            tooltip = driver.find_element(By.CLASS_NAME, "currently-sold-out-info")
            tooltip_text = tooltip.get_attribute("data-tippy-content") or ""
            if "no tickets available" in tooltip_text.lower():
                stamford_section.append("🔴 2. Tooltip Check: Sold Out (via tooltip text)")
            else:
                stamford_section.append("🟢 2. Tooltip Check: No sold-out text")
        except NoSuchElementException:
            stamford_section.append("🟢 2. Tooltip Check: No sold-out span found")

        stam_crop = img.crop((1120, 1370, 1210, 1405))  # Adjusted box
        stamford_section.append(analyze_color(stam_crop, "Stamford Grandstand"))

        status_msg = "\n".join(messages + walkabout_section + stamford_section)
        send_telegram_message(status_msg)

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
    threading.Thread(target=check_ticket_status).start()
    return "✅ Manual ticket check triggered."

threading.Thread(target=run_checker, daemon=True).start()

if TELEGRAM_TOKEN and CHAT_ID:
    print("🚀 Bot started. Monitoring will run at the start of every hour (SGT).")
    send_telegram_message("🚀 Bot started. Monitoring will run at the start of every hour (SGT).")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
