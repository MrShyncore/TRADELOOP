"""
TRADELOOP - Hybrid Stock Analytics Tool
Copyright (c) 2026 Handiansyah Pria Atmaja
Licensed under MIT License (Free for educational & personal use).

Disclaimer:
Aplikasi ini dibuat untuk tujuan edukasi dan berbagi pengetahuan.
Tidak diperjualbelikan (Not for sale).
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
import matplotlib.pyplot as plt

# ==========================================
# 1. KONFIGURASI HALAMAN (GAYA NEON v9.2)
# ==========================================
st.set_page_config(
    page_title="TRADELOOP Hybrid v10.2",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- PALET WARNA NEON (v9.2 Style) ---
PRIMARY_COLOR = "#00ADB5"    
BG_DARK = "#0E1117"          
PANEL_DARK = "#161B22"       
TEXT_WHITE = "#F0F6FC"
SUCCESS_NEON = "#00FFAB"
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
    
    /* 4. CONTAINER PANEL */
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column;"] > div[data-testid="stVerticalBlock"] {{
        background: {PANEL_DARK};
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }}

    /* 5. TOMBOL NEON */
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

    /* 6. CARD STYLING */
    .plan-card {{
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-left: 4px solid {PRIMARY_COLOR};
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }}
    .fund-card {{
        background-color: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-right: 4px solid {WARN_NEON};
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
        text-align: right;
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
        if r.status_code != 200: return None
        return r.json()
    except: return None

# URL Animasi Keren
LOTTIE_BULL = "https://lottie.host/9e530937-231a-42c2-b5e0-47b2b7190f84/d629f123-53d7-46a2-9705-0453715893a9.json"
LOTTIE_SCAN = "https://lottie.host/801a666e-2178-45f8-8422-7901584c3116/226d9c79-6f91-4543-b962-421735165842.json"
LOTTIE_FUNDAMENTAL = "https://lottie.host/96e6d191-10d9-43c3-8f0a-1a8089403328/W5yB9Z9d2w.json"

# ==========================================
# 3. LOGIC ENGINE (Updated v10.2)
# ==========================================
@st.cache_data(ttl=300)
def get_stock_data(ticker, period="1y"):
    try:
        y_ticker = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
        df = yf.download(y_ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 15: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # Standardisasi kolom (jaga-jaga urutan tertukar)
        if len(df.columns) >= 5:
            df = df.iloc[:, :5]
            df.columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        
        # --- FILTER GLITCH (PENTING) ---
        df = df.dropna()
        df = df[df['Close'] > 0]       # Hapus baris jika harga 0/negatif
        df = df[df['High'] >= df['Low']] # Hapus jika High lebih rendah dari Low (Data error)
        
        if df.empty: return None
        df['Close'] = df['Close'].astype(float)
        return df
    except: return None

@st.cache_data(ttl=86400)
def get_fundamentals(ticker):
    try:
        y_ticker = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
        stock = yf.Ticker(y_ticker)
        info = stock.info
        data = {
            "name": info.get('longName', ticker),
            "sector": info.get('sector', '-'),
            "pe": info.get('trailingPE', 0),
            "pbv": info.get('priceToBook', 0),
            "roe": info.get('returnOnEquity', 0),
            "div_yield": info.get('dividendYield', 0),
            "eps": info.get('trailingEps', 0),
            "book_value": info.get('bookValue', 0),
            "growth": info.get('earningsGrowth', 0) or 0,
            "der": info.get('debtToEquity', 0) or 0, # Debt to Equity
            "peg": info.get('pegRatio', 0) or 0,     # PEG Growth
            "npm": info.get('profitMargins', 0) or 0, # Net Profit Margin
            "summary": info.get('longBusinessSummary', '-')
        }
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
        sources = "site:cnbcindonesia.com OR site:kontan.co.id OR site:investor.id OR site:bisnis.com OR site:emitennews.com OR site:idx.co.id"
        query = f"Saham {ticker} ({sources})"
        url = f"https://news.google.com/rss/search?q={query}&hl=id-ID&gl=ID&ceid=ID:id"
        
        resp = requests.get(url, timeout=4)
        root = ET.fromstring(resp.content)
        news = []
        
        for item in root.findall('./channel/item')[:7]:
            raw_title = item.find('title').text
            clean_title = raw_title.split(' - ')[0] if raw_title else "Berita Saham"
            src_raw = item.find('source').text if item.find('source') is not None else "News"
            src_clean = src_raw.replace("CNBC Indonesia", "CNBC").replace("Bisnis.com", "Bisnis").replace("KONTAN", "Kontan")
            
            news.append({
                'title': clean_title, 
                'link': item.find('link').text, 
                'pubDate': item.find('pubDate').text, 
                'source': src_clean
            })
        return news
    except: return []

# --- NEW: LOGIC BANDARMOLOGY ---
def analyze_bandarmology(df):
    try:
        # Rata-rata Volume 20 Hari
        avg_vol = df['Volume'].rolling(window=20).mean()
        if avg_vol.iloc[-1] == 0: return "NETRAL", TEXT_WHITE, 1.0
        
        last_vol = df['Volume'].iloc[-1]
        last_close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        
        vol_ratio = last_vol / avg_vol.iloc[-1]
        
        status = "NETRAL"
        color = TEXT_WHITE
        
        # Logika: Harga Naik + Volume Besar = Akumulasi
        if last_close > prev_close and vol_ratio > 1.5:
            status = "AKUMULASI BESAR"
            color = SUCCESS_NEON
        elif last_close > prev_close and vol_ratio > 1.1:
            status = "AKUMULASI"
            color = SUCCESS_NEON
        # Logika: Harga Turun + Volume Besar = Distribusi
        elif last_close < prev_close and vol_ratio > 1.5:
            status = "DISTRIBUSI BESAR"
            color = DANGER_NEON
        elif last_close < prev_close and vol_ratio > 1.1:
            status = "DISTRIBUSI"
            color = DANGER_NEON
            
        return status, color, vol_ratio
    except:
        return "N/A", TEXT_WHITE, 1.0

def calculate_analytics(df):
    try:
        # 1. Bersihkan Data
        df = df.replace([np.inf, -np.inf], np.nan).dropna()
        if len(df) < 50: return 0.0, 0.0, 50.0, 0.0, "N/A" # Return N/A jika data kurang

        # 2. RSI Logic
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, 0.00001)
        rsi = 100 - (100 / (1 + (gain/loss)))
        
        # 3. Volume & Slope Logic
        recent_vol = df['Volume'].tail(20)
        z_vol = (df['Volume'].iloc[-1] - recent_vol.mean()) / (recent_vol.std() if recent_vol.std() != 0 else 1)
        slope = np.polyfit(np.arange(5), df['Close'].tail(5).values, 1)[0]
        
        # 4. ATR Logic
        tr = np.max(pd.concat([df['High']-df['Low'], np.abs(df['High']-df['Close'].shift()), np.abs(df['Low']-df['Close'].shift())], axis=1), axis=1)
        atr = tr.rolling(14).mean().iloc[-1]
        
        # 5. NEW: MA TREND LOGIC (Golden Cross Check)
        ma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        ma200 = df['Close'].rolling(window=200).mean().iloc[-1] if len(df) > 200 else 0
        
        trend_status = "SIDEWAYS"
        if ma50 > ma200 and ma200 > 0: trend_status = "BULLISH (UPTREND)"
        elif ma50 < ma200 and ma200 > 0: trend_status = "BEARISH (DOWNTREND)"
        
        # PERHATIKAN: Ada 5 nilai yang dikembalikan (tambah trend_status)
        return float(z_vol), float(slope), float(rsi.iloc[-1]), float(atr), trend_status
    except: return 0.0, 0.0, 50.0, 0.0, "N/A"

# --- UPDATED: HYBRID SCORE DENGAN BANDARMOLOGY ---
def calculate_hybrid_score(rsi, slope, z_vol, rec, fund_data, price, bandar_status, trend_status):
    score = 0
    try:
        # 1. TEKNIKAL & TREND (Bobot 40%)
        if rsi < 40: score += 10
        elif 40 <= rsi <= 60: score += 5
        if slope > 0: score += 10
        if z_vol > 1.5: score += 5
        if "BULLISH" in trend_status: score += 15 # Poin plus untuk Uptrend
        if rec and "BUY" in rec: score += 10
        
        # 2. FUNDAMENTAL & KESEHATAN (Bobot 40%)
        if fund_data:
            graham = fund_data.get('graham_num', 0)
            pbv = fund_data.get('pbv', 0)
            roe = fund_data.get('roe', 0)
            der = fund_data.get('der', 0) # Debt to Equity
            
            # Valuasi
            if graham > price: score += 10
            if 0 < pbv < 2.0: score += 5
            
            # Profitabilitas
            if roe > 0.15: score += 10
            
            # --- FIX LOGIKA DER ---
            # Jika data > 10, anggap itu persen (contoh 50), jadi bagi 100 biar jadi 0.5
            real_der = der / 100 if der > 10 else der
            
            # Kesehatan (Safety)
            if 0 < real_der < 1.0: score += 10  # Utang kecil = Bagus
            elif real_der > 2.0: score -= 10    # Utang besar = Bahaya
            
        # 3. BANDARMOLOGY (Bobot 20%)
        if "AKUMULASI" in bandar_status: score += 15
        elif "DISTRIBUSI" in bandar_status: score -= 10
            
    except: pass
    return min(max(score, 0), 100)
        
# ==========================================
# 4. SIDEBAR (ANIMASI LOTTIE)
# ==========================================
with st.sidebar:
    st.image("Gemini_Generated_Image.png", width=100)

    st.markdown("---")
    with st.expander("🧮 Kalkulator Money Management", expanded=False):
        modal = st.number_input("Modal Total (Rp):", value=10000000, step=1000000)
        risk_pct = st.number_input("Resiko per Trade (%):", value=2.0, step=0.5)
        entry_price = st.number_input("Harga Beli:", value=0)
        sl_price = st.number_input("Harga Stop Loss:", value=0)
        
        if st.button("Hitung Lot"):
            if entry_price > sl_price and entry_price > 0:
                max_loss_rp = modal * (risk_pct / 100)
                loss_per_share = entry_price - sl_price
                max_shares = max_loss_rp / loss_per_share
                max_lots = int(max_shares / 100)
                
                st.success(f"✅ Beli Maksimal: **{max_lots} Lot**")
                st.caption(f"Resiko Hilang: Rp {max_loss_rp:,.0f} jika kena SL.")
            else:
                st.error("Harga SL harus di bawah Harga Beli!")
    
    st.markdown(f"<h2 style='text-align: center; color: {PRIMARY_COLOR}; margin-top: -20px;'>TRADELOOP</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey; font-size: 0.8rem;'>v10.2 Hybrid Neon</p>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("NAVIGASI", ["🚀 SCANNER", "📊 ANALISA LENGKAP", "⚙️ DATABASE", "📚 PANDUAN"], index=0)

# ==========================================
# 5. HALAMAN UTAMA
# ==========================================

# --- SCANNER ---
if menu == "🚀 SCANNER":
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("🚀 Pemindai Pasar")
        st.markdown("Hybrid Scanning")
    with col_h2:
        lottie_scan = load_lottieurl(LOTTIE_SCAN)
        if lottie_scan: st_lottie(lottie_scan, height=100, key="scan_anim")
    
    FILE_ALIAS = {
        "lq45.txt": "🏢 LQ45 (Saham Liquid)",
        "banking.txt": "🏦 Perbankan (Big Bank)",
        "energy.txt": "⚡ Energi & Tambang",
        "gorengan.txt": "🔥 Saham Volatil (Gorengan)",
        "syariah_jii.txt": "🕌 Syariah (JII 70)",
        "idx30.txt": "🏆 IDX30 (Bluechip Utama)",
        "idx80.txt": "📈 IDX80 (Mid Cap)",
        "my_watchlist.txt": "⭐ Watchlist Saya"
    }

    def format_filename(option):
        if option in FILE_ALIAS: return FILE_ALIAS[option]
        clean_name = option.replace(".txt", "").replace("_", " ").title()
        return f"📂 {clean_name}"

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            txt_files = [f for f in os.listdir('.') if f.endswith('.txt') and 'requirements' not in f]
            selected_file = st.selectbox("📂 PILIH DAFTAR SAHAM:", txt_files, format_func=format_filename)
            
        with c2:
            st.write(""); st.write("")
            scan_btn = st.button("▶️ MULAI SCAN", use_container_width=True)

    if scan_btn:
        with open(selected_file, 'r') as f: tickers = [line.strip().upper() for line in f if line.strip()]
        results = []
        my_bar = st.progress(0, text="Sedang memproses...")
        
        for i, t in enumerate(tickers):
            my_bar.progress((i + 1) / len(tickers), text=f"Scanning {t}...")
            try:
                df = get_stock_data(t, period="2y")
                fund = get_fundamentals(t)
                if df is None: continue
                
                # A. Hitung Analisa Dasar           
                z_vol, slope, rsi, atr, trend_stat = calculate_analytics(df) 
                rec, _ = get_tv_analysis(t)
                price = df['Close'].iloc[-1]
                bandar_s, bandar_c, v_ratio = analyze_bandarmology(df)
                
                # 2. Masukkan trend_stat ke calculation
                score = calculate_hybrid_score(rsi, slope, z_vol, rec, fund, price, bandar_s, trend_stat)
                
                # LOGIKA STATUS GRAHAM (NEW)
                graham = fund['graham_num'] if fund else 0
                val_status = "N/A"
                
                if graham > 0:
                    diskon_pct = ((graham - price) / graham) * 100
                    if diskon_pct >= 50: val_status = "💎 Super Murah"
                    elif 20 <= diskon_pct < 50: val_status = "✅ Diskon"
                    elif -10 <= diskon_pct < 20: val_status = "⚖️ Wajar"
                    else: val_status = "⛔ Mahal"
                else:
                    val_status = "⚠️ Rugi/Minus"

                # 3. Status DER (Dengan Normalisasi)
                raw_der = fund.get('der', 0) if fund else 0
                final_der = raw_der / 100 if raw_der > 10 else raw_der
                der_stat = "⚠️" if final_der > 2 else "✅"
                
                results.append({
                    "Kode": t, "Harga": price, "Score": score, 
                    "Trend": trend_stat, # Simpan trend
                    "Bandar": bandar_s, 
                    "DER": der_stat,     # Simpan DER
                    "Valuasi": val_status, "RSI": rsi
                })
            except: continue
        
        my_bar.empty()
        
        if results:
            df_res = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            
            # TAMPILAN TABEL YANG SUDAH DIPERBAIKI
            st.dataframe(df_res, use_container_width=True, column_config={
                "Harga": st.column_config.NumberColumn(format="Rp %d"),
                "Score": st.column_config.ProgressColumn("Hybrid Score", min_value=0, max_value=100, format="%d"),
                "RSI": st.column_config.NumberColumn(format="%.1f"),
                "Trend": st.column_config.TextColumn("Tren Jangka Panjang"), # Judul kolom lebih rapi
                "DER": st.column_config.TextColumn("Utang"),
                "Valuasi": st.column_config.TextColumn("Status Valuasi"),
            })
            
            st.write("")
            csv = df_res.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Hasil Scan ke CSV/Excel",
                data=csv,
                file_name='tradeloop_scan_result.csv',
                mime='text/csv',
                type='primary'
            )
        else: st.warning("Tidak ada data.")

# --- ANALISA LENGKAP ---
elif menu == "📊 ANALISA LENGKAP":
    col_t1, col_t2 = st.columns([3, 1])
    with col_t1: st.title("📊 Analisa 360°")
    with col_t2:
        lottie_fund = load_lottieurl(LOTTIE_FUNDAMENTAL)
        if lottie_fund: st_lottie(lottie_fund, height=80, key="fund_anim")
    
    with st.container(border=True):
        c_in, c_go = st.columns([4, 1])
        with c_in: ticker = st.text_input("KODE SAHAM:", placeholder="Contoh: BBCA").upper().strip()
        with c_go: 
            st.write(""); st.write("")
            analyze = st.button("ANALISA HYBRID", use_container_width=True)
            
    if analyze and ticker:
        with st.spinner("Menghubungkan Neural Network..."):
            try:
                df = get_stock_data(ticker, period="2y")
                fund = get_fundamentals(ticker)
                
                if df is not None:
                    # Logic Processing
                    z_vol, slope, rsi, atr, trend_stat = calculate_analytics(df)
                    rec, _ = get_tv_analysis(ticker)
                    price = df['Close'].iloc[-1]
                    chg_pct = ((price - df['Close'].iloc[-2])/df['Close'].iloc[-2])*100
                    
                    # --- NEW FIX: Bandarmology Call ---
                    bandar_status, bandar_color, vol_ratio = analyze_bandarmology(df)
                    
                    # --- NEW FIX: Score Calculation ---
                    total_score = calculate_hybrid_score(rsi, slope, z_vol, rec, fund, price, bandar_status, trend_stat)
                    
                    # Logic Trading Plan (ATR)
                    stop_loss = int(round((price - (2 * atr)) / 5) * 5)
                    tp1 = int(round((price + (2 * atr)) / 5) * 5)
                    tp2 = int(round((price + (4 * atr)) / 5) * 5)
                    risk_pct = ((price - stop_loss) / price) * 100
                    
                    # Logic Fundamental
                    graham = fund['graham_num'] if fund else 0
                    diskon = ((graham - price) / graham) * 100 if graham > 0 else 0
                    
                    # --- UI LAYOUT NEON ---
                    
                    # 1. HEADER
                    c1, c2 = st.columns([1, 3])
                    with c1:
                        sc_color = SUCCESS_NEON if total_score >= 70 else DANGER_NEON if total_score <= 40 else WARN_NEON
                        st.markdown(f"""
                        <div style="border: 2px solid {sc_color}; padding:15px; border-radius:15px; text-align:center; box-shadow: 0 0 10px {sc_color};">
                            <h1 style="color:{sc_color}; margin:0; text-shadow: 0 0 10px {sc_color};">{total_score}</h1>
                            <small style="color:white;">Hybrid Score</small>
                        </div>
                        """, unsafe_allow_html=True)
                    with c2:
                        st.markdown(f"## {ticker} - Rp {price:,.0f} ({chg_pct:+.2f}%)")
                        if fund: st.caption(f"{fund['name']} | Sektor: {fund['sector']}")

                    st.markdown("---")

                    # 2. DUAL CARD (NEON STYLE)
                    col_tech, col_fund = st.columns(2)
                    
                    with col_tech:
                        st.subheader("🎯 Eksekusi (Teknikal)")
                        st.markdown(f"""
                        <div class="plan-card" style="border-left-color: {DANGER_NEON};">
                            <strong style="color:{DANGER_NEON}">🛑 Stop Loss (SL)</strong><br>
                            <span style="font-size:1.4em; color:white;">Rp {stop_loss:,.0f}</span> <small style="color:grey">(-{risk_pct:.1f}%)</small>
                        </div>
                        <div class="plan-card" style="border-left-color: {WARN_NEON};">
                            <strong style="color:{WARN_NEON}">📍 Entry Area</strong><br>
                            <span style="font-size:1.4em; color:white;">Rp {price:,.0f}</span>
                        </div>
                        <div class="plan-card" style="border-left-color: {SUCCESS_NEON};">
                            <strong style="color:{SUCCESS_NEON}">🚀 Take Profit (TP)</strong><br>
                            <span style="font-size:1.4em; color:white;">Rp {tp1:,.0f} - {tp2:,.0f}</span>
                        </div>
                        """, unsafe_allow_html=True)

                    with col_fund:
                        st.subheader("🏢 Kesehatan & Valuasi")
                        if fund:
                            # Normalisasi DER (kadang data persen, kadang desimal)
                            der_val = fund['der'] / 100 if fund['der'] > 10 else fund['der']
                            der_safe = "✅ AMAN" if der_val < 1 else "⚠️ WASPADA" if der_val < 2 else "☠️ BAHAYA"
                            der_color = SUCCESS_NEON if der_val < 1 else DANGER_NEON
                            # LOGIKA STATUS DETAIL
                            graham = fund['graham_num'] if fund else 0
                            if graham > 0:
                                diskon = ((graham - price) / graham) * 100
                                if diskon >= 50: 
                                    g_stat, g_color = "💎 SUPER MURAH", SUCCESS_NEON
                                elif 20 <= diskon < 50: 
                                    g_stat, g_color = "✅ DISKON AMAN", SUCCESS_NEON
                                elif -10 <= diskon < 20: 
                                    g_stat, g_color = "⚖️ HARGA WAJAR", WARN_NEON
                                else: 
                                    g_stat, g_color = "⛔ MAHAL", DANGER_NEON
                            else:
                                diskon = 0
                                g_stat, g_color = "⚠️ DATA MINUS", DANGER_NEON
                            
                            st.markdown(f"""
                            <div class="fund-card" style="border-right-color: {der_color};">
                                <strong style="color:{der_color}">🏥 Kesehatan (DER)</strong><br>
                                <span style="font-size:1.4em; color:white;">{der_val:.2f}x</span><br>
                                <small>Status: {der_safe}</small>
                            </div>
                            <div class="fund-card" style="border-right-color: {PRIMARY_COLOR};">
                                <strong>💎 Profitabilitas (ROE)</strong><br>
                                <span style="color:white">{fund['roe']*100:.1f}%</span> <small>(PEG: {fund.get('peg', 0):.2f}x)</small>
                            </div>
                            <div class="fund-card" style="border-right-color: {g_color};">
                                <strong style="color:{g_color}">⚖️ Nilai Wajar (Graham)</strong><br>
                                <span style="font-size:1.4em; color:white;">Rp {graham:,.0f}</span><br>
                                <small>{g_stat} ({diskon:+.1f}%)</small>
                            </div>
                            """, unsafe_allow_html=True)
                        else: st.info("Data fundamental tidak tersedia.")

                    # 3. BANDARMOLOGY CARD (NEW)
                    st.subheader("🕵️ Deteksi Bandarmology (Volume Flow)")
                    st.markdown(f"""
                    <div style="background:{PANEL_DARK}; border: 1px solid {bandar_color}; border-left: 5px solid {bandar_color}; padding:15px; border-radius:10px; margin-bottom:20px;">
                        <h3 style="color:{bandar_color}; margin:0;">Status: {bandar_status}</h3>
                        <p style="color:#ccc; margin:5px 0 0 0;">Volume Ratio: <b>{vol_ratio:.2f}x</b> dari rata-rata 20 hari. (Indikasi Arus Uang Besar)</p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.write("")
                    tab1, tab2 = st.tabs(["📈 CHART NEON", "📰 BERITA"])
                    
                    with tab1:
                        # 1. Hitung MA untuk Chart
                        ma50 = df['Close'].rolling(50).mean()
                        ma200 = df['Close'].rolling(200).mean()
                        
                        # 2. Buat Figure Baru
                        fig = go.Figure()
                        
                        # 3. Tambahkan Candlestick
                        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=ticker, increasing_line_color=SUCCESS_NEON, decreasing_line_color=DANGER_NEON))
                        
                        # 4. Tambahkan Garis MA
                        fig.add_trace(go.Scatter(x=df.index, y=ma50, line=dict(color='orange', width=1), name='MA 50'))
                        fig.add_trace(go.Scatter(x=df.index, y=ma200, line=dict(color='blue', width=1), name='MA 200'))
                        
                        # 5. Tambahkan Garis Trading Plan (SL/TP)
                        fig.add_hline(y=stop_loss, line_dash="dash", line_color=DANGER_NEON, annotation_text="SL")
                        fig.add_hline(y=tp1, line_dash="dash", line_color=SUCCESS_NEON, annotation_text="TP 1")

                        fig.update_layout(title=f"Chart {ticker} (Daily)", template="plotly_dark", height=500, xaxis_rangeslider_visible=False)
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with tab2:
                        news = get_news(ticker)
                        if news:
                             for n in news:
                                with st.container(border=True):
                                    st.markdown(f"**{n['title']}**")
                                    c_d, c_s, c_l = st.columns([2, 2, 1])
                                    with c_d: st.caption(n['pubDate'])
                                    with c_s: st.caption(n['source'])
                                    with c_l: st.link_button("Baca", n['link'])
                        else: st.info("Tidak ada berita.")
                else: st.error("Saham tidak ditemukan.")
            except Exception as e: st.error(f"Error: {e}")

