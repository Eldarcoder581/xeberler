import urllib.request
import sqlite3
import threading
import time
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)

# --- PORTAL DİZAYNI (Müasir və tünd mövzu) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS - Canlı Portal</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f0f0f; color: #e0e0e0; margin: 0; padding: 0; }
        .navbar { background: #1a1a1a; color: #ffcc00; padding: 20px; text-align: center; border-bottom: 3px solid #ffcc00; position: sticky; top: 0; z-index: 100; }
        .container { max-width: 1000px; margin: 20px auto; padding: 0 15px; }
        .news-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 20px; }
        .news-card { background: #1e1e1e; border-radius: 12px; overflow: hidden; border: 1px solid #333; transition: 0.3s; }
        .news-card:hover { transform: translateY(-5px); border-color: #ffcc00; }
        .card-content { padding: 20px; }
        .card-content h3 { font-size: 18px; margin: 0 0 15px 0; line-height: 1.5; color: #fff; height: 80px; overflow: hidden; }
        .read-more { display: inline-block; background: #ffcc00; color: #000; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; }
        .read-more:hover { background: #e6b800; }
        .footer { text-align: center; padding: 40px; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="navbar">
        <h1 style="margin:0;">BAKU NEWS</h1>
        <small>Ən son xəbərlər dərhal burada</small>
    </div>
    <div class="container">
        <div class="news-grid">
            {% for x in data %}
            <div class="news-card">
                <div class="card-content">
                    <h3>{{ x[1] }}</h3>
                    <a href="{{ x[2] }}" target="_blank" class="read-more">Xəbərə get →</a>
                </div>
            </div>
            {% endfor %}
        </div>
        {% if not data %}
        <div style="text-align:center; padding: 50px;">
            <p>Hələ ki xəbər tapılmadı. Zəhmət olmasa bir az gözləyin...</p>
        </div>
        {% endif %}
    </div>
    <div class="footer">Baku News Project &copy; 2026 | Developed by Cuppulu</div>
</body>
</html>
"""

# --- VERİLƏNLƏR BAZASI ---
def init_db():
    conn = sqlite3.connect('bakunews.db', check_same_thread=False)
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE, shekil TEXT)')
    conn.commit()
    conn.close()

# --- XƏBƏR ÇƏKMƏ FUNKSİYASI ---
def fetch_milli():
    while True:
        url = "http://news.milli.az/society/" 
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                items = soup.find_all("div", class_="news-item-title", limit=20)
                
                conn = sqlite3.connect('bakunews.db', check_same_thread=False)
                cursor = conn.cursor()
                new_count = 0
                for item in items:
                    try:
                        title = item.find("a").text.strip()
                        link = "https://news.milli.az" + item.find("a")["href"]
                        cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link, shekil) VALUES (?, ?, ?)", (title, link, ""))
                        if cursor.rowcount > 0:
                            new_count += 1
                    except: continue
                conn.commit()
                conn.close()
                print(f"Bot: {new_count} yeni xeber bazaya elave edildi.")
        except Exception as e:
            print(f"Bot Xetasi: {e}")
        
        time.sleep(600) # 10 deqiqeden bir yoxla

# --- FLASK YOLLARI ---
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
        return "Baza hele hazir deyil, sehifeni yenileyin..."

# --- İŞƏ SALMA ---
if __name__ == '__main__':
    init_db()
    # Xeber çekme prosesini ayrica bir qolda (thread) başladırıq
    threading.Thread(target=fetch_milli, daemon=True).start()
    # Render ve PythonAnywhere üçün uyğun port ayarı
    app.run(host='0.0.0.0', port=10000)
