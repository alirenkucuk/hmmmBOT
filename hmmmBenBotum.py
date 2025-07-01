import requests
import time
import sqlite3
import threading
from telegram import Update, Bot
from telegram.ext import Updater, CommandHandler, CallbackContext
import json # JSON işlemleri için

# ----- CONFIGURATION -----
BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN_HERE"  # Buraya kendi bot token'ınızı yapıştırın
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
    c = conn.close()
    return [row[0] for row in c.fetchall()]

# ----- TELEGRAM KOMUTLARI -----
def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    add_user(chat_id)
    context.bot.send_message(chat_id=chat_id, text=WELCOME_MESSAGE)


def help_command(update: Update, context: CallbackContext):
    update.message.reply_text(WELCOME_MESSAGE)

# ----- BİLDİRİM İŞLEVİ -----
# Avni'nin API endpoint ve parametreleri kullanılıyor
API_URL = "https://ielts.idp.com/book/Json/FindAvailableTestSessionForNewBooking"
HEADERS = {
    "Accept": "*/*",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://ielts.idp.com",
    "Referer": "https://ielts.idp.com/book/IELTS?countryId=212&testCentreId=11995&testVenueId=1771",
}
PAYLOAD = {
    "testSessionFromDate": "2025-Jun-01", # Kontrol edilecek başlangıç tarihi
    "testSessionToDate": "2025-Jul-31",   # Kontrol edilecek bitiş tarihi
    "testVenueId": 1771,
    "testCentreId": 11995,
    "testModules": [1, 7], # 1: Academic, 7: General Training
    "testFormatId": 1,
    "specialNeedId": "",
    "isSelt": False,
    "token": "d02942a0c5bfd2446de2c0049cc303a0137f98b43ee5d5266201ebfdc4778cad"
}
# Opsiyonel: Çerez gerekiyorsa buraya eklenebilir
COOKIES = {
    "ASP.NET_SessionId": "y4oo4s54jkdmstrnqhe3hwxf",
    # diğer önemli çerezleri buraya eklemen gerekebilir
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
            response = requests.post(API_URL, headers=HEADERS, json=PAYLOAD, cookies=COOKIES)
            if response.status_code == 200:
                data = response.json()
                available_sessions = []

                for session in data.get("data", []):
                    if session.get("isAvailable"):
                        available_sessions.append({
                            "date": session.get("testSessionDate"),
                            "module": session.get("moduleName"),
                            "availableSeats": session.get("availableCapacity")
                        })

                if available_sessions:
                    msg = "🟢 **Uygun IELTS Sınav Tarihleri Bulundu!**\n\n"
                    for s in available_sessions:
                        msg += f"🗓️ **Tarih:** {s['date']}\n"
                        msg += f"📚 **Modül:** {s['module']}\n"
                        msg += f"🪑 **Boş Koltuk:** {s['availableSeats']}\n"
                        msg += "-----------------------------------\n"
                    inform_users(bot, msg)
                    print("Uygun tarihler bulundu ve kullanıcılara bildirildi.")
                else:
                    print("Şu anda uygun sınav tarihi yok.")
            else:
                print(f"API hatası: {response.status_code}")
                print(response.text)
        except Exception as err:
            print(f"Hata oluştu: {err}")
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
