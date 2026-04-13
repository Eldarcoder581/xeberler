import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template, request, redirect, session

app = Flask(__name__, template_folder='.')
app.secret_key = 'baku_news_2026_key' # Session üçün gizli açar
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
        (id INTEGER PRIMARY KEY AUTOINCREMENT, xeber_id INTEGER, ad TEXT, mesaj TEXT)''')
    conn.commit()
    conn.close()

def get_category(title):
    t = title.lower()
    if any(x in t for x in ['futbol', 'idman', 'oyun']): return 'İdman'
    if any(x in t for x in ['iqtisadiyyat', 'dollar', 'euro', 'bank']): return 'İqtisadiyyat'
    if any(x in t for x in ['analiz', 'strateji', 'hesabat']): return 'Analitik Hesabat'
    return 'Dünya'

def get_live_weather(city="Quba"):
    try:
        url = f"https://wttr.in/{city}?format=%t"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as res:
            return f"{res.read().decode('utf-8')} {city}"
    except: return f"18°C {city}"

def bot_logic():
    # Yeni mənbələr: Report, Qafqazinfo, Trend, BBC
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
                with urllib.request.urlopen(req, timeout=15) as res:
                    soup = BeautifulSoup(res.read(), "html.parser")
                    for item in soup.find_all("a", href=True)[:15]: # Hər mənbədən 15 xəbər
                        link = item["href"]
                        if link.startswith("/"): link = target["base"] + link
                        title = item.text.strip()
                        
                        if len(title) > 30 and "http" in link:
                            cursor.execute("SELECT id FROM xeberler WHERE link = ?", (link,))
                            if not cursor.fetchone():
                                img_url, summary = "", "Məzmun yüklənir..."
                                try:
                                    c_req = urllib.request.Request(link, headers=headers)
                                    with urllib.request.urlopen(c_req, timeout=5) as c_res:
                                        c_soup = BeautifulSoup(c_res.read(), "html.parser")
                                        img_tag = c_soup.find('meta', property="og:image")
                                        if img_tag: img_url = img_tag['content']
                                        
                                        p_tags = c_soup.find_all('p')
                                        if p_tags:
                                            summary = " ".join([p.text.strip() for p in p_tags[:2]])
                                            if len(summary) > 400: summary = summary[:400] + "..."
                                except: pass
                                
                                cursor.execute("INSERT INTO xeberler (bashliq, link, meqale, img_url, kateqoriya) VALUES (?,?,?,?,?)",
                                               (title, link, summary, img_url, get_category(title)))
                                conn.commit()
            conn.close()
        except: pass
        time.sleep(900) # 15 dəqiqədən bir yenilə

from googletrans import Translator

translator = Translator()

@app.route('/')
def home():
    query = request.args.get('q', '').strip().lower()
    is_admin = request.args.get('key') == '1eldar123*'
    lang = session.get('lang', 'az') # Seçilən dili burdan götürürük
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Xəbərləri gətiririk
    cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 40")
    all_news_raw = cursor.fetchall()
    
    all_news = []
    if lang != 'az':
        # Əgər dil azərbaycan dili deyilsə, başlıqları tərcümə edirik
        for item in all_news_raw:
            item_list = list(item)
            try:
                # Başlığı tərcümə et (Məsələn: 'en' və ya 'ru')
                translated = translator.translate(item[1], dest=lang).text
                item_list[1] = translated
            except:
                pass
            all_news.append(item_list)
    else:
        all_news = all_news_raw

    info = {
        "usd": "1.7000", 
        "hava": get_live_weather("Quba"), 
        "query": query, 
        "is_admin": is_admin,
        "lang": lang
    }
    conn.close()
    return render_template("index.html", all_news=all_news, info=info)

@app.route('/set_lang/<lang>')
def set_lang(lang):
    session['lang'] = lang
    return redirect(request.referrer or '/')

@app.route('/admin')
def admin_panel():
    if request.args.get('key') != '1eldar123*': return "Giriş qadağandır!", 403
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, bashliq, kateqoriya FROM xeberler ORDER BY id DESC LIMIT 100")
    news = cursor.fetchall()
    conn.close()
    return f"""
    <body style="background:#1a1a1a; color:white; font-family:sans-serif; padding:20px;">
        <h2>Baku News - İdarəetmə Paneli</h2>
        <a href="/" style="color:#ffeb3b;">← Sayta qayıt</a><br><br>
        <table border="1" style="width:100%; border-collapse:collapse;">
            <tr style="background:#333;"><th>ID</th><th>Başlıq</th><th>Kateqoriya</th><th>Əməliyyat</th></tr>
            {"".join([f"<tr><td>{n[0]}</td><td>{n[1][:50]}...</td><td>{n[2]}</td><td><a href='/delete/{n[0]}?key=1eldar123*' style='color:red;'>Sil</a></td></tr>" for n in news])}
        </table>
    </body>
    """

@app.route('/delete/<int:news_id>')
def delete_news(news_id):
    if request.args.get('key') == '1eldar123*':
        conn = sqlite3.connect(DB_PATH); cursor = conn.cursor()
        cursor.execute("DELETE FROM xeberler WHERE id = ?", (news_id,))
        conn.commit(); conn.close()
    return redirect(f'/admin?key=1eldar123*')

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
