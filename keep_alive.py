from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "MacSonuSpor Bot is Alive!"

def run():
    # Render'ın atadığı portu al, yoksa 8080 kullan
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    # daemon=True: Ana program kapanınca bu thread de kapansın
    t = Thread(target=run, daemon=True)
    t.start()

