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
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS</title>
    <style>
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #0b0e14; color: #e1e1e1; margin: 0; padding: 0; }
        .header { background: #161b22; padding: 20px; border-bottom: 2px solid #58a6ff; text-align: center; position: sticky; top: 0; z-index: 100; }
        
        /* Grid Sistemi: Yan-yana 4 dənə */
        .container { 
            display: grid; 
            grid-template-columns: repeat(4, 1fr); 
            gap: 20px; 
            padding: 25px; 
            max-width: 1400px; 
            margin: auto; 
        }

        .news-card { 
            background: #1c2128; 
            padding: 20px; 
            border-radius: 12px; 
            border: 1px solid #30363d; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.3); 
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: transform 0.2s;
        }

        .news-card:hover { transform: translateY(-5px); border-color: #58a6ff; }

        h3 { font-size: 16px; line-height: 1.4; color: #adbac7; margin: 0 0 15px 0; height: 65px; overflow: hidden; }
        
        .btn { 
            display: block; 
            background: #238636; 
            color: white; 
            padding: 10px; 
            border-radius: 6px; 
            text-decoration: none; 
            font-weight: bold; 
            text-align: center;
            font-size: 14px;
        }

        /* Ekran tənzimləmələri */
        @media (max-width: 1100px) { .container { grid-template-columns: repeat(3, 1fr); } }
        @media (max-width: 850px) { .container { grid-template-columns: repeat(2, 1fr); } }
        @media (max-width: 550px) { 
            .container { grid-template-columns: 1fr; padding: 15px; } 
            .header h1 { font-size: 20px; }
        }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS 📰</h1></div>
    <div class="container">
        {% if not data %}
            <div style="grid-column: 1/-1; text-align: center; margin-top: 50px;">
                <p>Xəbərlər gətirilir... Zəhmət olmasa 10 saniyə sonra yeniləyin.</p>
            </div>
        {% else %}
            {% for x in data %}
            <div class="news-card">
                <h3>{{ x[1] }}</h3>
                <a class="btn" href="{{ x[2] }}" target="_blank">Xəbəri Oxu</a>
            </div>
            {% endfor %}
        {% endif %}
    </div>
</body>
</html>
"""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Bazanı təmizləyib yenidən yaradırıq
    cursor.execute("DROP TABLE IF EXISTS xeberler")
    cursor.execute('''CREATE TABLE IF NOT EXISTS xeberler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         bashliq TEXT, 
         link TEXT UNIQUE, 
         img_url TEXT)''')
    conn.commit()
    conn.close()
    print("Baza sıfırlandı.")

def fetch_milli():
    while True:
        try:
            # Milli.az-ın Cəmiyyət bölməsinə daxil oluruq (burada xəbər daha çoxdur)
            url = "https://news.milli.az/society/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                
                # BÜTÜN xəbər linklərini və başlıqlarını tutmaq üçün geniş süzgəc:
                # Bu həm şəkilli blokları, həm də sadə siyahıları tapır
                items = soup.find_all("a", href=True)

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                new_count = 0
                for item in items:
                    link = item["href"]
                    # Yalnız xəbər linkləri olduğunu yoxlayırıq (rəqəmlə bitən linklər xəbərdir)
                    if "/society/" in link or link.split('/')[-1].isdigit():
                        if not link.startswith("http"):
                            link = "https://news.milli.az" + link
                        
                        # Başlığı götürürük
                        title = item.get("title") or item.text.strip()
                        
                        # Əgər başlıq çox qısadırsa və ya boşdursa, keçirik
                        if len(title) < 15:
                            continue
                            
                        # Bazaya yazırıq
                        cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link) VALUES (?, ?)", (title, link))
                        if cursor.rowcount > 0:
                            new_count += 1
                            
                    # 100 xəbərə çatanda dayanırıq
                    if new_count >= 100:
                        break
                
                conn.commit()
                conn.close()
                print(f"Bot: Yenilənmə bitdi. {new_count} yeni xəbər bazaya əlavə edildi.")

        except Exception as e:
            print(f"Bot xətası: {e}")
        
        # 15 dəqiqə gözləyirik
        time.sleep(900)

@app.route('/')
def home():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 100")
        data = cursor.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, data=data)
    except Exception as e:
        return f"Xəta: {e}"

# Başlatma
init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
