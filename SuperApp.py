"""
TRADELOOP - Hybrid Stock Analytics Tool
Copyright (c) 2026 Handiansyah Pria Atmaja
Licensed under MIT License (Free for educational & personal use).

Disclaimer:
Aplikasi ini dibuat untuk tujuan edukasi dan berbagi pengetahuan.
Tidak diperjualbelikan (Not for sale).
"""
"""
TRADELOOP - V12.0 Dual-Tier System (Trading vs Investing)
Copyright (c) 2026 Handiansyah Pria Atmaja
Updated: Integrasi Real-time Data + Dual Scoring Engine
"""
import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import os
import requests
import xml.etree.ElementTree as ET
from tradingview_ta import TA_Handler, Interval, Exchange
import matplotlib
from streamlit_lottie import st_lottie

# [BACKEND SETUP]
matplotlib.use('Agg')

# ==========================================
# 1. KONFIGURASI HALAMAN
# ==========================================
st.set_page_config(
    page_title="TRADELOOP Pro V12",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- PALET WARNA NEON ---
PRIMARY_COLOR = "#00ADB5"    
BG_DARK = "#0E1117"          
PANEL_DARK = "#161B22"       
TEXT_WHITE = "#F0F6FC"
SUCCESS_NEON = "#00FFAB" # Hijau Trading
INVEST_GOLD = "#FFD700"  # Emas Investing
DANGER_NEON = "#FF2E63"
WARN_NEON = "#FCE38A"

st.markdown(f"""
<style>
    /* 1. BACKGROUND GLOW */
    .stApp {{
        background-color: {BG_DARK};
        background-image: radial-gradient(circle at 50% 0%, #1f2937 0%, {BG_DARK} 50%);
    }}

    /* 2. SIDEBAR GLASS */
    section[data-testid="stSidebar"] {{
        background-color: rgba(22, 27, 34, 0.85);
        backdrop-filter: blur(12px);
        border-right: 1px solid rgba(255, 255, 255, 0.08);
    }}
    
    /* 3. METRIK GLOWING */
    div[data-testid="stMetricValue"] {{
        font-family: 'Segoe UI', sans-serif;
        font-size: 1.8rem !important;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #FFF, {PRIMARY_COLOR});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-shadow: 0 0 20px rgba(0, 173, 181, 0.3);
    }}
    
    /* 4. TOMBOL NEON */
    div.stButton > button {{
        background: linear-gradient(90deg, {PRIMARY_COLOR} 0%, #00FFF5 100%);
        color: #000;
        border: none;
        border-radius: 12px;
        height: 45px;
        font-weight: bold;
        transition: all 0.3s;
    }}
    div.stButton > button:hover {{
        box-shadow: 0 0 15px {PRIMARY_COLOR};
        transform: scale(1.02);
    }}
    
    /* 5. BADGE KATEGORI */
    .badge-trade {{
        background-color: rgba(0, 255, 171, 0.15);
        border: 1px solid {SUCCESS_NEON};
        color: {SUCCESS_NEON};
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
    }}
    .badge-invest {{
        background-color: rgba(255, 215, 0, 0.15);
        border: 1px solid {INVEST_GOLD};
        color: {INVEST_GOLD};
        padding: 5px 10px;
        border-radius: 15px;
        font-weight: bold;
    }}

    .block-container {{ padding-top: 2rem; }}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. UTILITIES & ANIMASI
# ==========================================
@st.cache_data
def load_lottieurl(url):
    try:
        r = requests.get(url, timeout=3)
        return r.json() if r.status_code == 200 else None
    except: return None

LOTTIE_SCAN = "https://lottie.host/801a666e-2178-45f8-8422-7901584c3116/226d9c79-6f91-4543-b962-421735165842.json"
LOTTIE_FUNDAMENTAL = "https://lottie.host/96e6d191-10d9-43c3-8f0a-1a8089403328/W5yB9Z9d2w.json"

# ==========================================
# 3. LOGIC ENGINE (BUG FIX YFINANCE + CACHE)
# ==========================================

# FIX 1: Cache dipercepat jadi 15 detik biar harga berasa live
@st.cache_data(ttl=15)
def get_stock_data(ticker, period="1y"):
    try:
        y_ticker = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
        
        # Download Data Harian
        df = yf.download(y_ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        
        if df is None or df.empty: return None
        
        # FIX 2: Handle MultiIndex (Masalah Kolom Yahoo Baru)
        if isinstance(df.columns, pd.MultiIndex): 
            try: df.columns = df.columns.get_level_values(0)
            except: pass
        
        # Standardisasi Nama Kolom
        df.columns = [c.capitalize() for c in df.columns]
        req_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # Cek kelengkapan kolom
        if not all(c in df.columns for c in req_cols): return None
        df = df[req_cols].dropna()
        df = df[df['Close'] > 0]

        # FIX 3: Paksa Update Harga Terakhir dengan Data Menitan (Realtime)
        try:
            df_live = yf.download(y_ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
            if not df_live.empty:
                if isinstance(df_live.columns, pd.MultiIndex): 
                    df_live.columns = df_live.columns.get_level_values(0)
                # Timpa harga close terakhir
                live_price = float(df_live['Close'].iloc[-1])
                df.iloc[-1, df.columns.get_loc('Close')] = live_price
        except: pass

        return df

    except Exception: return None

@st.cache_data(ttl=3600)
def get_fundamentals(ticker):
    try:
        stock = yf.Ticker(f"{ticker}.JK")
        info = stock.info
        if not info: return None

        data = {
            "name": info.get('longName', ticker),
            "sector": info.get('sector', '-'),
            "pe": info.get('trailingPE', 0),
            "pbv": info.get('priceToBook', 0),
            "roe": info.get('returnOnEquity', 0),
            "div_yield": info.get('dividendYield', 0),
            "eps": info.get('trailingEps', 0),
            "book_value": info.get('bookValue', 0),
            "der": info.get('debtToEquity', 0) or 0,
            "current_ratio": info.get('currentRatio', 0) or 0,
        }
        # Hitung Graham
        if data['eps'] > 0 and data['book_value'] > 0:
            data['graham_num'] = np.sqrt(22.5 * data['eps'] * data['book_value'])
        else: data['graham_num'] = 0
        return data
    except: return None

def get_tv_analysis(ticker):
    try:
        handler = TA_Handler(symbol=ticker, screener="indonesia", exchange="IDX", interval=Interval.INTERVAL_1_DAY)
        analysis = handler.get_analysis()
        return analysis.summary.get('RECOMMENDATION', 'N/A'), analysis.summary
    except: return "N/A", {}

def get_news(ticker):
    try:
        sources = "site:cnbcindonesia.com OR site:kontan.co.id OR site:investor.id OR site:idx.co.id"
        query = f"Saham {ticker} ({sources})"
        url = f"https://news.google.com/rss/search?q={query}&hl=id-ID&gl=ID&ceid=ID:id"
        resp = requests.get(url, timeout=4)
        root = ET.fromstring(resp.content)
        news = []
        for item in root.findall('./channel/item')[:5]:
            news.append({'title': item.find('title').text, 'link': item.find('link').text, 'pubDate': item.find('pubDate').text})
        return news
    except: return []

# --- BANDARMOLOGY ---
def analyze_bandarmology(df):
    try:
        avg_vol = df['Volume'].rolling(20).mean()
        if avg_vol.iloc[-1] == 0: return "NETRAL", TEXT_WHITE, 1.0
        vol_ratio = df['Volume'].iloc[-1] / avg_vol.iloc[-1]
        close, prev = df['Close'].iloc[-1], df['Close'].iloc[-2]
        
        status, color = "NETRAL", TEXT_WHITE
        if close > prev and vol_ratio > 1.1: status, color = "AKUMULASI", SUCCESS_NEON
        elif close < prev and vol_ratio > 1.1: status, color = "DISTRIBUSI", DANGER_NEON
        return status, color, vol_ratio
    except: return "NETRAL", TEXT_WHITE, 1.0

def calculate_analytics(df):
    try:
        # Indikator Dasar
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, 0.00001)
        rsi = 100 - (100 / (1 + (gain/loss)))
        
        ma50 = df['Close'].rolling(50).mean().iloc[-1]
        ma200 = df['Close'].rolling(200).mean().iloc[-1] if len(df) > 200 else 0
        trend_status = "UPTREND" if ma50 > ma200 else "DOWNTREND"
        
        # ATR & Slope
        tr = np.max(pd.concat([df['High']-df['Low'], np.abs(df['High']-df['Close'].shift()), np.abs(df['Low']-df['Close'].shift())], axis=1), axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        slope = np.polyfit(np.arange(5), df['Close'].tail(5).values, 1)[0]
        
        # CAGR
        days = (df.index[-1] - df.index[0]).days
        cagr = (df['Close'].iloc[-1] / df['Close'].iloc[0]) ** (365.25/days) - 1 if days > 0 else 0
        
        # OBV Logic (Smart Money)
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        obv_slope = np.polyfit(np.arange(10), df['OBV'].tail(10).values, 1)[0]
        avg_vol = df['Volume'].mean()
        norm_obv = obv_slope / avg_vol if avg_vol != 0 else 0
        
        return float(rsi.iloc[-1]), trend_status, float(cagr), float(atr), float(slope), float(norm_obv)
    except: return 50.0, "SIDEWAYS", 0.0, 0.0, 0.0, 0.0

# --- NEW: DUAL TIER SCORING ENGINE ---
def calculate_dual_score(rsi, trend, bandar, fund, price, cagr, slope, obv_val):
    # A. TRADING SCORE (Momentum, Bandar, Trend, OBV)
    t_score = 0
    
    # 1. RSI (20 poin)
    if rsi < 40: t_score += 20       # Diskon
    elif 40 <= rsi <= 60: t_score += 10
    
    # 2. Trend & Price Action (30 poin)
    if "UPTREND" in trend: t_score += 20
    if slope > 0: t_score += 10 # Harga sedang nanjak
    
    # 3. Bandar & Smart Money (30 poin)
    if "AKUMULASI" in bandar: t_score += 20
    elif "NETRAL" in bandar: t_score += 10
    if obv_val > 0.1: t_score += 10 # Akumulasi senyap
    
    # 4. Bonus Sinyal Kuat (20 poin)
    # Divergence: Harga turun/datar tapi OBV naik (Bandar tampung)
    if slope <= 0 and obv_val > 0.05: t_score += 20
    
    t_score = min(t_score + 10, 100) # Base score bonus

    # B. INVESTING SCORE (Valuasi, Kesehatan, Dividen)
    i_score = 0
    if fund:
        graham = fund.get('graham_num', 0)
        pbv = fund.get('pbv', 0)
        
        # 1. Valuasi (40 poin)
        if graham > price: i_score += 20
        if 0 < pbv < 1.5: i_score += 20
        elif pbv < 3.0: i_score += 10
        
        # 2. Kesehatan (30 poin)
        der = fund.get('der', 0)
        real_der = der/100 if der > 10 else der
        if real_der < 1.0: i_score += 20 # Utang Aman
        cr = fund.get('current_ratio', 0)
        if cr > 1.0: i_score += 10       # Likuiditas Aman
        
        # 3. Profit & Growth (30 poin)
        if fund.get('roe', 0) > 0.15: i_score += 15
        if cagr > 0.10: i_score += 15    # Perusahaan Tumbuh
        
        # Denda Fundamental Busuk
        if fund.get('eps', 0) < 0: i_score -= 20 # Rugi
        if real_der > 2.5: i_score -= 20         # Utang Kebanyakan
        
    return max(0, min(t_score, 100)), max(0, min(i_score, 100))

# ==========================================
# 4. INTERFACE
# ==========================================
with st.sidebar:
    st.image("Gemini_Generated_Image.png", width=100)
    st.markdown("---")
    
    if st.button("🔄 REFRESH DATA", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
        
    menu = st.radio("MENU", ["🚀 SCANNER DUAL-TIER", "📊 ANALISA LENGKAP", "⚙️ DATABASE","📚 PANDUAN"])

# --- SCANNER ---
if menu == "🚀 SCANNER DUAL-TIER":
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("⚖️ Dual-Tier Scanner")
        st.markdown("Memisahkan saham **Trading (Cuan Cepat)** vs **Investing (Nabung)**.")
    with col_h2:
        lottie_scan = load_lottieurl(LOTTIE_SCAN)
        if lottie_scan: st_lottie(lottie_scan, height=80, key="scan")
    
    txt_files = [f for f in os.listdir('.') if f.endswith('.txt')]
    c1, c2 = st.columns([3,1])
    with c1: selected_file = st.selectbox("Daftar Saham:", txt_files)
    with c2: mode = st.selectbox("Filter Mode:", ["SEMUA", "HANYA TRADING ⚡", "HANYA INVESTING 💎"])
    
    if st.button("MULAI SCAN", type="primary", use_container_width=True):
        with open(selected_file, 'r') as f: tickers = [line.strip().upper() for line in f if line.strip()]
        results = []
        bar = st.progress(0, "Scanning...")
        
        for i, t in enumerate(tickers):
            bar.progress((i+1)/len(tickers), f"Checking {t}...")
            try:
                df = get_stock_data(t)
                fund = get_fundamentals(t)
                if df is None: continue
                
                rsi, trend, cagr, atr, slope, obv_val = calculate_analytics(df)
                bandar, _, _ = analyze_bandarmology(df)
                price = df['Close'].iloc[-1]
                
                # HITUNG DUAL SCORE
                t_score, i_score = calculate_dual_score(rsi, trend, bandar, fund, price, cagr, slope, obv_val)
                
                # KATEGORI
                cat = "NETRAL"
                if t_score > i_score and t_score >= 60: cat = "⚡ TRADING"
                elif i_score > t_score and i_score >= 60: cat = "💎 INVEST"
                elif t_score >= 60 and i_score >= 60: cat = "👑 HYBRID"
                
                # FILTERING
                show = False
                if mode == "SEMUA": show = True
                elif mode == "HANYA TRADING ⚡" and ("TRADING" in cat or "HYBRID" in cat): show = True
                elif mode == "HANYA INVESTING 💎" and ("INVEST" in cat or "HYBRID" in cat): show = True
                
                if show:
                    results.append({
                        "Kode": t, "Harga": price, "Tipe": cat,
                        "Trade Score": t_score, "Invest Score": i_score,
                        "Sinyal": bandar if "TRADING" in cat else "Value"
                    })
            except: continue
            
        bar.empty()
        if results:
            df_res = pd.DataFrame(results).sort_values("Trade Score", ascending=False)
            st.dataframe(df_res, use_container_width=True, hide_index=True, column_config={
                "Harga": st.column_config.NumberColumn(format="Rp %d"),
                "Trade Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
                "Invest Score": st.column_config.ProgressColumn(min_value=0, max_value=100, format="%d"),
            })
            csv = df_res.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Download CSV", csv, "scan_result.csv", "text/csv")
        else: st.warning("Tidak ada data yang cocok.")

# --- ANALISA LENGKAP ---
elif menu == "📊 ANALISA LENGKAP":
    st.title("📊 Analisa 360°")
    c1, c2 = st.columns([3,1])
    with c1: ticker = st.text_input("Kode Saham:", placeholder="BBCA").upper()
    with c2: 
        st.write(""); st.write("")
        btn = st.button("ANALISA", type="primary", use_container_width=True)
    
    if btn and ticker:
        with st.spinner("Analyzing..."):
            df = get_stock_data(ticker)
            fund = get_fundamentals(ticker)
            
            if df is not None:
                rsi, trend, cagr, atr, slope, obv_val = calculate_analytics(df)
                bandar, bandar_col, _ = analyze_bandarmology(df)
                price = df['Close'].iloc[-1]
                t_score, i_score = calculate_dual_score(rsi, trend, bandar, fund, price, cagr, slope, obv_val)
                
                # HEADER
                st.markdown(f"## {ticker} - Rp {price:,.0f}")
                
                # SCORE CARDS
                c1, c2 = st.columns(2)
                with c1:
                    bg = "rgba(0, 255, 171, 0.15)" if t_score >= 60 else "rgba(255, 255, 255, 0.05)"
                    st.markdown(f"""
                    <div style="background:{bg}; border: 2px solid {SUCCESS_NEON}; padding:15px; border-radius:10px; text-align:center;">
                        <h1 style="color:{SUCCESS_NEON}; margin:0;">{t_score}</h1>
                        <small style="color:white; font-weight:bold;">⚡ TRADING POTENTIAL</small><br>
                        <span style="color:grey; font-size:12px;">Driven by: Momentum, Bandar, OBV</span>
                    </div>""", unsafe_allow_html=True)
                with c2:
                    bg = "rgba(255, 215, 0, 0.15)" if i_score >= 60 else "rgba(255, 255, 255, 0.05)"
                    st.markdown(f"""
                    <div style="background:{bg}; border: 2px solid {INVEST_GOLD}; padding:15px; border-radius:10px; text-align:center;">
                        <h1 style="color:{INVEST_GOLD}; margin:0;">{i_score}</h1>
                        <small style="color:white; font-weight:bold;">💎 INVESTING QUALITY</small><br>
                        <span style="color:grey; font-size:12px;">Driven by: Valuasi, ROE, Growth</span>
                    </div>""", unsafe_allow_html=True)
                
                st.write("")

                # CHART & TABS
                tab1, tab2 = st.tabs(["📈 CHART NEON", "📰 NEWS"])
                with tab1:
                    ma50 = df['Close'].rolling(50).mean()
                    ma200 = df['Close'].rolling(200).mean()
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=ticker, increasing_line_color=SUCCESS_NEON, decreasing_line_color=DANGER_NEON))
                    fig.add_trace(go.Scatter(x=df.index, y=ma50, line=dict(color='orange', width=1), name='MA 50'))
                    fig.add_trace(go.Scatter(x=df.index, y=ma200, line=dict(color='blue', width=1), name='MA 200'))
                    fig.update_layout(template="plotly_dark", height=450, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=20, b=0))
                    st.plotly_chart(fig, use_container_width=True)
                
                with tab2:
                    news = get_news(ticker)
                    for n in news: st.markdown(f"[{n['title']}]({n['link']})")

                # DATA DETAILS
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown("###### ⚡ Indikator Trading")
                    st.dataframe(pd.DataFrame({
                        "Metrik": ["Tren Arah", "Bandar Flow", "RSI", "OBV Strength"],
                        "Nilai": [trend, bandar, f"{rsi:.1f}", f"{obv_val:.2f}"]
                    }).set_index('Metrik'), use_container_width=True)
                with c2:
                    st.markdown("###### 💎 Indikator Fundamental")
                    if fund:
                        der_val = fund.get('der', 0)
                        der_val = der_val/100 if der_val > 10 else der_val
                        graham = fund.get('graham_num', 0)
                        upside = ((graham - price)/price)*100 if price > 0 else 0
                        st.dataframe(pd.DataFrame({
                            "Metrik": ["Graham Upside", "ROE (Profit)", "DER (Utang)", "PBV"],
                            "Nilai": [f"{upside:+.1f}%", f"{fund.get('roe',0)*100:.1f}%", f"{der_val:.2f}x", f"{fund.get('pbv',0):.2f}x"]
                        }).set_index('Metrik'), use_container_width=True)

            else: st.error("Data tidak ditemukan.")

# --- DATABASE ---
elif menu == "⚙️ DATABASE":
    st.title("⚙️ Edit Database")
    files = [f for f in os.listdir('.') if f.endswith('.txt')]
    f_edit = st.selectbox("File:", files)
    if f_edit:
        with open(f_edit, "r") as f: content = f.read()
        new = st.text_area("Isi:", content, height=300)
        if st.button("Simpan", use_container_width=True):
            with open(f_edit, "w") as f: f.write(new)
            st.toast("Disimpan!")

# --- PANDUAN PENGGUNA (V12.0 DUAL-TIER EDU) ---
elif menu == "📚 PANDUAN":
    st.title("📘 Panduan & Edukasi TradeLoop V12")
    st.caption("Mastering the Dual-Tier System: Trading vs Investing")
    
    # 1. KONSEP UTAMA
    with st.container(border=True):
        st.markdown("### ☯️ Filosofi Dual-Tier")
        c1, c2 = st.columns(2)
        with c1:
            st.info("⚡ TIER 1: TRADING (Hunter)")
            st.markdown("""
            * **Fokus:** Cuan Cepat (Harian/Mingguan).
            * **Kunci:** Momentum, Arus Uang (Bandar), Tren.
            * **Tidak Peduli:** Perusahaan rugi atau utang besar, asal harga naik, kita ikut naik.
            * **Indikator:** RSI, OBV, Bandarmology.
            """)
        with c2:
            st.warning("💎 TIER 2: INVESTING (Farmer)")
            st.markdown("""
            * **Fokus:** Kekayaan Jangka Panjang (Bulanan/Tahunan).
            * **Kunci:** Valuasi Murah, Perusahaan Sehat, Dividen.
            * **Tidak Peduli:** Harga turun hari ini (malah senang karena diskon).
            * **Indikator:** Graham Number, ROE, DER, PBV.
            """)

    # 2. CARA BACA SKOR
    st.markdown("---")
    st.subheader("📊 Cara Membaca Skor & Sinyal")
    
    tab1, tab2, tab3 = st.tabs(["⚡ Skor Trading", "💎 Skor Investing", "🚨 Sinyal Bahaya"])
    
    with tab1:
        st.markdown("""
        **Skor Trading (0-100)** mengukur seberapa "panas" saham ini.
        
        * **Skor > 80 (Strong Buy):** Momentum sangat kuat. Bandar sedang akumulasi besar + Tren Naik.
        * **Skor 60-80 (Speculative Buy):** Potensi bagus, tapi pasang Stop Loss ketat.
        * **Skor < 40 (Cold):** Saham "tidur" atau sedang didistribusi (dibuang) bandar. Hindari.
        
        **Tips:** Cari saham dengan label **UPTREND** dan **AKUMULASI**.
        """)
        
    with tab2:
        st.markdown("""
        **Skor Investing (0-100)** mengukur "kesehatan & kewajaran harga".
        
        * **Skor > 80 (Gem):** Saham "Salah Harga". Sangat murah & perusahaan sangat untung.
        * **Skor 60-80 (Good Value):** Harga wajar, fundamental solid. Cocok untuk nabung rutin.
        * **Skor < 40 (Junk):** Perusahaan rugi, utang besar, atau harga terlalu mahal (Gorengan).
        
        **Tips:** Cari saham dengan Valuasi **SUPER MURAH** atau **DISKON**.
        """)
        
    with tab3:
        st.error("⛔ RED FLAGS (Tanda Bahaya)")
        st.markdown("""
        Jangan sentuh saham jika:
        1.  **DER > 3.0x:** Utang perusahaan 3x lipat dari modalnya. Risiko bangkrut tinggi.
        2.  **EPS Negatif:** Perusahaan sedang rugi, membakar uang investor.
        3.  **Distribusi Besar:** Harga turun + Volume besar = Bandar kabur.
        4.  **Likuiditas Macet:** Saham harga < Rp 55 (Gocap) seringkali susah dijual kembali.
        """)

    # 3. KAMUS INDIKATOR BARU (OBV)
    st.markdown("---")
    with st.expander("🧠 Kamus Indikator Canggih (New in V12)"):
        st.markdown("""
        ### 1. OBV (On Balance Volume) - "Detektor Smart Money"
        OBV mendeteksi aliran uang yang tidak terlihat di harga.
        * **Kasus Unik:** Harga saham *Sideways* (datar), tapi OBV naik terus.
        * **Artinya:** Ada "Smart Money" yang diam-diam menampung barang tanpa menaikkan harga. **Sinyal akan meledak.**
        
        ### 2. Graham Number
        Rumus legendaris guru Warren Buffett.
        * Jika Harga Pasar < Graham Number = **Diskon (Undervalued)**.
        * Jika Harga Pasar > Graham Number = **Mahal (Overvalued)**.
        
        ### 3. CAGR (Growth)
        Rata-rata pertumbuhan harga per tahun.
        * Jika CAGR positif (misal 15%), artinya rata-rata tiap tahun Anda untung 15% jika hold saham ini.
        """)

    # 4. STUDI KASUS STRATEGI
    st.markdown("---")
    st.subheader("🎯 Pilih Strategi Anda")
    
    col1, col2 = st.columns(2)
    with col1:
        st.success("Tipe Trader Agresif")
        st.markdown("""
        * **Filter Scanner:** Pilih "HANYA TRADING ⚡".
        * **Cari:** Trade Score > 70 + Bandar Akumulasi.
        * **Action:** Beli sore/pagi, jual saat profit 5-10% atau saat Tren patah.
        * **Wajib:** Pasang Stop Loss.
        """)
    with col2:
        st.info("Tipe Investor Santai")
        st.markdown("""
        * **Filter Scanner:** Pilih "HANYA INVESTING 💎".
        * **Cari:** Invest Score > 70 + Dividen Yield > 4%.
        * **Action:** Cicil beli (DCA) setiap bulan.
        * **Mindset:** "Saya membeli bisnis, bukan kertas."
        """)

    # ... (Lanjutan dari kode PANDUAN sebelumnya) ...

    st.markdown("---")
    st.subheader("🎓 Studi Kasus: Bedah Saham")
    st.caption("Contoh cara mengambil keputusan berdasarkan data aplikasi.")

    # Gunakan Tabs untuk memisahkan kasus agar rapi
    case_tab1, case_tab2, case_tab3 = st.tabs(["🚀 Kasus Trading", "💎 Kasus Investing", "☠️ Kasus Jebakan (Trap)"])

    # KASUS 1: TRADING (Mencari Cuan Cepat)
    with case_tab1:
        st.markdown("### Studi Kasus: PT Energy Mega (Misal: ADRO/PTBA)")
        st.info("🎯 **Target:** Profit 5-10% dalam 1-2 minggu.")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("""
            **Data di Scanner:**
            * **Trade Score:** 85 (Tinggi)
            * **Tren:** UPTREND
            * **Bandar:** AKUMULASI
            * **RSI:** 55 (Belum Overbought)
            * **OBV:** Naik Tajam
            """)
        with c2:
            st.success("✅ **KEPUTUSAN: BUY (HAKA)**")
            st.markdown("""
            **Analisa Logika:**
            1.  **Skor 85** artinya semua lampu hijau menyala.
            2.  **Bandar Akumulasi + OBV Naik:** Uang besar masuk, harga kemungkinan besar akan didorong naik.
            3.  **RSI 55:** Masih ada ruang untuk naik sampai RSI 70 (Jual di sana).
            
            **Action Plan:**
            * Beli di harga penutupan.
            * Stop Loss jika harga turun di bawah Garis MA50.
            * Jual separuh jika profit sudah 5%.
            """)

    # KASUS 2: INVESTING (Mencari Tabungan Masa Depan)
    with case_tab2:
        st.markdown("### Studi Kasus: Bank Raksasa (Misal: BBRI/BMRI)")
        st.info("🎯 **Target:** Dividen & Kenaikan harga dalam 1-3 tahun.")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("""
            **Data di Scanner:**
            * **Invest Score:** 90 (Sangat Bagus)
            * **Graham Upside:** +40% (Diskon)
            * **ROE:** 18% (Profit Tebal)
            * **Dividen Yield:** 5.5%
            * **Tren:** DOWNTREND (Harga sedang turun)
            """)
        with c2:
            st.success("✅ **KEPUTUSAN: CICIL BELI (DCA)**")
            st.markdown("""
            **Analisa Logika:**
            1.  **Tren Downtrend?** Bagi investor, ini justru berita bagus karena harga jadi murah (Diskon).
            2.  **Graham Upside +40%:** Harga sekarang jauh di bawah nilai wajarnya.
            3.  **ROE & Dividen Tinggi:** Sambil menunggu harga naik, kita dibayar dividen tiap tahun.
            
            **Action Plan:**
            * Jangan All-in (masuk semua uang).
            * Beli bertahap setiap harga turun 5% (Average Down).
            * Hold sampai harga kembali ke Nilai Wajar Graham.
            """)

    # KASUS 3: JEBAKAN / VALUE TRAP (Hati-hati!)
    with case_tab3:
        st.markdown("### Studi Kasus: PT Konstruksi Rugi (Saham Gorengan)")
        st.error("⚠️ **Peringatan:** Terlihat murah, tapi mematikan.")
        
        c1, c2 = st.columns([1, 2])
        with c1:
            st.markdown("""
            **Data di Scanner:**
            * **Harga:** Rp 60 (Murah meriah?)
            * **PBV:** 0.3x (Terlihat sangat murah)
            * **Trade Score:** 20 (Merah)
            * **Invest Score:** 30 (Merah)
            * **DER (Utang):** 4.5x (Bahaya!)
            * **Bandar:** DISTRIBUSI
            """)
        with c2:
            st.error("⛔ **KEPUTUSAN: HINDARI (AVOID)**")
            st.markdown("""
            **Analisa Logika:**
            1.  **PBV 0.3x memang murah, TAPI...** Utang (DER) 4.5x modal. Perusahaan ini risiko bangkrutnya tinggi.
            2.  **Harga Rp 60:** Mendekati gocap (Rp 50). Jika nyangkut di Rp 50, uang Anda tidak bisa keluar selamanya.
            3.  **Bandar Distribusi:** Pemilik barang sedang kabur/jualan.
            
            **Pelajaran:** Murah tidak selalu bagus. Murah karena "sampah" beda dengan murah karena "diskon".
            """)    

    st.caption("TradeLoop V12.0 • Edukasi oleh Handiansyah Pria Atmaja")
    # --- FOOTER ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: grey; font-size: 0.8em;'>
    <b>Disclaimer:</b> Aplikasi ini adalah alat bantu analisa (tools), bukan ajakan membeli atau menjual. 
    Segala keuntungan dan kerugian investasi adalah tanggung jawab penuh pengguna (Do Your Own Research).
    <br>Built with 🐍 Python & TradeLoop Engine v10.6
</div>
""", unsafe_allow_html=True)
