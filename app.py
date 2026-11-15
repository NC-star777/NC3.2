import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import json
import os

# 1. Page Configuration
st.set_page_config(
    page_title="NC2 Algorithmic Stock Screener & Persistent Backtester",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; padding: 15px; border-radius: 10px; border: 1px solid #30363d; }
    </style>
""", unsafe_allow_html=True)

# Persistent Storage File for Quarters
STORAGE_FILE = "nc2_quarterly_storage.json"

def load_persistent_storage():
    if os.path.exists(STORAGE_FILE):
        try:
            with open(STORAGE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_persistent_storage(data):
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f, indent=4)

# S&P 500 Universe Dictionary
SP500_UNIVERSE = {
    "Information Technology": ["AAPL", "MSFT", "NVDA", "AVGO", "ORCL", "CRM", "AMD", "ACN", "QCOM", "IBM"],
    "Financials": ["BRK-B", "JPM", "V", "MA", "BAC", "WFC", "GS", "MS", "SPGI", "BLK"],
    "Health Care": ["LLY", "UNH", "JNJ", "ABBV", "MRK", "TMO", "ABT", "ISRG", "PFE", "AMGN"],
    "Consumer Discretionary": ["AMZN", "TSLA", "HD", "MCD", "DIS", "NKE", "LOW", "SBUX", "BKNG", "TJX"],
    "Communication Services": ["GOOGL", "META", "NFLX", "TMUS", "VZ", "T", "CMCSA", "EA", "TTWO"],
    "Industrials": ["GE", "CAT", "RTX", "UNP", "HON", "UPS", "BA", "DE", "LMT", "ETN"],
    "Consumer Staples": ["WMT", "PG", "COST", "KO", "PEP", "PM", "MO", "CL", "MDLZ", "TGT"],
    "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "KMI"],
    "Utilities": ["NEE", "SO", "DUK", "CEG", "SRE", "AEP", "PCG", "EXC", "XEL", "ED"],
    "Real Estate": ["PLD", "AMT", "EQIX", "SPG", "O", "WELL", "PSA", "VICI", "CBRE", "CCI"],
    "Materials": ["LIN", "SHW", "FCX", "APD", "ECL", "NEM", "CTVA", "DOW", "PPG", "MLM"]
}

@st.cache_data(ttl=3600)
def calculate_nc2_score(ticker_symbol):
    """Calculates the 13-factor NC2 score for a given ticker."""
    try:
        stock = yf.Ticker(ticker_symbol)
        hist = stock.history(period="1y")
        info = stock.info

        if hist.empty:
            return 1, {}

        forward_pe = info.get('forwardPE', None)
        earnings_growth = info.get('earningsGrowth', 0.10)
        if earnings_growth is None: earnings_growth = 0.10
        f1_score = 50 if not forward_pe or forward_pe <= 0 else round(max(1, min(100, 50 + (25 * min(2.0, (10 + (2 * max(0, earnings_growth * 100))) / forward_pe)))))
        
        rec_mean = info.get('recommendationMean', None)
        f2_score = round(max(1, min(100, 100 - ((rec_mean - 1.0) * 25)))) if rec_mean else 50

        rec_key = info.get('recommendationKey', 'hold').lower()
        f3_score = {'strong_buy': 95, 'buy': 75, 'hold': 50, 'sell': 25, 'strong_sell': 5}.get(rec_key, 50)

        summary = info.get('longBusinessSummary', '').lower()
        f4_score = 25 if ("lawsuit" in summary or "investigation" in summary) else 85

        window = hist.tail(170)
        if len(window) < 10:
            f5_score = 50
        else:
            high, low, curr = window['High'].max(), window['Low'].min(), window['Close'].iloc[-1]
            ratio = 0.5 if high == low else (curr - low) / (high - low)
            f5_score = round(max(1, min(100, 100 - (abs(ratio - 0.5) * 100))))

        f6_score = 80
        insider = info.get('heldPercentInsiders', None)
        f7_score = round(max(1, min(100, (insider * 100 * 2) + 50))) if insider is not None else 40

        fcf, mcap = info.get('freeCashflow', None), info.get('marketCap', None)
        f8_score = 50 if not fcf or not mcap or mcap == 0 else (95 if (fcf/mcap)*100 > 7 else 60)

        inst = info.get('heldPercentInstitutions', None)
        f9_score = 50 if inst is None else (90 if inst*100 > 70 else 50)

        f10_score, f11_score = 70, 70

        hist['MA50'] = hist['Close'].rolling(window=50).mean()
        hist['MA200'] = hist['Close'].rolling(window=200).mean()
        c_price, ma50, ma200 = hist['Close'].iloc[-1], hist['MA50'].iloc[-1], hist['MA200'].iloc[-1]
        f12_score = 100 if (c_price > ma50 and c_price > ma200) else 50
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi_val = (100 - (100 / (1 + (gain / loss)))).iloc[-1]
        f13_score = 100 if (40 <= rsi_val <= 65) else 50

        
