import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template

app = Flask(__name__, template_folder='.')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bakunews.db')

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS xeberler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         bashliq TEXT, 
         link TEXT UNIQUE, 
         meqale TEXT, 
         img_url TEXT)''')
    conn.commit()
    conn.close()

def bot_logic():
    targets = [
        {"url": "https://news.milli.az/society/", "name": "Milli.az"},
        {"url": "https://az.trend.az/", "name": "Trend News"},
        {"url": "https://caliber.az/az/", "name": "Caliber.az"},
        {"url": "https://think-tanks.az/", "name": "Think-Tanks"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        for target in targets:
            try:
                req = urllib.request.Request(target["url"], headers=headers)
                with urllib.request.urlopen(req, timeout=15) as response:
                    soup = BeautifulSoup(response.read(), "html.parser")
                    links = soup.find_all("a", href=True)
                    
                    count = 0
                    for item in links:
                        if count >= 8: break # Hər saytdan dərhal 8 xəbər (Toplam ~32 xəbər)
                        
                        link = item["href"]
                        if not link.startswith("http"): continue
                        title = item.get("title") or item.text.strip()
                        
                        if len(title) > 25:
                            # Bazada yoxdursa dərhal çək
                            cursor.execute("SELECT id FROM xeberler WHERE link = ?", (link,))
                            if cursor.fetchone(): continue

                            img_url = ""
                            content_text = "Məzmun yüklənir..."
                            try:
                                c_req = urllib.request.Request(link, headers=headers)
                                with urllib.request.urlopen(c_req, timeout=5) as c_res:
                                    c_soup = BeautifulSoup(c_res.read(), "html.parser")
                                    ps = c_soup.find_all('p')
                                    content_text = " ".join([p.text.strip() for p in ps[:3]])[:500]
                                    img_tag = c_soup.find('meta', property="og:image")
                                    if img_tag: img_url = img_tag['content']
                            except: pass
                            
                            cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link, meqale, img_url) VALUES (?, ?, ?, ?)", 
                                           (f"[{target['name']}] {title}", link, content_text, img_url))
                            count += 1
            except: continue
        
        conn.commit()
        conn.close()
        print("Bot: 30-dan çox xəbər dərhal bazaya yükləndi!")
    except Exception as e:
        print(f"Bot xətası: {e}")

def fetch_milli():
    # Sayt açılan kimi birinci dəfə dərhal işləyir
    bot_logic()
    # Sonra dayanmadan (hər 10 saniyədən bir) yeni xəbər axtarır
    while True:
        time.sleep(10)
        bot_logic()

@app.route('/')
def home():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, bashliq, img_url FROM xeberler ORDER BY id DESC LIMIT 10")
    slider_news = cursor.fetchall()
    cursor.execute("SELECT id, bashliq, meqale, img_url FROM xeberler ORDER BY id DESC LIMIT 40")
    all_news = cursor.fetchall()
    conn.close()
    return render_template("index.html", slider_news=slider_news, all_news=all_news)

@app.route('/xeber/<int:news_id>')
def news_detail(news_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT bashliq, meqale, img_url, link FROM xeberler WHERE id = ?", (news_id,))
    news = cursor.fetchone()
    conn.close()
    if news:
        return f"<html><body style='background:#0b0e14;color:white;padding:20px;font-family:sans-serif;'><div style='max-width:800px;margin:auto;'><a href='/' style='color:#ffeb3b'>← Geri</a><h1>{news[0]}</h1><img src='{news[2]}' style='width:100%;border-radius:10px;'><p>{news[1]}</p><hr><a href='{news[3]}' style='color:#ffeb3b' target='_blank'>Mənbəyə keç</a></div></body></html>"
    return "Xəbər tapılmadı", 404

init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
    
