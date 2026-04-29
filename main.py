import requests
import time
import schedule
import os
from datetime import datetime, timezone, timedelta
from keep_alive import keep_alive

# --- AYARLAR ---
TR_TZ = timezone(timedelta(hours=3))
ZERNIO_API_KEY = os.environ.get('ZERNIO_API_KEY')
FOOTBALL_DATA_KEY = os.environ.get('FOOTBALL_DATA_KEY')
ZERNIO_API_URL = os.environ.get('ZERNIO_API_URL', 'https://api.zernio.com/v1/posts')
TWITTER_ACCOUNT_ID = "69ef66bb985e734bf3c0b515"

# --- HAFIZA ---
last_scores = {}

# --- TAKIM LİSTESİ ---
TEAM_TAGS = {
    "Fenerbahce": "@Fenerbahce", 
    "Galatasaray": "@GalatasaraySK", 
    "Besiktas": "@Besiktas", 
    "Trabzonspor": "@Trabzonspor",
    "Samsunspor": "@Samsunspor", 
    "Goztepe": "@Goztepe",
    "Farul": "#TestGol",
    "Craiova": "#TestGol"
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
        url = "https://api.football-data.org/v4/matches"
        headers = {'X-Auth-Token': FOOTBALL_DATA_KEY}
        params = {'status': 'LIVE'}
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code != 200:
            print(f"[{saat_simdi}] API Hatası! Kod: {response.status_code}", flush=True)
            return

        data = response.json()
        matches = data.get('matches', [])
        
        found_tracked = False
        for match in matches:
            home_team = match['homeTeam']['name']
            away_team = match['awayTeam']['name']
            match_id = str(match['id'])
            
            h_score = match['score']['fullTime']['home']
            a_score = match['score']['fullTime']['away']
            current_score = f"{h_score}-{a_score}"
            
            h_tag = next((tag for name, tag in TEAM_TAGS.items() if name.lower() in home_team.lower()), None)
            a_tag = next((tag for name, tag in TEAM_TAGS.items() if name.lower() in away_team.lower()), None)

            if h_tag or a_tag:
                found_tracked = True
                print(f"[{saat_simdi}] Takipte: {home_team} {current_score} {away_team}", flush=True)

                if match_id in last_scores and last_scores[match_id] != current_score:
                    print(f"⚽ GOL TESPİT EDİLDİ!", flush=True)
                    tweet = f"⚽ GOOOL! {home_team} {current_score} {away_team}\n#CanlıSkor {h_tag or ''} {a_tag or ''}"
                    send_tweet(tweet)
                
                last_scores[match_id] = current_score

        if not found_tracked:
            print(f"[{saat_simdi}] {len(matches)} canlı maç taranıyor, bizimkiler sahada değil.", flush=True)

    except Exception as e:
        print(f"Hata: {e}", flush=True)

schedule.every(60).seconds.do(check_scores)

if __name__ == "__main__":
    print("--- MacSonuSpor V4 (Official API Engine) Aktif ---", flush=True)
    keep_alive()
    check_scores()
    while True:
        schedule.run_pending()
        time.sleep(1)
