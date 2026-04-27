import requests
import time
import schedule
import os
from datetime import datetime, timezone, timedelta

# Render'ı uyanık tutacak web sunucusu modülü
from keep_alive import keep_alive

# --- AYARLAR VE TÜRKİYE SAAT DİLİMİ ---
TR_TZ = timezone(timedelta(hours=3))

# --- API ANAHTARLARI ---
FOOTBALL_API_KEY = os.environ.get('FOOTBALL_API_KEY')
ZERNIO_API_KEY = os.environ.get('ZERNIO_API_KEY')
ZERNIO_API_URL = os.environ.get('ZERNIO_API_URL', 'https://api.zernio.com/v1/posts') 

# --- API SPORTS AYARLARI ---
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-key': FOOTBALL_API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# --- HAFIZA VE TEMİZLİK ---
last_scores = {}
processed_matches = set()
LAST_CLEANUP = datetime.now(TR_TZ).date()

# --- TAKIM ETİKETLERİ (Tam Eşleşme İçin Güncellendi) ---
TEAM_TAGS = {
    "Fenerbahce": "@Fenerbahce", "Galatasaray": "@GalatasaraySK", "Besiktas": "@Besiktas", "Trabzonspor": "@Trabzonspor",
    "Konyaspor": "@Konyaspor", "Samsunspor": "@Samsunspor", "Goztepe": "@Goztepe", "Alanyaspor": "@Alanyaspor",
    "Antalyaspor": "@Antalyaspor", "Basaksehir": "@Basaksehir_FK", "Adana Demirspor": "@AdanaDemirspor",
    "Real Madrid": "@realmadrid", "Barcelona": "@FCBarcelona", "Manchester City": "@ManCity", "Liverpool": "@LFC",
    "Bayern Munich": "@FCBayern", "Borussia Dortmund": "@BVB", "Paris Saint Germain": "@PSG_inside", "Inter": "@Inter"
}

def get_team_tag(team_name):
    # Gemini'nin uyarısı: Kısmi eşleşme yerine tam eşleşme kontrolü
    for name, tag in TEAM_TAGS.items():
        if name.lower() == team_name.lower():
            return tag
    return None

def send_tweet(text):
    # Karakter sınırı kontrolü (X limiti: 280)
    if len(text) > 275:
        text = text[:272] + "..."
        
    saat_log = datetime.now(TR_TZ).strftime('%H:%M:%S')
    print(f"[{saat_log}] Zernio yayını deneniyor...", flush=True)
    
    # Retry (Yeniden Deneme) Mekanizması
    for attempt in range(3):
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
            response = requests.post(ZERNIO_API_URL, json=payload, headers=headers, timeout=10)
            if response.status_code in [200, 201]:
                print(f"[{saat_log}] BAŞARILI! 🎉", flush=True)
                return True
            print(f"Hata {response.status_code}, tekrar deneniyor ({attempt+1}/3)...")
            time.sleep(2)
        except Exception as e:
            print(f"Bağlantı hatası: {e}, tekrar deneniyor...")
            time.sleep(2)
    return False

def check_matches():
    global LAST_CLEANUP, last_scores, processed_matches
    
    # Günlük Hafıza Temizliği (Bellek şişmesini önler)
    bugun = datetime.now(TR_TZ).date()
    if bugun > LAST_CLEANUP:
        last_scores.clear()
        processed_matches.clear()
        LAST_CLEANUP = bugun
        print(f"[{bugun}] Günlük hafıza temizlendi.", flush=True)

    try:
        url = f"{BASE_URL}/fixtures/live"
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code != 200:
            return
        
        matches = response.json().get('response', [])
        saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
        print(f"[{saat_simdi}] {len(matches)} canlı maç taranıyor...", flush=True)
        
        for match in matches:
            home_name = match['teams']['home']['name']
            away_name = match['teams']['away']['name']
            
            home_tag = get_team_tag(home_name)
            away_tag = get_team_tag(away_name)

            # Sadece takibimizdeki takımlar için işlem yap
            if home_tag or away_tag:
                fixture_id = match['fixture']['id']
                score_home = match['goals']['home'] or 0
                score_away = match['goals']['away'] or 0
                current_score = f"{score_home}-{score_away}"
                status = match['fixture']['status']['short']
                minute = match['fixture']['status']['elapsed'] or 0

                prev_score = last_scores.get(fixture_id)
                
                # Gol Tespiti
                if prev_score and prev_score != current_score and status not in ['FT', 'AET', 'PEN']:
                    # Golcü tespiti için Gemini'nin uyarısıyla events kontrolü
                    goal_scorer = "Gol!"
                    events = match.get('events', [])
                    if not events:
                        # Eğer olaylar yoksa maç detayına gitmeyi dene (Opsiyonel ama güvenli)
                        goal_scorer = "Skor güncellendi"
                    else:
                        for event in reversed(events):
                            if event['type'] == 'Goal':
                                goal_scorer = event['player']['name']
                                break
                    
                    tweet = f"⚽ {minute}' GOOOL! {home_name} {current_score} {away_name}\n👤 {goal_scorer}\n#CanlıSkor {home_tag or ''} {away_tag or ''}"
                    send_tweet(tweet)

                # Maç Sonu
                if status in ['FT', 'AET', 'PEN'] and fixture_id not in processed_matches:
                    tweet = f"🏁 MAÇ SONU: {home_name} {score_home}-{score_away} {away_name}\n#MaçSonu {home_tag or ''} {away_tag or ''}"
                    send_tweet(tweet)
                    processed_matches.add(fixture_id)

                last_scores[fixture_id] = current_score

    except Exception as e:
        print(f"Hata oluştu: {e}", flush=True)

# 90 saniyede bir kontrol
schedule.every(90).seconds.do(check_matches)

if __name__ == "__main__":
    print("Senior Bot Aktif Edildi. Keskin Nişancı Modu On.", flush=True)
    keep_alive()
    while True:
        schedule.run_pending()
        time.sleep(1)
