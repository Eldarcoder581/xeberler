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
DB_PATH = os.path.join(BASE_DIR, 'siyaset_v2.db')

# --- ALT-ALTA DİPLOMATİK DİZAYN ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS - Siyasət</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f0f2f5; color: #1c1e21; margin: 0; padding: 0; }
        .header { background: #003366; color: white; padding: 20px; text-align: center; border-bottom: 5px solid #d90429; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .header h1 { margin: 0; font-size: 24px; text-transform: uppercase; letter-spacing: 1px; }
        
        .container { max-width: 900px; margin: 20px auto; padding: 15px; }
        
        .news-link { text-decoration: none; color: inherit; display: block; margin-bottom: 12px; }
        
        .news-item { 
            background: white; border-radius: 8px; padding: 20px; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.1); transition: 0.3s;
            border-left: 5px solid #003366;
        }
        .news-item:hover { transform: translateX(10px); background: #f8f9fa; border-left-color: #d90429; }
        
        .news-title { font-size: 19px; font-weight: bold; color: #003366; line-height: 1.4; }
        .news-meta { font-size: 13px; color: #65676b; margin-top: 10px; font-style: italic; }
        
        .footer { text-align: center; padding: 30px; color: #888; font-size: 13px; }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS - Siyasət & Diplomatiya 🇦🇿</h1></div>
    <div class="container">
        {% for x in data %}
        <a class="news-link" href="{{ x[2] }}" target="_blank">
            <div class="news-item">
                <div class="news-title">{{ x[1] }}</div>
                <div class="news-meta">Mənbə: Milli.az | Siyasət Bölməsi</div>
            </div>
        </a>
        {% else %}
            <div style="text-align:center; padding: 50px; background: white; border-radius: 8px;">
                <h3>Məlumatlar hazırlanır...</h3>
                <p>Bot Siyasət xəbərlərini gətirir. Zəhmət olmasa 30 saniyəyə yeniləyin.</p>
            </div>
        {% endfor %}
    </div>
    <div class="footer">© 2026 Əhmədzadə Diplomatik Xəbər Xidməti</div>
</body>
</html>
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS siyaset (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE)')
    conn.commit()
    return conn

def fetch_politics():
    """Ancaq Siyasət xəbərlərini çəkir."""
    while True:
        try:
            url = "https://news.milli.az/politics/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as response:
                # Şəkildəki xətanın düzəldilmiş forması (mötərizələr bağlanıb)
                soup = BeautifulSoup(response.read(), "html.parser")
                items = soup.select(".news-item, .p-news-item, .category-news-item")
                
                conn = get_db()
                cursor = conn.cursor()
                for item in items[:25]:
                    a_tag = item.find("a", href=True)
                    if a_tag:
                        link = a_tag["href"]
                        if not link.startswith("http"): link = "https://news.milli.az" + link
                        title = a_tag.get("title") or a_tag.text.strip()
                        if title and len(title) > 10:
                            cursor.execute("INSERT OR IGNORE INTO siyaset (bashliq, link) VALUES (?, ?)", (title, link))
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Bot xətası: {e}")
        time.sleep(1800)

@app.route('/')
def home():
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM siyaset ORDER BY id DESC LIMIT 30")
        data = cursor.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, data=data)
    except:
        return "Sistem yenilənir..."

if __name__ == '__main__':
    get_db().close()
    threading.Thread(target=fetch_politics, daemon=True).start()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
