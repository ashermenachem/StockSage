import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import numpy as np

from utils.stock_data import get_stock_data, get_company_info
from utils.technical_analysis import calculate_indicators, generate_signals

# Page config
st.set_page_config(
    page_title="Stock Market Analysis",
    page_icon="📈",
    layout="wide"
)

# Load custom CSS
with open('styles/custom.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Sidebar
st.sidebar.title("Stock Analysis")
symbol = st.sidebar.text_input("Enter Stock Symbol", value="AAPL").upper()
period = st.sidebar.selectbox(
    "Select Time Period",
    options=['1mo', '3mo', '6mo', '1y', '2y', '5y'],
    index=3
)

try:
    # Fetch Data
    df = get_stock_data(symbol, period)
    info = get_company_info(symbol)
    
    # Calculate indicators
    df = calculate_indicators(df)
    df = generate_signals(df)
    
    # Main layout
    col1, col2, col3 = st.columns([2,1,1])
    
    with col1:
        st.markdown(f"<h1 class='stock-header'>{info['name']} ({symbol})</h1>", unsafe_allow_html=True)
    
    with col2:
        current_price = df['Close'].iloc[-1]
        price_change = df['Close'].iloc[-1] - df['Close'].iloc[-2]
        price_change_pct = (price_change / df['Close'].iloc[-2]) * 100
        
        st.metric(
            "Current Price",
            f"${current_price:.2f}",
            f"{price_change_pct:.2f}%",
            delta_color="normal"
        )
    
    with col3:
        st.metric("Market Cap", f"${info['market_cap']:,.0f}")
    
    # Create main chart
    fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3],
                        shared_xaxes=True, vertical_spacing=0.03)
    
    # Candlestick chart
    candlestick = go.Candlestick(
        x=df.index,
        open=df['Open'],
        high=df['High'],
        low=df['Low'],
        close=df['Close'],
        name="OHLC"
    )
    fig.add_trace(candlestick, row=1, col=1)
    
    # Add Moving Averages
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_20'], name='SMA 20',
                            line=dict(color='#1E88E5', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['SMA_50'], name='SMA 50',
                            line=dict(color='#FF5252', width=1)), row=1, col=1)
    
    # Add Bollinger Bands
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_High'], name='BB Upper',
                            line=dict(color='gray', width=1, dash='dash')), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df['BB_Low'], name='BB Lower',
                            line=dict(color='gray', width=1, dash='dash')), row=1, col=1)
    
    # Volume bars
    colors = ['#FF5252' if row['Open'] > row['Close'] else '#4CAF50' for index, row in df.iterrows()]
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name='Volume',
                        marker_color=colors), row=2, col=1)
    
    # Update layout
    fig.update_layout(
        height=800,
        showlegend=True,
        xaxis_rangeslider_visible=False,
        template='plotly_white'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Technical Indicators Section
    st.subheader("Technical Indicators")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("<div class='trading-card'>", unsafe_allow_html=True)
        st.metric("RSI", f"{df['RSI'].iloc[-1]:.2f}")
        rsi_status = "Overbought" if df['RSI'].iloc[-1] > 70 else "Oversold" if df['RSI'].iloc[-1] < 30 else "Neutral"
        st.markdown(f"Status: {rsi_status}")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='trading-card'>", unsafe_allow_html=True)
        macd_signal = "Bullish" if df['MACD'].iloc[-1] > df['MACD_Signal'].iloc[-1] else "Bearish"
        st.metric("MACD", f"{df['MACD'].iloc[-1]:.2f}")
        st.markdown(f"Signal: {macd_signal}")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<div class='trading-card'>", unsafe_allow_html=True)
        current_signal = df['Signal'].iloc[-1]
        signal_color = "#4CAF50" if current_signal == "BUY" else "#FF5252" if current_signal == "SELL" else "#1E88E5"
        st.metric("Trading Signal", current_signal)
        st.markdown(f"Based on technical analysis")
        st.markdown("</div>", unsafe_allow_html=True)

except Exception as e:
    st.error(f"Error: {str(e)}")
    st.info("Please enter a valid stock symbol and try again.")
