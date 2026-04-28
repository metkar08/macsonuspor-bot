import requests
import time
import schedule
import os
from datetime import datetime, timezone, timedelta
from keep_alive import keep_alive

# --- AYARLAR ---
TR_TZ = timezone(timedelta(hours=3))
FOOTBALL_API_KEY = os.environ.get('FOOTBALL_API_KEY')
ZERNIO_API_KEY = os.environ.get('ZERNIO_API_KEY')
ZERNIO_API_URL = os.environ.get('ZERNIO_API_URL', 'https://api.zernio.com/v1/posts')
TWITTER_ACCOUNT_ID = "69ef66bb985e734bf3c0b515" # Senin Zernio Twitter ID'n

# --- API-SPORTS AYARLARI ---
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-key': FOOTBALL_API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# --- HAFIZA ---
last_scores = {}
processed_matches = set()
LAST_CLEANUP = datetime.now(TR_TZ).date()

# --- GENİŞLETİLMİŞ TAKIM LİSTESİ (Süper Lig + Avrupa Devleri) ---
TEAM_TAGS = {
    # TÜRKİYE SÜPER LİG (19 Takım)
    "Fenerbahce": "@Fenerbahce", "Galatasaray": "@GalatasaraySK", "Besiktas": "@Besiktas", "Trabzonspor": "@Trabzonspor",
    "Konyaspor": "@Konyaspor", "Samsunspor": "@Samsunspor", "Goztepe": "@Goztepe", "Alanyaspor": "@Alanyaspor",
    "Antalyaspor": "@Antalyaspor", "Basaksehir": "@Basaksehir_FK", "Adana Demirspor": "@AdanaDemirspor",
    "Kasımpaşa": "@kasimpasa", "Sivasspor": "@Sivasspor", "Rizespor": "@CRizesporAS", "Kayserispor": "@KayserisporFK",
    "Gaziantep": "@GaziantepFK", "Hatayspor": "@Hatayspor_FK", "Eyupspor": "@eyupspor", "Bodrum": "@BodrumFK",

    # AVRUPA DEVLERİ
    "Real Madrid": "@realmadrid", "Barcelona": "@FCBarcelona", "Atletico Madrid": "@Atleti",
    "Manchester City": "@ManCity", "Liverpool": "@LFC", "Arsenal": "@Arsenal", "Manchester United": "@ManUtd",
    "Bayern Munich": "@FCBayern", "Borussia Dortmund": "@BVB", "Bayer Leverkusen": "@bayer04fussball",
    "Paris Saint Germain": "@PSG_inside", "Inter": "@Inter", "Milan": "@acmilan", "Juventus": "@juventusfc"
}

def normalize_string(s):
    if not s: return ""
    translation_table = str.maketrans("ğüşıöçĞÜŞİÖÇ", "gusioctgusioct")
    return s.lower().translate(translation_table).strip()

def get_team_tag(team_name):
    norm_input = normalize_string(team_name)
    for key, tag in TEAM_TAGS.items():
        norm_key = normalize_string(key)
        if norm_key in norm_input:
            return tag
    return None

def send_tweet(text):
    if len(text) > 275:
        text = text[:272] + "..."
    
    saat_log = datetime.now(TR_TZ).strftime('%H:%M:%S')
    for attempt in range(3):
        try:
            headers = {"Authorization": f"Bearer {ZERNIO_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "content": text,
                "publishNow": True,
                "platforms": [{"platform": "twitter", "accountId": TWITTER_ACCOUNT_ID}]
            }
            response = requests.post(ZERNIO_API_URL, json=payload, headers=headers, timeout=15)
            if response.status_code in [200, 201]:
                print(f"[{saat_log}] TWEET BAŞARILI! 🎉", flush=True)
                return True
            time.sleep(3)
        except Exception as e:
            print(f"[{saat_log}] Hata: {e}", flush=True)
            time.sleep(3)
    return False

def check_matches():
    global LAST_CLEANUP, last_scores, processed_matches
    
    # Günlük Temizlik
    bugun = datetime.now(TR_TZ).date()
    if bugun > LAST_CLEANUP:
        last_scores.clear()
        processed_matches.clear()
        LAST_CLEANUP = bugun

    try:
        url = f"{BASE_URL}/fixtures/live"
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            data = response.json()
            print(f"API Hatası ({response.status_code}): {data.get('errors')}", flush=True)
            return
        
        matches = response.json().get('response', [])
        saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
        
        found_tracked_match = False
        for match in matches:
            home_name = match['teams']['home']['name']
            away_name = match['teams']['away']['name']
            
            home_tag = get_team_tag(home_name)
            away_tag = get_team_tag(away_name)

            if home_tag or away_tag:
                found_tracked_match = True
                fixture_id = match['fixture']['id']
                score_home = match['goals']['home'] or 0
                score_away = match['goals']['away'] or 0
                current_score = f"{score_home}-{score_away}"
                status = match['fixture']['status']['short']
                minute = match['fixture']['status']['elapsed'] or 0

                print(f"[{saat_simdi}] Takipte: {home_name} {current_score} {away_name}", flush=True)

                prev_score = last_scores.get(fixture_id)
                
                # GOL TESPİTİ
                if prev_score and prev_score != current_score and status not in ['FT', 'AET', 'PEN']:
                    goal_scorer = "Gol!"
                    events = match.get('events', [])
                    for event in reversed(events or []):
                        if event.get('type') == 'Goal':
                            goal_scorer = event.get('player', {}).get('name', 'Gol!')
                            break
                    
                    tweet = f"⚽ {minute}' GOOOL! {home_name} {current_score} {away_name}\n👤 {goal_scorer}\n#CanlıSkor {home_tag or ''} {away_tag or ''}"
                    send_tweet(tweet)

                # MAÇ SONU TESPİTİ
                if status in ['FT', 'AET', 'PEN'] and fixture_id not in processed_matches:
                    tweet = f"🏁 MAÇ SONU: {home_name} {score_home}-{score_away} {away_name}\n#MaçSonu {home_tag or ''} {away_tag or ''}"
                    send_tweet(tweet)
                    processed_matches.add(fixture_id)

                last_scores[fixture_id] = current_score
        
        if not found_tracked_match:
            print(f"[{saat_simdi}] {len(matches)} canlı maç var ama takibimizde kimse yok.", flush=True)

    except Exception as e:
        print(f"Döngü hatası: {e}", flush=True)

# 90 saniyede bir kontrol
schedule.every(90).seconds.do(check_matches)

if __name__ == "__main__":
    print("--- MacSonuSpor V1 - Elite Edition Aktif ---", flush=True)
    keep_alive()
    check_matches() # Hemen ilk kontrol
    while True:
        schedule.run_pending()
        time.sleep(1)
