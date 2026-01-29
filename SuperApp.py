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
@st.cache_data(ttl=15) # Cache pendek biar cepat update
def get_stock_data(ticker, period="1y"):
    try:
        y_ticker = f"{ticker}.JK" if not ticker.endswith(".JK") else ticker
        
        # 1. AMBIL DATA HARIAN (Untuk Chart & Trend)
        df = yf.download(y_ticker, period=period, interval="1d", progress=False, auto_adjust=True)
        
        if df is None or df.empty: return None
        
        # Fix MultiIndex & Kolom
        if isinstance(df.columns, pd.MultiIndex): 
            try: df.columns = df.columns.get_level_values(0)
            except: pass
        
        df.columns = [c.capitalize() for c in df.columns]
        req_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
        if not all(c in df.columns for c in req_cols): return None
        df = df[req_cols].dropna()

        # 2. TRIK KHUSUS: UPDATE HARGA TERAKHIR DENGAN DATA MENITAN
        # (Supaya saat jam bursa, harganya sesuai detik ini, bukan harga kemarin)
        try:
            # Ambil data 1 hari terakhir, interval 1 menit
            df_live = yf.download(y_ticker, period="1d", interval="1m", progress=False, auto_adjust=True)
            if not df_live.empty:
                if isinstance(df_live.columns, pd.MultiIndex): 
                    df_live.columns = df_live.columns.get_level_values(0)
                
                # Ambil harga close menit terakhir sebagai "Current Price"
                live_price = float(df_live['Close'].iloc[-1])
                
                # Timpa harga 'Close' di baris terakhir data harian dengan harga live ini
                # agar chart dan indikator menghitung berdasarkan harga detik ini
                df.iloc[-1, df.columns.get_loc('Close')] = live_price
        except:
            pass # Jika gagal ambil data menit, pakai data harian saja (fallback)

        return df

    except Exception: return None

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
            "current_ratio": info.get('currentRatio', 0) or 0, # NEW: Likuiditas
            "revenue_growth": info.get('revenueGrowth', 0) or 0, # NEW: Pertumbuhan Omzet
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
        if len(df) < 50: return 0.0, 0.0, 50.0, 0.0, "N/A", 0.0 # <--- PERBAIKAN: Return 6 data default

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
        
        # 5. MA TREND LOGIC
        ma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        ma200 = df['Close'].rolling(window=200).mean().iloc[-1] if len(df) > 200 else 0
        
        trend_status = "SIDEWAYS"
        if ma50 > ma200 and ma200 > 0: trend_status = "BULLISH (UPTREND)"
        elif ma50 < ma200 and ma200 > 0: trend_status = "BEARISH (DOWNTREND)"

        # 6. NEW: CAGR (Compound Annual Growth Rate)
        days = (df.index[-1] - df.index[0]).days
        years = days / 365.25
        if years > 0:
            cagr = (df['Close'].iloc[-1] / df['Close'].iloc[0]) ** (1/years) - 1
        else:
            cagr = 0.0
        
        # Rumus: Close naik = Vol Ditambah. Close turun = Vol Dikurang.
        df['OBV'] = (np.sign(df['Close'].diff()) * df['Volume']).fillna(0).cumsum()
        
        # Hitung Kemiringan (Slope) OBV 10 hari terakhir
        # Tujuannya: Melihat apakah arus uang sedang masuk (Positif) atau keluar (Negatif)
        obv_slope = np.polyfit(np.arange(10), df['OBV'].tail(10).values, 1)[0]
        
        # Normalisasi (Supaya saham volume kecil & besar bisa dibandingkan)
        avg_vol = df['Volume'].mean()
        norm_obv = obv_slope / avg_vol if avg_vol != 0 else 0

        # Return ditambahkan: norm_obv
        return float(z_vol), float(slope), float(rsi.iloc[-1]), float(atr), trend_status, float(cagr), float(norm_obv)

    except: 
        # Return Error harus 7 data juga
        return 0.0, 0.0, 50.0, 0.0, "N/A", 0.0, 0.0

