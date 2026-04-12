import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template

# Sənin strukturuna görə fayllar eyni qovluqdadır
app = Flask(__name__, template_folder='.')
DB_PATH = 'bakunews.db'

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

def fetch_milli():
    targets = [
        {"url": "https://news.milli.az/society/", "name": "Milli.az"},
        {"url": "https://az.trend.az/", "name": "Trend News"},
        {"url": "https://caliber.az/az/", "name": "Caliber.az"},
        {"url": "https://think-tanks.az/", "name": "Think-Tanks"}
    ]
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            for target in targets:
                try:
                    req = urllib.request.Request(target["url"], headers=headers)
                    with urllib.request.urlopen(req, timeout=30) as response:
                        soup = BeautifulSoup(response.read(), "html.parser")
                        links = soup.find_all("a", href=True)
                        for item in links:
                            link = item["href"]
                            if not link.startswith("http"): continue
                            title = item.get("title") or item.text.strip()
                            if len(title) > 25:
                                # Məzmun və Şəkil çəkmə
                                content_text = "Məzmun yüklənir..."
                                img_url = ""
                                try:
                                    c_req = urllib.request.Request(link, headers=headers)
                                    with urllib.request.urlopen(c_req, timeout=10) as c_res:
                                        c_soup = BeautifulSoup(c_res.read(), "html.parser")
                                        ps = c_soup.find_all('p')
                                        content_text = " ".join([p.text.strip() for p in ps[:4]])[:600]
                                        img_tag = c_soup.find('meta', property="og:image")
                                        if img_tag: img_url = img_tag['content']
                                except: pass
                                cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link, meqale, img_url) VALUES (?, ?, ?, ?)", 
                                               (f"[{target['name']}] {title}", link, content_text, img_url))
                except: continue
            conn.commit()
            conn.close()
        except: pass
        time.sleep(900)

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
        return f"""
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: sans-serif; background: #0b0e14; color: white; padding: 20px; }}
                    .box {{ max-width: 800px; margin: auto; background: #1c2128; padding: 20px; border-radius: 12px; }}
                    img {{ width: 100%; border-radius: 10px; }}
                    .back {{ color: #ffeb3b; text-decoration: none; display: block; margin-bottom: 20px; }}
                </style>
            </head>
            <body>
                <div class="box">
                    <a href="/" class="back">← Geri</a>
                    <h1>{news[0]}</h1>
                    <img src="{news[2] or 'https://via.placeholder.com/600x400'}">
                    <p>{news[1]}</p>
                    <hr>
                    <a href="{news[3]}" style="color:#ffeb3b" target="_blank">Orijinal mənbə</a>
                </div>
            </body>
        </html>
        """
    return "Xəbər tapılmadı", 404

init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
                                
