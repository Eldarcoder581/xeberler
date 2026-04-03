import urllib.request
import urllib.parse
import sqlite3
import threading
import time
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

# --- TELEGRAM AYARLARI ---
TOKEN = "BURA_BOT_TOKENINI_YAZ" 
CHAT_ID = "BURA_CHAT_ID_YAZ" 

app = Flask(__name__)
DB_PATH = 'bakunews.db'

def send_tg(text):
    try:
        msg = urllib.parse.quote(text)
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}&parse_mode=HTML"
        urllib.request.urlopen(url, timeout=10)
    except: pass

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE, shekil TEXT)')
    conn.commit()
    conn.close()
    send_tg("🚀 <b>Sistem Yenidən Başladı!</b>\nBaza quruldu, xəbərlər axtarılır...")

def fetch_milli():
    while True:
        try:
            url = "http://news.milli.az/society/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                items = soup.find_all("div", class_="news-item-title", limit=10)
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                new_found = False
                for item in items:
                    title = item.find("a").text.strip()
                    link = "https://news.milli.az" + item.find("a")["href"]
                    cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link) VALUES (?, ?)", (title, link))
                    if cursor.rowcount > 0:
                        send_tg(f"🔔 <b>YENİ XƏBƏR:</b>\n\n{title}\n\n<a href='{link}'>Oxu →</a>")
                        new_found = True
                conn.commit()
                conn.close()
                if new_found: print("Bot: Yeni xəbərlər göndərildi.")
        except Exception as e:
            print(f"Bot xetasi: {e}")
        time.sleep(300)

@app.route('/')
def home():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 30")
        data = cursor.fetchall()
        conn.close()
        
        if not data:
            return "<h1>Xəbərlər yüklənir... Zəhmət olmasa 1 dəqiqə gözləyib səhifəni yeniləyin (F5).</h1>"
            
        html = "<html><body style='background:#121212;color:white;font-family:Arial;text-align:center;'>"
        html += "<h1 style='color:gold;'>BAKU NEWS</h1><hr>"
        for x in data:
            html += f"<div style='border:1px solid #333;margin:10px;padding:10px;border-radius:10px;'>"
            html += f"<h3>{x[1]}</h3><a style='color:gold;' href='{x[2]}' target='_blank'>OXU</a></div>"
        html += "</body></html>"
        return html
    except:
        return "Sistem hələ tam hazır deyil..."

init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
