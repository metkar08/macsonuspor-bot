import requests
import time
import schedule
import os
from datetime import datetime, timezone, timedelta

# Render'ı uyanık tutacak web sunucusu modülü
from keep_alive import keep_alive

# --- TÜRKİYE SAAT DİLİMİ (UTC+3) ---
TR_TZ = timezone(timedelta(hours=3))

# --- API ANAHTARLARI ---
FOOTBALL_API_KEY = os.environ.get('FOOTBALL_API_KEY')
ZERNIO_API_KEY = os.environ.get('ZERNIO_API_KEY')
ZERNIO_API_URL = os.environ.get('ZERNIO_API_URL', 'https://api.zernio.com/v1/posts') 

# --- API SPORTS AYARLARI ---
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-key': FOOTBALL_API_KEY, # API-Sports anahtarın buraya gelecek
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# --- HAFIZA ---
last_scores = {}
processed_matches = set()

# --- TAKIM ETİKETLERİ ---
TEAM_TAGS = {
    "Fenerbahçe": "@Fenerbahce", "Galatasaray": "@GalatasaraySK", "Beşiktaş": "@Besiktas", "Trabzonspor": "@Trabzonspor",
    "Konyaspor": "@Konyaspor", "Samsunspor": "@Samsunspor", "Göztepe": "@Goztepe", "Alanyaspor": "@Alanyaspor",
    "Antalyaspor": "@Antalyaspor", "Başakşehir": "@Basaksehir_FK", "Adana Demirspor": "@AdanaDemirspor",
    "Real Madrid": "@realmadrid", "Barcelona": "@FCBarcelona", "Manchester City": "@ManCity", "Liverpool": "@LFC",
    "Bayern Munich": "@FCBayern", "Borussia Dortmund": "@BVB", "Paris Saint Germain": "@PSG_inside", "Inter": "@Inter"
}

def get_team_tag(team_name):
    for name, tag in TEAM_TAGS.items():
        if name in team_name:
            return tag
    return None

def send_tweet(text):
    saat_log = datetime.now(TR_TZ).strftime('%H:%M:%S')
    print(f"[{saat_log}] Zernio üzerinden yayınlama denemesi...", flush=True)
    try:
        headers = {
            "Authorization": f"Bearer {ZERNIO_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "content": text,
            "publishNow": True,
            "platforms": [{"platform": "twitter", "accountId": "69ef66bb985e734bf3c0b515"}]
        }
        response = requests.post(ZERNIO_API_URL, json=payload, headers=headers)
        if response.status_code in [200, 201]:
            print(f"[{saat_log}] ZERNIO BAŞARILI! 🎉", flush=True)
        else:
            print(f"[{saat_log}] ZERNIO HATA: {response.status_code}", flush=True)
    except Exception as e:
        print(f"[{saat_log}] Bağlantı hatası: {e}", flush=True)

def check_matches():
    try:
        url = f"{BASE_URL}/fixtures/live"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"API hatası: {response.status_code}", flush=True)
            return
        
        matches = response.json().get('response', [])
        saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
        print(f"[{saat_simdi}] API'den {len(matches)} canlı maç geldi.", flush=True)
        
        for match in matches:
            home = match['teams']['home']['name']
            away = match['teams']['away']['name']
            
            # Lig ID'sini sildik, sadece takımlarımıza bakıyoruz
            home_tag = get_team_tag(home)
            away_tag = get_team_tag(away)

            if home_tag or away_tag:
                fixture_id = match['fixture']['id']
                score_home = match['goals']['home'] or 0
                score_away = match['goals']['away'] or 0
                current_score = f"{score_home}-{score_away}"
                status = match['fixture']['status']['short']
                minute = match['fixture']['status']['elapsed'] or 0

                # Gol tespiti
                prev_score = last_scores.get(fixture_id)
                if prev_score and prev_score != current_score and status not in ['FT', 'AET', 'PEN']:
                    goal_scorer = "Bilinmiyor"
                    events = match.get('events', [])
                    for event in reversed(events):
                        if event['type'] == 'Goal':
                            goal_scorer = event['player']['name']
                            break
                    tweet = f"⚽ {minute}' GOOOL! {home} {current_score} {away} ({goal_scorer})\n#CanlıSkor {home_tag or ''} {away_tag or ''}"
                    send_tweet(tweet)

                # Maç sonu
                if status == 'FT' and fixture_id not in processed_matches:
                    tweet = f"🏁 MAÇ SONU: {home} {score_home}-{score_away} {away}\n#MaçSonu {home_tag or ''} {away_tag or ''}"
                    send_tweet(tweet)
                    processed_matches.add(fixture_id)

                last_scores[fixture_id] = current_score

    except Exception as e:
        print(f"Genel hata: {e}", flush=True)

schedule.every(90).seconds.do(check_matches)

if __name__ == "__main__":
    print("Sistem başlatıldı (Geniş tarama aktif)...", flush=True)
    keep_alive()
    while True:
        schedule.run_pending()
        time.sleep(1)
