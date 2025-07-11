import requests
import time
import sqlite3
import threading
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, CallbackContext


BOT_TOKEN = "Bot_TOKEN_GİR" 
DB_PATH = "users.db"
CHECK_INTERVAL = 600 


API_URL = "https://ielts.idp.com/book/Json/FindAvailableTestSessionForNewBooking"
HEADERS = {
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "X-Requested-With": "XMLHttpRequest",
    "Origin": "https://ielts.idp.com",
    "Referer": "https://ielts.idp.com/book/IELTS?countryId=212&testCentreId=11995&testVenueId=1771",
}
PAYLOAD = {
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
COOKIES = {
    "ASP.NET_SessionId": "y4oo4s54jkdmstrnqhe3hwxf",
}


WELCOME_MESSAGE = (
    "Merhaba\\!\n"
    "Bu bot, belirttiğiniz IELTS test oturumlarındaki boş kontenjanları düzenli olarak kontrol eder ve size bildirir\\.\n\n"
    "Aşağıdaki komutları kullanabilirsiniz:\n"
    "`/start` \\- Botu başlatır ve bildirimleri almak için kaydınızı yapar\\.\n"
    "`/help` \\- Yardım mesajını gösterir\\."
)


def init_db():
    
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def add_user(chat_id: int):
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users(chat_id) VALUES(?)", (chat_id,))
    conn.commit()
    conn.close()
    print(f"Yeni kullanıcı eklendi/güncellendi: {chat_id}")

def get_all_users():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("SELECT chat_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users


async def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    add_user(chat_id)
    await context.bot.send_message(
        chat_id=chat_id, text=WELCOME_MESSAGE, parse_mode="MarkdownV2"
    )

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        text=WELCOME_MESSAGE, parse_mode="MarkdownV2"
    )


async def inform_users(bot: Bot, message: str):
    users = get_all_users()
    for chat_id in users:
        try:
            await bot.send_message(
                chat_id=chat_id, text=message, parse_mode="MarkdownV2"
            )
        except Exception as e:
            print(f"Mesaj gönderilemedi {chat_id}: {e}")


def check_availability_loop(bot: Bot):
    while True:
        print(f"{time.ctime()} - Uygunluk kontrol ediliyor...")
        try:
            response = requests.post(API_URL, headers=HEADERS, json=PAYLOAD, cookies=COOKIES, timeout=30)
            if response.status_code == 200:
                data = response.json()
                available_sessions = []
                if data and "data" in data:
                    for session in data.get("data", []):
                        if session.get("isAvailable"):
                            available_sessions.append({
                                "date": session.get("testSessionDate", "Bilinmiyor"),
                                "module": session.get("moduleName", "Bilinmiyor"),
                                "availableSeats": session.get("availableCapacity", 0)
                            })
                
                
                if available_sessions:
                    msg = "🟢 *Uygun IELTS Sınav Tarihleri Bulundu\\!*\n\n"
                    for s in available_sessions:
                        msg += f"🗓️ *Tarih:* {s['date']}\n"
                        msg += f"📚 *Modül:* {s['module']}\n"
                        msg += f"🪑 *Boş Koltuk:* {s['availableSeats']}\n"
                        msg += "-----------------------------------\n"
                    msg = msg.replace("-", "\\-")
                    
                    print("Uygun tarihler bulundu! Kullanıcılara bildiriliyor...")
                   
                    asyncio.run(inform_users(bot, msg))
                else:
                    print("Şu anda uygun sınav tarihi yok.")
            else:
                print(f"API hatası: {response.status_code} - {response.reason}")
        except requests.exceptions.RequestException as req_err:
            print(f"Ağ hatası oluştu: {req_err}")
        except Exception as err:
            print(f"Beklenmedik bir hata oluştu: {err}")
        
        time.sleep(CHECK_INTERVAL)


def main():
    """Botu başlatır ve çalışır durumda tutar."""
    init_db()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    monitor_thread = threading.Thread(
        target=check_availability_loop,
        args=(application.bot,),
        daemon=True
    )
    monitor_thread.start()

    print("Bot çalışmaya başladı...")
    
    application.run_polling()


if __name__ == "__main__":
    main()
