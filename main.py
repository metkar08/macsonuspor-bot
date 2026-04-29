import requests
import time
import schedule
import os
from datetime import datetime, timezone, timedelta
from keep_alive import keep_alive

# --- AYARLAR ---
TR_TZ = timezone(timedelta(hours=3))
ZERNIO_API_KEY = os.environ.get('ZERNIO_API_KEY')
FOOTBALL_DATA_KEY = os.environ.get('FOOTBALL_DATA_KEY') # Yeni Anahtarın

# --- TAKIM LİSTESİ ---
TEAM_TAGS = {
    "Fenerbahce": "@Fenerbahce", "Galatasaray": "@GalatasaraySK", "Besiktas": "@Besiktas"
}

def check_scores():
    saat_simdi = datetime.now(TR_TZ).strftime('%H:%M:%S')
    try:
        # Football-Data.org Canlı Maçlar Endpoint'i
        url = "https://api.football-data.org/v4/matches"
        headers = { 'X-Auth-Token': FOOTBALL_DATA_KEY }
        
        # Filtre: Sadece canlı devam eden maçlar (Status: LIVE)
        params = { 'status': 'LIVE' }
        
        response = requests.get(url, headers=headers, params=params, timeout=15)
        
        if response.status_code == 200:
            data = response.json()
            matches = data.get('matches', [])
            print(f"[{saat_simdi}] {len(matches)} canlı maç taranıyor...", flush=True)
            # Gol kontrol mantığı buraya gelecek...
        elif response.status_code == 403:
            print(f"[{saat_simdi}] Kota doldu veya yetkisiz erişim.", flush=True)
        else:
            print(f"[{saat_simdi}] Hata: {response.status_code}", flush=True)

    except Exception as e:
        print(f"Hata: {e}", flush=True)

schedule.every(60).seconds.do(check_scores)

if __name__ == "__main__":
    keep_alive()
    check_scores()
    while True:
        schedule.run_pending()
        time.sleep(1)
