import requests
import time
import schedule
import os
import unicodedata
from datetime import datetime, timezone, timedelta

# keep_alive modülü yoksa hata vermemesi için try-except
try:
    from keep_alive import keep_alive
except ImportError:
    def keep_alive(): print("keep_alive modülü bulunamadı, Flask başlatılmadı.")

# --- YAPILANDIRMA VE KONTROL ---
TR_TZ = timezone(timedelta(hours=3))
ZERNIO_API_KEY = os.environ.get('ZERNIO_API_KEY')
FOOTBALL_DATA_KEY = os.environ.get('FOOTBALL_DATA_KEY')
ZERNIO_API_URL = os.environ.get('ZERNIO_API_URL', 'https://api.zernio.com/v1/posts')
TWITTER_ACCOUNT_ID = "69ef66bb985e734bf3c0b515"

# Ortam değişkeni kontrolü
if not ZERNIO_API_KEY or not FOOTBALL_DATA_KEY:
    raise ValueError("KRİTİK HATA: API Anahtarları (ZERNIO veya FOOTBALL_DATA) eksik!")

# --- HAFIZA ---
last_scores = {}

# --- TAKIM LİSTESİ ---
TEAM_TAGS = {
    "fenerbahce": "@Fenerbahce", 
    "galatasaray": "@GalatasaraySK", 
    "besiktas": "@Besiktas", 
    "trabzonspor": "@Trabzonspor",
    "samsunspor": "@Samsunspor", 
    "goztepe": "@Goztepe",
    "farul": "#Test",
    "craiova": "#Test"
}

def normalize_text(text):
    """Türkçe karakterleri temizler ve küçük harfe çevirir."""
    text = text.replace('I', 'i').replace('İ', 'i') # Özel durum
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

def send_tweet(text):
    """Tweet gönderir ve uzunluk kontrolü yapar."""
    if len(text) > 280:
        text = text[:277] + "..."
        
    saat_log = datetime.now(TR_TZ).strftime('%H:%M:%S')
    headers = {"Authorization": f"Bearer {ZERNIO_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "content": text,
        "publishNow": True, # API sürümüne göre kontrol edilmeli
        "platforms": [{"platform": "twitter", "accountId": TWITTER_ACCOUNT_ID}]
    }
    
    try:
        response = requests.post(ZERNIO_API_URL, json=payload, headers=headers, timeout=15)
        print(f"[{saat_log}] Tweet Durumu: {response.status_code} - {response.text[:50]}", flush=True)
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"Tweet gönderilemedi: {e}", flush=True)
        return False

def check_scores():
    saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
    url = "https://api.football-data.org/v4/matches"
    headers = {'X-Auth-Token': FOOTBALL_DATA_KEY}
    params = {'status': 'LIVE'}
    
    try:
        # Retry mekanizmalı istek
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        matches = data.get('matches', [])
        
        found_tracked = False
        for match in matches:
            home_raw = match['homeTeam']['name']
            away_raw = match['awayTeam']['name']
            match_id = str(match['id'])
            
            # Normalizasyon ile eşleşme (ç -> c, ş -> s)
            home_norm = normalize_text(home_raw)
            away_norm = normalize_text(away_raw)
            
            # Skor çekme (API varyasyonlarına karşı güvenli)
            score_data = match.get('score', {}).get('fullTime', {})
            h_score = score_data.get('home')
            a_score = score_data.get('away')

            # Skor None ise sahte golü önlemek için atla
            if h_score is None or a_score is None:
                continue
                
            current_score = f"{h_score}-{a_score}"
            
            # Takım kontrolü
            h_tag = next((tag for name, tag in TEAM_TAGS.items() if name in home_norm), None)
            a_tag = next((tag for name, tag in TEAM_TAGS.items() if name in away_norm), None)

            if h_tag or a_tag:
                found_tracked = True
                # GOL TESPİTİ (Sadece skor değiştiğinde ve önceki skor biliniyorsa)
                if match_id in last_scores:
                    if last_scores[match_id] != current_score:
                        print(f"⚽ GOL: {home_raw} {current_score} {away_raw}", flush=True)
                        tweet_msg = f"⚽ GOOOL! {home_raw} {current_score} {away_raw}\n#CanlıSkor {h_tag or ''} {a_tag or ''}"
                        send_tweet(tweet_msg)
                
                last_scores[match_id] = current_score

        if not found_tracked:
            print(f"[{saat_simdi}] {len(matches)} canlı maç taranıyor, takip edilen takım yok.", flush=True)

    except Exception as e:
        print(f"[{saat_simdi}] API Hatası: {e}", flush=True)

# 60 saniyede bir kontrol
schedule.every(60).seconds.do(check_scores)

if __name__ == "__main__":
    print("--- MacSonuSpor V5 (Safe Engine) Aktif ---", flush=True)
    keep_alive()
    check_scores()
    while True:
        schedule.run_pending()
        time.sleep(1)
