import urllib.request
import sqlite3
import threading
import time
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)

# --- PORTALIN GÖRÜNÜŞÜ (HTML/CSS) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS - Canlı Portal</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #121212; color: #eee; margin: 0; padding: 0; }
        .navbar { background: #1a1a1a; color: #ffcc00; padding: 20px; text-align: center; border-bottom: 3px solid #ffcc00; }
        .container { max-width: 1000px; margin: 20px auto; padding: 0 15px; }
        .news-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .news-card { background: #1e1e1e; border-radius: 10px; border: 1px solid #333; overflow: hidden; transition: 0.3s; padding: 20px; }
        .news-card:hover { transform: translateY(-5px); border-color: #ffcc00; }
        .news-card h3 { font-size: 18px; margin: 0 0 15px 0; line-height: 1.5; color: #fff; height: 80px; overflow: hidden; }
        .btn { display: inline-block; background: #ffcc00; color: #000; padding: 10px 15px; text-decoration: none; border-radius: 5px; font-weight: bold; }
        .footer { text-align: center; padding: 30px; color: #666; font-size: 13px; }
    </style>
</head>
<body>
    <div class="navbar"><h1>BAKU NEWS</h1><p>Milli.az-dan ən son xəbərlər</p></div>
    <div class="container">
        <div class="news-grid">
            {% for x in data %}
            <div class="news-card">
                <h3>{{ x[1] }}</h3>
                <a href="{{ x[2] }}" target="_blank" class="btn">Xəbəri Oxu →</a>
            </div>
            {% endfor %}
        </div>
        {% if not data %}
        <div style="text-align:center; margin-top: 50px;">
            <h3>Xəbərlər yüklənir... Zəhmət olmasa 10 saniyə sonra səhifəni yeniləyin.</h3>
        </div>
        {% endif %}
    </div>
    <div class="footer">Baku News Project &copy; 2026 | Developed by Cuppulu</div>
</body>
</html>
"""

# --- VERİLƏNLƏR BAZASINI QURMAQ ---
def init_db():
    conn = sqlite3.connect('bakunews.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE, shekil TEXT)')
    conn.commit()
    conn.close()

# --- XƏBƏR ÇƏKMƏ FUNKSİYASI (BOT) ---
def start_bot():
    while True:
        url = "http://news.milli.az/society/" 
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                items = soup.find_all("div", class_="news-item-title", limit=20)
                
                conn = sqlite3.connect('bakunews.db', check_same_thread=False)
                cursor = conn.cursor()
                for item in items:
                    try:
                        title = item.find("a").text.strip()
                        link = "https://news.milli.az" + item.find("a")["href"]
                        cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link, shekil) VALUES (?, ?, ?)", (title, link, ""))
                    except: continue
                conn.commit()
                conn.close()
                print("Bot: Xəbərlər yeniləndi.")
        except Exception as e:
            print(f"Bot Xətası: {e}")
        
        time.sleep(600) # 10 dəqiqədən bir yeni xəbərləri yoxla

# --- SAYTIN YOLLARI ---
@app.route('/')
def home():
    try:
        conn = sqlite3.connect('bakunews.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 30")
        data = cursor.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, data=data)
    except:
        return "Sistem işə düşür, zəhmət olmasa gözləyin..."

# --- İŞƏ SALMA ---
if __name__ == '__main__':
    init_db()
    # Botu ayrı bir qolda (Thread) başladırıq ki, saytı dayandırmasın
    threading.Thread(target=start_bot, daemon=True).start()
    # Render üçün port ayarı
    app.run(host='0.0.0.0', port=10000)
