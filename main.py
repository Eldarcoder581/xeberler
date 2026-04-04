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
   .container { 
    display: grid; 
    grid-template-columns: repeat(4, 1fr); /* 3-ü 4 ilə əvəz et */
    gap: 15px; 
}
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
            # 1. Milli.az-a daxil oluruq
            url = "https://news.milli.az/society/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                
                # 2. Saytdakı xəbər bloklarını tapırıq (limit yoxdur, hamısını götürürük)
                items = soup.select(".category-news-item, .news-item, .p-news-item, .news-item-title")
                
                if not items:
                    items = soup.find_all("a", href=True)

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                new_count = 0
                # 3. İLK 100 XƏBƏRİ BAZAYA VURURUQ (Sayt dərhal dolsun deyə)
                for item in items[:100]:
                    try:
                        a_tag = item if item.name == "a" else item.find("a", href=True)
                        if a_tag:
                            link = a_tag["href"]
                            if not link.startswith("http"):
                                link = "https://news.milli.az" + link
                            
                            title = a_tag.get("title") or a_tag.text.strip()
                            
                            img_tag = item.find("img")
                            img_url = ""
                            if img_tag:
                                img_url = img_tag.get("src") or img_tag.get("data-src") or ""

                            if title and len(title) > 10:
                                # INSERT OR IGNORE sayəsində:
                                # Əgər baza boşdursa, 100-nü də bura yazacaq.
                                # Əgər baza doludursa, köhnələri keçib ancaq yeniləri əlavə edəcək.
                                cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link, img_url) VALUES (?, ?, ?)", (title, link, img_url))
                                if cursor.rowcount > 0:
                                    new_count += 1
                    except:
                        continue
                
                conn.commit()
                conn.close()
                
                if new_count > 0:
                    print(f"Bot: {new_count} xəbər uğurla işlənildi. Sayt yeniləndi.")
                else:
                    print("Bot: Yeni xəbər tapılmadı (Baza artıq doludur).")

        except Exception as e:
            print(f"Bot xətası: {e}")
        
        # 4. 15 dəqiqə (900 saniyə) gözləyirik və dövrə başa çatır
        time.sleep(900)

@app.route('/')
def home():
    try:  # BAX BU SƏTİRİ ƏLAVƏ ETDİK (Səndə yox idi)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Yeni xəbərləri yuxarıda göstərmək üçün DESC istifadə edirik
        cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 100")
        
        data = cursor.fetchall()
        conn.close()
        
        return render_template_string(HTML_TEMPLATE, data=data)
        
    except Exception as e: # Bura "Exception as e" əlavə etmək daha yaxşıdır
        print(f"Xəta: {e}")
        return "Sistem hazırlanır..."
# Başlatma
init_db()
threading.Thread(target=fetch_milli, daemon=True).start()

if __name__ == '__main__':
    # Railway üçün port ayarı
    p = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=p)
