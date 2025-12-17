import requests
import time
import schedule
import os
from datetime import datetime

# Tweepy v5+ için
import tweepy

# Gizli key'ler
FOOTBALL_API_KEY = os.environ.get('FOOTBALL_API_KEY')
BEARER_TOKEN = os.environ.get('BEARER_TOKEN')
CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('ACCESS_TOKEN_SECRET')

# API-Sports
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-key': FOOTBALL_API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

LEAGUES = [203, 204, 2, 3, 39, 140, 135, 78, 61]

last_scores = {}
processed_matches = set()

TURK_TEAMS = {
    "Galatasaray": "@GalatasaraySK",
    "Fenerbahçe": "@Fenerbahce",
    "Beşiktaş": "@Besiktas",
    "Trabzonspor": "@Trabzonspor",
    "Başakşehir": "@Basaksehir_FK",
    "Adana Demirspor": "@AdanaDemirspor",
    # İstersen ekle
}

def get_turk_tag(team_name):
    for name, tag in TURK_TEAMS.items():
        if name in team_name:
            return tag
    return None

def generate_hashtag(home, away):
    short_home = "".join(word[0] for word in home.split()[:2]).upper()
    short_away = "".join(word[0] for word in away.split()[:2]).upper()
    return f"#{short_home}{short_away}"

def send_tweet(text):
    try:
        client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=CONSUMER_KEY,
            consumer_secret=CONSUMER_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
        response = client.create_tweet(text=text)
        print(f"[{datetime.now()}] TWEET ATILDI: {text}")
    except Exception as e:
        print(f"[{datetime.now()}] Tweet hatası: {e}")

def check_matches():
    try:
        url = f"{BASE_URL}/fixtures/live"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"API hatası: {response.status_code} - {response.text}")
            return

        matches = response.json()['response']
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
        print(f"Hata: {e}")

schedule.every(45).seconds.do(check_matches)

# Test tweet (çalıştığını görmek için)
send_tweet("🤖 @macsonuspor bot aktif! ⚽ Gol ve maç sonu bildirimleri geliyor... #MaçSonu")

if __name__ == "__main__":
    print("Bot başlatıldı, maçlar takip ediliyor...")
    while True:
        schedule.run_pending()
        time.sleep(1)
# Ekstra test tweet (deploy sonrası bir kere atsın, sonra silersin)
send_tweet("🤖 Bot yeniden aktif! Test tweet – canlı gol bildirimleri geliyor ⚽ #Test #MaçSonu")
# Zorla test tweet (her deploy’da bir kere atsın)
import datetime
if datetime.datetime.now().hour % 2 == 0:  # Her çift saatte bir test atsın, sonra silersin
    send_tweet("🤖 Bot çalışıyor lan! Test tweet – gol bildirimleri aktif ⚽ #MaçSonuTest")
import requests
import time
import schedule
import os
from datetime import datetime

# Tweepy (4.16.0 ile uyumlu)
import tweepy

# Gizli key'ler Render environment'tan
FOOTBALL_API_KEY = os.environ.get('FOOTBALL_API_KEY')
BEARER_TOKEN = os.environ.get('BEARER_TOKEN')
CONSUMER_KEY = os.environ.get('CONSUMER_KEY')
CONSUMER_SECRET = os.environ.get('CONSUMER_SECRET')
ACCESS_TOKEN = os.environ.get('ACCESS_TOKEN')
ACCESS_TOKEN_SECRET = os.environ.get('ACCESS_TOKEN_SECRET')

# API-Sports ayarları
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-key': FOOTBALL_API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# Takip edilecek ligler
LEAGUES = [203, 204, 2, 3, 39, 140, 135, 78, 61]  # Süper Lig, 1.Lig, ŞL, AvL, PL, LaLiga, SerieA, Bundesliga, Ligue1

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
    "Konyaspor": "@Konyaspor",
    # İstersen daha ekle
}

def get_turk_tag(team_name):
    for name, tag in TURK_TEAMS.items():
        if name in team_name:
            return tag
    return None

def generate_hashtag(home, away):
    # Daha iyi hashtag için manuel mapping
    mapping = {
        "Galatasaray": "GS", "Fenerbahçe": "FB", "Beşiktaş": "BJK", "Trabzonspor": "TS",
        "Başakşehir": "BAS", "Adana Demirspor": "ADS", "Manchester City": "MCI", "Liverpool": "LIV",
        "Real Madrid": "RMA", "Barcelona": "BAR", "Bayern München": "BAY", "Borussia Dortmund": "BVB"
    }
    home_short = mapping.get(home, "".join(w[0] for w in home.split()[:2]).upper())
    away_short = mapping.get(away, "".join(w[0] for w in away.split()[:2]).upper())
    return f"#{home_short}{away_short}"

def send_tweet(text):
    print(f"[{datetime.now()}] Tweet denemesi yapılıyor: {text[:50]}...")  # Log için
    try:
        client = tweepy.Client(
            bearer_token=BEARER_TOKEN,
            consumer_key=CONSUMER_KEY,
            consumer_secret=CONSUMER_SECRET,
            access_token=ACCESS_TOKEN,
            access_token_secret=ACCESS_TOKEN_SECRET,
            wait_on_rate_limit=True
        )
        response = client.create_tweet(text=text)
        print(f"[{datetime.now()}] TWEET BAŞARILI ATILDI: {text}")
        return response
    except Exception as e:
        print(f"[{datetime.now()}] TWEET HATA DETAY: {type(e).__name__}: {e}")

def check_matches():
    try:
        url = f"{BASE_URL}/fixtures/live"
        response = requests.get(url, headers=HEADERS)
        if response.status_code != 200:
            print(f"API hatası: {response.status_code} - {response.text}")
            return
        matches = response.json()['response']
        print(f"[{datetime.now()}] {len(matches)} canlı maç bulundu.")
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
        print(f"Genel hata: {e}")

# Her 45 saniyede kontrol
schedule.every(45).seconds.do(check_matches)

# Başlangıçta ZORUNLU test tweet
print("Bot başlatılıyor...")
send_tweet("🤖 @macsonuspor bot aktif oldu! ⚽ Canlı gol ve maç sonu bildirimleri başlıyor... #MaçSonu")

if __name__ == "__main__":
    print("Bot başlatıldı, maçlar takip ediliyor...")
    while True:
        schedule.run_pending()
        time.sleep(1)
