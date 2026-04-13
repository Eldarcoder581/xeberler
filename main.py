import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template, request

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
         img_url TEXT, kateqoriya TEXT DEFAULT 'Gündəm')''')
    conn.commit()
    conn.close()

def get_category(title):
    t = title.lower()
    if any(x in t for x in ['iqtisadiyyat', 'dollar', 'manat', 'bank']): return 'İqtisadiyyat'
    if any(x in t for x in ['hərbi', 'ordu', 'müdafiə', 'əsgər']): return 'Hərbi'
    if any(x in t for x in ['təhsil', 'elm', 'məktəb', 'imtahan']): return 'Təhsil'
    if any(x in t for x in ['siyasət', 'prezident', 'nazir', 'əliyev']): return 'Siyasət'
    return 'Gündəm'

def bot_logic():
    targets = [
        {"url": "https://report.az/son-xeberler/", "base": "https://report.az"},
        {"url": "https://qafqazinfo.az/", "base": ""},
        {"url": "https://az.trend.az/azerbaijan/", "base": "https://az.trend.az"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for target in targets:
                try:
                    req = urllib.request.Request(target["url"], headers=headers)
                    with urllib.request.urlopen(req, timeout=10) as res:
                        soup = BeautifulSoup(res.read(), "html.parser")
                        for item in soup.find_all("a", href=True)[:30]:
                            link = item["href"]
                            if link.startswith("/"): link = target["base"] + link
                            title = item.text.strip()
                            
                            if len(title) > 25 and "http" in link:
                                cursor.execute("SELECT id FROM xeberler WHERE link = ?", (link,))
                                if not cursor.fetchone():
                                    cat = get_category(title)
                                    cursor.execute("INSERT INTO xeberler (bashliq, link, kateqoriya) VALUES (?,?,?)",
                                                   (title, link, cat))
                                    conn.commit()
                except: continue
            conn.close()
        except: pass
        time.sleep(30)

@app.route('/')
def home():
    is_admin = request.args.get('key') == '1eldar123*'
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, bashliq, link, meqale, img_url, kateqoriya FROM xeberler ORDER BY id DESC LIMIT 100")
    all_news = cursor.fetchall()
    conn.close()
    info = {"is_admin": is_admin, "hava": "18°C Quba"}
    return render_template("index.html", all_news=all_news, info=info)

if __name__ == '__main__':
    init_db()
    threading.Thread(target=bot_logic, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
