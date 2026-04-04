import telebot
import requests
from bs4 import BeautifulSoup
import time

# Məlumatlarını bura yaz
TOKEN = "BOT_TOKENINI_BURA_YAZ"
MY_ID = "TELEGRAM_ID_NI_BURA_YAZ"

bot = telebot.TeleBot(TOKEN)

# Diplomatik xəbərləri tanıyan açar sözlər
DIPLOMATIC_KEYWORDS = [
    "diplomatik", "səfir", "xin", "prezident", "görüş", 
    "münasibət", "əməkdaşlıq", "bəyanat", "rəsmi", "səfər", 
    "beynəlxalq", "strateji", "müzakirə", "nazir"
]

def get_diplomatic_news():
    sources = {
        "OXU.AZ (Siyasət)": "https://oxu.az/politics",
        "REPORT.AZ (Siyasət)": "https://report.az/xarici-siyaset/",
        "AZƏRTAC": "https://azertag.az/xeber/siyaset"
    }
    
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    for name, url in sources.items():
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                links = soup.find_all('a')
                
                found_count = 0
                for link in links:
                    title = link.text.strip().lower()
                    href = link.get('href')
                    
                    # Yalnız diplomatik açar sözlər varsa xəbəri götür
                    if any(word in title for word in DIPLOMATIC_KEYWORDS) and len(title) > 30:
                        if href and not href.startswith('http'):
                            # Saytın ana linkini əlavə et
                            base_url = "https://oxu.az" if "oxu" in name.lower() else "https://report.az"
                            if not href.startswith('http'): href = base_url + href
                        
                        msg = (
                            f"🏛 *DİPLOMATİK XƏBƏR*\n"
                            f"───────────────────\n"
                            f"🌐 *Mənbə:* {name}\n\n"
                            f"📄 *Məzmun:* \n_{link.text.strip()}_\n\n"
                            f"🔗 [Rəsmi keçid]({href})\n"
                            f"───────────────────"
                        )
                        
                        bot.send_message(MY_ID, msg, parse_mode="Markdown")
                        found_count += 1
                        time.sleep(2)
                        
                        if found_count == 3: break # Hər saytdan ən vacib 3 xəbər
            
        except Exception as e:
            print(f"Xəta ({name}): {e}")

if __name__ == "__main__":
    get_diplomatic_news()
