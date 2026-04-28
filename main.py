import requests
import time
import schedule
import os
from datetime import datetime, timezone, timedelta
from keep_alive import keep_alive

# --- AYARLAR ---
TR_TZ = timezone(timedelta(hours=3))
ZERNIO_API_KEY = os.environ.get('ZERNIO_API_KEY')
ZERNIO_API_URL = os.environ.get('ZERNIO_API_URL', 'https://api.zernio.com/v1/posts')
TWITTER_ACCOUNT_ID = "69ef66bb985e734bf3c0b515"

# --- HAFIZA ---
last_scores = {}
processed_matches = set()

# --- TAKIM LİSTESİ (Maçkolik ve Genel Eşleşme İçin) ---
TEAM_TAGS = {
    "Fenerbahçe": "@Fenerbahce", 
    "Galatasaray": "@GalatasaraySK", 
    "Beşiktaş": "@Besiktas", 
    "Trabzonspor": "@Trabzonspor",
    "Samsunspor": "@Samsunspor", 
    "Göztepe": "@Goztepe", 
    "Real Madrid": "@realmadrid", 
    "Manchester City": "@ManCity",
    "Farul Constanta": "#TestGol", 
    "Univ. Craiova": "#TestGol"
}

def send_tweet(text):
    saat_log = datetime.now(TR_TZ).strftime('%H:%M:%S')
    try:
        headers = {
            "Authorization": f"Bearer {ZERNIO_API_KEY}", 
            "Content-Type": "application/json"
        }
        payload = {
            "content": text,
            "publishNow": True,
            "platforms": [{"platform": "twitter", "accountId": TWITTER_ACCOUNT_ID}]
        }
        response = requests.post(ZERNIO_API_URL, json=payload, headers=headers, timeout=10)
        print(f"[{saat_log}] Zernio Durumu: {response.status_code}", flush=True)
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"Tweet gönderim hatası: {e}", flush=True)
        return False

def check_mackolik():
    global last_scores
    saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
    
    try:
        # Maçkolik'in bot korumasını aşmak için daha detaylı header
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Origin': 'https://www.mackolik.com',
            'Referer': 'https://www.mackolik.com/canli-sonuclar'
        }
        
        url = "https://www.mackolik.com/pb-v3/live"
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[{saat_simdi}] Maçkolik Hatası! Kod: {response.status_code}. Erişim engellenmiş olabilir.", flush=True)
            return

        data = response.json()
        matches = data.get('data', {}).get('m', [])
        
        found_tracked = False
        for m in matches:
            # m[0]: ID, m[2]: Ev, m[4]: Dep, m[10]: EvSkor, m[12]: DepSkor, m[16]: Dakika
            try:
                m_id = str(m[0])
                home_n = m[2]
                away_n = m[4]
                h_score = m[10]
                a_score = m[12]
                minute = m[16]
                score_str = f"{h_score}-{a_score}"

                # Takım eşleşme kontrolü
                h_tag = next((tag for name, tag in TEAM_TAGS.items() if name in home_n), None)
                a_tag = next((tag for name, tag in TEAM_TAGS.items() if name in away_n), None)

                if h_tag or a_tag:
                    found_tracked = True
                    # GOL TESPİTİ
                    if m_id in last_scores and last_scores[m_id] != score_str:
                        print(f"⚽ GOL HABERİ: {home_n} {score_str} {away_n}", flush=True)
                        tweet = f"⚽ {minute}' GOOOL! {home_n} {score_score} {away_n}\n#CanlıSkor {h_tag or ''} {a_tag or ''}"
                        send_tweet(tweet)
                    
                    last_scores[m_id] = score_str
            except:
                continue

        if not found_tracked:
            print(f"[{saat_simdi}] {len(matches)} canlı maç taranıyor, listemizde maç yok.", flush=True)

    except Exception as e:
        print(f"[{saat_simdi}] Scraper döngü hatası: {e}", flush=True)

# 60 saniyede bir kontrol et
schedule.every(60).seconds.do(check_mackolik)

if __name__ == "__main__":
    print("--- MacSonuSpor V2 (Mackolik Scraper) Aktif ---", flush=True)
    keep_alive() # Flask sunucusunu başlatır
    
    # İlk çalıştırma
    check_mackolik()
    
    while True:
        schedule.run_pending()
        time.sleep(1)