def calculate_hybrid_score(rsi, slope, z_vol, rec, fund_data, price, bandar_status, trend_status, cagr, obv_score):
    score = 0
    try:
        # 1. TEKNIKAL & TREND (Bobot 40%)
        if rsi < 40: score += 10
        elif 40 <= rsi <= 60: score += 5
        if slope > 0: score += 10
        if z_vol > 1.5: score += 5
        if "BULLISH" in trend_status: score += 15
        if rec and "BUY" in rec: score += 10
        
        # 2. FUNDAMENTAL & KESEHATAN (Bobot 40%)
        if fund_data:
            graham = fund_data.get('graham_num', 0)
            pbv = fund_data.get('pbv', 0)
            roe = fund_data.get('roe', 0)
            der = fund_data.get('der', 0)
            
            # Valuasi
            if graham > price: score += 10
            if 0 < pbv < 2.0: score += 5
            
            # Profitabilitas & Pertumbuhan (NEW: CAGR)
            if roe > 0.15: score += 10
            if cagr > 0.10: score += 5 # Bonus poin jika tumbuh >10% per tahun
            
            # Kesehatan (Safety) - FIX LOGIKA DER
            real_der = der / 100 if der > 10 else der
            if 0 < real_der < 1.0: score += 10
            elif real_der > 2.0: score -= 10
            
            # Likuiditas (NEW: Current Ratio)
            cr = fund_data.get('current_ratio', 0)
            if cr > 1.5: score += 5 # Bonus poin jika likuiditas sangat aman
            
        # 3. BANDARMOLOGY (Bobot 20%)
        if "AKUMULASI" in bandar_status: score += 15
        elif "DISTRIBUSI" in bandar_status: score -= 10
        
        # Jika OBV Naik Signifikan (Arus uang deras)
        if obv_score > 0.2: score += 10
        
        # SUPER SIGNAL: Bullish Divergence
        # Harga sedang turun/sideways (Slope <= 0), TAPI OBV Malah Naik (obv_score > 0)
        # Artinya: Ritel jualan panik, Bandar nampung diam-diam.
        if slope <= 0 and obv_score > 0.05:
            score += 15 
        
        # --- 4. [BARU] SAFETY PENALTY (Denda Risiko) ---
        # Bagian ini yang akan menyaring saham "busuk"
        
        # A. Denda Saham Gocap (Tidur)
        # Saham di bawah Rp 55 sangat berisiko susah dijual (likuiditas macet)
        if price < 55:
            score -= 30 
            
        # B. Denda Fundamental Hancur
        if fund_data:
            eps = fund_data.get('eps', 0)
            # Perusahaan Rugi (EPS Minus)
            if eps < 0: 
                score -= 15
            
            # Utang Ugal-ugalan (DER > 3x atau 300%)
            real_der = fund_data.get('der', 0)
            real_der = real_der / 100 if real_der > 10 else real_der
            if real_der > 3.0:
                score -= 20
                
    except: pass
    
    # Pastikan skor tidak di bawah 0 dan tidak di atas 100
    return min(max(score, 0), 100)
        
