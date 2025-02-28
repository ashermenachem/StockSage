import pandas as pd
import numpy as np
from ta.trend import SMAIndicator, EMAIndicator, MACD, IchimokuIndicator
from ta.momentum import RSIIndicator, StochasticOscillator, WilliamsRIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from ta.volume import OnBalanceVolumeIndicator, AccDistIndexIndicator
from ta.others import DailyReturnIndicator

def calculate_indicators(df: pd.DataFrame, selected_indicators: list = None) -> pd.DataFrame:
    """
    Calculate technical indicators
    """
    available_indicators = {
        'SMA': lambda: {
            'SMA_20': SMAIndicator(close=df['Close'], window=20).sma_indicator(),
            'SMA_50': SMAIndicator(close=df['Close'], window=50).sma_indicator(),
            'SMA_200': SMAIndicator(close=df['Close'], window=200).sma_indicator()
        },
        'EMA': lambda: {
            'EMA_20': EMAIndicator(close=df['Close'], window=20).ema_indicator(),
            'EMA_50': EMAIndicator(close=df['Close'], window=50).ema_indicator()
        },
        'MACD': lambda: {
            'MACD': MACD(close=df['Close']).macd(),
            'MACD_Signal': MACD(close=df['Close']).macd_signal(),
            'MACD_Hist': MACD(close=df['Close']).macd_diff()
        },
        'RSI': lambda: {
            'RSI': RSIIndicator(close=df['Close']).rsi()
        },
        'Bollinger': lambda: {
            'BB_High': BollingerBands(close=df['Close']).bollinger_hband(),
            'BB_Low': BollingerBands(close=df['Close']).bollinger_lband(),
            'BB_Mid': BollingerBands(close=df['Close']).bollinger_mavg()
        },
        'Stochastic': lambda: {
            'Stoch_K': StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close']).stoch(),
            'Stoch_D': StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close']).stoch_signal()
        },
        'Williams': lambda: {
            'Williams_R': WilliamsRIndicator(high=df['High'], low=df['Low'], close=df['Close']).williams_r()
        },
        'ATR': lambda: {
            'ATR': AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close']).average_true_range()
        },
        'Volume': lambda: {
            'OBV': OnBalanceVolumeIndicator(close=df['Close'], volume=df['Volume']).on_balance_volume(),
            'ADI': AccDistIndexIndicator(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume']).acc_dist_index()
        },
        'Ichimoku': lambda: {
            'Ichimoku_A': IchimokuIndicator(high=df['High'], low=df['Low']).ichimoku_a(),
            'Ichimoku_B': IchimokuIndicator(high=df['High'], low=df['Low']).ichimoku_b()
        }
    }

    # If no indicators specified, use default set
    if not selected_indicators:
        selected_indicators = ['SMA', 'MACD', 'RSI', 'Bollinger']

    # Calculate selected indicators
    for indicator in selected_indicators:
        if indicator in available_indicators:
            indicator_values = available_indicators[indicator]()
            for name, values in indicator_values.items():
                df[name] = values

    return df

def generate_signals(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate trading signals based on technical indicators
    """
    df['Signal'] = 'HOLD'
    df['Signal_Strength'] = 0  # New column for signal strength

    # MACD Signal
    if 'MACD' in df.columns and 'MACD_Signal' in df.columns:
        df.loc[(df['MACD'] > df['MACD_Signal']) & (df['MACD'].shift(1) <= df['MACD_Signal'].shift(1)), 'Signal'] = 'BUY'
        df.loc[(df['MACD'] < df['MACD_Signal']) & (df['MACD'].shift(1) >= df['MACD_Signal'].shift(1)), 'Signal'] = 'SELL'

    # RSI Conditions
    if 'RSI' in df.columns:
        df.loc[df['RSI'] < 30, 'Signal'] = 'BUY'  # Oversold
        df.loc[df['RSI'] > 70, 'Signal'] = 'SELL'  # Overbought

        # Add to signal strength
        df.loc[df['RSI'] < 30, 'Signal_Strength'] += 1
        df.loc[df['RSI'] > 70, 'Signal_Strength'] += 1

    # Moving Average Crossovers
    if 'SMA_20' in df.columns and 'SMA_50' in df.columns:
        # Golden Cross / Death Cross
        df.loc[(df['SMA_20'] > df['SMA_50']) & (df['SMA_20'].shift(1) <= df['SMA_50'].shift(1)), 'Signal'] = 'BUY'
        df.loc[(df['SMA_20'] < df['SMA_50']) & (df['SMA_20'].shift(1) >= df['SMA_50'].shift(1)), 'Signal'] = 'SELL'

        # Add to signal strength
        df.loc[df['Close'] > df['SMA_20'], 'Signal_Strength'] += 0.5
        df.loc[df['Close'] > df['SMA_50'], 'Signal_Strength'] += 0.5

    # Bollinger Bands
    if all(col in df.columns for col in ['BB_High', 'BB_Low']):
        df.loc[df['Close'] <= df['BB_Low'], 'Signal'] = 'BUY'  # Price below lower band
        df.loc[df['Close'] >= df['BB_High'], 'Signal'] = 'SELL'  # Price above upper band

        # Add to signal strength
        df.loc[df['Close'] <= df['BB_Low'], 'Signal_Strength'] += 1
        df.loc[df['Close'] >= df['BB_High'], 'Signal_Strength'] += 1

    # Volume confirmation
    if 'OBV' in df.columns:
        df['OBV_EMA'] = EMAIndicator(close=df['OBV'], window=20).ema_indicator()
        volume_trend_up = (df['OBV'] > df['OBV_EMA']) & (df['OBV'].shift(1) <= df['OBV_EMA'].shift(1))
        volume_trend_down = (df['OBV'] < df['OBV_EMA']) & (df['OBV'].shift(1) >= df['OBV_EMA'].shift(1))

        df.loc[volume_trend_up, 'Signal_Strength'] += 0.5
        df.loc[volume_trend_down, 'Signal_Strength'] -= 0.5

    return df

def screen_stocks(symbols: list, criteria: dict) -> list:
    """
    Screen stocks based on technical and fundamental criteria
    """
    results = []

    for symbol in symbols:
        try:
            df = pd.DataFrame()  # Get stock data
            if df.empty:
                continue

            # Calculate indicators
            df = calculate_indicators(df)

            # Apply screening criteria
            meets_criteria = True

            if 'rsi' in criteria:
                rsi = df['RSI'].iloc[-1]
                if not (criteria['rsi']['min'] <= rsi <= criteria['rsi']['max']):
                    meets_criteria = False

            if 'volume' in criteria:
                avg_volume = df['Volume'].mean()
                if avg_volume < criteria['volume']['min']:
                    meets_criteria = False

            if 'price' in criteria:
                current_price = df['Close'].iloc[-1]
                if not (criteria['price']['min'] <= current_price <= criteria['price']['max']):
                    meets_criteria = False

            if meets_criteria:
                results.append(symbol)

        except Exception as e:
            print(f"Error screening {symbol}: {str(e)}")

    return results