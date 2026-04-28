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

# --- MACKOLIK AYARLARI ---
# Maçkolik'in canlı verileri çektiği gizli uç noktalardan biri
MACKOLIK_LIVE_URL = "https://www.mackolik.com/pb-v3/live" 

# --- HAFIZA ---
last_scores = {}
processed_matches = set()

# --- TAKIM LİSTESİ ---
TEAM_TAGS = {
    "Farul Constanta": "#TestGol", "Universitatea Craiova": "#TestGol"
    "Fenerbahçe": "@Fenerbahce", "Galatasaray": "@GalatasaraySK", "Beşiktaş": "@Besiktas", "Trabzonspor": "@Trabzonspor",
    "Samsunspor": "@Samsunspor", "Göztepe": "@Goztepe", "Real Madrid": "@realmadrid", "Manchester City": "@ManCity"
}

def send_tweet(text):
    saat_log = datetime.now(TR_TZ).strftime('%H:%M:%S')
    try:
        headers = {"Authorization": f"Bearer {ZERNIO_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "content": text,
            "publishNow": True,
            "platforms": [{"platform": "twitter", "accountId": TWITTER_ACCOUNT_ID}]
        }
        response = requests.post(ZERNIO_API_URL, json=payload, headers=headers, timeout=10)
        print(f"[{saat_log}] Tweet Durumu: {response.status_code}", flush=True)
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"Tweet hatası: {e}", flush=True)
        return False

def check_mackolik():
    global last_scores
    saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
    
    try:
        # Tarayıcı gibi görünmek için User-Agent ekliyoruz
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(MACKOLIK_LIVE_URL, headers=headers, timeout=10)
        
        if response.status_code != 200:
            print(f"[{saat_simdi}] Maçkolik'e ulaşılamadı. Kod: {response.status_code}", flush=True)
            return

        data = response.json()
        # Maçkolik JSON yapısı: data -> m (maçlar listesi)
        matches = data.get('data', {}).get('m', [])
        
        found_any = False
        for m in matches:
            # m[2]: Ev Sahibi, m[4]: Deplasman, m[10]: Ev Skor, m[12]: Dep Skor, m[16]: Dakika, m[0]: Maç ID
            match_id = str(m[0])
            home_name = m[2]
            away_name = m[4]
            home_score = m[10]
            away_score = m[12]
            minute = m[16]
            current_score = f"{home_score}-{away_score}"

            # Takip ettiğimiz takımlardan biri mi?
            home_tag = next((tag for name, tag in TEAM_TAGS.items() if name in home_name), None)
            away_tag = next((tag for name, tag in TEAM_TAGS.items() if name in away_name), None)

            if home_tag or away_tag:
                found_any = True
                print(f"[{saat_simdi}] Takipte: {home_name} {current_score} {away_name} ({minute}')", flush=True)

                # GOL KONTROLÜ
                if match_id in last_scores and last_scores[match_id] != current_score:
                    tweet = f"⚽ {minute}' GOOOL! {home_name} {current_score} {away_name}\n#CanlıSkor {home_tag or ''} {away_tag or ''}"
                    send_tweet(tweet)
                
                last_scores[match_id] = current_score

        if not found_any:
            print(f"[{saat_simdi}] {len(matches)} maç var ama bizimkiler sahada değil.", flush=True)

    except Exception as e:
        print(f"Scraper hatası: {e}", flush=True)

# 60 saniyede bir kontrol (API sınırı olmadığı için daha sık bakabiliriz)
schedule.every(60).seconds.do(check_mackolik)

if __name__ == "__main__":
    print("--- MacSonuSpor V2 (Mackolik Scraper) Başlatıldı ---", flush=True)
    keep_alive()
    check_mackolik()
    while True:
        schedule.run_pending()
        time.sleep(1)
