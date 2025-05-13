import time
import os
import requests
import threading
from flask import Flask
from datetime import datetime, timedelta
import pytz
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

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
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136 Safari/537.36")
    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(30)
    return driver

def check_ticket(url, ticket_name, driver):
    section = [f"\n🎫 {ticket_name}"]
    for attempt in range(2):
        try:
            driver.get(url)
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.panel-title'))
            )
            cards = driver.find_elements(By.CSS_SELECTOR, '.row.no-gutters.align-items-center.m-0')
            found = False
            for card in cards:
                try:
                    label = card.find_element(By.TAG_NAME, 'p').text.strip().lower()
                    if ticket_name.lower() in label:
                        btn = card.find_element(By.CSS_SELECTOR, 'a.btn-buy')
                        btn_text = btn.text.strip()
                        if "buy" in btn_text.lower():
                            section.append(f"✅ Available – {btn_text}")
                        elif "sold" in btn_text.lower():
                            section.append(f"❌ Sold Out – {btn_text}")
                        else:
                            section.append(f"⚠️ Unknown – {btn_text}")
                        found = True
                        break
                except Exception:
                    continue

            if not found:
                section.append("❌ Ticket not found on page")
            break  # Break if no timeout error occurred

        except TimeoutException:
            if attempt == 0:
                section.append("⚠️ Timeout – Retrying once...")
                continue
            else:
                section.append("❌ Error loading page: Timeout")
        except Exception as e:
            section.append(f"❌ Error loading page: {str(e)}")
            break

    return section

def check_ticket_status():
    driver = create_driver()
    try:
        messages = ["📡 Ticket Check Status:"]
        messages += check_ticket(WALKABOUT_URL, "Zone 4 Walkabout", driver)
        messages += check_ticket(GRANDSTAND_URL, "Stamford Grandstand", driver)
        send_telegram_message("\n".join(messages))
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
