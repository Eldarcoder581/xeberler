import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)
DB_PATH = 'bakunews.db'

# --- HTML DİZAYNI (Telefonda da gözəl görsənir) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS</title>
    <style>
    /* Ana konteyner: xəbərləri yan-yana düzən hissə */
.container { 
    display: grid; 
    /* repeat(3, 1fr) - yan-yana 3 bərabər sütun yaradır */
    grid-template-columns: repeat(3, 1fr); 
    gap: 20px; /* Qutular arasındakı məsafə */
    padding: 20px; 
    max-width: 1200px; 
    margin: 0 auto; 
}

/* Xəbər qutusu */
.news-card { 
    background: #1c2128; 
    border-radius: 12px; 
    border: 1px solid #30363d; 
    overflow: hidden; 
    display: flex;
    flex-direction: column;
}

/* Şəkil hissəsi */
.news-img { 
    width: 100%; 
    height: 200px; 
    object-fit: cover; /* Şəkli deformasiya etmədən qutuya sığdırır */
}

/* Telefonlar üçün (Ekran 900px-dən kiçik olsa 2-li, 600px-dən kiçik olsa 1-li sıra) */
@media (max-width: 900px) {
    .container { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
    .container { grid-template-columns: 1fr; }
}
        body { font-family: Arial, sans-serif; background: #0b0e14; color: #e1e1e1; text-align: center; margin: 0; padding: 0; }
        .header { background: #161b22; padding: 20px; border-bottom: 2px solid #58a6ff; }
        .container { padding: 10px; max-width: 600px; margin: auto; }
        .news-card { background: #1c2128; margin: 15px 0; padding: 20px; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h3 { font-size: 18px; line-height: 1.4; color: #adbac7; margin-bottom: 15px; }
        .btn { display: inline-block; background: #238636; color: white; padding: 10px 20px; border-radius: 6px; text-decoration: none; font-weight: bold; }
        .btn:hover { background: #2ea043; }
    </style>
</head>
<body>
<div class="header"><h1>BAKU NEWS 📰</h1></div>
    <div class="container">
        {% if not data %}
            <p style="margin-top:50px;">Xəbərlər gətirilir... <br> 15 saniyə sonra səhifəni yeniləyin (F5).</p>
            <script>setTimeout(function(){ location.reload(); }, 10000);</script>
        {% else %}
            {% for x in data %}
            <div class="news-card">
                <h3>{{ x[1] }}</h3>
                <a class="btn" href="{{ x[2] }}" target="_blank">Xəbəri Oxu</a>
            </div>
            {% endfor %}
        {% endif %}
    </div>
    {% endfor %}
</div>
    
</body>
</html>
"""

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS xeberler (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE)')
    conn.commit()
    conn.close()

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
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        # MÜTLƏQ "ORDER BY" OLMALIDIR
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 20")
        data = cursor.fetchall()
        conn.close()
        return render_template_string(HTML_TEMPLATE, data=data)
    except:
        return "Sistem hazırlanır..."

# Başlatma
init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    # Railway üçün port ayarı
    p = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=p)
