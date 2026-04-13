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
    # Sənin istədiyin əsas sahələr
    if any(x in t for x in ['iqtisadiyyat', 'dollar', 'manat', 'bank', 'maliyyə', 'büdcə', 'neft', 'qaz']): return 'İqtisadiyyat'
    if any(x in t for x in ['hərbi', 'ordu', 'müdafiə', 'əsgər', 'silah', 'atəşkəs', 'şəhid', 'qazi']): return 'Hərbi'
    if any(x in t for x in ['təhsil', 'elm', 'məktəb', 'universitet', 'imtahan', 'tələbə', 'ədəbiyyat']): return 'Təhsil'
    if any(x in t for x in ['siyasət', 'prezident', 'nazir', 'görüş', 'diplomat', 'əliyev', 'paşinyan', 'parlament']): return 'Siyasət'
    if any(x in t for x in ['innovasiya', 'texno', 'it', 'smartfon', 'süni zəka', 'startap', 'kosmos']): return 'İnnovasiya'
    
    # Əgər yuxarıdakılar tapılmasa, "Gündəm" olaraq qeyd et ki, sayt boş qalmasın
    return 'Gündəm'

def bot_logic():
    # Sənin istədiyin spesifik bölmələr
    targets = [
        {"url": "https://report.az/iqtisadiyyat/", "base": "https://report.az"},
        {"url": "https://report.az/daxili-siyaset/", "base": "https://report.az"},
        {"url": "https://report.az/herbi/", "base": "https://report.az"},
        {"url": "https://report.az/elm-tehsil/", "base": "https://report.az"},
        {"url": "https://qafqazinfo.az/politics", "base": ""},
        {"url": "https://az.trend.az/business/", "base": "https://az.trend.az"}
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
                    # [:50] edirik ki, hər bölmədən 50 linki birdən yoxlasın
                    for item in soup.find_all("a", href=True)[:50]:
                        link = item["href"]
                        if link.startswith("/"): link = target["base"] + link
                        title = item.text.strip()
                        
                        if len(title) > 30 and "http" in link:
                            category = get_category(title)
                            # Əgər kateqoriya tapılsa (və ya 'Gündəm' olsa) bazaya yaz
                            cursor.execute("SELECT id FROM xeberler WHERE link = ?", (link,))
                            if not cursor.fetchone():
                                cursor.execute("INSERT INTO xeberler (bashliq, link, kateqoriya) VALUES (?,?,?)",
                                               (title, link, category))
                                conn.commit()
            conn.close()
        except: pass
        time.sleep(10) # İlk başda bazanı doldurmaq üçün hər 10 saniyədən bir dövr eləsin

@app.route('/')
def home():
    is_admin = request.args.get('key') == '1eldar123*'
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 100")
    all_news = cursor.fetchall()
    conn.close()
    return render_template("index.html", all_news=all_news, info={"is_admin": is_admin})

if __name__ == '__main__':
    init_db()
    threading.Thread(target=bot_logic, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
