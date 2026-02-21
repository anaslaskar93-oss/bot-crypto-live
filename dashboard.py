import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import feedparser
from datetime import datetime, timedelta
import time
import warnings
import urllib.request
import urllib.parse
import json

warnings.filterwarnings('ignore')

# 1. IMPOSTAZIONI PAGINA
st.set_page_config(layout="wide", page_title="Bot Dashboard LIVE")
st.title("🤖 Multi-Timeframe Quant Bot - BTC/USDT")

# --- CREDENZIALI TELEGRAM ---
TOKEN_TELEGRAM = "8535553514:AAGVLr5Q3csodsRV-DRDUjGE6Ca68ePrz2c"
CHAT_ID_TELEGRAM = "868767099"

def invia_messaggio_telegram(testo):
    try:
        url = f"https://api.telegram.org/bot{TOKEN_TELEGRAM}/sendMessage?chat_id={CHAT_ID_TELEGRAM}&text={urllib.parse.quote(testo)}"
        urllib.request.urlopen(url)
    except Exception as e:
        pass

# Memoria per non spammare
if 'ultima_candela_1h' not in st.session_state:
    st.session_state.ultima_candela_1h = None

exchange = ccxt.kraken()
analizzatore = SentimentIntensityAnalyzer()
simbolo = 'BTC/USDT'

# --- 2. IA NOTIZIE MULTI-FEED ---
urls_news = [
    ("Crypto", "https://cointelegraph.com/rss"),
    ("Macro USA", "https://finance.yahoo.com/news/rss")
]
titoli_raccolti = []
punteggi = []

for fonte, url in urls_news:
    try:
        feed = feedparser.parse(url)
        if feed.entries:
            titolo = feed.entries[0].title
            titoli_raccolti.append(f"**{fonte}:** {titolo}")
            punteggi.append(analizzatore.polarity_scores(titolo)['compound'])
    except:
        pass

punteggio_news = np.mean(punteggi) if punteggi else 0

# --- 3. FEAR & GREED INDEX ---
try:
    url_fng = "https://api.alternative.me/fng/?limit=1"
    req_fng = urllib.request.Request(url_fng, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_fng) as response:
        fng_data = json.loads(response.read().decode())
        fng_value = int(fng_data['data'][0]['value'])
        fng_class = fng_data['data'][0]['value_classification']
except:
    fng_value = 50
    fng_class = "Neutral"

# --- 4. CALENDARIO ECONOMICO USA ---
eventi_usa_oggi = []
try:
    url_cal = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
    req_cal = urllib.request.Request(url_cal, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_cal) as response:
        calendario = json.loads(response.read().decode())
        oggi = datetime.now().strftime("%Y-%m-%d")
        for evento in calendario:
            if evento['country'] == 'USD' and evento['impact'] == 'High':
                if evento['date'].startswith(oggi):
                    eventi_usa_oggi.append(f"⏰ {evento['time']} - {evento['title']}")
except:
    pass

# --- 5. INTERFACCIA RADAR (3 Colonne) ---
st.markdown("---")
colA, colB, colC = st.columns(3)

with colA:
    st.subheader("📰 Sentiment Intelligenza Artificiale")
    for t in titoli_raccolti:
        st.write(t)
    if punteggio_news > 0.2: st.success(f"**Media Sentiment:** {punteggio_news:.2f} (Positivo)")
    elif punteggio_news < -0.2: st.error(f"**Media Sentiment:** {punteggio_news:.2f} (Negativo)")
    else: st.info(f"**Media Sentiment:** {punteggio_news:.2f} (Neutro)")

with colB:
    st.subheader("🧠 Fear & Greed Index")
    st.metric(label="Mercato Globale", value=f"{fng_value} / 100")
    if fng_value <= 25: st.success(f"Stato: {fng_class} (Occasione d'Acquisto?)")
    elif fng_value >= 75: st.error(f"Stato: {fng_class} (Rischio Crollo Imminente)")
    else: st.info(f"Stato: {fng_class} (Neutro)")

with colC:
    st.subheader("🚨 Calendario Macro (Dati USA)")
    if eventi_usa_oggi:
        for ev in eventi_usa_oggi:
            st.error(ev)
    else:
        st.success("✅ Nessun evento USA ad alto impatto oggi.")
st.markdown("---")

# --- 6. IL MOTORE DI CALCOLO UNIVERSALE ---
def analizza_e_disegna(timeframe, delta_futuro):
    # Dati grezzi
    dati_grezzi = exchange.fetch_ohlcv(simbolo, timeframe, limit=100)
    df = pd.DataFrame(dati_grezzi, columns=['Timestamp', 'Apertura', 'Massimo', 'Minimo', 'Chiusura', 'Volume'])
    df['Data'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df = df.set_index('Data')
