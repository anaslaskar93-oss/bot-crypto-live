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

warnings.filterwarnings('ignore')

# 1. IMPOSTAZIONI PAGINA
st.set_page_config(layout="wide", page_title="Bot Dashboard LIVE")
st.title("🤖 Multi-Timeframe Quant Bot - BTC/USDT")

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
# Questa funzione calcola tutto in base al timeframe che gli chiediamo
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
    signal_attuale = df['Signal_Line'].iloc[-1]

    df['SMA_20'] = df['Chiusura'].rolling(window=20).mean()
    df['Std_Dev'] = df['Chiusura'].rolling(window=20).std()
    df['BB_Upper'] = df['SMA_20'] + (df['Std_Dev'] * 2)
    df['BB_Lower'] = df['SMA_20'] - (df['Std_Dev'] * 2)

    # Proiezione 
    ultimi_prezzi = df['Chiusura'].tail(15).values
    asse_tempo = np.arange(1, 16)
    modello = np.polyfit(asse_tempo, ultimi_prezzi, 1)
    impatto_news = prezzo_attuale * (punteggio_news * 0.005)
    target_price = (modello[0] * 16) + modello[1] + impatto_news
    ora_futura = ora_attuale + delta_futuro
    differenza_dollari = target_price - prezzo_attuale

    # Punteggio di Confluenza
    punteggio_totale = 0
    if target_price > prezzo_attuale: punteggio_totale += 1
    else: punteggio_totale -= 1
    
    if punteggio_news > 0.3: punteggio_totale += 1
    elif punteggio_news < -0.3: punteggio_totale -= 1
    
    if rsi_attuale < 30: punteggio_totale += 2
    elif rsi_attuale > 70: punteggio_totale -= 2
    
    if macd_attuale > signal_attuale: punteggio_totale += 1
    else: punteggio_totale -= 1

    # Creazione delle due colonne UI per questo specifico timeframe
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader(f"📊 Analisi {timeframe}")
        st.metric(label="Prezzo Attuale (BTC)", value=f"{prezzo_attuale:.2f} $")
        st.metric(label=f"Target Price (Tra 1 Candela)", value=f"{target_price:.2f} $", delta=f"{differenza_dollari:.2f} $")
        
        st.markdown("---")
        st.write(f"**RSI (Stanchezza):** {rsi_attuale:.0f}/100 " + ("🔴 Ipercomprato" if rsi_attuale > 70 else "🟢 Ipervenduto" if rsi_attuale < 30 else "⚪ Neutro"))
        st.write(f"**MACD (Inerzia):** " + ("🟢 Trend Rialzista" if macd_attuale > signal_attuale else "🔴 Trend Ribassista"))
        
        st.markdown("---")
        if punteggio_totale >= 2:
            st.success(f"🚀 VERDETTO {timeframe}: APRIRE LONG")
        elif punteggio_totale <= -2:
            st.error(f"🩸 VERDETTO {timeframe}: APRIRE SHORT")
        else:
            st.warning(f"⚖️ VERDETTO {timeframe}: ATTENDERE")

    with col2:
        fig = go.Figure()
        # Bollinger
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Upper'], mode='lines', line=dict(color='rgba(255, 255, 255, 0.2)', dash='dot'), name='Tetto (BB)'))
        fig.add_trace(go.Scatter(x=df.index, y=df['BB_Lower'], mode='lines', line=dict(color='rgba(255, 255, 255, 0.2)', dash='dot'), name='Fondo (BB)', fill='tonexty', fillcolor='rgba(255, 255, 255, 0.05)'))
        # Candele
        fig.add_trace(go.Candlestick(x=df.index, open=df['Apertura'], high=df['Massimo'], low=df['Minimo'], close=df['Chiusura'], name='BTC'))
        # Proiezione
        fig.add_trace(go.Scatter(x=[ora_attuale, ora_futura], y=[prezzo_attuale, target_price], mode='lines+markers', name='Proiezione', line=dict(color='cyan', width=3, dash='dash')))
        
        fig.update_layout(title=f'Grafico BTC/USDT ({timeframe})', yaxis_title='Prezzo ($)', template='plotly_dark', height=550, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)


# --- CREAZIONE DELLE SCHEDE (TABS) INTERATTIVE ---
tab1, tab2, tab3 = st.tabs(["🕒 1 Ora (Breve Termine)", "🕓 4 Ore (Medio Termine)", "📅 1 Giorno (Lungo Termine)"])

try:
    with tab1:
        analizza_e_disegna('1h', timedelta(hours=1))
        
    time.sleep(2) # <-- PAUSA: Evita il blocco anti-spam di Kraken
    
    with tab2:
        analizza_e_disegna('4h', timedelta(hours=4))
        
    time.sleep(2) # <-- PAUSA: Evita il blocco anti-spam di Kraken
        
    with tab3:
        analizza_e_disegna('1d', timedelta(days=1))

    st.caption("⏳ Auto-refresh di tutti i timeframe ogni 60 secondi...")
    time.sleep(60)
    st.rerun()

except Exception as e:
    st.error(f"Si è verificato un errore di connessione: {e}")
    time.sleep(10)
    st.rerun()
