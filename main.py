import urllib.request
import sqlite3
import threading
import time
import os
from bs4 import BeautifulSoup
from flask import Flask, render_template_string

app = Flask(__name__)

# Baza yolu (Sadələşdirilmiş)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'siyaset.db')

# --- SADƏ VƏ DİPLOMATİK DİZAYN (ALT-ALTA) ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="az">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BAKU NEWS - Siyasət</title>
    <style>
        body { font-family: 'Arial', sans-serif; background: #f4f4f4; color: #333; margin: 0; padding: 0; }
        .header { background: #002d5b; color: white; padding: 15px; text-align: center; border-bottom: 4px solid #cc0000; }
        .container { max-width: 800px; margin: 20px auto; padding: 10px; }
        
        /* TƏK SÜTUN - ALT-ALTA */
        .news-item { 
            background: white; border-bottom: 1px solid #ddd; padding: 15px; 
            margin-bottom: 10px; display: block; text-decoration: none; color: inherit;
            transition: 0.2s; border-radius: 5px;
        }
        .news-item:hover { background: #ebf2f9; }
        .news-title { font-size: 18px; font-weight: bold; margin-bottom: 5px; color: #002d5b; }
        .news-meta { font-size: 12px; color: #777; }
        
        .footer { text-align: center; padding: 20px; font-size: 12px; color: #888; }
    </style>
</head>
<body>
    <div class="header"><h1>BAKU NEWS - Siyasət & Diplomatiya 🇦🇿</h1></div>
    <div class="container">
        {% for x in data %}
        <a class="news-item" href="{{ x[2] }}" target="_blank">
            <div class="news-title">{{ x[1] }}</div>
            <div class="news-meta">Mənbə: Milli.az | Siyasət</div>
        </a>
        {% else %}
            <div style="text-align:center; padding: 50px;">Xəbərlər yenilənir... Zəhmət olmasa 1 dəqiqəyə yeniləyin.</div>
        {% endfor %}
    </div>
    <div class="footer">© 2026 Əhmədzadə News Service</div>
</body>
</html>
"""

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('CREATE TABLE IF NOT EXISTS siyaset (id INTEGER PRIMARY KEY AUTOINCREMENT, bashliq TEXT, link TEXT UNIQUE)')
    conn.commit()
    return conn

def fetch_siyaset():
    """Ancaq Siyasət xəbərlərini çəkir."""
    while True:
        try:
            # Milli.az-ın Siyasət bölməsi
            url = "https://news.milli.az/politics/"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/123.0.0.0'}
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=20) as response:
                soup = BeautifulSoup(response
