import urllib.request
import sqlite3
import threading
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)

# --- DİZAYN (SADƏ VƏ SÜRATLİ) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>BAKU NEWS - MILLI.AZ</title>
    <style>
        body { font-family: 'Segoe UI', Tahoma, sans-serif; background: #f0f2f5; margin: 0; padding: 0; }
        .top-bar { background: #cc0000; color: white; padding: 20px; text-align: center; font-size: 28px; font-weight: bold; box-shadow: 0 2px 10px rgba(0,0,0,0.2); }
        .container { max-width: 800px; margin: 30px auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }
        .news-item { border-bottom: 1px solid #eee; padding: 20px 0; display: flex; align-items: center; }
        .news-item:last-child { border-bottom: none; }
        .news-link { color: #1a1a1a; text-decoration: none; font-size: 19px; font-weight: 600; line-height: 1.4; }
        .news-link:hover { color: #cc0000; }
        .bullet { width: 10px; height: 10px; background: #cc0000; border-radius: 50%; margin-right: 15px; flex-shrink: 0; }
    </style>
</head>
<body>
    <div class="top-bar">BAKU NEWS</div>
    <div class="container">
        {% for x in data %}
        <div class="news-item">
            <div class="bullet"></div>
            <a href="{{ x[2] }}" target="_blank" class="news-link">{{ x[1] }}</a>
        </div>
        {% endfor %}
    </div>
</body>
</html>
"""

def init_db():
    conn = sqlite3.connect('bakunews.db')
    conn.execute('DROP TABLE IF EXISTS xeberler')
    conn.execute('CREATE TABLE xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE, shekil TEXT)')
    conn.commit()
    conn.close()

def fetch_milli():
    # Windows 7 üçün ən uyğun qorumasız 'http' keçidi
    url = "http://news.milli.az/society/" 
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'}
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            soup = BeautifulSoup(response.read(), "html.parser")
            # Bütün əsas xəbər başlıqlarını tapırıq
            items = soup.find_all("div", class_="news-item-title", limit=20)
            
            conn = sqlite3.connect('bakunews.db')
            cursor = conn.cursor()
            count = 0
            for item in items:
                try:
                    title = item.find("a").text.strip()
                    link = "https://news.milli.az" + item.find("a")["href"]
                    
                    cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link, shekil) VALUES (?, ?, ?)", (title, link, ""))
                    if cursor.rowcount > 0:
                        count += 1
                except: continue
            conn.commit()
            conn.close()
            print(f"Bot: {count} yeni xeber Milli.az-dan çekildi!")
    except Exception as e:
        print(f"Xeta bas verdi: {e}")

@app.route('/')
def home():
    conn = sqlite3.connect('bakunews.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM xeberler ORDER BY id DESC")
    data = cursor.fetchall()
    conn.close()
    return render_template_string(HTML_TEMPLATE, data=data)

if __name__ == '__main__':
    init_db()
    # Proqram açılan kimi xəbərləri çəkməyə başla
    threading.Thread(target=fetch_milli, daemon=True).start()
    print("Server: http://127.0.0.1:5000")
    app.run(port=5000)