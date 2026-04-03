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
DB_PATH = os.path.join(BASE_DIR, 'baku_v18_final.db')

# --- 3-LÜ YAN-YANA DÜZÜLÜŞ ---
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
        .news-card { 
            background: #1c2128; border-radius: 12px; border: 1px solid #30363d; 
            padding: 20px; display: flex; flex-direction: column; justify-content: space-between; height: 160px; transition: 0.3s;
        }
        .news-card:hover { border-color: #238636; transform: translateY(-5px); }
        .news-title { font-size: 15px; font-weight: bold; line-height: 1.5; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; }
        .btn { display: block; text-align: center; background: #238636; color: white; padding: 10px; text-decoration: none; border-radius: 6px; font-weight: bold; margin-top: 10px; }
        @media (max-width: 850px) { .container { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 600px) { .container { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS 📰</h1></div>
    <div class="container">
        {% for x in data %}
        <div class="news-card">
            <div class="news-title">{{ x[1] }}</div>
            <a class="btn" href="{{ x[2] }}" target="_blank">Oxu →</a>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE)')
    conn.commit()
    return conn

def seed_18_news():
    """Baza tam boşdursa, 18 dənə müvəqqəti xəbər qoyur."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM xeberler")
    if cursor.fetchone()[0] == 0:
        # 18 dənə müxtəlif başlıqla xəbər yeri yaradırıq
        placeholder_list = []
        for i in range(1, 19):
            placeholder_list.append((f"Köhnə Xəbər #{i}: Yenilənmə gözlənilir...", "https://news.milli.az/society/"))
        
        cursor.executemany("INSERT OR IGNORE INTO xeberler (bashliq, link) VALUES (?, ?)", placeholder_list)
        conn.commit()
    conn.close()

def fetch_milli():
    """Hər 30 dəqiqədən bir yeni xəbərləri çəkir və ən yuxarıya qoyur."""
    while True:
        try:
            url = "https://news.milli.az/society/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                items = soup.select(".news-item, .p-news-item, .category-news-item")
                conn = get_db()
                cursor = conn.cursor()
                for item in items[:21]:
                    a_tag = item.find("a", href=True)
                    if a_tag:
                        link = a_tag["href"]
                        if not link.startswith("http"): link = "https://news.milli.az" + link
                        title = a_tag.get("title") or a_tag.text.strip()
                        if title:
                            # INSERT OR IGNORE sayəsində eyni xəbər iki dəfə düşməyəcək
                            cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link) VALUES (?, ?)", (title, link))
                conn.commit()
                conn.close()
        except: pass
        time.sleep(1800) # 30 dəqiqə

@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()
    # ORDER BY id DESC yeni xəbərlərin həmişə yuxarıda olmasını təmin edir
    cursor.execute("SELECT * FROM xeberler ORDER BY id DESC")
    data = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, data=data)

if __name__ == '__main__':
    # 1. İlk olaraq 18 köhnə xəbəri bazaya yerləşdiririk
    seed_18_news()
    # 2. Yeni xəbərləri çəkmək üçün botu başladırıq
    threading.Thread(target=fetch_milli, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
