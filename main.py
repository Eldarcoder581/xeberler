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
    
    cursor.execute("SELECT COUNT(*) FROM xeberler")
    count = cursor.fetchone()[0]
    
    if count == 0:
        for i in range(1, 41):
            cursor.execute("""INSERT INTO xeberler (bashliq, link, meqale, img_url, kateqoriya) 
                              VALUES (?, ?, ?, ?, ?)""", 
                           (f"Xəbər yüklənir... Nümunə xəbər #{i}", f"https://example.com/{i}", 
                            "Tezliklə burada real xəbər görünəcək.", "https://via.placeholder.com/400x250", "Ümumi"))
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS serhler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, xeber_id INTEGER, ad TEXT, mesaj TEXT)''')
    conn.commit()
    conn.close()

def get_category(title):
    t = title.lower()
    if any(x in t for x in ['futbol', 'idman', 'oyun']): return 'İdman'
    if any(x in t for x in ['dollar', 'euro', 'iqtisadiyyat']): return 'İqtisadiyyat'
    if any(x in t for x in ['iphone', 'it', 'texnologiya']): return 'Texnologiya'
    return 'Siyasət' if 'siyasət' in t else 'Dünya'

def get_live_weather(city="Quba"):
    try:
        url = f"https://wttr.in/{city}?format=%t"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            return f"{res.read().decode('utf-8')} {city}"
    except: return f"18°C {city}"

def bot_logic():
    targets = [
        {"url": "https://news.milli.az/society/", "limit": 20},
        {"url": "https://az.trend.az/azerbaijan/", "limit": 20}
    ]
    headers = {'User-Agent': 'Mozilla/5.0'}
    
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for target in targets:
                count = 0
                req = urllib.request.Request(target["url"], headers=headers)
                with urllib.request.urlopen(req, timeout=15) as res:
                    soup = BeautifulSoup(res.read(), "html.parser")
                    for item in soup.find_all("a", href=True):
                        if count >= target["limit"]: break
                        link = item["href"]
                        if link.startswith("/"): link = "https://az.trend.az" + link
                        title = item.get("title") or item.text.strip()
                        
                        if len(title) > 25 and "http" in link:
                            cursor.execute("SELECT id FROM xeberler WHERE link = ?", (link,))
                            if not cursor.fetchone():
                                img_url, summary = "", "Məzmun yüklənir..."
                                try:
                                    c_req = urllib.request.Request(link, headers=headers)
                                    with urllib.request.urlopen(c_req, timeout=5) as c_res:
                                        c_soup = BeautifulSoup(c_res.read(), "html.parser")
                                        img_tag = c_soup.find('meta', property="og:image")
                                        if img_tag: img_url = img_tag['content']
                                        paragraphs = c_soup.find_all('p')
                                        if paragraphs:
                                            summary = " ".join([p.text.strip() for p in paragraphs[:3]])
                                            if len(summary) > 300: summary = summary[:300] + "..."
                                except: pass
                                
                                cursor.execute("INSERT INTO xeberler (bashliq, link, meqale, img_url, kateqoriya) VALUES (?,?,?,?,?)",
                                               (title, link, summary, img_url, get_category(title)))
                                count += 1
                                conn.commit()
            conn.close()
        except Exception as e: print(f"Bot xətası: {e}")
        time.sleep(600) # 10 dəqiqə gözlə

@app.route('/')
def home():
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * 40
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    if query:
        sql = "SELECT * FROM xeberler WHERE bashliq LIKE ? OR meqale LIKE ? ORDER BY id DESC LIMIT 40 OFFSET ?"
        p = f"%{query}%"
        cursor.execute(sql, (p, p, offset))
    else:
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 40 OFFSET ?", (offset,))
    
    all_news = cursor.fetchall()
    info = {"usd": "1.7000", "hava": get_live_weather("Quba"), "next_page": page + 1, "query": query}
    conn.close()
    return render_template("index.html", all_news=all_news, info=info)

@app.route('/xeber/<int:news_id>')
def news_detail(news_id):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT * FROM xeberler WHERE id = ?", (news_id,))
    news = cursor.fetchone()
    cursor.execute("SELECT ad, mesaj FROM serhler WHERE xeber_id = ?", (news_id,))
    serhler = cursor.fetchall()
    conn.close()
    return render_template("news_page.html", news=news, serhler=serhler)

@app.route('/send_serh', methods=['POST'])
def send_serh():
    x_id, ad, msg = request.form.get('xeber_id'), request.form.get('ad'), request.form.get('mesaj')
    conn = sqlite3.connect(DB_PATH); c = conn.cursor()
    c.execute("INSERT INTO serhler (xeber_id, ad, mesaj) VALUES (?,?,?)", (x_id, ad, msg))
    conn.commit(); conn.close()
    return redirect(f'/xeber/{x_id}')

if __name__ == '__main__':
    init_db()
    threading.Thread(target=bot_logic, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
