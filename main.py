import requests
import time
import tweepy  # X/Twitter için, ama şimdilik log'la tweet'leri (gerçek tweet için aşağıda açıklarım)
from datetime import datetime
import schedule
import os
from config import API_KEY  # API key'i config'den çek

# API-Sports endpoint'leri
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-key': API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# Takip edilecek lig ID'leri (API-Sports'tan: Süper Lig=203, ŞL=2, vs.)
LEAGUES = [203, 204, 2, 3, 39, 140, 135, 78, 61]  # Süper Lig, 1.Lig, ŞL, AvL, PL, LaLiga, SerieA, Bundesliga, Ligue1

# Son skorları takip için cache (değişiklikleri yakala)
last_scores = {}

def get_live_matches():
    """Canlı maçları çek, gol/maç sonu yakala"""
    try:
        url = f"{BASE_URL}/fixtures?live=all&league={','.join(map(str, LEAGUES))}"
        response = requests.get(url, headers=HEADERS)
        data = response.json()['response']
        for match in data:
            fixture_id = match['fixture']['id']
            teams = match['teams']
            home = teams['home']['name']
            away = teams['away']['name']
            score_home = match['goals']['home']
            score_away = match['goals']['away']
            status = match['fixture']['status']['short']
            minute = match['fixture']['status']['elapsed'] if 'elapsed' in match['fixture']['status'] else 0
            
            current_score = f"{score_home}-{score_away}"
            prev_score = last_scores.get(fixture_id, "0-0")
            
            # Gol tespiti
            if current_score != prev_score and score_home is not None and score_away is not None:
                # Gol tweet'i
                goal_text = f"⚽ {minute}' GOOOL! {home} {current_score} {away}"
                if 'events' in match:  # Gol atan kim (basit, events'ten son golü al)
                    last_event = match['events'][-1] if match['events'] else {}
                    scorer = last_event.get('player', {}).get('name', '??')
                    if last_event.get('type') == 'Goal':
                        goal_text += f" ({scorer})"
                hashtag = generate_hashtag(home, away, match['league']['name'])
                tweet = f"{goal_text}\n{hashtag}"
                send_tweet(tweet)  # Tweet fonksiyonu
            
            # Maç sonu
            if status == 'FT':
                goals_home = match['goals']['home'] or 0
                goals_away = match['goals']['away'] or 0
                end_text = f"🏁 MAÇ SONUUU!\n{home} {goals_home}-{goals_away} {away}"
                if 'lineups' in match:  # Goller listesi (basitçe)
                    goals_list = "Goller: " + ", ".join([f"{e['player']['name']} {e['time']['elapsed']}'" for e in match.get('events', []) if e['type'] == 'Goal'][:3])  # İlk 3 gol
                    end_text += f"\n{goals_list}"
                hashtag = generate_hashtag(home, away, match['league']['name'])
                tweet = f"{end_text}\n{hashtag}"
                send_tweet(tweet)
            
            last_scores[fixture_id] = current_score
    except Exception as e:
        print(f"Hata: {e}")

def generate_hashtag(home, away, league):
    """Otomatik hashtag + etiket"""
    short_home = home[:3].upper()
    short_away = away[:3].upper()
    tag = f"#{short_home}{short_away}"
    
    # Türk takımı etiketi
    turk_teams = ['Galatasaray', 'Fenerbahçe', 'Beşiktaş', 'Trabzonspor', 'Başakşehir', 'Adana Demirspor']  # Ekleyebilirsin
    if any(team in home or team in away for team in turk_teams):
        if 'Galatasaray' in home or 'Galatasaray' in away:
            tag += " @GalatasaraySK"
        # Diğerlerini ekle: Fenerbahçe @Fenerbahce, vs.
    
    if 'Süper Lig' in league:
        tag += " #TrendyolSüperLig"
    return tag

def send_tweet(text):
    """Tweet at (şimdilik log, gerçek için Tweepy kur)"""
    print(f"TWEET: {text}")  # Gerçek tweet için aşağıya bak
    # Gerçek için: client.create_tweet(text=text)

# Scheduler: Her 30 sn çalış
schedule.every(30).seconds.do(get_live_matches)

# Başlangıç
if __name__ == "__main__":
    print("Bot aktif! İlk tarama başlıyor...")
    get_live_matches()
    while True:
        schedule.run_pending()
        time.sleep(1)
