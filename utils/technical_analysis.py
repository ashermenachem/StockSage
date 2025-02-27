import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate technical indicators
    """
    # Moving Averages
    df['SMA_20'] = SMAIndicator(close=df['Close'], window=20).sma_indicator()
    df['SMA_50'] = SMAIndicator(close=df['Close'], window=50).sma_indicator()
    df['EMA_20'] = EMAIndicator(close=df['Close'], window=20).ema_indicator()
    
    # MACD
    macd = MACD(close=df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    
    # RSI
    df['RSI'] = RSIIndicator(close=df['Close']).rsi()
    
    # Bollinger Bands
    bollinger = BollingerBands(close=df['Close'])
    df['BB_High'] = bollinger.bollinger_hband()
    df['BB_Low'] = bollinger.bollinger_lband()
    df['BB_Mid'] = bollinger.bollinger_mavg()
    
    return df

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate trading signals based on technical indicators
    """
    df['Signal'] = 'HOLD'
    
    # MACD Signal
    df.loc[(df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1)), 'Signal'] = 'BUY'
    df.loc[(df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1)), 'Signal'] = 'SELL'
    
    # RSI Conditions
    df.loc[df['RSI'] < 30, 'Signal'] = 'BUY'  # Oversold
    df.loc[df['RSI'] > 70, 'Signal'] = 'SELL'  # Overbought
    
    return df
