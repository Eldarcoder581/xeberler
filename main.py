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
DB_PATH = os.path.join(BASE_DIR, 'diplomatik_arxiv_v5.db')

# --- CİDDİ ALT-ALTA DİZAYN ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS - Diplomatik Xidmət</title>
    <style>
        body { font-family: 'Times New Roman', serif; background: #f4f4f4; color: #1a1a1a; margin: 0; padding: 0; }
        .header { background: #002347; color: white; padding: 25px; text-align: center; border-bottom: 5px solid #b22222; position: sticky; top: 0; z-index: 1000; }
        .header h1 { margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 2px; }
        
        .container { max-width: 800px; margin: 20px auto; padding: 15px; }
        
        .news-link { text-decoration: none; color: inherit; display: block; margin-bottom: 12px; }
        
        .news-item { 
            background: white; border-radius: 4px; padding: 18px; 
            border-left: 6px solid #002347; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
            transition: 0.2s;
        }
        .news-item:hover { transform: translateX(8px); background: #fdfdfd; border-left-color: #b22222; }
        
        .news-title { font-size: 19px; font-weight: bold; color: #002347; line-height: 1.4; }
        .news-meta { font-size: 12px; color: #777; margin-top: 10px; text-transform: uppercase; }
        
        .footer { text-align: center; padding: 30px; color: #999; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS • Siyasət 🇦🇿</h1></div>
    <div class="container">
        {% for x in data %}
        <a class="news-link" href="{{ x[2] }}" target="_blank">
            <div class="news-item">
                <div class="news-title">{{ x[1] }}</div>
                <div class="news-meta">Diplomatik Arxiv | Milli.az</div>
            </div>
        </a>
        {% endfor %}
    </div>
    <div class="footer">© 2026 Əhmədzadə Diplomatik Xidmət</div>
</body>
</html>
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS siyaset (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE)')
    conn.commit()
    return conn

def seed_30_arxiv():
    """Baza boşdursa, 30 dənə yer tutucu köhnə xəbər əlavə edir."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT count(*) FROM siyaset")
    if cursor.fetchone()[0] == 0:
        arxiv_data = []
        for i in range(1, 31):
            arxiv_data.append((f"Arxiv Xəbər #{i}: Yenilənmə daxil olur...", "https://news.milli.az/politics/"))
        
        cursor.executemany("INSERT OR IGNORE INTO siyaset (bashliq, link) VALUES (?, ?)", arxiv_data)
        conn.commit()
    conn.close()

def fetch_milli():
    """Yeni siyasi xəbərləri çəkir və ən yuxarıya qoyur."""
    while True:
        try:
            url = "https://news.milli.az/politics/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                items = soup.select(".news-item, .p-news-item, .category-news-item")
                
                conn = get_db()
                cursor = conn.cursor()
                for item in items[:30]:
                    a_tag = item.find("a", href=True)
                    if a_tag:
                        link = a_tag["href"]
                        if not link.startswith("http"): link = "https://news.milli.az" + link
                        title = a_tag.get("title") or a_tag.text.strip()
                        if title and len(title) > 10:
                            # INSERT OR IGNORE sayəsində eyni xəbər təkrarlanmır
                            cursor.execute("INSERT OR IGNORE INTO siyaset (bashliq, link) VALUES (?, ?)", (title, link))
                conn.commit()
                conn.close()
        except: pass
        time.sleep(1800) # 30 dəqiqə

@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()
    # DESC (Descending) sayəsində yeni ID-li xəbərlər ən yuxarıda görünür
    cursor.execute("SELECT * FROM siyaset ORDER BY id DESC")
    data = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, data=data)

if __name__ == '__main__':
    # 1. İlk olaraq 30 arxiv xəbəri bazaya doldur
    seed_30_arxiv()
    # 2. Yeni xəbər botunu dərhal başlat
    threading.Thread(target=fetch_milli, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