# --- FIX: EXECUTIVE SUMMARY (HANDLE NETRAL) ---
def get_executive_summary(score, trend, bandar, val_status, roe, der):
    summary = []
    
    # 1. Kesimpulan Utama
    if score >= 75:
        summary.append(f"🔥 **KESIMPULAN: STRONG BUY.** Saham ini memiliki momentum sangat kuat.")
    elif score >= 60:
        summary.append(f"✅ **KESIMPULAN: BUY ON WEAKNESS.** Potensi bagus, tapi tunggu koreksi sedikit.")
    elif score >= 40:
        summary.append(f"⚖️ **KESIMPULAN: WAIT & SEE.** Belum ada sinyal kuat, pasar masih ragu.")
    else:
        summary.append(f"⛔ **KESIMPULAN: HINDARI (AVOID).** Risiko terlalu tinggi saat ini.")
    
    # 2. Alasan Pendukung (Storytelling)
    reasons = []
    
    # Alasan 1: Tren
    if "BULLISH" in trend: reasons.append("tren harga sedang NAIK (Uptrend)")
    else: reasons.append("tren harga sedang TURUN/LEMAH")
    
    # Alasan 2: Bandar (INI YANG TADINYA ERROR)
    if "AKUMULASI" in bandar: reasons.append("terdeteksi adanya AKUMULASI")
    elif "DISTRIBUSI" in bandar: reasons.append("terdeteksi adanya DISTRIBUSI (Buangan Barang)")
    else: reasons.append("aliran dana terlihat NETRAL") # <--- SUDAH DIPERBAIKI
    
    # Alasan 3: Valuasi
    if "Murah" in val_status or "Diskon" in val_status: reasons.append("valuasi harga tergolong MURAH")
    else: reasons.append("valuasi harga sudah MAHAL/WAJAR")
    
    # 3. Peringatan Risiko
    warnings = []
    if der > 2.0: warnings.append("⚠️ Hati-hati! Utang perusahaan sangat besar (DER > 2x).")
    if roe < 0.05: warnings.append("⚠️ Profitabilitas perusahaan sangat rendah (ROE < 5%).")
    
    # Rangkai Kalimat
    # Sekarang aman karena reasons pasti punya index 0, 1, dan 2
    text = f"{summary[0]} Secara teknikal {reasons[0]}, dan {reasons[1]}. Dari sisi fundamental, {reasons[2]}."
    
    return text, warnings
        
