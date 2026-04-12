import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect

app = Flask(__name__, template_folder='.')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bakunews.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS xeberler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         bashliq TEXT, link TEXT UNIQUE, meqale TEXT, 
         img_url TEXT, kateqoriya TEXT DEFAULT 'Ümumi')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS serhler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         xeber_id INTEGER, ad TEXT, mesaj TEXT)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS statistika (id INTEGER PRIMARY KEY, baxish_sayi INTEGER)''')
    cursor.execute('''INSERT OR IGNORE INTO statistika (id, baxish_sayi) VALUES (1, 0)''')
    conn.commit()
    conn.close()

def get_category(title):
    t = title.lower()
    if any(x in t for x in ['futbol', 'idman', 'oyun', 'klub']): return 'İdman'
    if any(x in t for x in ['dollar', 'euro', 'manat', 'iqtisadiyyat', 'bank']): return 'İqtisadiyyat'
    if any(x in t for x in ['iphone', 'it', 'texnologiya', 'smartfon', 'elm']): return 'Texnologiya'
    if any(x in t for x in ['paşinyan', 'siyasət', 'prezident', 'nazir', 'ordu']): return 'Siyasət'
    return 'Dünya'

def get_live_weather(city="Quba"):
    try:
        url = f"https://wttr.in/{city}?format=%t"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            return f"{res.read().decode('utf-8')} {city}"
    except: return f"18°C {city}"

def bot_logic():
    targets = [
        {"url": "https://news.milli.az/society/", "name": "Milli.az"},
        {"url": "https://az.trend.az/", "name": "Trend"},
        {"url": "https://caliber.az/az/", "name": "Caliber"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for target in targets:
                req = urllib.request.Request(target["url"], headers=headers)
                with urllib.request.urlopen(req, timeout=15) as res:
                    soup = BeautifulSoup(res.read(), "html.parser")
                    for item in soup.find_all("a", href=True):
                        link = item["href"]
                        title = item.get("title") or item.text.strip()
                        if len(title) > 30 and link.startswith("http"):
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
                                cat = get_category(title)
                                cursor.execute("INSERT INTO xeberler (bashliq, link, meqale, img_url, kateqoriya) VALUES (?,?,?,?,?)",
                                               (title, link, "Orijinal xəbəri oxumaq üçün mənbəyə keçid edin.", img_url, cat))
            conn.commit()
            conn.close()
        except: pass
        time.sleep(60)

@app.route('/')
def home():
    city = request.args.get('city', 'Quba')
    cat = request.args.get('cat')
    q = request.args.get('q')
    page = request.args.get('page', 1, type=int)
    per_page = 40
    offset = (page - 1) * per_page
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('UPDATE statistika SET baxish_sayi = baxish_sayi + 1 WHERE id = 1')
    conn.commit()
    cursor.execute('SELECT baxish_sayi FROM statistika WHERE id = 1')
    say = cursor.fetchone()[0]
    
    info = {"usd": "1.7000", "hava": get_live_weather(city), "say": say, "next_page": page + 1, "current_cat": cat or ""}
    
    if q:
        cursor.execute("SELECT * FROM xeberler WHERE bashliq LIKE ? ORDER BY id DESC", ('%'+q+'%',))
    elif cat:
        cursor.execute("SELECT * FROM xeberler WHERE kateqoriya = ? ORDER BY id DESC LIMIT ? OFFSET ?", (cat, per_page, offset))
    else:
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT ? OFFSET ?", (per_page, offset))
    
    all_news = cursor.fetchall()
    conn.close()
    return render_template("index.html", all_news=all_news, info=info)

@app.route('/xeber/<int:news_id>')
def news_detail(news_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM xeberler WHERE id = ?", (news_id,))
    news = cursor.fetchone()
    cursor.execute("SELECT ad, mesaj FROM serhler WHERE xeber_id = ?", (news_id,))
    serhler = cursor.fetchall()
    conn.close()
    if not news: return "Xəbər tapılmadı", 404
    return render_template("news_page.html", news=news, serhler=serhler)

@app.route('/send_serh', methods=['POST'])
def send_serh():
    x_id, ad, msg = request.form.get('xeber_id'), request.form.get('ad'), request.form.get('mesaj')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT INTO serhler (xeber_id, ad, mesaj) VALUES (?,?,?)", (x_id, ad, msg))
    conn.commit(); conn.close()
    return redirect(f'/xeber/{x_id}')

init_db()
threading.Thread(target=bot_logic, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
