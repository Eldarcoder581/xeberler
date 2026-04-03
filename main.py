import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)

# BAZA YOLU
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'baku_fixed.db')

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
        .container { 
            display: grid; 
            grid-template-columns: repeat(3, 1fr); 
            gap: 20px; padding: 20px; max-width: 1200px; margin: 0 auto; 
        }
        .news-card { background: #1c2128; border-radius: 12px; border: 1px solid #30363d; overflow: hidden; display: flex; flex-direction: column; transition: 0.3s; }
        .news-card:hover { transform: translateY(-5px); border-color: #238636; }
        .news-img { width: 100%; height: 180px; object-fit: cover; background: #30363d; }
        .news-content { padding: 15px; flex-grow: 1; display: flex; flex-direction: column; justify-content: space-between; }
        .news-title { font-size: 15px; font-weight: bold; margin-bottom: 10px; height: 42px; overflow: hidden; }
        .btn { display: block; text-align: center; background: #238636; color: white; padding: 10px; text-decoration: none; border-radius: 6px; font-weight: bold; }
        @media (max-width: 900px) { .container { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 600px) { .container { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS 📰</h1></div>
    <div class="container">
        {% if not data %}
            <div style="grid-column: 1/-1; text-align: center; margin-top: 50px;">
                <h3>Xəbərlər gətirilir...</h3>
                <p>Bot işə düşür. 15 saniyə gözləyib səhifəni yeniləyin.</p>
            </div>
        {% else %}
            {% for x in data %}
            <div class="news-card">
                <img class="news-img" src="{{ x[3] if x[3] else 'https://via.placeholder.com/300x180?text=Baku+News' }}">
                <div class="news-content">
                    <div class="news-title">{{ x[1] }}</div>
                    <a class="btn" href="{{ x[2] }}" target="_blank">Oxu →</a>
                </div>
            </div>
            {% endfor %}
        {% endif %}
    </div>
</body>
</html>
"""

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE, sekil TEXT)')
    conn.commit()
    return conn

def fetch_milli():
    while True:
        try:
            url = "https://news.milli.az/society/"
            # Daha güclü "User-Agent" əlavə edirik (Real brauzer kimi görünmək üçün)
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                # Milli.az-ın yeni strukturu üçün xəbər başlıqlarını tapırıq
                items = soup.find_all("div", class_="news-item-title", limit=20)
                
                if not items:
                    print("Bot: Xəbər tapılmadı, klass adlarını yoxlayıram...")
                    items = soup.find_all("a", href=True) # Ehtiyat variant
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                for item in items:
                    try:
                        a_tag = item.find("a") if item.name == "div" else item
                        title = a_tag.text.strip()
                        link = a_tag["href"]
                        if not link.startswith("http"):
                            link = "https://news.milli.az" + link
                        
                        if title and len(title) > 10: # Boş başlıqları keçirik
                            cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link) VALUES (?, ?)", (title, link))
                    except: continue
                conn.commit()
                conn.close()
                print("Bot: Xəbərlər uğurla yeniləndi!")
        except Exception as e:
            print(f"Bot xetasi: {e}")
        time.sleep(300)
@app.route('/')
def home():
    try:
        conn = get_db_connection() # Hər dəfə yoxlayır ki cədvəl varmı
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 21")
        data = cursor.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, data=data)
    except Exception as e:
        return f"Xəta: {e}"

if __name__ == '__main__':
    # Botu başlat
    threading.Thread(target=fetch_milli, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
