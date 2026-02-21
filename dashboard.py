import streamlit as st
import ccxt
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import feedparser
from datetime import timedelta
import warnings

warnings.filterwarnings('ignore')

# 1. IMPOSTAZIONI DELLA PAGINA WEB (A tutto schermo)
st.set_page_config(layout="wide", page_title="Bot Dashboard")
st.title("🤖 Trading Quantitativo - Dashboard")

# Creiamo due colonne: una stretta per il testo (sinistra) e una larga per il grafico (destra)
col_testo, col_grafico = st.columns([1, 2])

# --- INIZIALIZZAZIONE STRUMENTI ---
exchange = ccxt.binance()
analizzatore = SentimentIntensityAnalyzer()
simbolo = 'BTC/USDT'
url_news = "https://cointelegraph.com/rss"

try:
    # --- SCARICAMENTO DATI ---
    dati_grezzi = exchange.fetch_ohlcv(simbolo, '1h', limit=50)
    df = pd.DataFrame(dati_grezzi, columns=['Timestamp', 'Apertura', 'Massimo', 'Minimo', 'Chiusura', 'Volume'])
    df['Data'] = pd.to_datetime(df['Timestamp'], unit='ms')
    df = df.set_index('Data')

    prezzo_attuale = df['Chiusura'].iloc[-1]
    ora_attuale = df.index[-1]

    # --- LETTURA NEWS ---
    feed = feedparser.parse(url_news)
    ultima_notizia = feed.entries[0].title if feed.entries else "Nessuna notizia trovata."
    punteggio_news = analizzatore.polarity_scores(ultima_notizia)['compound']

    # --- CALCOLO PROIEZIONE ---
    ultimi_prezzi = df['Chiusura'].tail(15).values
    asse_tempo = np.arange(1, 16)
    modello = np.polyfit(asse_tempo, ultimi_prezzi, 1)
    
    # Aggiustiamo col sentiment
    impatto_news = prezzo_attuale * (punteggio_news * 0.005)
    target_price = (modello[0] * 16) + modello[1] + impatto_news
    ora_futura = ora_attuale + timedelta(hours=1)
    
    differenza_dollari = target_price - prezzo_attuale

    # ==========================================
    # COLONNA SINISTRA: TESTO E METRICHE
    # ==========================================
    with col_testo:
        st.subheader("📊 Analisi di Mercato")
        
        # Mostra i prezzi con le freccette verdi o rosse
        st.metric(label="Prezzo Attuale (BTC)", value=f"{prezzo_attuale:.2f} $")
        st.metric(label="Target Price (Prossima Ora)", value=f"{target_price:.2f} $", delta=f"{differenza_dollari:.2f} $")
        
        st.markdown("---")
        st.subheader("📰 Intelligenza Artificiale")
        st.write(f"**Ultima Notizia:** {ultima_notizia}")
        
        if punteggio_news > 0.3:
            st.success(f"Sentiment Positivo: {punteggio_news}")
        elif punteggio_news < -0.3:
            st.error(f"Sentiment Negativo: {punteggio_news}")
        else:
            st.info(f"Sentiment Neutro: {punteggio_news}")
            
        st.markdown("---")
        st.subheader("🤖 Decisione Operativa")
        if target_price > prezzo_attuale:
            st.success("🚀 SUGGERIMENTO: APRIRE LONG")
        else:
            st.error("🩸 SUGGERIMENTO: APRIRE SHORT")

    # ==========================================
    # COLONNA DESTRA: IL GRAFICO
    # ==========================================
    with col_grafico:
        fig = go.Figure()

        # Candele storiche
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Apertura'], high=df['Massimo'], low=df['Minimo'], close=df['Chiusura'],
            name='Prezzo Reale'
        ))

        # Linea di proiezione
        fig.add_trace(go.Scatter(
            x=[ora_attuale, ora_futura], y=[prezzo_attuale, target_price],
            mode='lines+markers', name='Proiezione Bot',
            line=dict(color='cyan', width=3, dash='dash'),
            marker=dict(size=10)
        ))

        fig.update_layout(
            title=f'Grafico e Proiezione {simbolo}',
            yaxis_title='Prezzo in Dollari ($)',
            template='plotly_dark',
            height=600,
            xaxis_rangeslider_visible=False
        )

        # Mostra il grafico nella pagina web
        st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"Si è verificato un errore: {e}")