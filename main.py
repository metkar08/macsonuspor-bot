import requests
import time
import schedule
import os
from datetime import datetime, timezone, timedelta

# Render'ı uyanık tutacak güncellenmiş web sunucusu modülü
from keep_alive import keep_alive

# --- AYARLAR VE TÜRKİYE SAAT DİLİMİ (UTC+3) ---
TR_TZ = timezone(timedelta(hours=3))

# --- API ANAHTARLARI (Render Environment Variables) ---
FOOTBALL_API_KEY = os.environ.get('FOOTBALL_API_KEY')
ZERNIO_API_KEY = os.environ.get('ZERNIO_API_KEY')
ZERNIO_API_URL = os.environ.get('ZERNIO_API_URL', 'https://api.zernio.com/v1/posts') 

# --- API-SPORTS AYARLARI ---
BASE_URL = "https://v3.football.api-sports.io"
HEADERS = {
    'x-rapidapi-key': FOOTBALL_API_KEY,
    'x-rapidapi-host': 'v3.football.api-sports.io'
}

# --- HAFIZA VE TEMİZLİK ---
last_scores = {}
processed_matches = set()
LAST_CLEANUP = datetime.now(TR_TZ).date()

# --- TAKIM ETİKETLERİ ---
# API'den gelebilecek farklı yazımları (İngilizce/Türkçe) normalize ederek eşleştireceğiz
TEAM_TAGS = {
    "Fenerbahce": "@Fenerbahce", "Galatasaray": "@GalatasaraySK", "Besiktas": "@Besiktas", "Trabzonspor": "@Trabzonspor",
    "Konyaspor": "@Konyaspor", "Samsunspor": "@Samsunspor", "Goztepe": "@Goztepe", "Alanyaspor": "@Alanyaspor",
    "Antalyaspor": "@Antalyaspor", "Basaksehir": "@Basaksehir_FK", "Adana Demirspor": "@AdanaDemirspor",
    "Real Madrid": "@realmadrid", "Barcelona": "@FCBarcelona", "Manchester City": "@ManCity", "Liverpool": "@LFC",
    "Bayern Munich": "@FCBayern", "Borussia Dortmund": "@BVB", "Paris Saint Germain": "@PSG_inside", "Inter": "@Inter"
}

def normalize_string(s):
    """Türkçe karakterleri İngilizce karşılıklarına çevirir ve küçük harf yapar."""
    translation_table = str.maketrans("ğüşıöçĞÜŞİÖÇ", "gusioctgusioct")
    return s.lower().translate(translation_table).strip()

def get_team_tag(team_name):
    """Takım ismini normalize ederek listede arar."""
    norm_input = normalize_string(team_name)
    for key, tag in TEAM_TAGS.items():
        norm_key = normalize_string(key)
        # 'Besiktas JK' içinde 'besiktas' geçiyor mu kontrolü (Garantici yöntem)
        if norm_key in norm_input:
            return tag
    return None

def send_tweet(text):
    """Zernio üzerinden X'e tweet fırlatır (Retry mekanizmalı)."""
    # X karakter sınırı kontrolü
    if len(text) > 275:
        text = text[:272] + "..."
        
    saat_log = datetime.now(TR_TZ).strftime('%H:%M:%S')
    
    # 3 kez yeniden deneme (Retry)
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
            response = requests.post(ZERNIO_API_URL, json=payload, headers=headers, timeout=15)
            
            if response.status_code in [200, 201]:
                print(f"[{saat_log}] TWEET BAŞARILI! 🎉", flush=True)
                return True
            
            print(f"[{saat_log}] Zernio Hatası ({response.status_code}), deneme {attempt+1}/3", flush=True)
            time.sleep(3)
        except Exception as e:
            print(f"[{saat_log}] Yayınlama hatası: {e}, deneme {attempt+1}/3", flush=True)
            time.sleep(3)
    return False

