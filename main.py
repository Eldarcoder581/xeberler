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
    # Cədvəlləri yaradın
    cursor.execute('''CREATE TABLE IF NOT EXISTS xeberler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         bashliq TEXT, link TEXT UNIQUE, meqale TEXT, 
         img_url TEXT, kateqoriya TEXT DEFAULT 'Ümumi')''')
    
    # Yoxlayırıq əgər baza boşdursa, 40 dənə nümunə xəbər əlavə edirik
    cursor.execute("SELECT COUNT(*) FROM xeberler")
    count = cursor.fetchone()[0]
    
    if count == 0:
        for i in range(1, 41):
            placeholder_title = f"Xəbər yüklənir... Nümunə xəbər #{i}"
            placeholder_link = f"https://example.com/placeholder-{i}"
            placeholder_img = "https://via.placeholder.com/400x250?text=BAKU+NEWS"
            cursor.execute("""INSERT INTO xeberler (bashliq, link, meqale, img_url, kateqoriya) 
                              VALUES (?, ?, ?, ?, ?)""", 
                           (placeholder_title, placeholder_link, "Tezliklə burada real xəbər görünəcək.", placeholder_img, "Ümumi"))
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS serhler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, xeber_id INTEGER, ad TEXT, mesaj TEXT)''')
    conn.commit()
    conn.close()

def get_category(title):
    t = title.lower()
    if any(x in t for x in ['futbol', 'idman', 'oyun', 'klub', 'federasiya']): return 'İdman'
    if any(x in t for x in ['dollar', 'euro', 'manat', 'iqtisadiyyat', 'qiymət', 'bank']): return 'İqtisadiyyat'
    if any(x in t for x in ['iphone', 'it', 'texnologiya', 'kosmos', 'smartfon']): return 'Texnologiya'
    if any(x in t for x in ['paşinyan', 'siyasət', 'prezident', 'nazir', 'diplomat']): return 'Siyasət'
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
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
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
                                # ŞƏKİL ÇƏKMƏ MƏNTİQİ
                                img_url = ""
                                try:
                                    c_req = urllib.request.Request(link, headers=headers)
                                    with urllib.request.urlopen(c_req, timeout=7) as c_res:
                                        c_soup = BeautifulSoup(c_res.read(), "html.parser")
                                        # Öncə meta tag-dan şəkli axtarır (ən keyfiyyətlisi budur)
                                        img_tag = c_soup.find('meta', property="og:image")
                                        if img_tag: 
                                            img_url = img_tag['content']
                                        else:
                                            # Meta yoxdursa, ilk böyük şəkli götürür
                                            main_img = c_soup.find('img', src=True)
                                            if main_img: img_url = main_img['src']
                                except: pass
                                
                                cat = get_category(title)
                                cursor.execute("INSERT INTO xeberler (bashliq, link, meqale, img_url, kateqoriya) VALUES (?,?,?,?,?)",
                                               (f"{title}", link, "Ətraflı məlumat üçün orijinal mənbəyə keçid edə bilərsiniz.", img_url, cat))
            conn.commit()
            conn.close()
        except: pass
        time.sleep(30)

@app.route('/')
def home():
    city = request.args.get('city', 'Quba')
    cat = request.args.get('cat')
    q = request.args.get('q')
    info = {"usd": "1.7000", "hava": get_live_weather(city)}
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if q:
        cursor.execute("SELECT * FROM xeberler WHERE bashliq LIKE ? ORDER BY id DESC", ('%'+q+'%',))
    elif cat:
        cursor.execute("SELECT * FROM xeberler WHERE kateqoriya = ? ORDER BY id DESC LIMIT 40", (cat,))
    else:
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 40")
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
