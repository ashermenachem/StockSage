import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import numpy as np
from typing import List, Optional

from utils.stock_data import get_stock_data, get_company_info
from utils.technical_analysis import calculate_indicators, generate_signals
from utils.database import get_db, engine, Base
from models.portfolio import Position
from utils.portfolio_manager import PortfolioManager
from utils.paper_trading_manager import PaperTradingManager, AssetType, OrderSide, OrderType
from utils.news_analyzer import NewsAnalyzer
from utils.stock_screener import StockScreener # Add after the existing imports

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
paper_trading_manager = PaperTradingManager(db)

# Sidebar
st.sidebar.title("Stock Analysis")
tab = st.sidebar.radio("Navigation", ["Market Analysis", "Portfolio", "Paper Trading", "Watchlist"])

if tab == "Market Analysis":
    # Left sidebar for analysis controls
    st.sidebar.subheader("Analysis Settings")

    # More timeframe options
    period = st.sidebar.selectbox(
        "Select Time Period",
        options=['1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', 'ytd', 'max'],
        index=3
    )

    # Indicator selection
    available_indicators = [
        'SMA', 'EMA', 'MACD', 'RSI', 'Bollinger',
        'Stochastic', 'Williams', 'ATR', 'Volume', 'Ichimoku'
    ]
    selected_indicators = st.sidebar.multiselect(
        "Select Technical Indicators",
        options=available_indicators,
        default=['SMA', 'MACD', 'RSI', 'Bollinger']
    )

    # Stock selection methods
    search_method = st.sidebar.radio(
        "Stock Search Method",
        ["Symbol Search", "Stock Screener"]
    )

    if search_method == "Symbol Search":
        symbol = st.sidebar.text_input("Enter Stock Symbol", value="AAPL").upper()
    else:
        st.sidebar.subheader("Stock Screener")

        screener = StockScreener()
        screener_mode = st.sidebar.selectbox(
            "Screener Mode",
            ["Quick Scan", "Technical Patterns", "Custom Filter"]
        )

        if screener_mode == "Quick Scan":
            if st.sidebar.button("Find Top Movers"):
                with st.spinner("Scanning market movements..."):
                    movers = screener.get_top_movers()

                    st.subheader("Top Gainers")
                    gainers_df = pd.DataFrame(movers['gainers'])
                    st.dataframe(gainers_df)

                    st.subheader("Top Losers")
                    losers_df = pd.DataFrame(movers['losers'])
                    st.dataframe(losers_df)

        elif screener_mode == "Technical Patterns":
            pattern_symbols = st.sidebar.text_input(
                "Enter symbols to scan (comma-separated)",
                value="AAPL,MSFT,GOOGL"
            ).split(',')

            if st.sidebar.button("Scan Patterns"):
                with st.spinner("Scanning for technical patterns..."):
                    patterns = screener.scan_technical_patterns(pattern_symbols)
                    if patterns:
                        st.subheader("Technical Patterns Found")
                        for result in patterns:
                            st.markdown(f"""
                            **{result['symbol']}** - Price: ${result['last_price']:.2f}
                            - Patterns: {', '.join(result['patterns'])}
                            """)
                    else:
                        st.info("No significant patterns found")

        else:  # Custom Filter
            with st.sidebar.expander("Price Criteria"):
                price_range = st.slider(
                    "Price Range ($)",
                    min_value=0,
                    max_value=1000,
                    value=(0, 500)
                )

            with st.sidebar.expander("Volume Criteria"):
                min_volume = st.number_input(
                    "Minimum Volume",
                    min_value=0,
                    value=100000
                )

            with st.sidebar.expander("Technical Indicators"):
                rsi_range = st.slider(
                    "RSI Range",
                    min_value=0,
                    max_value=100,
                    value=(30, 70)
                )

                macd_range = st.slider(
                    "MACD Range",
                    min_value=-10.0,
                    max_value=10.0,
                    value=(-5.0, 5.0)
                )

            if st.sidebar.button("Run Custom Screen"):
                with st.spinner("Filtering stocks..."):
                    criteria = {
                        'price': {'min': price_range[0], 'max': price_range[1]},
                        'volume': {'min': min_volume},
                        'rsi': {'min': rsi_range[0], 'max': rsi_range[1]},
                        'macd': {'min': macd_range[0], 'max': macd_range[1]}
                    }

                    results = screener.filter_stocks(criteria)
                    if results:
                        st.subheader("Screening Results")
                        results_df = pd.DataFrame(results)
                        st.dataframe(results_df)
                    else:
                        st.info("No stocks match the selected criteria")


    try:
        # Fetch Data
        df = get_stock_data(symbol, period)
        info = get_company_info(symbol)

        # Calculate indicators with selected ones
        df = calculate_indicators(df, selected_indicators)
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

        # Trading Signal Card
        signal_col1, signal_col2 = st.columns(2)
        with signal_col1:
            st.markdown("<div class='trading-card'>", unsafe_allow_html=True)
            current_signal = df['Signal'].iloc[-1]
            signal_strength = df['Signal_Strength'].iloc[-1]
            signal_color = "#4CAF50" if current_signal == "BUY" else "#FF5252" if current_signal == "SELL" else "#1E88E5"

            st.markdown(f"<h3 style='color: {signal_color}'>Trading Signal: {current_signal}</h3>", unsafe_allow_html=True)
            st.markdown(f"Signal Strength: {signal_strength:.1f}/3")
            st.markdown("Based on multiple technical indicators")
            st.markdown("</div>", unsafe_allow_html=True)

        # Create main chart
        chart_container = st.container()
        with chart_container:
            # Chart type selection
            chart_type = st.radio(
                "Chart Type",
                ["Candlestick", "Line", "Area"],
                horizontal=True
            )

            fig = make_subplots(rows=2, cols=1, row_heights=[0.7, 0.3],
                                shared_xaxes=True, vertical_spacing=0.03)

            # Main price chart
            if chart_type == "Candlestick":
                fig.add_trace(go.Candlestick(
                    x=df.index,
                    open=df['Open'],
                    high=df['High'],
                    low=df['Low'],
                    close=df['Close'],
                    name="OHLC"
                ), row=1, col=1)
            elif chart_type == "Line":
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['Close'],
                    name="Price",
                    line=dict(color='#1E88E5')
                ), row=1, col=1)
            else:  # Area
                fig.add_trace(go.Scatter(
                    x=df.index,
                    y=df['Close'],
                    name="Price",
                    fill='tozeroy',
                    line=dict(color='#1E88E5')
                ), row=1, col=1)

            # Add selected indicators
            if 'SMA' in selected_indicators:
                for ma in ['SMA_20', 'SMA_50', 'SMA_200']:
                    if ma in df.columns:
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df[ma],
                            name=ma,
                            line=dict(dash='dash')
                        ), row=1, col=1)

            if 'Bollinger' in selected_indicators:
                for band in ['BB_High', 'BB_Low', 'BB_Mid']:
                    if band in df.columns:
                        fig.add_trace(go.Scatter(
                            x=df.index,
                            y=df[band],
                            name=band,
                            line=dict(dash='dash')
                        ), row=1, col=1)

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

            # Volume chart
            colors = ['#FF5252' if row['Open'] > row['Close'] else '#4CAF50' for index, row in df.iterrows()]
            fig.add_trace(go.Bar(
                x=df.index,
                y=df['Volume'],
                name='Volume',
                marker_color=colors
            ), row=2, col=1)

            # Update layout
            fig.update_layout(
                height=800,
                showlegend=True,
                xaxis_rangeslider_visible=False,
                template='plotly_white'
            )

            st.plotly_chart(fig, use_container_width=True)

        # News Section
        st.subheader("Market News & Sentiment")
        news_tabs = st.tabs(["Stock News", "Market News"])

        # Initialize news analyzer
        news_analyzer = NewsAnalyzer()

        with news_tabs[0]:
            # Stock-specific news
            if 'symbol' in locals():
                stock_news = news_analyzer.get_stock_news(info['name'])
                if stock_news:
                    for article in stock_news:
                        with st.container():
                            st.markdown(f"""
                            <div style='padding: 10px; border-left: 4px solid {article['sentiment_color']}; margin: 10px 0;'>
                            <h4>{article['title']}</h4>
                            <p>{article['description']}</p>
                            <p><small>Source: {article['source']} | 
                            Sentiment: {article['sentiment']} ({article['sentiment_score']:.2f})</small></p>
                            <a href='{article['url']}' target='_blank'>Read more</a>
                            </div>
                            """, unsafe_allow_html=True)
                else:
                    st.info("No recent news found for this stock.")

        with news_tabs[1]:
            # General market news
            market_news = news_analyzer.get_market_news()
            if market_news:
                for article in market_news:
                    with st.container():
                        st.markdown(f"""
                        <div style='padding: 10px; border-left: 4px solid {article['sentiment_color']}; margin: 10px 0;'>
                        <h4>{article['title']}</h4>
                        <p>{article['description']}</p>
                        <p><small>Source: {article['source']} | 
                        Sentiment: {article['sentiment']} ({article['sentiment_score']:.2f})</small></p>
                        <a href='{article['url']}' target='_blank'>Read more</a>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No recent market news found.")


        # Technical Indicators Section
        st.subheader("Technical Indicators")
        indicator_cols = st.columns(3)

        # RSI
        if 'RSI' in selected_indicators:
            with indicator_cols[0]:
                st.markdown("<div class='trading-card'>", unsafe_allow_html=True)
                st.metric("RSI", f"{df['RSI'].iloc[-1]:.2f}")
                rsi_status = "Overbought" if df['RSI'].iloc[-1] > 70 else "Oversold" if df['RSI'].iloc[-1] < 30 else "Neutral"
                st.markdown(f"Status: {rsi_status}")
                st.markdown("</div>", unsafe_allow_html=True)

        # MACD
        if 'MACD' in selected_indicators:
            with indicator_cols[1]:
                st.markdown("<div class='trading-card'>", unsafe_allow_html=True)
                macd_signal = "Bullish" if df['MACD'].iloc[-1] > df['MACD_Signal'].iloc[-1] else "Bearish"
                st.metric("MACD", f"{df['MACD'].iloc[-1]:.2f}")
                st.markdown(f"Signal: {macd_signal}")
                st.markdown("</div>", unsafe_allow_html=True)

        # Volume Analysis
        if 'Volume' in selected_indicators:
            with indicator_cols[2]:
                st.markdown("<div class='trading-card'>", unsafe_allow_html=True)
                avg_volume = df['Volume'].mean()
                current_volume = df['Volume'].iloc[-1]
                volume_change = (current_volume - avg_volume) / avg_volume * 100
                st.metric("Volume", f"{current_volume:,.0f}", f"{volume_change:.1f}%")
                st.markdown("</div>", unsafe_allow_html=True)

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

elif tab == "Paper Trading":
    st.title("Paper Trading")

    # Initialize paper trading account if not exists
    if 'paper_account_id' not in st.session_state:
        account = paper_trading_manager.create_paper_account(st.session_state.user_id)
        st.session_state.paper_account_id = account.id

    # Get account information
    balance = paper_trading_manager.get_account_balance(st.session_state.paper_account_id)
    positions = paper_trading_manager.get_positions(st.session_state.paper_account_id)

    # Display account summary
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Paper Trading Balance", f"${balance:,.2f}")

    # Trading interface
    st.subheader("New Trade")
    col1, col2, col3 = st.columns(3)

    with col1:
        symbol = st.text_input("Symbol", value="AAPL").upper()
        asset_type = st.selectbox("Asset Type", ["Stock", "Crypto", "Option"])

    with col2:
        order_side = st.selectbox("Order Type", ["Buy", "Sell", "Short"])
        quantity = st.number_input("Quantity", min_value=0.0, step=0.1)

    with col3:
        current_price = get_stock_data(symbol, '1d')['Close'].iloc[-1]
        st.metric("Current Price", f"${current_price:.2f}")
        if st.button("Place Order"):
            try:
                order = paper_trading_manager.place_order(
                    account_id=st.session_state.paper_account_id,
                    symbol=symbol,
                    order_side=OrderSide(order_side.lower()),
                    quantity=quantity,
                    price=current_price,
                    asset_type=AssetType(asset_type.lower())
                )
                st.success(f"Order placed successfully: {order_side} {quantity} {symbol}")
            except Exception as e:
                st.error(f"Error placing order: {str(e)}")

    # Display positions
    if positions:
        st.subheader("Current Positions")
        # Update position values
        paper_trading_manager.update_positions_value(st.session_state.paper_account_id)

        position_data = []
        for position in positions:
            position_data.append({
                'Symbol': position.symbol,
                'Type': position.asset_type.value,
                'Quantity': position.quantity,
                'Avg Price': f"${position.average_price:.2f}",
                'Current Price': f"${position.current_price:.2f}",
                'P/L': f"${position.unrealized_pnl:.2f}"
            })

        df_positions = pd.DataFrame(position_data)
        st.dataframe(df_positions, use_container_width=True)
    else:
        st.info("No open positions. Start trading to build your portfolio!")

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