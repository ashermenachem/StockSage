import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def get_stock_data(symbol: str, period: str = '1y') -> pd.DataFrame:
    """
    Fetch stock data from Yahoo Finance
    """
    try:
        stock = yf.Ticker(symbol)
        df = stock.history(period=period)
        return df
    except Exception as e:
        raise Exception(f"Error fetching data for {symbol}: {str(e)}")

def get_company_info(symbol: str) -> dict:
    """
    Get company information
    """
    try:
        stock = yf.Ticker(symbol)
        info = stock.info
        return {
            'name': info.get('longName', symbol),
            'sector': info.get('sector', 'N/A'),
            'market_cap': info.get('marketCap', 0),
            'pe_ratio': info.get('forwardPE', 0),
            'dividend_yield': info.get('dividendYield', 0)
        }
    except:
        return {
            'name': symbol,
            'sector': 'N/A',
            'market_cap': 0,
            'pe_ratio': 0,
            'dividend_yield': 0
        }
