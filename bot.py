import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)
DB_PATH = 'bakunews.db'

# --- HTML DİZAYNI ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>BAKU NEWS - Railway Edition</title>
    <style>
        body { font-family: 'Segoe UI', Arial; background: #0b0e14; color: #e1e1e1; margin: 0; text-align: center; }
        .header { background: #161b22; padding: 30px; border-bottom: 2px solid #58a6ff; }
        .news-container { max-width: 800px; margin: 20px auto; padding: 10px; }
        .news-card { background: #1c2128; margin-bottom: 15px; padding: 20px; border-radius: 10px; border: 1px solid #30363d; transition: 0.2s; }
        .news-card:hover { border-color: #58a6ff; transform: scale(1.02); }
        h3 { margin: 0 0 10px 0; color: #adbac7; }
        a { color: #58a6ff; text-decoration: none; font-weight: bold; }
        .loading { font-size: 18px; color: #8b949e; margin-top: 50px; }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS 📰</h1></div>
    <div class="news-container">
        {% if not data %}
            <div class="loading">Xəbərlər Milli.az-dan gətirilir... <br> 10 saniyə sonra səhifəni yeniləyin (F5).</div>
        {% else %}
            {% for x in data %}
            <div class="news-card">
                <h3>{{ x[1] }}</h3>
                <a href="{{ x[2] }}" target="_blank">TAM OXU →</a>
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
                items = soup.find_all("div", class_="news-item-title", limit=20)
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                for item in items:
                    title = item.find("a").text.strip()
                    link = "https://news.milli.az" + item.find("a")["href"]
                    cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link) VALUES (?, ?)", (title, link))
                conn.commit()
                conn.close()
        except: pass
        time.sleep(300)

@app.route('/')
def home():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 30")
        data = cursor.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, data=data)
    except:
        return "Sistem işə düşür..."

init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    # Railway-in verdiyi portu tutmaq üçün:
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
