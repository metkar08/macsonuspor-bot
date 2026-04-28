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

# --- TAKIM LİSTESİ ---
TEAM_TAGS = {
    "Fenerbahce": "@Fenerbahce", 
    "Galatasaray": "@GalatasaraySK", 
    "Besiktas": "@Besiktas", 
    "Trabzonspor": "@Trabzonspor",
    "Samsunspor": "@Samsunspor", 
    "Goztepe": "@Goztepe", 
    "Real Madrid": "@realmadrid", 
    "Manchester City": "@ManCity",
    "Farul Constanta": "#TestGol", 
    "Univ. Craiova": "#TestGol"
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

def check_scores():
    global last_scores
    saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
    
    try:
        # SofaScore Canlı Veri Akışı
        url = "https://api.sofascore.com/api/v1/sport/football/events/live"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            print(f"[{saat_simdi}] Skor Servisi Hatası! Kod: {response.status_code}", flush=True)
            return

        data = response.json()
        events = data.get('events', [])
        
        found_tracked = False
        for event in events:
            home_team = event['homeTeam']['name']
            away_team = event['awayTeam']['name']
            event_id = str(event['id'])
            
            home_score = event.get('homeScore', {}).get('current', 0)
            away_score = event.get('awayScore', {}).get('current', 0)
            score_str = f"{home_score}-{away_score}"
            
            # Takım Eşleşme Kontrolü (Küçük harfe çevirerek daha esnek arama yapıyoruz)
            h_tag = next((tag for name, tag in TEAM_TAGS.items() if name.lower() in home_team.lower()), None)
            a_tag = next((tag for name, tag in TEAM_TAGS.items() if name.lower() in away_team.lower()), None)

            if h_tag or a_tag:
                found_tracked = True
                print(f"[{saat_simdi}] Takipte: {home_team} {score_str} {away_team}", flush=True)

                if event_id in last_scores and last_scores[event_id] != score_str:
                    print(f"⚽ GOL! {home_team} {score_str} {away_team}", flush=True)
                    tweet = f"⚽ GOOOL! {home_team} {score_str} {away_team}\n#CanlıSkor {h_tag or ''} {a_tag or ''}"
                    send_tweet(tweet)
                
                last_scores[event_id] = score_str

        if not found_tracked:
            print(f"[{saat_simdi}] {len(events)} maç taranıyor, takımlarımız henüz sahada değil.", flush=True)

    except Exception as e:
        print(f"Hata oluştu: {e}", flush=True)

schedule.every(60).seconds.do(check_scores)

if __name__ == "__main__":
    print("--- MacSonuSpor V3 (SofaScore Engine) Aktif ---", flush=True)
    keep_alive()
    check_scores()
    while True:
        schedule.run_pending()
        time.sleep(1)
