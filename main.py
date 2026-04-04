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
DB_PATH = os.path.join(BASE_DIR, 'baku_siyaset_final.db')

# --- DİPLOMATİK VƏ DOLU DİZAYN ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS - Siyasət</title>
    <style>
        body { font-family: 'Times New Roman', serif; background: #fdfdfd; color: #1a1a1a; margin: 0; padding: 0; }
        .header { background: #002347; color: white; padding: 25px; text-align: center; border-bottom: 5px solid #b22222; }
        .header h1 { margin: 0; font-size: 26px; text-transform: uppercase; letter-spacing: 2px; }
        .container { max-width: 800px; margin: 20px auto; padding: 15px; }
        .news-item { 
            background: white; border: 1px solid #ddd; padding: 20px; 
            margin-bottom: 15px; border-left: 8px solid #002347; transition: 0.2s;
        }
        .news-item:hover { border-left-color: #b22222; background: #f9f9f9; }
        .news-title { font-size: 20px; font-weight: bold; color: #002347; text-decoration: none; }
        .news-meta { font-size: 12px; color: #777; margin-top: 10px; }
        .footer { text-align: center; padding: 30px; color: #999; font-size: 13px; }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS • SİYASƏT 🇦🇿</h1></div>
    <div class="container">
        {% for x in data %}
        <div class="news-item">
            <a href="{{ x[2] }}" target="_blank" class="news-title">{{ x[1] }}</a>
            <div class="news-meta">MƏNBƏ: MİLLİ.AZ | SİYASƏT VƏ DİPLOMATİYA</div>
        </div>
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

def fetch_milli():
    """Xəbərləri dərhal və hər 30 dəqiqədən bir çəkir."""
    while True:
        try:
            url = "https://news.milli.az/politics/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
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
                        if title:
                            cursor.execute("INSERT OR IGNORE INTO siyaset (bashliq, link) VALUES (?, ?)", (title, link))
                conn.commit()
                conn.close()
        except: pass
        time.sleep(1800)

@app.route('/')
def home():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM siyaset ORDER BY id DESC LIMIT 35")
    data = cursor.fetchall()
    
    # Əgər hələ bazada xəbər yoxdursa, boş görünməməsi üçün müvəqqəti məlumat göstər
    if not data:
        data = [
            (0, "Xəbərlər hazırlanır, zəhmət olmasa 10 saniyə sonra yeniləyin...", "#"),
            (0, "Diplomatik arxiv yüklənir...", "#"),
            (0, "Siyasət bölməsinə qoşulur...", "#")
        ]
    conn.close()
    return render_template_string(HTML_TEMPLATE, data=data)

if __name__ == '__main__':
    # Botu dərhal başlat
    threading.Thread(target=fetch_milli, daemon=True).start()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
