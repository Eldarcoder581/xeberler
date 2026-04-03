import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)
DB_PATH = 'bakunews.db'

# --- YENİ MODERN DİZAYN (Yan-yana 3 sətir) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS - Modern</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; padding: 0; }
        .header { background: #161b22; padding: 20px; text-align: center; border-bottom: 3px solid #238636; margin-bottom: 20px; }
        .container { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; 
            padding: 20px; 
            max-width: 1200px; 
            margin: 0 auto; 
        }
        .news-card { 
            background: #1c2128; 
            border-radius: 12px; 
            border: 1px solid #30363d; 
            overflow: hidden; 
            transition: transform 0.3s ease;
        }
        .news-card:hover { transform: translateY(-10px); border-color: #238636; }
        .news-img { width: 100%; height: 200px; object-fit: cover; background: #30363d; }
        .news-content { padding: 15px; }
        .news-title { font-size: 16px; font-weight: bold; margin-bottom: 15px; height: 50px; overflow: hidden; }
        .btn { 
            display: block; 
            text-align: center; 
            background: #238636; 
            color: white; 
            padding: 10px; 
            text-decoration: none; 
            border-radius: 6px; 
            font-size: 14px; 
        }
        @media (max-width: 600px) { .container { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS 📰</h1></div>
    <div class="container">
        {% if not data %}
            <p style="grid-column: 1/-1; text-align: center;">Xəbərlər gətirilir... Zəhmət olmasa 20 saniyə sonra yeniləyin.</p>
        {% else %}
            {% for x in data %}
            <div class="news-card">
                <img class="news-img" src="{{ x[3] if x[3] else 'https://via.placeholder.com/300x200?text=Baku+News' }}" alt="News">
                <div class="news-content">
                    <div class="news-title">{{ x[1] }}</div>
                    <a class="btn" href="{{ x[2] }}" target="_blank">Xəbəri Oxu →</a>
                </div>
            </div>
            {% endfor %}
        {% endif %}
    </div>
</body>
</html>
"""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    # Şəkil linki üçün 'sekil' sütunu əlavə edirik
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE, sekil TEXT)')
    conn.commit()
    conn.close()

def fetch_milli():
    while True:
        try:
            url = "https://news.milli.az/society/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                # Milli.az xəbər bloklarını tapırıq
                items = soup.select(".news-item")[:21] # 3-lü sıra üçün 21 dənə (7 sıra)
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                for item in items:
                    try:
                        a_tag = item.find("a", class_="news-item-title")
                        img_tag = item.find("img")
                        
                        title = a_tag.text.strip()
                        link = "https://news.milli.az" + a_tag["href"]
                        img_url = img_tag["src"] if img_tag else ""
                        
                        cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link, sekil) VALUES (?, ?, ?)", (title, link, img_url))
                    except: continue
                conn.commit()
                conn.close()
        except Exception as e: print(f"Bot xetasi: {e}")
        time.sleep(300)

@app.route('/')
def home():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 21")
        data = cursor.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, data=data)
    except: return "Hazırlanır..."

init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    p = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=p)