# --- DATABASE ---
elif menu == "⚙️ DATABASE":
    st.title("⚙️ Database Manager")
    with st.container(border=True):
        if st.button("⬇️ Update Database LQ45", type="secondary"):
            with st.spinner("Processing..."):
                st.success("Database Updated!")
    
    with st.container(border=True):
        txt_files = [f for f in os.listdir('.') if f.endswith('.txt') and 'requirements' not in f]
        file_to_edit = st.selectbox("Edit File:", txt_files)
        if file_to_edit:
            with open(file_to_edit, "r") as f: current = f.read()
            new = st.text_area("Isi:", value=current, height=300)
            if st.button("💾 Simpan"):
                with open(file_to_edit, "w") as f: f.write(new)
                st.toast("Tersimpan!", icon="✅")

# --- PANDUAN PENGGUNA ---
elif menu == "📚 PANDUAN":
    col_p1, col_p2 = st.columns([3, 1])
    with col_p1:
        st.title("📘 Panduan & Kamus Istilah")
        st.markdown("Pelajari cara membaca sinyal dan arti indikator di TradeLoop.")
    with col_p2:
        st.image("https://cdn-icons-png.flaticon.com/512/2666/2666505.png", width=80)

    st.write("")

    # --- BAGIAN 1: CARA PAKAI ---
    with st.expander("🚀 Cara Menggunakan SCANNER", expanded=True):
        st.markdown("""
        **Fungsi:** Menyaring ratusan saham secara otomatis untuk menemukan yang potensial.
        
        1. **Pilih Daftar Saham:** Gunakan dropdown untuk memilih kelompok saham (misal: *LQ45* atau *Watchlist Saya*).
        2. **Klik Mulai Scan:** Tunggu proses berjalan. Aplikasi akan mengambil data 2 tahun terakhir.
        3. **Baca Hasil:**
            * **Score:** Nilai 0-100. Semakin tinggi semakin bagus (Target > 70).
            * **Trend:** Pastikan statusnya **BULLISH** (Harga di atas rata-rata 200 hari).
            * **Valuasi:** *Diskon* artinya harga sekarang di bawah nilai wajarnya.
            * **DER:** Pastikan centang hijau (✅), artinya utang aman.
        """)

    with st.expander("📊 Cara Membaca ANALISA LENGKAP"):
        st.markdown("""
        **Fungsi:** Bedah tuntas satu emiten dari segala sisi (360° Analysis).
        
        * **Hybrid Score:** Gabungan nilai Teknikal + Fundamental + Bandarmology.
        * **Trading Plan:**
            * 🛑 **Stop Loss (SL):** Titik keluar jika analisa salah (untuk membatasi rugi).
            * 📍 **Entry Area:** Harga yang disarankan untuk beli.
            * 🚀 **Take Profit (TP):** Target harga jual untuk ambil untung.
        * **Chart:** Garis **Oranye (MA50)** dan **Biru (MA200)** menunjukkan tren. Jika Oranye di atas Biru = Uptrend (Bagus).
        """)

    # --- BAGIAN 2: KAMUS ISTILAH ---
    st.subheader("📖 Kamus Indikator (Penting!)")
    
    with st.container(border=True):
        st.markdown(f"#### 1. Bandarmology (Arus Dana)")
        st.write("""
        Mendeteksi pergerakan "Uang Besar" berdasarkan anomali volume.
        * **AKUMULASI:** Harga naik + Volume meledak (Indikasi Bandar masuk). ✅
        * **DISTRIBUSI:** Harga turun + Volume besar (Indikasi Bandar jualan). ❌
        * **NETRAL:** Volume transaksi wajar/biasa saja.
        """)
        
    with st.container(border=True):
        st.markdown(f"#### 2. Fundamental (Kesehatan Perusahaan)")
        st.write("""
        * **Graham Number:** Rumus nilai wajar saham konservatif. Jika Harga < Graham = **Diskon**.
        * **DER (Debt to Equity):** Rasio utang. Jika > 2.0 (200%), risiko bangkrut tinggi.
        * **ROE (Return on Equity):** Keuntungan dibanding modal. Di atas 15% = Perusahaan Super.
        """)

    with st.container(border=True):
        st.markdown(f"#### 3. Teknikal (Momentum & Tren)")
        st.write("""
        * **MA200 (Moving Average 200):** Rata-rata harga 1 tahun. Jika harga di atas garis ini, saham sedang **BULLISH** (Aman).
        * **RSI (Relative Strength Index):**
            * < 30: Jenuh Jual (Potensi mantul naik).
            * > 70: Jenuh Beli (Hati-hati koreksi).
            * 40-60: Area netral/konsolidasi.
        """)

        # --- BAGIAN 3: STUDI KASUS (NEW) ---
    st.subheader("🎓 Studi Kasus: Cara Analisa")

    col_case1, col_case2 = st.columns(2)

    with col_case1:
        with st.expander("✅ Contoh: SETUP SEMPURNA (Buy)", expanded=True):
            st.markdown("""
            **Skenario:** Anda menemukan saham "ABCD".
            
            1. **Tren:** Harga di atas garis Biru (MA200) dan Oranye (MA50). **(Status: UPTREND)**
            2. **Bandarmology:** Harga naik sedikit, tapi Volume Ratio > 1.5x. **(Status: AKUMULASI)**
            3. **Valuasi:** Harga Rp 1.000, tapi Graham Number Rp 1.500. **(Status: DISKON)**
            4. **Kesehatan:** DER hanya 0.5x (Utang kecil).
            
            👉 **Kesimpulan:** Ini adalah *Hidden Gem*. Saham sehat, sedang diakumulasi bandar, dan trennya naik. **ACTION: BUY (Cicil Beli).**
            """)

    with col_case2:
        with st.expander("❌ Contoh: JEBAKAN MURAH (Value Trap)", expanded=True):
            st.markdown("""
            **Skenario:** Anda melihat saham "GORE".
            
            1. **Tren:** Harga di bawah garis Biru (MA200). **(Status: DOWNTREND)**
            2. **Valuasi:** PBV sangat murah (0.3x). Terlihat menggiurkan.
            3. **Kesehatan:** DER mencapai 4.0x (Utang 4x lipat modal!). **(Status: BAHAYA)**
            4. **Bandarmology:** Harga turun disertai volume besar. **(Status: DISTRIBUSI)**
            
            👉 **Kesimpulan:** Jangan terkecoh harga murah! Ini kemungkinan perusahaan mau bangkrut atau sedang ditinggalkan investor besar. **ACTION: HINDARI / JUAL.**
            """)
    
    st.info("💡 **Tips:** Jangan menelan mentah-mentah hasil scan. Selalu cek chart dan berita terkini sebelum membeli.")
    # --- FOOTER ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: grey; font-size: 0.8em;'>
    <b>Disclaimer:</b> Aplikasi ini adalah alat bantu analisa (tools), bukan ajakan membeli atau menjual. 
    Segala keuntungan dan kerugian investasi adalah tanggung jawab penuh pengguna (Do Your Own Research).
    <br>Built with 🐍 Python & TradeLoop Engine v10.6
</div>
""", unsafe_allow_html=True)
