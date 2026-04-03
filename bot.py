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
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS</title>
    <style>
        body { font-family: Arial; background: #0b0e14; color: #e1e1e1; text-align: center; margin: 0; }
        .header { background: #161b22; padding: 20px; border-bottom: 2px solid #58a6ff; position: sticky; top: 0; }
        .news-card { background: #1c2128; margin: 15px auto; padding: 15px; border-radius: 8px; border: 1px solid #30363d; max-width: 500px; }
        h3 { font-size: 18px; color: #adbac7; }
        a { color: #58a6ff; text-decoration: none; font-weight: bold; }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS 📰</h1></div>
    {% if not data %}
        <p style="margin-top:50px;">Xəbərlər yüklənir... <br> 10 saniyə sonra səhifəni yeniləyin.</p>
    {% else %}
        {% for x in data %}
        <div class="news-card">
            <h3>{{ x[1] }}</h3>
            <a href="{{ x[2] }}" target="_blank">OXU →</a>
        </div>
        {% endfor %}
    {% endif %}
</body>
</html>
"""

def init_db():
    # Bu funksiya mütləq cədvəli yaratmalıdır
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE)')
    conn.commit()
    conn.close()
    print("Baza sistemi hazırlandı.")

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
        except Exception as e:
            print(f"Bot xetasi: {e}")
        time.sleep(300)

@app.route('/')
def home():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # "SIFARIŞ BY" yox, "ORDER BY" olmalıdır!
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 30")
        data = cursor.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, data=data)
    except Exception as e:
        return f"Xəta baş verdi: {e}"

# İŞƏ SALMA SIRALAMASI
init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
