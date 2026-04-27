import requests
import time
import schedule
import os
from datetime import datetime

# Render'ı uyanık tutacak web sunucusu modülü
from keep_alive import keep_alive

# Gizli key'ler Render environment'tan
FOOTBALL_API_KEY = os.environ.get('FOOTBALL_API_KEY')
OPENTWEET_API_URL = os.environ.get('OPENTWEET_API_URL') # OpenTweet API Endpoint'in
OPENTWEET_API_KEY = os.environ.get('OPENTWEET_API_KEY') # OpenTweet için yetki anahtarın

# API-Sports ayarları
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-key': FOOTBALL_API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# Takip edilecek ligler (347 = Türkiye Kupası dahil)
LEAGUES = [203, 204, 347, 2, 3, 39, 140, 135, 78, 61]

# Hafıza
last_scores = {}
processed_matches = set()

# Türk takımları resmi etiketleri
TURK_TEAMS = {
    "Galatasaray": "@GalatasaraySK",
    "Fenerbahçe": "@Fenerbahce",
    "Beşiktaş": "@Besiktas",
    "Trabzonspor": "@Trabzonspor",
    "Başakşehir": "@Basaksehir_FK",
    "Adana Demirspor": "@AdanaDemirspor",
    "Alanyaspor": "@Alanyaspor",
    "Antalyaspor": "@Antalyaspor",
    "Kasımpaşa": "@KasimpasaSK",
    "Konyaspor": "@Konyaspor"
}

def get_turk_tag(team_name):
    for name, tag in TURK_TEAMS.items():
        if name in team_name:
            return tag
    return None

def generate_hashtag(home, away):
    mapping = {
        "Galatasaray": "GS", "Fenerbahçe": "FB", "Beşiktaş": "BJK", "Trabzonspor": "TS",
        "Başakşehir": "BAS", "Adana Demirspor": "ADS", "Manchester City": "MCI", "Liverpool": "LIV",
        "Real Madrid": "RMA", "Barcelona": "BAR", "Bayern München": "BAY", "Borussia Dortmund": "BVB"
    }
    home_short = mapping.get(home, "".join(w[0] for w in home.split()[:2]).upper())
    away_short = mapping.get(away, "".join(w[0] for w in away.split()[:2]).upper())
    return f"#{home_short}{away_short}"

def send_tweet(text):
    print(f"[{datetime.now()}] OpenTweet'e veri gönderiliyor: {text[:50]}...", flush=True)
    try:
        # Eğer henüz URL girilmediyse loga uyarı basıp geçsin, kod çökmesin
        if not OPENTWEET_API_URL:
            print(f"[{datetime.now()}] UYARI: OPENTWEET_API_URL tanımlı değil! Mesaj: {text}", flush=True)
            return

        headers = {
            "Authorization": f"Bearer {OPENTWEET_API_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "content": text
        }
        
        response = requests.post(OPENTWEET_API_URL, json=payload, headers=headers)
        
        if response.status_code in [200, 201]:
            print(f"[{datetime.now()}] OPENTWEET BAŞARILI: Sistem kabul etti.", flush=True)
        else:
            print(f"[{datetime.now()}] OPENTWEET HATA: {response.status_code} - {response.text}", flush=True)
            
    except Exception as e:
        print(f"[{datetime.now()}] OPENTWEET BAĞLANTI HATASI: {e}", flush=True)

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
            home_tag = get_turk_tag(home)
            away_tag = get_turk_tag(away)
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
                tweet = f"⚽ {minute}' GOOOL! {home} {current_score} {away} ({goal_scorer})\n{hashtag} #TrendyolSüperLig {tags}"
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
                tweet = f"🏁 MAÇ SONUUU!\n{home} {score_home}-{score_away} {away}{gol_text}\n{hashtag} #TrendyolSüperLig {tags}"
                send_tweet(tweet)
                processed_matches.add(fixture_id)

            last_scores[fixture_id] = current_score

    except Exception as e:
        print(f"Genel hata: {e}", flush=True)

# Her 45 saniyede kontrol
schedule.every(45).seconds.do(check_matches)

if __name__ == "__main__":
    print("Sistem başlatılıyor...", flush=True)
    
    # 1. ÖNCE WEB SUNUCUSUNU BAŞLAT
    keep_alive()
    
    # 2. BAŞLANGIÇ TEST MESAJI
    su_an = datetime.now().strftime("%H:%M:%S")
    send_tweet(f"🤖 @macsonuspor bot sistemi OpenTweet'e bağlandı! [{su_an}] ⚽ Canlı skor takibi devrede.")
    
    print("Bot döngüye girdi, maçlar takip ediliyor...", flush=True)
    # 3. 45 SANİYELİK KONTROL DÖNGÜSÜ
    while True:
        schedule.run_pending()
        time.sleep(1)
