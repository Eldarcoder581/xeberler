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
            # Society (Cəmiyyət) bölməsindən xəbərləri götürürük
            url = "https://news.milli.az/society/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=30) as response:
                soup = BeautifulSoup(response.read(), "html.parser")
                
                # Maksimum 100 xəbər blokunu tapırıq
                items = soup.find_all("div", class_="category-news-item", limit=100)
                
                # Əgər yuxarıdakı klass tapılmasa, alternativ xəbər başlıqlarını yoxlayırıq
                if not items:
                    items = soup.find_all("div", class_="news-item-title", limit=100)

                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                
                new_count = 0
                for item in items:
                    try:
                        # Link və başlığı tapırıq
                        a_tag = item.find("a", href=True)
                        # Şəkli tapırıq
                        img_tag = item.find("img")
                        
                        if a_tag:
                            title = a_tag.get("title") or a_tag.text.strip()
                            link = a_tag["href"]
                            if not link.startswith("http"):
                                link = "https://news.milli.az" + link
                            
                            # Şəkil linkini götürürük (src və ya data-src)
                            img_url = ""
                            if img_tag:
                                img_url = img_tag.get("src") or img_tag.get("data-src") or ""
                            
                            if title and len(title) > 10:
                                # INSERT OR IGNORE sayəsində ancaq yeni xəbərlər bazaya girir
                                # ID avtomatik artdığı üçün yeni xəbərlər böyük ID ilə yuxarıda qalacaq
                                cursor.execute("INSERT OR IGNORE INTO xeberler (bashliq, link, img_url) VALUES (?, ?, ?)", (title, link, img_url))
                                if cursor.rowcount > 0:
                                    new_count += 1
                    except:
                        continue
                
                conn.commit()
                conn.close()
                print(f"Bot: Yenilənmə tamamlandı. {new_count} yeni xəbər əlavə edildi.")

        except Exception as e:
            print(f"Bot xətası: {e}")
        
        # 15 dəqiqə (900 saniyə) gözləmə müddəti
        time.sleep(900)

@app.route('/')
def home():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # BAX BU SƏTİR ƏN VACİBİDİR: 
    # "ORDER BY id DESC" əmri yeni xəbərləri yuxarı qoyur, köhnələri aşağı itələyir.
    # "LIMIT 100" isə saytda cəmi 100 xəbər saxlayır.
    cursor.execute("SELECT * FROM xeberler ORDER BY id DESC LIMIT 100")
    
    data = cursor.fetchall()
    conn.close()
    
    # HTML-i render edirik
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
