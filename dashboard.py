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
    dati_grezzi = exchange.fetch_ohlcv(simbolo, timeframe, limit=100)
    df = pd.DataFrame(dati_grezzi, columns=['Timestamp', 'Apertura', 'Massimo', 'Minimo', 'Chiusura', 'Volume'])
    df['Data'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df = df.set_index('Data')
    
    prezzo_attuale = df['Chiusura'].iloc[-1]
    prezzo_precedente = df['Chiusura'].iloc[-2]
    ora_attuale = df.index[-1]

    delta = df['Chiusura'].diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    rs = up.ewm(com=13, adjust=False).mean() / down.ewm(com=13, adjust=False).mean()
    df['RSI'] = 100 - (100 / (1 + rs))
    rsi_attuale = df['RSI'].iloc[-1]

    df['MACD'] = df['Chiusura'].ewm(span=12, adjust=False).mean() - df['Chiusura'].ewm(span=26, adjust=False).mean()
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    macd_attuale = df['MACD'].iloc[-1]
    signal_attuale = df['Signal_Line'].iloc[-1]

    df['SMA_20'] = df['Chiusura'].rolling(window=20).mean()
    df['Std_Dev'] = df['Chiusura'].rolling(window=20).std()
    df['BB_Upper'] = df['SMA_20'] + (df['Std_Dev'] * 2)
    df['BB_Lower'] = df['SMA_20'] - (df['Std_Dev'] * 2)

    df['Vol_SMA'] = df['Volume'].rolling(window=20).mean()
    vol_attuale = df['Volume'].iloc[-1]
    vol_medio = df['Vol_SMA'].iloc[-1]
    prezzo_in_salita = prezzo_attuale > prezzo_precedente
    
    anomalia_volumi = 0
    testo_volumi = "🟢 Volumi nella norma."
    
    if vol_attuale < (vol_medio * 0.7):
        if prezzo_in_salita:
            testo_volumi = "⚠️ ATTENZIONE: Rialzo dei prezzi ma VOLUMI ASSENTI (Possibile Trappola/Fakeout!)"
            anomalia_volumi = -2
        else:
            testo_volumi = "⚠️ Discesa con volumi deboli."
    elif vol_attuale > (vol_medio * 1.5):
        testo_volumi = "🔥 VOLUMI ALTI: Forte spinta istituzionale dietro questo movimento!"

    modello = np.polyfit(np.arange(1, 16), df['Chiusura'].tail(15).values, 1)
    impatto_news = prezzo_attuale * (punteggio_news * 0.005)
    target_price = (modello[0] * 16) + modello[1] + impatto_news
    ora_futura = ora_attuale + delta_futuro
    differenza_dollari = target_price - prezzo_attuale

    punteggio_totale = 0
    if target_price > prezzo_attuale: punteggio_totale += 1
    else: punteggio_totale -= 1
    
    if punteggio_news > 0.3: punteggio_totale += 1
    elif punteggio_news < -0.3: punteggio_totale -= 1
    
    if rsi_attuale < 30: punteggio_totale += 2
    elif rsi_attuale > 70: punteggio_totale -= 2
    
    if macd_attuale > signal_attuale: punteggio_totale += 1
    else: punteggio_totale -= 1
    
    if fng_value <= 25: punteggio_totale += 1
    elif fng_value >= 75: punteggio_totale -= 1
    
    punteggio_totale += anomalia_volumi

    verdetto_testo = "ATTENDERE ⚖️"
    if punteggio_totale >= 2: verdetto_testo = "APRIRE LONG 🚀"
    elif punteggio_totale <= -2: verdetto_testo = "APRIRE SHORT 🩸"

    if timeframe == '1h':
        if st.session_state.ultima_candela_1h != ora_attuale:
            avviso_macro = "\n\n🚨 ATTENZIONE: Ci sono eventi USA Alto Impatto oggi!" if eventi_usa_oggi else ""
            avviso_fng = f"\n🧠 Fear&Greed Index: {fng_value} ({fng_class})"
            
            messaggio_telegram = f"🤖 AGGIORNAMENTO BOT (1H)\n\n💰 Prezzo BTC: {prezzo_attuale:.2f} $\n🎯 Target: {target_price:.2f} $\n📊 RSI: {rsi_attuale:.0f}\n⚖️ Volumi: {testo_volumi}\n{avviso_fng}\n\n⚖️ VERDETTO: {verdetto_testo}{avviso_macro}"
            invia_messaggio_telegram(messaggio_telegram)
            st.session_state.ultima_candela_1h = ora_attuale

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader(f"📊 Analisi {timeframe}")
        st.metric(label="Prezzo Attuale (BTC)", value=f"{prezzo_attuale:.2f} $")
        st.metric(label=f"Target Price (Tra 1 Candela)", value=f"{target_price:.2f} $", delta=f"{differenza_dollari:.2f} $")
        st.markdown("---")
        st.write(f"**RSI (Stanchezza):** {rsi_attuale:.0f}/100 ")
        st.write(f"**MACD (Inerzia):** " + ("🟢 Rialzista" if macd_attuale > signal_attuale else "🔴 Ribassista"))
        st.write(f"**Analisi Volumi:** {testo_volumi}")
        st.markdown("---")
        if punteggio_totale >= 2: st.success(f"🚀 VERDETTO {timeframe}: {verdetto_testo}")
        elif punteggio_totale <= -2: st.error(f"🩸 VERDETTO {timeframe}: {verdetto_testo}")
        else: st.warning(f"⚖️ VERDETTO {timeframe}: {verdetto_testo}")

    with col2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], mode='lines', line=dict(color='rgba(255, 255, 255, 0.2)', dash='dot'), name='Tetto (BB)'))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], mode='lines', line=dict(color='rgba(255, 255, 255, 0.2)', dash='dot'), name='Fondo (BB)', fill='tonexty', fillcolor='rgba(255, 255, 255, 0.05)'))
        fig.add_trace(go.Candlestick(x=df.index, open=df['Apertura'], high=df['Massimo'], low=df['Minimo'], close=df['Chiusura'], name='BTC'))
        fig.add_trace(go.Scatter(x=[ora_attuale, ora_futura], y=[prezzo_attuale, target_price], mode='lines+markers', name='Proiezione', line=dict(color='cyan', width=3, dash='dash')))
        fig.update_layout(title=f'Grafico BTC/USDT ({timeframe})', yaxis_title='Prezzo ($)', template='plotly_dark', height=550, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

# --- 7. SCHEDE TABS ---
tab1, tab2, tab3 = st.tabs(["🕒 1 Ora (Breve Termine)", "🕓 4 Ore (Medio Termine)", "📅 1 Giorno (Lungo Termine)"])

try:
    with tab1: analizza_e_disegna('1h', timedelta(hours=1))
    time.sleep(2)
    with tab2: analizza_e_disegna('4h', timedelta(hours=4))
    time.sleep(2)
    with tab3: analizza_e_disegna('1d', timedelta(days=1))

    st.caption("⏳ Auto-refresh ogni 60 secondi...")
    time.sleep(60)
    st.rerun()

except Exception as e:
    st.error(f"Errore di rete: {e}")
    time.sleep(10)
    st.rerun()
