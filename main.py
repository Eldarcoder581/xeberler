import urllib.request
import sqlite3
import threading
import time
import os
# ... digər importlar ...

# Bu sətiri tap və aşağıdakı ilə dəyiş:
# app = Flask(__name__, template_folder='xeberler')

# Yeni sətir (main.py ilə eyni qovluqda axtarması üçün):
app = Flask(__name__, template_folder='.') 
)
DB_PATH = 'bakunews.db'

# 1. BAZA QURULMASI
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS xeberler 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         bashliq TEXT, 
         link TEXT UNIQUE, 
         meqale TEXT, 
         img_url TEXT)''')
    conn.commit()
    conn.close()

# 2. BOT FUNKSİYASI (Şəkil və Məzmun çəkən)
def fetch_milli():
    targets = [
        {"url": "https://news.milli.az/society/", "name": "Milli.az"},
        {"url": "https://az.trend.az/", "name": "Trend News"},
        {"url": "https://caliber.az/az/", "name": "Caliber.az"},
        {"url": "https://think-tanks.az/", "name": "Think-Tanks"}
    ]
    
    while True:
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}

            for target in targets:
                try:
                    req = urllib.request.Request(target["url"], headers=headers)
                    with urllib.request.urlopen(req, timeout=30) as response:
                        soup = BeautifulSoup(response.read(), "html.parser")
                        links = soup.find_all("a", href=True)
                        
                        for item in links:
                            link = item["href"]
                            if not link.startswith("http"): continue
                            title = item.get("title") or item.text.strip()

                            if len(title) > 25:
                                # Xəbərin içinə girmək
                                content_text = "Məzmun yüklənir..."
                                img_url = ""
                                try:
                                    c_req = urllib.request.Request(link, headers=headers)
                                    with urllib.request.urlopen(c_req, timeout=10) as c_res:
                                        c_soup = BeautifulSoup(c_res.read(), "html.parser")
                                        # İlk bir neçə paraqrafı götürürük
                                        paragraphs = c_soup.find_all('p')
                                        content_text = " ".join([p.text.strip() for p in paragraphs[:3]])[:600]
                                        # Şəkli götürürük
                                        img_tag = c_soup.find('meta', property="og:image")
                                        if img_tag: img_url = img_tag['content']
                                except: pass

                                cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link, meqale, img_url) VALUES (?, ?, ?, ?)", 
                                               (f"[{target['name']}] {title}", link, content_text, img_url))
                except: continue
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Bot xətası: {e}")
        time.sleep(900)

# 3. ANA SƏHİFƏ (Slider + 40 Xəbər)
@app.route('/')
def home():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # Slider üçün son 10
        cursor.execute("SELECT id, bashliq, img_url FROM xeberler ORDER BY id DESC LIMIT 10")
        slider_news = cursor.fetchall()
        # Siyahı üçün son 40
        cursor.execute("SELECT id, bashliq, meqale, img_url FROM xeberler ORDER BY id DESC LIMIT 40")
        all_news = cursor.fetchall()
        conn.close()
        return render_template("index.html", slider_news=slider_news, all_news=all_news)
    except Exception as e:
        return f"Xəta: {e}"

# 4. DAXİLİ XƏBƏR SƏHİFƏSİ
@app.route('/xeber/<int:news_id>')
def news_detail(news_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT bashliq, meqale, img_url, link FROM xeberler WHERE id = ?", (news_id,))
    news = cursor.fetchone()
    conn.close()
    if news:
        return f"""
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body {{ font-family: sans-serif; background: #0b0e14; color: white; padding: 20px; line-height: 1.6; }}
                    .box {{ max-width: 800px; margin: auto; background: #1c2128; padding: 20px; border-radius: 12px; }}
                    img {{ width: 100%; border-radius: 10px; margin: 20px 0; }}
                    .back {{ color: #58a6ff; text-decoration: none; display: block; margin-bottom: 15px; }}
                    h1 {{ font-size: 22px; color: #adbac7; }}
                </style>
            </head>
            <body>
                <div class="box">
                    <a href="/" class="back">← Ana səhifəyə qayıt</a>
                    <h1>{news[0]}</h1>
                    <img src="{news[2] or 'https://via.placeholder.com/600x400'}">
                    <p>{news[1]}</p>
                    <hr>
                    <p>Davamını oxu: <a href="{news[3]}" style="color:#238636" target="_blank">Orijinal sayta keç</a></p>
                </div>
            </body>
        </html>
        """
    return "Xəbər tapılmadı", 404

# BAŞLATMA
init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