def check_matches():
    global LAST_CLEANUP, last_scores, processed_matches
    
    # Her gün başında hafızayı temizle
    bugun = datetime.now(TR_TZ).date()
    if bugun > LAST_CLEANUP:
        last_scores.clear()
        processed_matches.clear()
        LAST_CLEANUP = bugun
        print(f"[{bugun}] Günlük temizlik yapıldı.", flush=True)

    try:
        # Canlı maçları çek
        url = f"{BASE_URL}/fixtures/live"
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            print(f"API Hatası: {response.status_code}", flush=True)
            return
        
        data = response.json()
        matches = data.get('response', [])
        
        saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
        print(f"[{saat_simdi}] {len(matches)} canlı maç taranıyor...", flush=True)
        
        for match in matches:
            home_name = match['teams']['home']['name']
            away_name = match['teams']['away']['name']
            
            home_tag = get_team_tag(home_name)
            away_tag = get_team_tag(away_name)

            # Sadece takip ettiğimiz takımlardan biriyse içeri gir
            if home_tag or away_tag:
                fixture_id = match['fixture']['id']
                score_home = match['goals']['home'] or 0
                score_away = match['goals']['away'] or 0
                current_score = f"{score_home}-{score_away}"
                status = match['fixture']['status']['short']
                minute = match['fixture']['status']['elapsed'] or 0

                prev_score = last_scores.get(fixture_id)
                
                # --- GOL TESPİTİ ---
                if prev_score and prev_score != current_score and status not in ['FT', 'AET', 'PEN']:
                    goal_scorer = "Gol!"
                    events = match.get('events', [])
                    for event in reversed(events):
                        if event['type'] == 'Goal':
                            goal_scorer = event['player']['name']
                            break
                    
                    tweet = f"⚽ {minute}' GOOOL! {home_name} {current_score} {away_name}\n👤 {goal_scorer}\n#CanlıSkor {home_tag or ''} {away_tag or ''}"
                    send_tweet(tweet)

                # --- MAÇ SONU TESPİTİ ---
                if status in ['FT', 'AET', 'PEN'] and fixture_id not in processed_matches:
                    tweet = f"🏁 MAÇ SONU: {home_name} {score_home}-{score_away} {away_name}\n#MaçSonu {home_tag or ''} {away_tag or ''}"
                    send_tweet(tweet)
                    processed_matches.add(fixture_id)

                # Skoru güncelle
                last_scores[fixture_id] = current_score

    except Exception as e:
        print(f"Döngü hatası: {e}", flush=True)

# 90 saniyede bir çalıştır
schedule.every(90).seconds.do(check_matches)

if __name__ == "__main__":
    print("--- MacSonuSpor SENIOR BOT BAŞLATILDI ---", flush=True)
    
    # Web sunucusunu (keep_alive) başlat
    keep_alive()
    
    # İlk çalıştırmada hemen bir kontrol yap (90 saniye beklememesi için)
    check_matches()
    
    while True:
        schedule.run_pending()
        time.sleep(1)
def check_matches():
    global LAST_CLEANUP, last_scores, processed_matches
    
    bugun = datetime.now(TR_TZ).date()
    if bugun > LAST_CLEANUP:
        last_scores.clear()
        processed_matches.clear()
        LAST_CLEANUP = bugun
        print(f"[{bugun}] Günlük temizlik yapıldı.", flush=True)

    try:
        url = f"{BASE_URL}/fixtures/live"
        response = requests.get(url, headers=HEADERS, timeout=15)
        
        if response.status_code != 200:
            print(f"API Hatası: {response.status_code}", flush=True)
            return
        
        data = response.json()
        matches = data.get('response', [])
        
        saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
        print(f"[{saat_simdi}] API'den toplam {len(matches)} canlı maç geldi.", flush=True)

        # --- DEBUG SATIRI BAŞLANGIÇ ---
        if len(matches) == 0:
             print(f"[{saat_simdi}] UYARI: API şu an canlı maç bildirmiyor. Yanıt: {data}", flush=True)
        # --- DEBUG SATIRI BİTİŞ ---
        
        for match in matches:
            home_name = match['teams']['home']['name']
            away_name = match['teams']['away']['name']
            
            # --- DEBUG: BOTUN GÖRDÜĞÜ MAÇLARI LOGA BAS ---
            print(f"[{saat_simdi}] Taranan Maç: {home_name} - {away_name}", flush=True)
            
            home_tag = get_team_tag(home_name)
            away_tag = get_team_tag(away_name)

            if home_tag or away_tag:
                # Buradan sonrası zaten senin kodunla aynı...
                fixture_id = match['fixture']['id']
                # ... devam ediyor ...