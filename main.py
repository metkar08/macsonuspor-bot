import requests
import time
import schedule
import os
import unicodedata
from datetime import datetime, timezone, timedelta

# keep_alive modülü kontrolü
try:
    from keep_alive import keep_alive
except ImportError:
    def keep_alive(): 
        print("--- keep_alive.py bulunamadı, Flask başlatılmadı. ---", flush=True)

# --- YAPILANDIRMA ---
TR_TZ = timezone(timedelta(hours=3))
ZERNIO_API_KEY = os.environ.get('ZERNIO_API_KEY')
FOOTBALL_DATA_KEY = os.environ.get('FOOTBALL_DATA_KEY')
ZERNIO_API_URL = os.environ.get('ZERNIO_API_URL', 'https://api.zernio.com/v1/posts')
TWITTER_ACCOUNT_ID = "69ef66bb985e734bf3c0b515"

# Ortam değişkeni güvenliği
if not ZERNIO_API_KEY or not FOOTBALL_DATA_KEY:
    print("!!! KRİTİK HATA: API Anahtarları Render panelinde tanımlanmamış !!!", flush=True)

# --- HAFIZA ---
last_scores = {}

# --- TAKIM LİSTESİ (Küçük harf ve Türkçe karaktersiz) ---
TEAM_TAGS = {
    "fenerbahce": "@Fenerbahce", 
    "galatasaray": "@GalatasaraySK", 
    "besiktas": "@Besiktas", 
    "trabzonspor": "@Trabzonspor",
    "samsunspor": "@Samsunspor", 
    "goztepe": "@Goztepe",
    "farul": "#TestGol",
    "craiova": "#TestGol"
}

def normalize_text(text):
    """Metni temizler, Türkçe karakterleri İngilizceye çevirir ve küçük harf yapar."""
    if not text:
        return ""
    # Türkçe karakter eşleşmeleri
    text = text.replace('I', 'i').replace('İ', 'i').replace('ı', 'i')
    # Diğer aksanları temizle (ç -> c, ş -> s vb.)
    nfkd_form = unicodedata.normalize('NFKD', text)
    return "".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

def send_tweet(text):
    """Zernio üzerinden tweet gönderir ve uzunluk kontrolü yapar."""
    if len(text) > 280:
        text = text[:277] + "..."
        
    saat_log = datetime.now(TR_TZ).strftime('%H:%M:%S')
    headers = {
        "Authorization": f"Bearer {ZERNIO_API_KEY}", 
        "Content-Type": "application/json"
    }
    payload = {
        "content": text,
        "publishNow": True,
        "platforms": [{"platform": "twitter", "accountId": TWITTER_ACCOUNT_ID}]
    }
    
    try:
        # Retry (Yeniden deneme) mekanizması olmadan tekil sağlam istek
        response = requests.post(ZERNIO_API_URL, json=payload, headers=headers, timeout=15)
        print(f"[{saat_log}] Tweet Durumu: {response.status_code}", flush=True)
        return response.status_code in [200, 201]
    except Exception as e:
        print(f"[{saat_log}] Tweet gönderim hatası: {e}", flush=True)
        return False

def check_scores():
    global last_scores
    saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
    
    url = "https://api.football-data.org/v4/matches"
    headers = {'X-Auth-Token': FOOTBALL_DATA_KEY}
    params = {'status': 'LIVE'}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        
        data = response.json()
        matches = data.get('matches', [])
        
        found_tracked = False
        for match in matches:
            # Takım isimlerini al (None kontrolü ile)
            home_raw = match.get('homeTeam', {}).get('name', "")
            away_raw = match.get('awayTeam', {}).get('name', "")
            match_id = str(match.get('id', ""))
            
            if not home_raw or not away_raw or not match_id:
                continue

            # Normalizasyon (Türkçe karakterleri çözme)
            home_norm = normalize_text(home_raw)
            away_norm = normalize_text(away_raw)
            
            # Skor verilerini çek (Safe/Güvenli çekim)
            score_data = match.get('score', {}).get('fullTime', {})
            h_score = score_data.get('home')
            a_score = score_data.get('away')

            # Eğer skorlardan biri None ise henüz veri gelmemiştir, atla
            if h_score is None or a_score is None:
                continue
                
            current_score = f"{h_score}-{a_score}"
            
            # TEAM_TAGS içindeki anahtarların takım isimlerinde geçip geçmediğine bak
            h_tag = next((tag for name, tag in TEAM_TAGS.items() if name in home_norm), None)
            a_tag = next((tag for name, tag in TEAM_TAGS.items() if name in away_norm), None)

            if h_tag or a_tag:
                found_tracked = True
                # GOL KONTROLÜ: Hafızada maç varsa ve skor değişmişse
                if match_id in last_scores:
                    if last_scores[match_id] != current_score:
                        print(f"⚽ GOL TESPİTİ: {home_raw} {current_score} {away_raw}", flush=True)
                        msg = f"⚽ GOOOL! {home_raw} {current_score} {away_raw}\n#CanlıSkor {h_tag or ''} {a_tag or ''}"
                        send_tweet(msg)
                
                # Skoru her durumda güncelle
                last_scores[match_id] = current_score

        if not found_tracked:
            print(f"[{saat_simdi}] {len(matches)} maç taranıyor, listemizde maç yok.", flush=True)

    except Exception as e:
        print(f"[{saat_simdi}] API Hatası: {e}", flush=True)

# 60 saniyede bir döngüyü çalıştır
schedule.every(60).seconds.do(check_scores)

if __name__ == "__main__":
    print("--- MacSonuSpor V5.1 (Stable Engine) Aktif ---", flush=True)
    keep_alive()
    # İlk çalıştırmayı hemen yap
    check_scores()
    
    while True:
        schedule.run_pending()
        time.sleep(1)
