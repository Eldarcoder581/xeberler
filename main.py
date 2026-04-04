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
    /* Container-i grid sisteminə salırıq */
.container { 
    display: grid; 
    grid-template-columns: repeat(3, 1fr); /* Yan-yana 3 dənə */
    gap: 20px; 
    padding: 20px; 
    max-width: 1200px; 
    margin: 0 auto; 
}

/* Xəbər qutusunun ölçülərini sabitləyirik */
.news-item { 
    background: white; 
    border-radius: 8px; 
    padding: 20px; 
    border-left: 6px solid #002347; 
    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 150px; /* Qutuların boyu eyni olsun */
}

/* Telefonlar üçün (ekran kiçiləndə alt-alta düşsün) */
@media (max-width: 900px) {
    .container { grid-template-columns: repeat(2, 1fr); } /* Planşetdə 2-li */
}

@media (max-width: 600px) {
    .container { grid-template-columns: 1fr; } /* Telefonda 1-li */
}
        body { font-family: Arial, sans-serif; background: #0b0e14; color: #e1e1e1; text-align: center; margin: 0; padding: 0; }
        .header { background: #161b22; padding: 20px; border-bottom: 2px solid #58a6ff; }
        .container { padding: 10px; max-width: 600px; margin: auto; }
        .news-card { background: #1c2128; margin: 15px 0; padding: 20px; border-radius: 12px; border: 1px solid #30363d; box-shadow: 0 4px 6px rgba(0,0,0,0.3); }
        h3 { font-size: 18px; line-height: 1.4; color: #adbac7; margin-bottom: 15px; }
      .news-img { 
    width: 100%; 
    height: 180px; /* Qutunun içində şəklin hündürlüyü */
    object-fit: cover; /* Şəkli əzmir, sahəyə tam sığdırır */
    border-bottom: 1px solid #ddd; /* Şəkillə başlığı ayırmaq üçün nazik xətt */
}
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
           <img src="{{ x[3] if x[3] else 'https://via.placeholder.com/400x200' }}" class="news-img">
            {% for x in data %}
            <div class="news-card">
    <img src="{{ x[3] if x[3] else 'https://via.placeholder.com/400x200' }}" class="news-img">
    
    <div class="news-content">
        <a href="{{ x[2] }}" target="_blank" class="news-title">{{ x[1] }}</a>
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
                       url = "https://news.milli.az/politics/"
            headers = {'User-Agent': 'Mozilla/5.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as response:
                # 1. Screenshot_4-dəki mötərizə xətasını burada bağladıq:
                soup = BeautifulSoup(response.read(), "html.parser") 
                
                items = soup.select(".news-item, .p-news-item, .category-news-item")
                
                conn = get_db()
                cursor = conn.cursor()
                for item in items[:30]:
                    a_tag = item.find("a", href=True)
                    
                    # 2. Screenshot_7-dəki boşluq xətasını burada düzəltdik:
                    img_tag = item.find("img")
                    img_url = ""
                    if img_tag:
                        img_url = img_tag.get("src") or img_tag.get("data-src") or ""

                    if a_tag:
                        link = a_tag["href"]
                        if not link.startswith("http"): link = "https://news.milli.az" + link
                        title = a_tag.get("title") or a_tag.text.strip()
                        cursor.execute("INSERT OR IGNORE INTO siyaset (bashliq, link, img_url) VALUES (?, ?, ?)", (title, link, img_url))
                conn.commit()
                conn.close()
        except Exception as e:
            print(f"Xeta bas verdi: {e}")
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
