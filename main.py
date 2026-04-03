import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)
# Bazanı sıfırlamaq üçün adını dəyişirik
DB_PATH = 'baku_v5.db'

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS</title>
    <style>
        body { font-family: sans-serif; background: #0d1117; color: #c9d1d9; margin: 0; }
        .header { background: #161b22; padding: 20px; text-align: center; border-bottom: 3px solid #238636; }
        .container { 
            display: grid; 
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); 
            gap: 20px; padding: 20px; max-width: 1200px; margin: 0 auto; 
        }
        .news-card { background: #1c2128; border-radius: 12px; border: 1px solid #30363d; overflow: hidden; }
        .news-img { width: 100%; height: 200px; object-fit: cover; background: #30363d; }
        .news-content { padding: 15px; }
        .btn { display: block; text-align: center; background: #238636; color: white; padding: 10px; text-decoration: none; border-radius: 6px; }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS 📰</h1></div>
    <div class="container">
        {% if not data %}
            <p style="grid-column: 1/-1; text-align: center; margin-top: 50px;">
                Xəbərlər gətirilir... <br> Zəhmət olmasa 30 saniyə sonra səhifəni yeniləyin (F5).
            </p>
        {% else %}
            {% for x in data %}
            <div class="news-card">
                <img class="news-img" src="{{ x[3] if x[3] else 'https://via.placeholder.com/300x200?text=Baku+News' }}">
                <div class="news-content">
                    <h3 style="font-size:16px; height:50px; overflow:hidden;">{{ x[1] }}</h3>
                    <a class="btn" href="{{ x[2] }}" target="_blank">Oxu →</a>
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
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE, sekil TEXT)')
    conn.commit()
    conn.close()

def fetch_milli():
    while True:
        try:
            # Milli.az-ın əsas xəbər bölməsi
            url = "https://news.milli.az/society/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                # ƏN VACİB HİSSƏ: Milli.az-dakı xəbər bloklarını tapmaq
                # Milli.az-da xəbərlər adətən "p-news-item" və ya "news-item" daxilində olur
                items = soup.select(".news-item, .p-news-item")
                
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                for item in items[:21]: # 21 xəbər (7 sıra)
                    try:
                        # Link və Başlıq
                        link_tag = item.find("a", href=True)
                        if not link_tag: continue
                        
                        link = "https://news.milli.az" + link_tag["href"] if not link_tag["href"].startswith("http") else link_tag["href"]
                        title = link_tag.get("title") or link_tag.text.strip()
                        
                        # Şəkil tapmaq üçün bir neçə variantı yoxlayırıq
                        img_tag = item.find("img")
                        img_url = ""
                        if img_tag:
                            img_url = img_tag.get("data-src") or img_tag.get("src") or ""
                        
                        if title and len(title) > 5:
                            cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link, sekil) VALUES (?, ?, ?)", (title, link, img_url))
                    except: continue
                
                conn.commit()
                conn.close()
                print("Bot: Xəbərlər bazaya yazıldı.")
        except Exception as e:
            print(f"Bot xetasi: {e}")
        time.sleep(300)

@app.run
