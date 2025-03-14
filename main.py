import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from datetime import datetime
import numpy as np

from utils.stock_data import get_stock_data, get_company_info
from utils.technical_analysis import calculate_indicators, generate_signals
from utils.database import get_db, engine, Base
from models.portfolio import Position
from utils.portfolio_manager import PortfolioManager
from utils.paper_trading_manager import PaperTradingManager, AssetType, OrderSide, OrderType
from utils.news_analyzer import NewsAnalyzer

# Initialize database
Base.metadata.create_all(bind=engine)

# Page config
st.set_page_config(
    page_title="Simple Stock Analysis",
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

# Initialize managers
db = next(get_db())
portfolio_manager = PortfolioManager(db)
paper_trading_manager = PaperTradingManager(db)

# Simple navigation
st.sidebar.title("Navigation")
tab = st.sidebar.radio("Choose what to do:", 
    ["📊 View Stock Charts", "💼 My Portfolio", "🎮 Paper Trading"])

if tab == "📊 View Stock Charts":
    st.title("Stock Charts - Simple & Easy")

    # Simple stock input
    symbol = st.text_input("Enter a stock symbol (example: AAPL for Apple):", value="AAPL").upper()

    # Simple timeframe selection
    period = st.select_slider(
        "How much history do you want to see?",
        options=['1d', '1wk', '1mo', '3mo', '6mo', '1y'],
        value='3mo'
    )

    try:
        # Fetch Data
        df = get_stock_data(symbol, period)
        info = get_company_info(symbol)

        # Display current price and change
        col1, col2 = st.columns(2)
        with col1:
            current_price = df['Close'].iloc[-1]
            price_change = df['Close'].iloc[-1] - df['Close'].iloc[-2]
            price_change_pct = (price_change / df['Close'].iloc[-2]) * 100

            st.metric(
                "Current Price",
                f"${current_price:.2f}",
                f"{price_change_pct:.2f}%"
            )

        # Calculate technical indicators and generate signals
        df = calculate_indicators(df, ['SMA', 'EMA', 'MACD', 'RSI', 'Bollinger', 'Volume'])
        df = generate_signals(df)

        # Simple chart
        fig = go.Figure()

        # Price line
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['Close'],
            name="Price",
            line=dict(color='#1E88E5', width=2)
        ))

        # Add simple moving averages
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['SMA_20'],
            name="20-day average",
            line=dict(color='#4CAF50', dash='dash')
        ))

        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['SMA_50'],
            name="50-day average",
            line=dict(color='#FF5252', dash='dash')
        ))
        
        # Add Buy signals
        buy_signals = df[df['Signal'] == 'BUY']
        if not buy_signals.empty:
            fig.add_trace(go.Scatter(
                x=buy_signals.index,
                y=buy_signals['Close'],
                mode='markers',
                name='Buy Signal',
                marker=dict(
                    symbol='triangle-up',
                    size=12,
                    color='green',
                    line=dict(width=1, color='darkgreen')
                )
            ))
            
        # Add Sell signals
        sell_signals = df[df['Signal'] == 'SELL']
        if not sell_signals.empty:
            fig.add_trace(go.Scatter(
                x=sell_signals.index,
                y=sell_signals['Close'],
                mode='markers',
                name='Sell Signal',
                marker=dict(
                    symbol='triangle-down',
                    size=12,
                    color='red',
                    line=dict(width=1, color='darkred')
                )
            ))

        # Update layout
        fig.update_layout(
            height=600,
            showlegend=True,
            xaxis_rangeslider_visible=False,
            template='plotly_white',
            yaxis_title="Price ($)",
            xaxis_title="Date"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Signal analysis
        st.subheader("Technical Analysis")
        
        # Display signal strength meter
        current_signal = df['Signal'].iloc[-1]
        signal_strength = df['Signal_Strength'].iloc[-1]
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Current Signal", current_signal, delta=f"Strength: {signal_strength:.1f}")
            
            # Signal explanation
            if current_signal == 'BUY':
                st.success("AI analysis suggests this may be a good time to buy.")
            elif current_signal == 'SELL':
                st.warning("AI analysis suggests this may be a good time to sell.")
            else:
                st.info("AI analysis suggests holding or no clear signal at this time.")
                
        with col2:
            # Traditional analysis
            if df['Close'].iloc[-1] > df['SMA_50'].iloc[-1]:
                st.success("The stock is trading above its 50-day average - this is usually positive.")
            else:
                st.warning("The stock is trading below its 50-day average - this might be concerning.")
            
            # RSI indicator interpretation
            if 'RSI' in df.columns:
                rsi_value = df['RSI'].iloc[-1]
                st.write(f"RSI: {rsi_value:.1f}")
                if rsi_value < 30:
                    st.info("RSI indicates the stock may be oversold.")
                elif rsi_value > 70:
                    st.info("RSI indicates the stock may be overbought.")

        # Recent news
        st.subheader("Recent News")
        news_analyzer = NewsAnalyzer()
        news = news_analyzer.get_stock_news(info['name'], days=3)

        if news:
            for article in news[:3]:  # Show only top 3 news
                st.markdown(f"""
                **{article['title']}**  
                {article['description']}  
                [Read more]({article['url']})
                """)
        else:
            st.info("No recent news found.")

    except Exception as e:
        st.error("Oops! Something went wrong. Please check the stock symbol and try again.")

elif tab == "💼 My Portfolio":
    st.title("My Portfolio")

    # Get portfolio positions
    positions = db.query(Position).filter(Position.portfolio_id == st.session_state.portfolio_id).all()

    # Add position
    with st.expander("Add New Stock to Portfolio"):
        col1, col2 = st.columns(2)
        with col1:
            new_symbol = st.text_input("Stock Symbol (e.g., AAPL)").upper()
        with col2:
            shares = st.number_input("Number of Shares", min_value=0.0, step=0.1)

        if st.button("Add to Portfolio"):
            try:
                current_price = get_stock_data(new_symbol, '1d')['Close'].iloc[-1]
                portfolio_manager.add_position(st.session_state.portfolio_id, new_symbol, shares, current_price)
                st.success(f"Added {shares} shares of {new_symbol}")
                st.rerun()
            except Exception as e:
                st.error("Please check the stock symbol and try again.")

    # Display portfolio
    if positions:
        for position in positions:
            current_price = get_stock_data(position.symbol, '1d')['Close'].iloc[-1]
            value = position.shares * current_price
            gain_loss = value - (position.shares * position.average_price)

            st.metric(
                f"{position.symbol} - {position.shares} shares",
                f"${value:.2f}",
                f"${gain_loss:.2f}"
            )
    else:
        st.info("Your portfolio is empty. Add some stocks to get started!")

elif tab == "🎮 Paper Trading":
    st.title("Paper Trading - Practice Trading")

    # Initialize account if needed
    if 'paper_account_id' not in st.session_state:
        account = paper_trading_manager.create_paper_account(st.session_state.user_id)
        st.session_state.paper_account_id = account.id

    # Get account info
    balance = paper_trading_manager.get_account_balance(st.session_state.paper_account_id)
    st.metric("Available Cash", f"${balance:,.2f}")

    # Simple trading interface
    st.subheader("Make a Trade")

    col1, col2, col3 = st.columns(3)
    with col1:
        symbol = st.text_input("Stock Symbol", "AAPL").upper()
    with col2:
        action = st.selectbox("Buy or Sell?", ["Buy", "Sell"])
    with col3:
        shares = st.number_input("Number of Shares", min_value=0.1, step=0.1)

    # Show current price
    try:
        current_price = get_stock_data(symbol, '1d')['Close'].iloc[-1]
        st.metric("Current Price", f"${current_price:.2f}")

        total_cost = current_price * shares
        st.write(f"Total Cost: ${total_cost:,.2f}")

        if st.button("Place Order"):
            try:
                order = paper_trading_manager.place_order(
                    account_id=st.session_state.paper_account_id,
                    symbol=symbol,
                    order_side=OrderSide.BUY if action == "Buy" else OrderSide.SELL,
                    quantity=shares,
                    price=current_price,
                    asset_type=AssetType.STOCK
                )
                st.success(f"Order placed: {action} {shares} shares of {symbol}")
                st.rerun()
            except Exception as e:
                st.error(str(e))
    except:
        st.error("Please enter a valid stock symbol")

    # Show positions
    st.subheader("My Positions")
    positions = paper_trading_manager.get_positions(st.session_state.paper_account_id)

    if positions:
        paper_trading_manager.update_positions_value(st.session_state.paper_account_id)
        for pos in positions:
            st.metric(
                f"{pos.symbol} - {pos.quantity} shares",
                f"${pos.current_price * pos.quantity:.2f}",
                f"${pos.unrealized_pnl:.2f}"
            )
    else:
        st.info("No positions yet. Try buying some stocks!")