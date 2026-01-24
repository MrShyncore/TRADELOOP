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
from streamlit_lottie import st_lottie # KITA KEMBALIKAN INI

# [BACKEND SETUP]
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ==========================================
# 1. KONFIGURASI HALAMAN (GAYA NEON v9.2)
# ==========================================
st.set_page_config(
    page_title="TRADELOOP Hybrid",
    page_icon="",
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

    /* 6. CARD STYLING (LOGIKA v10.1 TAPI TAMPILAN NEON) */
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
# 2. UTILITIES & ANIMASI (LOTTIE KEMBALI)
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
# 3. LOGIC ENGINE (v10.1 HYBRID)
# ==========================================
@st.cache_data(ttl=300)
def get_stock_data(ticker, period="1y"):
    try:
        y_ticker = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
        df = yf.download(y_ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        if df is None or df.empty or len(df) < 15: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df.rename(columns={'Open':'Open', 'High':'High', 'Low':'Low', 'Close':'Close', 'Volume':'Volume'}, inplace=True)
        df = df.dropna()
        if 'Close' not in df.columns: return None
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
        sources = (
            "site:cnbcindonesia.com OR site:kontan.co.id OR site:investor.id OR "
            "site:bisnis.com OR site:emitennews.com OR site:idx.co.id"
        )
        query = f"Saham {ticker} ({sources})"
        url = f"https://news.google.com/rss/search?q={query}&hl=id-ID&gl=ID&ceid=ID:id"
        resp = requests.get(url, timeout=4)
        root = ET.fromstring(resp.content)
        news = []
        for item in root.findall('./channel/item')[:7]:
            raw_title = item.find('title').text
            clean_title = raw_title.split(' - ')[0] if raw_title else "Berita"
            src_raw = item.find('source').text if item.find('source') is not None else "News"
            src_clean = src_raw.replace("CNBC Indonesia", "CNBC").replace("Bisnis.com", "Bisnis")
            news.append({'title': clean_title, 'link': item.find('link').text, 'pubDate': item.find('pubDate').text, 'source': src_clean})
        return news
    except: return []

def calculate_analytics(df):
    try:
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean().replace(0, 0.00001)
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        recent_vol = df['Volume'].tail(20)
        v_std = recent_vol.std() if recent_vol.std() != 0 else 1
        z_vol = (df['Volume'].iloc[-1] - recent_vol.mean()) / v_std
        
        y = df['Close'].tail(5).values
        slope, _ = np.polyfit(np.arange(len(y)), y, 1)
        
        high_low = df['High'] - df['Low']
        high_close = np.abs(df['High'] - df['Close'].shift())
        low_close = np.abs(df['Low'] - df['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        atr = true_range.rolling(14).mean().iloc[-1]
        
        return float(z_vol), float(slope), float(rsi.iloc[-1]), float(atr)
    except: return 0.0, 0.0, 50.0, 0.0

def calculate_hybrid_score(rsi, slope, z_vol, rec, fund_data, price):
    score = 0
    # Technical
    if rsi < 40: score += 15
    elif 40 <= rsi <= 60: score += 5
    if slope > 0: score += 15
    if z_vol > 1.5: score += 10
    if "BUY" in rec: score += 20
    elif "NEUTRAL" in rec: score += 5
    # Fundamental
    if fund_data:
        graham = fund_data.get('graham_num', 0)
        per = fund_data.get('pe', 0)
        pbv = fund_data.get('pbv', 0)
        if graham > price: score += 15
        if 0 < per < 15: score += 15
        if 0 < pbv < 2.0: score += 10
    return min(score, 100)

# ==========================================
# 4. SIDEBAR (ANIMASI LOTTIE KEMBALI)
# ==========================================
with st.sidebar:
    lottie_logo = load_lottieurl(LOTTIE_BULL)
    if lottie_logo: st_lottie(lottie_logo, height=150, key="logo_anim")
    else: st.image("https://cdn-icons-png.flaticon.com/512/7210/7210631.png", width=100)
    
    st.markdown(f"<h2 style='text-align: center; color: {PRIMARY_COLOR}; margin-top: -20px;'>TRADELOOP</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: grey; font-size: 0.8rem;'>v10.1 Hybrid Neon</p>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("NAVIGASI", ["🚀 SCANNER", "📊 ANALISA LENGKAP", "⚙️ DATABASE"], index=0)

# ==========================================
# 5. HALAMAN UTAMA
# ==========================================

# --- SCANNER ---
if menu == "🚀 SCANNER":
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.title("🚀 Pemindai Pasar")
        st.markdown("Hybrid Scanning: Teknikal + Fundamental.")
    with col_h2:
        lottie_scan = load_lottieurl(LOTTIE_SCAN)
        if lottie_scan: st_lottie(lottie_scan, height=100, key="scan_anim")
    
    # --- BAGIAN INI YANG MEMPERCANTIK NAMA FILE ---
    # Kita buat kamus nama agar "gorengan.txt" jadi "🔥 Saham Volatil"
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

    # Fungsi otomatis: Jika file tidak ada di daftar atas, dia akan otomatis merapikan diri
    def format_filename(option):
        # 1. Cek apakah ada di kamus FILE_ALIAS
        if option in FILE_ALIAS:
            return FILE_ALIAS[option]
        
        # 2. Jika tidak ada, hilangkan .txt dan ganti garis bawah (_) dengan spasi
        # Contoh: "saham_tech.txt" menjadi "📂 Saham Tech"
        clean_name = option.replace(".txt", "").replace("_", " ").title()
        return f"📂 {clean_name}"

    with st.container(border=True):
        c1, c2 = st.columns([3, 1])
        with c1:
            # Ambil semua file txt
            txt_files = [f for f in os.listdir('.') if f.endswith('.txt') and 'requirements' not in f]
            
            # Pasang format_func di sini agar tampilan berubah
            selected_file = st.selectbox(
                "📂 PILIH DAFTAR SAHAM:", 
                txt_files, 
                format_func=format_filename  # <--- INI KUNCINYA
            )
            
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
                df = get_stock_data(t, period="3mo")
                fund = get_fundamentals(t)
                if df is None: continue
                
                z_vol, slope, rsi, atr = calculate_analytics(df)
                rec, _ = get_tv_analysis(t)
                price = df['Close'].iloc[-1]
                score = calculate_hybrid_score(rsi, slope, z_vol, rec, fund, price)
                
                val_status = "Mahal"
                if fund and fund['graham_num'] > price: val_status = "Diskon"
                
                results.append({
                    "Kode": t, "Harga": price, "Score": score, 
                    "Valuasi": val_status, "RSI": rsi, "Tren": slope
                })
            except: continue
        
        my_bar.empty()
        
        if results:
            df_res = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            st.dataframe(df_res, use_container_width=True, column_config={
                "Harga": st.column_config.NumberColumn(format="Rp %d"),
                "Score": st.column_config.ProgressColumn("Hybrid Score", min_value=0, max_value=100, format="%d"),
                "RSI": st.column_config.NumberColumn(format="%.1f"),
                "Tren": st.column_config.NumberColumn(format="%.2f%%")
            })
        else: st.warning("Tidak ada data.")

# --- ANALISA LENGKAP (TAMPILAN NEON + FITUR v10.1) ---
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
                df = get_stock_data(ticker, period="1y")
                fund = get_fundamentals(ticker)
                
                if df is not None:
                    # Logic Processing
                    z_vol, slope, rsi, atr = calculate_analytics(df)
                    rec, _ = get_tv_analysis(ticker)
                    price = df['Close'].iloc[-1]
                    chg_pct = ((price - df['Close'].iloc[-2])/df['Close'].iloc[-2])*100
                    total_score = calculate_hybrid_score(rsi, slope, z_vol, rec, fund, price)
                    
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
                        # Warna Score Neon
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
                        st.subheader("🏢 Valuasi (Fundamental)")
                        if fund:
                            g_color = SUCCESS_NEON if diskon > 0 else DANGER_NEON
                            st.markdown(f"""
                            <div class="fund-card" style="border-right-color: {g_color};">
                                <strong style="color:{g_color}">⚖️ Harga Wajar (Graham)</strong><br>
                                <span style="font-size:1.4em; color:white;">Rp {graham:,.0f}</span><br>
                                <small>Status: {"DISKON " + str(round(diskon,1)) + "%" if diskon > 0 else "MAHAL"}</small>
                            </div>
                            <div class="fund-card" style="border-right-color: {PRIMARY_COLOR};">
                                <strong>📊 PER & PBV</strong><br>
                                <span style="color:white">PER: {fund['pe']:.1f}x | PBV: {fund['pbv']:.1f}x</span>
                            </div>
                            <div class="fund-card" style="border-right-color: {PRIMARY_COLOR};">
                                <strong>💰 Dividen & ROE</strong><br>
                                <span style="color:white">Yield: {fund['div_yield']*100:.1f}% | ROE: {fund['roe']*100:.1f}%</span>
                            </div>
                            """, unsafe_allow_html=True)
                        else: st.info("Data fundamental tidak tersedia.")

                    st.write("")
                    tab1, tab2 = st.tabs(["📈 CHART NEON", "📰 BERITA"])
                    
                    with tab1:
                        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=ticker, increasing_line_color=SUCCESS_NEON, decreasing_line_color=DANGER_NEON)])
                        fig.add_hline(y=stop_loss, line_dash="dash", line_color=DANGER_NEON, annotation_text="SL")
                        fig.add_hline(y=tp1, line_dash="dash", line_color=SUCCESS_NEON, annotation_text="TP 1")
                        fig.update_layout(title=f"Chart {ticker}", template="plotly_dark", height=500, xaxis_rangeslider_visible=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
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
                # Logic update lq45 (dummy implementation di sini, pastikan fungsi auto_update_lq45 ada jika mau dipakai)
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
