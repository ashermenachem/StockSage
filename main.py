import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import numpy as np

from utils.stock_data import get_stock_data, get_company_info
from utils.technical_analysis import calculate_indicators, generate_signals
from utils.database import get_db, engine, Base
from utils.portfolio_manager import PortfolioManager
from models.portfolio import Position

# Initialize database
Base.metadata.create_all(bind=engine)

# Page config
st.set_page_config(
    page_title="Stock Market Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open('styles/custom.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Initialize session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = 1  # Demo user
if 'portfolio_id' not in st.session_state:
    st.session_state.portfolio_id = 1  # Demo portfolio

# Initialize PortfolioManager
db = next(get_db())
portfolio_manager = PortfolioManager(db)

# Sidebar
st.sidebar.title("Stock Analysis")
tab = st.sidebar.radio("Navigation", ["Market Analysis", "Portfolio", "Watchlist"])

if tab == "Market Analysis":
    # Stock Analysis Section
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

        # Add buy/sell markers
        buy_signals = df[df['Signal'] == 'BUY'].index
        sell_signals = df[df['Signal'] == 'SELL'].index

        fig.add_trace(go.Scatter(
            x=buy_signals,
            y=df.loc[buy_signals, 'Low'] * 0.99,
            mode='markers',
            name='Buy Signal',
            marker=dict(symbol='triangle-up', size=15, color='#4CAF50'),
        ), row=1, col=1)

        fig.add_trace(go.Scatter(
            x=sell_signals,
            y=df.loc[sell_signals, 'High'] * 1.01,
            mode='markers',
            name='Sell Signal',
            marker=dict(symbol='triangle-down', size=15, color='#FF5252'),
        ), row=1, col=1)

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

        # Trading Actions
        st.subheader("Trading Actions")
        col1, col2 = st.columns(2)

        with col1:
            shares = st.number_input("Number of Shares", min_value=0.0, step=0.1)

        with col2:
            if st.button("Add to Portfolio"):
                portfolio_manager.add_position(
                    st.session_state.portfolio_id,
                    symbol,
                    shares,
                    current_price
                )
                st.success(f"Added {shares} shares of {symbol} to portfolio")

    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.info("Please enter a valid stock symbol and try again.")

elif tab == "Portfolio":
    st.title("Portfolio Overview")

    # Get portfolio positions
    positions = db.query(Position).filter(Position.portfolio_id == st.session_state.portfolio_id).all()

    if positions:
        # Create portfolio summary
        portfolio_data = []
        total_value = 0

        for position in positions:
            current_price = get_stock_data(position.symbol, '1d')['Close'].iloc[-1]
            market_value = position.shares * current_price
            gain_loss = market_value - (position.shares * position.average_price)
            gain_loss_pct = (gain_loss / (position.shares * position.average_price)) * 100

            portfolio_data.append({
                'Symbol': position.symbol,
                'Shares': position.shares,
                'Avg Price': f"${position.average_price:.2f}",
                'Current Price': f"${current_price:.2f}",
                'Market Value': f"${market_value:.2f}",
                'Gain/Loss': f"${gain_loss:.2f}",
                'Gain/Loss %': f"{gain_loss_pct:.2f}%"
            })
            total_value += market_value

        # Display portfolio summary
        st.metric("Total Portfolio Value", f"${total_value:,.2f}")

        # Create portfolio table
        df_portfolio = pd.DataFrame(portfolio_data)
        st.dataframe(df_portfolio, use_container_width=True)

    else:
        st.info("No positions in portfolio. Add some stocks to get started!")

elif tab == "Watchlist":
    st.title("Watchlist")

    # Add to watchlist
    col1, col2 = st.columns(2)
    with col1:
        new_symbol = st.text_input("Add Symbol to Watchlist").upper()
    with col2:
        price_alert = st.number_input("Price Alert (optional)", min_value=0.0, step=0.1)

    if st.button("Add to Watchlist"):
        portfolio_manager.add_to_watchlist(st.session_state.user_id, new_symbol, price_alert)
        st.success(f"Added {new_symbol} to watchlist")

    # Display watchlist
    watchlist = portfolio_manager.get_watchlist(st.session_state.user_id)

    if watchlist:
        watchlist_data = []
        for item in watchlist:
            current_data = get_stock_data(item.symbol, '1d')
            current_price = current_data['Close'].iloc[-1]
            price_change = current_price - current_data['Open'].iloc[0]
            price_change_pct = (price_change / current_data['Open'].iloc[0]) * 100

            watchlist_data.append({
                'Symbol': item.symbol,
                'Current Price': f"${current_price:.2f}",
                'Change': f"${price_change:.2f}",
                'Change %': f"{price_change_pct:.2f}%",
                'Alert Price': f"${item.price_alert:.2f}" if item.price_alert else "None"
            })

        df_watchlist = pd.DataFrame(watchlist_data)
        st.dataframe(df_watchlist, use_container_width=True)
    else:
        st.info("Your watchlist is empty. Add some stocks to track!")