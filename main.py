import requests
import time
import schedule
import os
from datetime import datetime

# Render'ı uyanık tutacak web sunucusu modülü
from keep_alive import keep_alive

# --- API ANAHTARLARI ---
FOOTBALL_API_KEY = os.environ.get('FOOTBALL_API_KEY')

# Zernio API Ayarları
ZERNIO_API_KEY = os.environ.get('ZERNIO_API_KEY') # Zernio'dan aldığın sk_... ile başlayan şifre
ZERNIO_API_URL = os.environ.get('ZERNIO_API_URL', 'https://api.zernio.com/v1/posts') 

# --- API SPORTS AYARLARI ---
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-key': FOOTBALL_API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# Ligler: TR Süper Lig (203), 1.Lig (204), Kupa (347), ŞL (2), AvL (3), PL (39), LaLiga (140), SerieA (135), Bundesliga (78), Ligue1 (61)
LEAGUES = [203, 204, 347, 2, 3, 39, 140, 135, 78, 61]

# --- HAFIZA ---
last_scores = {}
processed_matches = set()

# --- TAKIM ETİKETLERİ ---
TEAM_TAGS = {
    "Fenerbahçe": "@Fenerbahce", "Galatasaray": "@GalatasaraySK", "Beşiktaş": "@Besiktas", "Trabzonspor": "@Trabzonspor",
    "Başakşehir": "@Basaksehir_FK", "Adana Demirspor": "@AdanaDemirspor", "Alanyaspor": "@Alanyaspor", "Antalyaspor": "@Antalyaspor",
    "Kasımpaşa": "@KasimpasaSK", "Konyaspor": "@Konyaspor", "Samsunspor": "@Samsunspor", "Göztepe": "@Goztepe",
    "Rizespor": "@CRizesporAS", "Sivasspor": "@Sivasspor", "Kayserispor": "@KayserisporFK", "Gaziantep FK": "@GaziantepFK",
    "Real Madrid": "@realmadrid", "Barcelona": "@FCBarcelona", "Manchester City": "@ManCity", "Liverpool": "@LFC",
    "Bayern Munich": "@FCBayern", "Borussia Dortmund": "@BVB", "Paris Saint Germain": "@PSG_inside", "Inter": "@Inter"
}

def get_team_tag(team_name):
    for name, tag in TEAM_TAGS.items():
        if name in team_name:
            return tag
    return None

def generate_hashtag(home, away):
    mapping = {
        "Fenerbahçe": "FB", "Galatasaray": "GS", "Beşiktaş": "BJK", "Trabzonspor": "TS",
        "Manchester City": "MCI", "Liverpool": "LIV", "Real Madrid": "RMA", "Barcelona": "BAR"
    }
    home_short = mapping.get(home, home.replace(" ", ""))
    away_short = mapping.get(away, away.replace(" ", ""))
    return f"#{home_short}{away_short}"

def send_tweet(text):
    print(f"[{datetime.now()}] Zernio üzerinden Post gönderiliyor: {text[:50]}...", flush=True)
    try:
        if not ZERNIO_API_KEY:
            print(f"[{datetime.now()}] UYARI: ZERNIO_API_KEY Render'da tanımlı değil!", flush=True)
            return

        headers = {
            "Authorization": f"Bearer {ZERNIO_API_KEY}",
            "Content-Type": "application/json"
        }
        
        # Zernio'nun istediği kusursuz format: Taslağa atma, direkt yayınla!
        payload = {
            "content": text,
            "status": "published",  
            "platforms": [
                {
                    "platform": "twitter",
                    "accountId": "69ef66bb985e734bf3c0b515"
                }
            ]
        }
        
        response = requests.post(ZERNIO_API_URL, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"[{datetime.now()}] ZERNIO BAŞARILI: Mesaj hedefe ulaştı ve yayınlandı! 🎉", flush=True)
        else:
            print(f"[{datetime.now()}] ZERNIO HATA: {response.status_code} - {response.text}", flush=True)
            
    except Exception as e:
        print(f"[{datetime.now()}] ZERNIO BAĞLANTI HATASI: {e}", flush=True)

def check_matches():
    try:
        url = f"{BASE_URL}/fixtures/live"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"API hatası: {response.status_code} - {response.text}", flush=True)
            return
        
        matches = response.json()['response']
        print(f"[{datetime.now()}] {len(matches)} canlı maç bulundu.", flush=True)
        
        for match in matches:
            league_id = match['league']['id']
            if league_id not in LEAGUES:
                continue
                
            fixture_id = match['fixture']['id']
            home = match['teams']['home']['name']
            away = match['teams']['away']['name']
            score_home = match['goals']['home'] or 0
            score_away = match['goals']['away'] or 0
            status = match['fixture']['status']['short']
            minute = match['fixture']['status']['elapsed'] or 0
            current_score = f"{score_home}-{score_away}"

            hashtag = generate_hashtag(home, away)
            home_tag = get_team_tag(home)
            away_tag = get_team_tag(away)
            tags = " ".join(filter(None, [home_tag, away_tag]))

            # Gol tespiti
            prev_score = last_scores.get(fixture_id)
            if prev_score and prev_score != current_score and status not in ['FT', 'AET', 'PEN']:
                goal_scorer = "Bilinmiyor"
                events = match.get('events', [])
                for event in reversed(events):
                    if event['type'] == 'Goal':
                        goal_scorer = event['player']['name']
                        break
                tweet = f"⚽ {minute}' GOOOL! {home} {current_score} {away} ({goal_scorer})\n{hashtag} {tags}"
                send_tweet(tweet)

            # Maç sonu
            if status == 'FT' and fixture_id not in processed_matches:
                goller = []
                for event in match.get('events', []):
                    if event['type'] == 'Goal':
                        dak = event['time']['elapsed']
                        ekstra = event['time']['extra'] or 0
                        dak_str = f"{dak}+{ekstra}'" if ekstra else f"{dak}'"
                        goller.append(f"{event['player']['name']} {dak_str}")
                gol_text = "\nGoller: " + ", ".join(goller) if goller else ""
                tweet = f"🏁 MAÇ SONUUU!\n{home} {score_home}-{score_away} {away}{gol_text}\n{hashtag} {tags}"
                send_tweet(tweet)
                processed_matches.add(fixture_id)

            last_scores[fixture_id] = current_score

    except Exception as e:
        print(f"Genel hata: {e}", flush=True)

# Her 90 saniyede kontrol
schedule.every(90).seconds.do(check_matches)

if __name__ == "__main__":
    print("Sistem başlatılıyor...", flush=True)
    
    keep_alive()
    
    # Sistemin ayağa kalktığını göstermek için Zernio üzerinden ilk test mesajı
    su_an = datetime.now().strftime("%H:%M:%S")
    send_tweet(f"🤖 @macsonuspor bot sistemi Zernio altyapısı ile tam otomatik aktif edildi! [{su_an}] ⚽")
    
    print("Bot döngüye girdi, maçlar takip ediliyor...", flush=True)
    while True:
        schedule.run_pending()
        time.sleep(1)
