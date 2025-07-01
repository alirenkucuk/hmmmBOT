import requests
import time
import sqlite3
import threading
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext

# ----- CONFIGURATION -----
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"
DB_PATH = "users.db"
CHECK_INTERVAL = 600  # saniye cinsinden, 600 = 10 dakika

# Açılış mesajı
WELCOME_MESSAGE = (
    "Merhaba!\n"
    "Bu bot, belirttiğiniz IELTS test oturumlarındaki boş kontenjanları düzenli olarak kontrol eder ve size bildirir.\n"
    "Aşağıdaki komutları kullanabilirsiniz:\n"
    "/start - Botu başlatır ve bildirimleri almak için kaydınızı yapar.\n"
    "/help - Yardım mesajını gösterir.\n"
)

# ----- VERİTABANI İŞLEMLERİ -----
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY
        )
        """
    )
    conn.commit()
    conn.close()


def add_user(chat_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users(chat_id) VALUES(?)", (chat_id,))
    conn.commit()
    conn.close()


def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT chat_id FROM users")
    rows = c.fetchall()
    conn.close()
    return [row[0] for row in rows]

# ----- TELEGRAM KOMUTLARI -----
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    add_user(chat_id)
    context.bot.send_message(chat_id=chat_id, text=WELCOME_MESSAGE)


def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(WELCOME_MESSAGE)

# ----- BİLDİRİM İŞLEVİ -----
# API üzerinden sınav boşluğu kontrolü
API_URL = "https://ielts.idp.com/api/testsession/availability"
API_PARAMS = {
    "countryId": 212,
    "testCentreId": 11995,
    "testVenueId": 1771,
    "testCentreLocationId": 1654,
    "testSessionDate": "2025-06-28T00:00:00.0000000",
    "isSelt": "false",
    "restrictToSpecifiedDate": "true",
    "testmoduleid": 1,
    "token": "d02942a0c5bfd2446de2c0049cc303a0137f98b43ee5d5266201ebfdc4778cad"
}
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json"
}

def inform_users(bot: Bot, message: str):
    users = get_all_users()
    for chat_id in users:
        try:
            bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            print(f"Mesaj gönderilemedi {chat_id}: {e}")


def check_availability_loop(bot: Bot):
    while True:
        try:
            response = requests.get(API_URL, params=API_PARAMS, headers=HEADERS)
            if response.status_code == 200:
                data = response.json()
                # TODO: data içinden uygun şartları kontrol edin
                # Örnek: eğer availableSlots > 0 ise bildir
                available = data.get("availableSlots", 0)
                if available and available > 0:
                    msg = f"Dikkat! {API_PARAMS['testSessionDate']} tarihli oturumda {available} boş kontenjan bulundu."
                    inform_users(bot, msg)
            else:
                print(f"API hatası: {response.status_code}")
        except Exception as err:
            print(f"Hata: {err}")
        time.sleep(CHECK_INTERVAL)

# ----- MAIN -----
def main():
    init_db()
    updater = Updater(token=BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))

    # Botu çalıştır
    updater.start_polling()

    # Arka planda boşluk kontrol döngüsü
    monitor_thread = threading.Thread(target=check_availability_loop, args=(updater.bot,), daemon=True)
    monitor_thread.start()

    updater.idle()

if __name__ == "__main__":
    main()



#Avni Part
import requests
import json
import time

# API endpoint
url = "https://ielts.idp.com/book/Json/FindAvailableTestSessionForNewBooking"

# Header bilgileri (User-Agent vs. kritik)
headers = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://ielts.idp.com",
    "Referer": "https://ielts.idp.com/book/IELTS?countryId=212&testCentreId=11995&testVenueId=1771",
}

# İsteğe özel token ve parametrelerle body
payload = {
    "testSessionFromDate": "2025-Jun-01",
    "testSessionToDate": "2025-Jul-31",
    "testVenueId": 1771,
    "testCentreId": 11995,
    "testModules": [1, 7],
    "testFormatId": 1,
    "specialNeedId": "",
    "isSelt": False,
    "token": "d02942a0c5bfd2446de2c0049cc303a0137f98b43ee5d5266201ebfdc4778cad"
}

# Opsiyonel: Çerez gerekiyorsa buraya eklenebilir
cookies = {
    "ASP.NET_SessionId": "y4oo4s54jkdmstrnqhe3hwxf",
    # diğer önemli çerezleri buraya eklemen gerekebilir
}

def check_available_dates():
    try:
        response = requests.post(url, headers=headers, json=payload, cookies=cookies)
        if response.status_code == 200:
            data = response.json()
            available = []

            for session in data.get("data", []):
                if session.get("isAvailable"):
                    available.append({
                        "date": session.get("testSessionDate"),
                        "module": session.get("moduleName"),
                        "availableSeats": session.get("availableCapacity")
                    })

            if available:
                print("\n🟢 Uygun Tarihler Bulundu:")
                for s in available:
                    print(f"{s['date']} — {s['module']} — {s['availableSeats']} koltuk")
            else:
                print("🔴 Şu anda uygun sınav tarihi yok.")
        else:
            print(f"❌ Hata: Status Code {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"⚠️ Hata oluştu: {e}")

# Manuel çalıştırma
check_available_dates()

# (İsteğe bağlı) Periyodik tarama
# while True:
#     check_available_dates()
#     time.sleep(3600)  # 1 saatte bir çalışır

