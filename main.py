import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect

app = Flask(__name__, template_folder='.')
app.secret_key = 'baku_news_2026_key'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bakunews.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS xeberler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         bashliq TEXT, link TEXT UNIQUE, meqale TEXT, 
         img_url TEXT, kateqoriya TEXT DEFAULT 'Ümumi')''')
    conn.commit()
    conn.close()

def get_category(title):
    t = title.lower()
    if any(x in t for x in ['futbol', 'idman', 'oyun']): return 'İdman'
    if any(x in t for x in ['iqtisadiyyat', 'dollar', 'euro', 'bank']): return 'İqtisadiyyat'
    return 'Dünya'

def bot_logic():
    targets = [
        {"url": "https://report.az/son-xeberler/", "base": "https://report.az"},
        {"url": "https://qafqazinfo.az/", "base": ""},
        {"url": "https://az.trend.az/azerbaijan/", "base": "https://az.trend.az"},
        {"url": "https://www.bbc.com/azeri", "base": "https://www.bbc.com"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for target in targets:
                req = urllib.request.Request(target["url"], headers=headers)
                with urllib.request.urlopen(req, timeout=10) as res:
                    soup = BeautifulSoup(res.read(), "html.parser")
                    for item in soup.find_all("a", href=True)[:15]:
                        link = item["href"]
                        if link.startswith("/"): link = target["base"] + link
                        title = item.text.strip()
                        
                        if len(title) > 30 and "http" in link:
                            cursor.execute("SELECT id FROM xeberler WHERE link = ?", (link,))
                            if not cursor.fetchone():
                                img_url = ""
                                try:
                                    c_req = urllib.request.Request(link, headers=headers)
                                    with urllib.request.urlopen(c_req, timeout=5) as c_res:
                                        c_soup = BeautifulSoup(c_res.read(), "html.parser")
                                        img_tag = c_soup.find('meta', property="og:image")
                                        if img_tag: img_url = img_tag['content']
                                except: pass
                                
                                cursor.execute("INSERT INTO xeberler (bashliq, link, img_url, kateqoriya) VALUES (?,?,?,?)",
                                               (title, link, img_url, get_category(title)))
                                conn.commit()
            conn.close()
        except: pass
        time.sleep(60)

@app.route('/')
def home():
    is_admin = request.args.get('key') == '1eldar123*'
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 60")
    all_news = cursor.fetchall()
    
    info = {
        "hava": "18°C Quba", 
        "is_admin": is_admin
    }
    conn.close()
    return render_template("index.html", all_news=all_news, info=info)

# Digər admin və xəbər detalları funksiyaları bura əlavə oluna bilər...

if __name__ == '__main__':
    init_db()
    threading.Thread(target=bot_logic, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
