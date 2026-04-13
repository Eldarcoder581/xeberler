import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, session
from googletrans import Translator

app = Flask(__name__, template_folder='.')
app.secret_key = 'baku_news_2026_key'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bakunews.db')

translator = Translator()

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS xeberler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         bashliq TEXT, link TEXT UNIQUE, meqale TEXT, 
         img_url TEXT, kateqoriya TEXT DEFAULT 'Ümumi')''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS serhler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, xeber_id INTEGER, ad TEXT, mesaj TEXT)''')
    conn.commit()
    conn.close()

def get_category(title):
    t = title.lower()
    if any(x in t for x in ['futbol', 'idman', 'oyun', 'karate', 'federasiya']): return 'İdman'
    if any(x in t for x in ['iqtisadiyyat', 'dollar', 'euro', 'bank', 'neft', 'qiymət']): return 'İqtisadiyyat'
    if any(x in t for x in ['texnologiya', 'iphone', 'smartfon', 'süni zəka']): return 'Texnologiya'
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
        {"url": "https://report.az/son-xeberler/", "base": "https://report.az"},
        {"url": "https://qafqazinfo.az/", "base": ""},
        {"url": "https://az.trend.az/azerbaijan/", "base": "https://az.trend.az"},
        {"url": "https://www.bbc.com/azeri", "base": "https://www.bbc.com"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
    
    first_run = True # İlk dəfə çoxlu xəbər çəkmək üçün

    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            for target in targets:
                # İlk işə düşəndə hər saytdan 30 dənə, sonra hər dəqiqə 10 təzə link yoxlayır
                check_limit = 35 if first_run else 10
                
                req = urllib.request.Request(target["url"], headers=headers)
                with urllib.request.urlopen(req, timeout=15) as res:
                    soup = BeautifulSoup(res.read(), "html.parser")
                    links = soup.find_all("a", href=True)
                    
                    found_count = 0
                    for item in links:
                        if found_count >= check_limit: break
                        
                        link = item["href"]
                        if link.startswith("/"): link = target["base"] + link
                        title = item.text.strip()
                        
                        if len(title) > 30 and "http" in link:
                            cursor.execute("SELECT id FROM xeberler WHERE link = ?", (link,))
                            if not cursor.fetchone():
                                try:
                                    c_req = urllib.request.Request(link, headers=headers)
                                    with urllib.request.urlopen(c_req, timeout=7) as c_res:
                                        c_soup = BeautifulSoup(c_res.read(), "html.parser")
                                        img_tag = c_soup.find('meta', property="og:image")
                                        img_url = img_tag['content'] if img_tag else ""
                                        
                                        p_tags = c_soup.find_all('p')
                                        summary = " ".join([p.text.strip() for p in p_tags[:2]])[:350] + "..."
                                        
                                        cursor.execute("INSERT INTO xeberler (bashliq, link, meqale, img_url, kateqoriya) VALUES (?,?,?,?,?)",
                                                       (title, link, summary, img_url, get_category(title)))
                                        conn.commit()
                                        found_count += 1
                                except: continue
            conn.close()
            first_run = False 
        except: pass
        time.sleep(60) # Hər 1 dəqiqədən bir təzə xəbər yoxla

@app.route('/')
def home():
    query = request.args.get('q', '').strip().lower()
    is_admin = request.args.get('key') == '1eldar123*'
    lang = session.get('lang', 'az')
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Axtarış və ya normal list
    if query:
        cursor.execute("SELECT * FROM xeberler WHERE bashliq LIKE ? ORDER BY id DESC LIMIT 40", (f'%{query}%',))
    else:
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 40")
    
    all_news_raw = cursor.fetchall()
    all_news = []
    
    # Dil tərcüməsi
    if lang != 'az' and all_news_raw:
        for item in all_news_raw:
            item_list = list(item)
            try:
                item_list[1] = translator.translate(item[1], dest=lang).text
            except: pass
            all_news.append(item_list)
    else:
        all_news = all_news_raw

    info = {
        "hava": get_live_weather("Quba"), 
        "query": query, "is_admin": is_admin, "lang": lang
    }
    conn.close()
    return render_template("index.html", all_news=all_news, info=info)

@app.route('/set_lang/<lang>')
def set_lang(lang):
    session['lang'] = lang
    return redirect(request.referrer or '/')

@app.route('/xeber/<int:news_id>')
def news_detail(news_id):
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT * FROM xeberler WHERE id = ?", (news_id,))
    news = cursor.fetchone()
    cursor.execute("SELECT ad, mesaj FROM serhler WHERE xeber_id = ?", (news_id,))
    serhler = cursor.fetchall()
    conn.close()
    return render_template("news_page.html", news=news, serhler=serhler)

@app.route('/admin')
def admin_panel():
    if request.args.get('key') != '1eldar123*': return "Giriş qadağandır!", 403
    conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
    cursor.execute("SELECT id, bashliq, kateqoriya FROM xeberler ORDER BY id DESC LIMIT 100")
    news = cursor.fetchall(); conn.close()
    # Admin paneli HTML-i bura yazıla bilər və ya ayrı fayl
    return f"Admin Panel: {len(news)} xəbər aktivdir."

@app.route('/delete/<int:news_id>')
def delete_news(news_id):
    if request.args.get('key') == '1eldar123*':
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("DELETE FROM xeberler WHERE id = ?", (news_id,))
        conn.commit(); conn.close()
    return redirect(f'/admin?key=1eldar123*')

if __name__ == '__main__':
    init_db()
    threading.Thread(target=bot_logic, daemon=True).start()
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
