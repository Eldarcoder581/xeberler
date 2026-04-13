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
    # Sənin istədiyin sahələrə uyğun mənbə linkləri
    targets = [
        {"url": "https://report.az/iqtisadiyyat/", "base": "https://report.az"},
        {"url": "https://report.az/daxili-siyaset/", "base": "https://report.az"},
        {"url": "https://report.az/herbi/", "base": "https://report.az"},
        {"url": "https://report.az/elm-tehsil/", "base": "https://report.az"},
        {"url": "https://report.az/texnologiya/", "base": "https://report.az"},
        {"url": "https://qafqazinfo.az/politics", "base": ""},
        {"url": "https://az.trend.az/business/", "base": "https://az.trend.az"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36'}
    
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for target in targets:
                req = urllib.request.Request(target["url"], headers=headers)
                with urllib.request.urlopen(req, timeout=15) as res:
                    soup = BeautifulSoup(res.read(), "html.parser")
                    links = soup.find_all("a", href=True)
                    
                    for item in links[:40]: # Hər bölmədən daha çox linkə baxırıq
                        link = item["href"]
                        if link.startswith("/"): link = target["base"] + link
                        title = item.text.strip()
                        
                        if len(title) > 30 and "http" in link:
                            category = get_category(title)
                            
                            # Əgər xəbər bizim kateqoriyalara uyğun deyilsə, bazaya yazma
                            if category:
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
                                                   (title, link, img_url, category))
                                    conn.commit()
            conn.close()
        except: pass
        time.sleep(120) # 2 dəqiqədən bir yenilə

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
