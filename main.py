import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)

# Baza yolu
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'baku_clean.db')

# --- 3-LÜ YAN-YANA DÜZÜLÜŞ (ŞƏKİLSİZ) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; }
        .header { background: #161b22; padding: 20px; text-align: center; border-bottom: 3px solid #238636; position: sticky; top: 0; z-index: 1000; }
        
        /* 3 SÜTUNLU SİSTEM */
        .container { 
            display: grid; 
            grid-template-columns: repeat(3, 1fr); 
            gap: 15px; padding: 20px; max-width: 1200px; margin: 0 auto; 
        }

        .news-card { 
            background: #1c2128; border-radius: 10px; border: 1px solid #30363d; 
            padding: 20px; display: flex; flex-direction: column; justify-content: space-between; transition: 0.3s;
        }
        .news-card:hover { border-color: #238636; transform: translateY(-3px); }
        
        .news-title { font-size: 16px; font-weight: bold; margin-bottom: 15px; line-height: 1.4; height: 65px; overflow: hidden; }
        
        .btn { 
            display: block; text-align: center; background: #238636; color: white; 
            padding: 10px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 14px;
        }

        @media (max-width: 850px) { .container { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS 📰</h1></div>
    <div class="container">
        {% if not data %}
            <div style="grid-column: 1/-1; text-align: center; margin-top: 50px;">
                <h3>Xəbərlər gətirilir...</h3>
                <p>Zəhmət olmasa 15 saniyə sonra səhifəni yeniləyin.</p>
            </div>
        {% else %}
            {% for x in data %}
            <div class="news-card">
                <div class="news-title">{{ x[1] }}</div>
                <a class="btn" href="{{ x[2] }}" target="_blank">Xəbəri Oxu →</a>
            </div>
            {% endfor %}
        {% endif %}
    </div>
</body>
</html>
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE)')
    conn.commit()
    return conn

def fetch_milli():
    while True:
        try:
            url = "https://news.milli.az/society/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                items = soup.select(".news-item, .p-news-item, .category-news-item")
                
                conn = get_db()
                cursor = conn.cursor()
                for item in items[:21]:
                    try:
                        a_tag = item.find("a", href=True)
                        if a_tag:
                            link = a_tag["href"]
                            if not link.startswith("http"): link = "https://news.milli.az" + link
                            title = a_tag.get("title") or a_tag.text.strip()
                            if title and len(title) > 10:
                                cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link) VALUES (?, ?)", (title, link))
                    except: continue
                conn.commit()
                conn.close()
        except: pass
        time.sleep(1800) # 30 dəqiqə

@app.route('/')
def home():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 21")
        data = cursor.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, data=data)
    except:
        return "Sistem işə düşür..."

if __name__ == '__main__':
    threading.Thread(target=fetch_milli, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
