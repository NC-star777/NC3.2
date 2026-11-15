import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Algorithmic Stock Screener & Backtester", layout="wide")

st.title("📈 Algorithmic Stock Screener & Backtester")
st.write("Welcome to your live algorithmic stock screener and backtesting application!")

# Sidebar inputs
st.sidebar.header("Configuration")
ticker_input = st.sidebar.text_input("Enter Ticker Symbol", value="AAPL").upper()
period_input = st.sidebar.selectbox("Historical Period", ["1y", "2y", "5y"], index=0)

if st.sidebar.button("Run Analysis"):
    try:
        ticker = yf.Ticker(ticker_input)
        hist = ticker.history(period=period_input)
        
        if hist.empty:
            st.error(f"No historical data found for {ticker_input}. Please check the symbol.")
        else:
            st.success(f"Data successfully loaded for {ticker_input}!")
            
            # Calculations
            hist['MA50'] = hist['Close'].rolling(window=50).mean()
            hist['MA200'] = hist['Close'].rolling(window=200).mean()
            
            c_price = hist['Close'].iloc[-1]
            ma50 = hist['MA50'].iloc[-1]
            ma200 = hist['MA200'].iloc[-1]
            
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rsi_val = (100 - (100 / (1 + (gain / loss)))).iloc[-1]
            
            # Display metrics
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Price", f"${c_price:.2f}")
            col2.metric("50-Day MA", f"${ma50:.2f}" if not pd.isna(ma50) else "N/A")
            col3.metric("RSI (14)", f"{rsi_val:.1f}" if not pd.isna(rsi_val) else "N/A")
            
            # Plotly chart
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name='Close Price'))
            fig.add_trace(go.Scatter(x=hist.index, y=hist['MA50'], mode='lines', name='50 MA'))
            fig.update_layout(title=f"{ticker_input} Price Chart", xaxis_title="Date", yaxis_title="Price ($)")
            st.plotly_chart(fig, use_container_width=True)
            
    except Exception as e:
        st.error(f"An error occurred during analysis: {e}")