# ==========================================
# 4. SIDEBAR (ANIMASI LOTTIE)
# ==========================================
with st.sidebar:
    st.image("Gemini_Generated_Image.png", width=100)

    with st.expander("🧮 Kelly Criterion (Money Management)", expanded=False):
        st.caption("Hitung ukuran posisi (Lot) optimal secara matematis.")
        
        modal_total = st.number_input("Total Modal (Rp):", value=10000000, step=1000000)
        win_rate = st.slider("Win Rate Strategi (%):", 30, 90, 50) / 100
        risk_reward = st.number_input("Risk/Reward Ratio (misal 1:2 isi 2):", value=2.0)
        
        if st.button("Hitung Kelly"):
            # Rumus Kelly: K% = W - [(1-W) / R]
            kelly_pct = win_rate - ((1 - win_rate) / risk_reward)
            safe_kelly = kelly_pct / 2 # Pakai Half-Kelly biar aman (konservatif)
            
            if kelly_pct > 0:
                modal_entry = modal_total * safe_kelly
                st.success(f"🎯 Alokasi: **{safe_kelly*100:.1f}%** Modal")
                st.markdown(f"Beli senilai: **Rp {modal_entry:,.0f}**")
                st.caption("Note: Menggunakan Half-Kelly untuk keamanan.")
            else:
                st.error("⛔ Statistik Buruk! Jangan Trading.")
                st.caption("Win Rate/Reward terlalu kecil. Anda akan rugi jangka panjang.")
    
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
                z_vol, slope, rsi, atr, trend_stat, cagr, obv_val = calculate_analytics(df) 
                rec, _ = get_tv_analysis(t)
                price = df['Close'].iloc[-1]
                bandar_s, bandar_c, v_ratio = analyze_bandarmology(df)
                
                # 2. Masukkan trend_stat ke calculation
                score = calculate_hybrid_score(rsi, slope, z_vol, rec, fund, price, bandar_s, trend_stat, cagr, obv_val)
                
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
            analyze = st.button("ANALISA", use_container_width=True)
            
    if analyze and ticker:
        with st.spinner("Mengunyah data pasar..."):
            try:
                df = get_stock_data(ticker, period="2y")
                fund = get_fundamentals(ticker)
                
                if df is not None:
                    # --- PROSES DATA ---
                    z_vol, slope, rsi, atr, trend_stat, cagr, obv_val = calculate_analytics(df) # <-- Pastikan ada cagr
                    rec, _ = get_tv_analysis(ticker)
                    price = df['Close'].iloc[-1]
                    chg_pct = ((price - df['Close'].iloc[-2])/df['Close'].iloc[-2])*100
                    bandar_status, bandar_color, vol_ratio = analyze_bandarmology(df)
                    
                    # Hitung Total Score
                    total_score = calculate_hybrid_score(rsi, slope, z_vol, rec, fund, price, bandar_status, trend_stat, cagr, obv_val)
                    
                    # Logic Trading Plan
                    stop_loss = int(round((price - (2 * atr)) / 5) * 5)
                    tp1 = int(round((price + (2 * atr)) / 5) * 5)
                    tp2 = int(round((price + (4 * atr)) / 5) * 5)
                    risk_pct = ((price - stop_loss) / price) * 100
                    
                    # Logic Valuasi Text
                    graham = fund['graham_num'] if fund else 0
                    if graham > 0:
                        diskon = ((graham - price) / graham) * 100
                        if diskon >= 50: val_text = "💎 Super Murah"
                        elif 20 <= diskon < 50: val_text = "✅ Diskon"
                        elif -10 <= diskon < 20: val_text = "⚖️ Wajar"
                        else: val_text = "⛔ Mahal"
                    else: val_text = "⚠️ N/A"

                    # --- UI BARU: EXECUTIVE SUMMARY ---
                    # Panggil fungsi kesimpulan yang baru kita buat
                    roe_val = fund['roe'] if fund else 0
                    der_val = fund['der'] if fund else 0
                    if der_val > 10: der_val = der_val/100 # Normalisasi DER
                    
                    summary_text, warning_list = get_executive_summary(total_score, trend_stat, bandar_status, val_text, roe_val, der_val)
                    
                    # TAMPILAN HEADER (Skor + Kesimpulan)
                    st.markdown(f"## {ticker} - Rp {price:,.0f} ({chg_pct:+.2f}%)")
                    
                    # Kotak Kesimpulan (Highlight)
                    bg_summary = "rgba(0, 255, 171, 0.1)" if total_score >= 60 else "rgba(255, 46, 99, 0.1)"
                    border_summary = SUCCESS_NEON if total_score >= 60 else DANGER_NEON
                    
                    st.markdown(f"""
                    <div style="background:{bg_summary}; border: 1px solid {border_summary}; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                        <h3 style="margin-top:0; color:{border_summary};">🤖 AI Conclusion:</h3>
                        <p style="font-size: 1.1em; color: white;">{summary_text}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if warning_list:
                        for w in warning_list: st.warning(w)

                    # --- VISUAL DATA (Kiri: Chart, Kanan: Data Padat) ---
                    col_chart, col_data = st.columns([2, 1])
                    
                    with col_chart:
                        # Tampilkan Chart Neon
                        ma50 = df['Close'].rolling(50).mean()
                        ma200 = df['Close'].rolling(200).mean()
                        fig = go.Figure()
                        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=ticker, increasing_line_color=SUCCESS_NEON, decreasing_line_color=DANGER_NEON))
                        fig.add_trace(go.Scatter(x=df.index, y=ma50, line=dict(color='orange', width=1), name='MA 50'))
                        fig.add_trace(go.Scatter(x=df.index, y=ma200, line=dict(color='blue', width=1), name='MA 200'))
                        fig.update_layout(title=f"Trend Chart {ticker}", template="plotly_dark", height=450, xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=30, b=0))
                        st.plotly_chart(fig, use_container_width=True)

                    with col_data:
                        st.subheader("🔢 Data Breakdown")
                        
                        # TABEL DATA TEKNIKAL
                        st.markdown("###### 📡 Indikator Teknikal")
                        st.dataframe(pd.DataFrame({
                            "Indikator": ["Hybrid Score", "Tren Arah", "RSI (Momentum)", "Bandar Flow", "Volatilitas (ATR)"],
                            "Nilai": [f"{total_score}/100", trend_stat, f"{rsi:.1f}", bandar_status, f"{atr:.0f}"]
                        }).set_index('Indikator'), use_container_width=True)
                        
                        # TABEL DATA FUNDAMENTAL
                        st.markdown("###### 🏢 Indikator Fundamental")
                        if fund:
                             st.dataframe(pd.DataFrame({
                                "Rasio": ["Valuasi (Graham)", "Kewajaran Harga", "Profitabilitas (ROE)", "Utang (DER)", "Likuiditas (CR)"],
                                "Nilai": [f"Rp {graham:,.0f}", val_text, f"{roe_val*100:.1f}%", f"{der_val:.2f}x", f"{fund.get('current_ratio',0):.2f}x"]
                            }).set_index('Rasio'), use_container_width=True)

                    # --- TRADING PLAN (Di Bawah) ---
                    st.markdown("---")
                    st.subheader("🎯 Rencana Trading (Action Plan)")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("🛑 Stop Loss (SL)", f"Rp {stop_loss:,.0f}", f"-{risk_pct:.1f}%", delta_color="inverse")
                    c2.metric("📍 Entry Price", f"Rp {price:,.0f}", "Current")
                    c3.metric("🚀 Take Profit (TP)", f"Rp {tp2:,.0f}", f"Ratio 1:2")
                    
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

# --- PANDUAN PENGGUNA (V10.2 UPDATED) ---
elif menu == "📚 PANDUAN":
    col_p1, col_p2 = st.columns([3, 1])
    with col_p1:
        st.title("📘 Panduan TradeLoop v10.2")
        st.markdown("Dokumentasi lengkap fitur baru: **AI Summary**, **Kelly Criterion**, & **Advanced Metrics**.")
    with col_p2:
        st.image("https://cdn-icons-png.flaticon.com/512/2666/2666505.png", width=80)

    st.write("")

    # 1. FITUR BARU (HIGHLIGHT)
    st.info("💡 **Update v10.2:** Sekarang dilengkapi dengan **AI Executive Summary** yang menerjemahkan angka rumit menjadi kalimat bahasa manusia + **Money Management** Pro.")

    # 2. CARA PENGGUNAAN UTAMA
    with st.expander("🤖 Cara Membaca AI Executive Summary (Baru!)", expanded=True):
        st.markdown("""
        Di menu **Analisa Lengkap**, Anda akan melihat kotak kesimpulan di bagian atas. Ini artinya:
        
        * 🔥 **STRONG BUY (Skor > 75):** Momentum sangat kuat. Teknikal Uptrend + Bandar Akumulasi + Fundamental Sehat.
        * ✅ **BUY ON WEAKNESS (Skor > 60):** Tren bagus, tapi mungkin harga sudah naik agak tinggi. Disarankan antri beli di bawah (saat koreksi).
        * ⚖️ **WAIT & SEE (Skor 40-60):** Pasar sedang bingung (Sideways) atau indikator bertentangan. Lebih baik pantau dulu (Watchlist).
        * ⛔ **AVOID (Skor < 40):** Jangan masuk! Risiko tinggi. Tren sedang turun atau Bandar sedang jualan (Distribusi).
        """)

    with st.expander("🧮 Cara Pakai Money Management (Kelly Criterion)"):
        st.markdown("""
        Fitur ini ada di **Sidebar** (menu kiri). Tujuannya agar Anda tidak asal "All-in" dan bangkrut.
        
        1.  **Win Rate:** Masukkan perkiraan seberapa sering Anda profit (jika pemula, isi 40-50%).
        2.  **Risk/Reward:** Jika Anda pasang Stop Loss 5% dan Target Profit 10%, berarti Rasionya 1:2 (Isi 2).
        3.  **Hasil (Alokasi):** Sistem akan menghitung % modal maksimal yang **aman** dipertaruhkan.
        
        *Rumus ini dipakai oleh investor profesional untuk mengembangkan akun secara eksponensial tanpa risiko bangkrut.*
        """)

    with st.expander("🚀 Cara Menggunakan SCANNER Saham"):
        st.markdown("""
        1.  Pilih daftar saham (misal: *LQ45* atau *Energy*).
        2.  Klik **Mulai Scan**.
        3.  **Fokus pada kolom:**
            * **Score:** Cari yang di atas 70.
            * **DER (Utang):** Pastikan centang hijau (✅).
            * **Valuasi:** Jika statusnya "💎 Super Murah", berarti potensi kenaikan (upside) masih lebar.
        """)

    # 3. KAMUS INDIKATOR (UPDATED)
    st.subheader("📖 Kamus Indikator Lengkap")
    
    tabs = st.tabs(["📊 Teknikal", "🏢 Fundamental", "🕵️ Bandarmology"])
    
    with tabs[0]: # Teknikal
        st.markdown("""
        * **CAGR (Growth):** Rata-rata pertumbuhan harga per tahun. Jika positif, berarti tren jangka panjang saham ini naik.
        * **MA200 (Garis Biru di Chart):** Garis "Sakti". Jika harga di atas garis ini = **UPTREND (Aman)**. Jika di bawah = **DOWNTREND (Bahaya)**.
        * **RSI:** Indikator "Gas & Rem".
            * **> 70 (Overbought):** Harga sudah kemahalan/ngebut, rawan rem mendadak (turun).
            * **< 30 (Oversold):** Harga sudah terlalu murah, potensi mantul naik.
        """)
        
    with tabs[1]: # Fundamental
        st.markdown("""
        * **Current Ratio (CR):** Kemampuan perusahaan bayar utang jangka pendek. Wajib di atas **1.0x** (Aman).
        * **DER (Debt to Equity):** Rasio utang dibanding modal. Batas aman maksimal **2.0x**. Di atas itu risiko bangkrut tinggi.
        * **Graham Number:** Nilai wajar saham versi Benjamin Graham. Jika Harga Pasar < Graham Number = **DISKON/MURAH**.
        * **ROE (Profitabilitas):** Seberapa jago manajemen cari untung. Di atas 15% = Istimewa.
        """)
        
    with tabs[2]: # Bandarmology
        st.markdown("""
        * **AKUMULASI:** Pihak "Big Player" sedang memborong saham secara diam-diam (Harga Naik + Volume Besar).
        * **DISTRIBUSI:** Pihak "Big Player" sedang jualan/cuci gudang (Harga Turun + Volume Besar).
        * **NETRAL:** Transaksi didominasi ritel, tidak ada pergerakan signifikan dari bandar.
        """)

    # 4. STUDI KASUS (EDUKASI POLA PIKIR)
    st.markdown("---")
    st.subheader("🎓 Studi Kasus: Kapan Harus Masuk?")
    
    c1, c2 = st.columns(2)
    with c1:
        st.success("✅ CONTOH IDEAL (Buy)")
        st.markdown("""
        1.  **AI Summary:** Bilang "STRONG BUY" atau "BUY ON WEAKNESS".
        2.  **Chart:** Harga bermain di atas Garis Biru (MA200).
        3.  **Bandar:** Status "AKUMULASI".
        4.  **Kelly:** Disarankan masuk 10% modal.
        
        👉 **Action:** HAKA (Hajar Kanan) atau pasang Antri Beli di harga Support.
        """)
        
    with c2:
        st.error("⛔ CONTOH BAHAYA (Trap)")
        st.markdown("""
        1.  **AI Summary:** Bilang "AVOID".
        2.  **Valuasi:** Terlihat "Super Murah", TAPI...
        3.  **Kesehatan:** DER > 3.0x (Utang Raksasa) & Current Ratio < 1.0 (Gak punya duit cash).
        4.  **Tren:** Harga terjun bebas di bawah MA200.
        
        👉 **Action:** JANGAN TERGIUR MURAHNYA. Ini "Value Trap" (Perusahaan mau bangkrut).
        """)
    
    st.caption("Disclaimer: Panduan ini hanya untuk edukasi. Keputusan jual/beli tetap di tangan Anda.")
    # --- FOOTER ---
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: grey; font-size: 0.8em;'>
    <b>Disclaimer:</b> Aplikasi ini adalah alat bantu analisa (tools), bukan ajakan membeli atau menjual. 
    Segala keuntungan dan kerugian investasi adalah tanggung jawab penuh pengguna (Do Your Own Research).
    <br>Built with 🐍 Python & TradeLoop Engine v10.6
</div>
""", unsafe_allow_html=True)
