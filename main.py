import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)
DB_PATH = 'bakunews.db'

# --- HTML DİZAYNI (Telefonda da gözəl görsənir) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS</title>
    <style>
        body { font-family: Arial, sans-serif; background: #0b0e14; color: #e1e1e1; text-align: center; margin: 0; padding: 0; }
        .header { background: #161b22; padding: 20px; border-bottom: 2px solid #58a6ff; }
        .container { padding: 10px; max-width: 600px; margin: auto; }
        .news-card { background: #1c2128; margin: 15px 0; padding: 20px; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h3 { font-size: 18px; line-height: 1.4; color: #adbac7; margin-bottom: 15px; }
        .btn { display: inline-block; background: #238636; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; }
        .btn:hover { background: #2ea043; }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS 📰</h1></div>
    <div class="container">
        {% if not data %}
            <p style="margin-top:50px;">Xəbərlər gətirilir... <br> 15 saniyə sonra səhifəni yeniləyin (F5).</p>
            <script>setTimeout(function(){ location.reload(); }, 10000);</script>
        {% else %}
            {% for x in data %}
            <div class="news-card">
                <h3>{{ x[1] }}</h3>
                <a class="btn" href="{{ x[2] }}" target="_blank">Xəbəri Oxu</a>
            </div>
            {% endfor %}
        {% endif %}
    </div>
</body>
</html>
"""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE)')
    conn.commit()
    conn.close()

def fetch_milli():
    while True:
        try:
            url = "http://news.milli.az/society/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                items = soup.find_all("div", class_="news-item-title", limit=15)
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                for item in items:
                    try:
                        title = item.find("a").text.strip()
                        link = "https://news.milli.az" + item.find("a")["href"]
                        cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link) VALUES (?, ?)", (title, link))
                    except: continue
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Bot xetasi: {e}")
        time.sleep(300)

@app.route('/')
def home():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # MÜTLƏQ "ORDER BY" OLMALIDIR
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 20")
        data = cursor.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, data=data)
    except:
        return "Sistem hazırlanır..."

# Başlatma
init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    # Railway üçün port ayarı
    p = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=p)
