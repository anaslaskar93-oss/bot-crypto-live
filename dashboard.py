import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import feedparser
from datetime import timedelta
import time
import warnings
import urllib.request
import urllib.parse

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

# Memoria per non spammare (salva l'orario dell'ultima candela)
if 'ultima_candela_1h' not in st.session_state:
    st.session_state.ultima_candela_1h = None

exchange = ccxt.kraken()
analizzatore = SentimentIntensityAnalyzer()
simbolo = 'BTC/USDT'
url_news = "https://cointelegraph.com/rss"

# --- IA NOTIZIE (Comune a tutti i grafici) ---
try:
    feed = feedparser.parse(url_news)
    ultima_notizia = feed.entries[0].title if feed.entries else "Nessuna notizia trovata."
    punteggio_news = analizzatore.polarity_scores(ultima_notizia)['compound']
except:
    ultima_notizia = "Impossibile caricare le notizie."
    punteggio_news = 0

st.markdown("---")
st.subheader("📰 Intelligenza Artificiale (Contesto Globale)")
st.write(f"_{ultima_notizia}_  **(Sentiment Score: {punteggio_news:.2f})**")
st.markdown("---")

# --- IL MOTORE DI CALCOLO UNIVERSALE ---
def analizza_e_disegna(timeframe, delta_futuro):
    # Dati
    dati_grezzi = exchange.fetch_ohlcv(simbolo, timeframe, limit=100)
    df = pd.DataFrame(dati_grezzi, columns=['Timestamp', 'Apertura', 'Massimo', 'Minimo', 'Chiusura', 'Volume'])
    df['Data'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df = df.set_index('Data')
    prezzo_attuale = df['Chiusura'].iloc[-1]
    ora_attuale = df.index[-1]

    # Indicatori (RSI, MACD, Bollinger)
    delta = df['Chiusura'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ema_up = up.ewm(com=13, adjust=False).mean()
    ema_down = down.ewm(com=13, adjust=False).mean()
    rs = ema_up / ema_down
    df['RSI'] = 100 - (100 / (1 + rs))
    rsi_attuale = df['RSI'].iloc[-1]

    ema_12 = df['Chiusura'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Chiusura'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    macd_attuale = df['MACD'].iloc[-1]
    signal_attuale = df['Signal_Line'].
