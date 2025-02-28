import pandas as pd
import yfinance as yf
from typing import List, Dict
from utils.technical_analysis import calculate_indicators

class StockScreener:
    def __init__(self):
        self.sector_etfs = {
            'Technology': 'XLK',
            'Healthcare': 'XLV',
            'Financial': 'XLF',
            'Consumer': 'XLY',
            'Industrial': 'XLI',
            'Energy': 'XLE'
        }

    def get_top_movers(self, limit: int = 10) -> List[Dict]:
        """Get top gaining and losing stocks"""
        gainers = []
        losers = []
        
        for sector, etf in self.sector_etfs.items():
            try:
                etf_data = yf.Ticker(etf)
                holdings = etf_data.holdings
                
                if holdings is not None:
                    for symbol in holdings:
                        stock = yf.Ticker(symbol)
                        hist = stock.history(period='1d')
                        if not hist.empty:
                            change = ((hist['Close'].iloc[-1] - hist['Open'].iloc[0]) / hist['Open'].iloc[0]) * 100
                            stock_info = {
                                'symbol': symbol,
                                'sector': sector,
                                'change': change,
                                'volume': hist['Volume'].iloc[-1]
                            }
                            
                            if change > 0:
                                gainers.append(stock_info)
                            else:
                                losers.append(stock_info)
            except Exception as e:
                print(f"Error processing {etf}: {str(e)}")
                
        gainers = sorted(gainers, key=lambda x: x['change'], reverse=True)[:limit]
        losers = sorted(losers, key=lambda x: x['change'])[:limit]
        
        return {'gainers': gainers, 'losers': losers}

    def scan_technical_patterns(self, symbols: List[str]) -> List[Dict]:
        """Scan for technical patterns"""
        results = []
        
        for symbol in symbols:
            try:
                stock = yf.Ticker(symbol)
                df = stock.history(period='1mo')
                
                if not df.empty:
                    # Calculate indicators
                    df = calculate_indicators(df)
                    
                    # Pattern detection logic
                    patterns = []
                    
                    # Golden Cross (50 SMA crosses above 200 SMA)
                    if df['SMA_50'].iloc[-1] > df['SMA_200'].iloc[-1] and \
                       df['SMA_50'].iloc[-2] <= df['SMA_200'].iloc[-2]:
                        patterns.append('Golden Cross')
                    
                    # Death Cross (50 SMA crosses below 200 SMA)
                    if df['SMA_50'].iloc[-1] < df['SMA_200'].iloc[-1] and \
                       df['SMA_50'].iloc[-2] >= df['SMA_200'].iloc[-2]:
                        patterns.append('Death Cross')
                    
                    # RSI Oversold/Overbought
                    if df['RSI'].iloc[-1] < 30:
                        patterns.append('RSI Oversold')
                    elif df['RSI'].iloc[-1] > 70:
                        patterns.append('RSI Overbought')
                    
                    # MACD Crossover
                    if df['MACD'].iloc[-1] > df['MACD_Signal'].iloc[-1] and \
                       df['MACD'].iloc[-2] <= df['MACD_Signal'].iloc[-2]:
                        patterns.append('MACD Bullish Crossover')
                    elif df['MACD'].iloc[-1] < df['MACD_Signal'].iloc[-1] and \
                         df['MACD'].iloc[-2] >= df['MACD_Signal'].iloc[-2]:
                        patterns.append('MACD Bearish Crossover')
                    
                    if patterns:
                        results.append({
                            'symbol': symbol,
                            'patterns': patterns,
                            'last_price': df['Close'].iloc[-1],
                            'volume': df['Volume'].iloc[-1]
                        })
            
            except Exception as e:
                print(f"Error processing {symbol}: {str(e)}")
        
        return results

    def filter_stocks(self, criteria: Dict) -> List[Dict]:
        """Filter stocks based on technical and fundamental criteria"""
        results = []
        
        symbols = []  # Get symbols from sector ETFs
        for etf in self.sector_etfs.values():
            try:
                etf_data = yf.Ticker(etf)
                holdings = etf_data.holdings
                if holdings is not None:
                    symbols.extend(holdings)
            except:
                continue
        
        for symbol in symbols:
            try:
                stock = yf.Ticker(symbol)
                hist = stock.history(period='1mo')
                info = stock.info
                
                if hist.empty:
                    continue
                
                meets_criteria = True
                
                # Price criteria
                if 'price' in criteria:
                    price = hist['Close'].iloc[-1]
                    if not (criteria['price']['min'] <= price <= criteria['price']['max']):
                        meets_criteria = False
                
                # Volume criteria
                if 'volume' in criteria:
                    volume = hist['Volume'].iloc[-1]
                    if volume < criteria['volume']['min']:
                        meets_criteria = False
                
                # Market cap criteria
                if 'market_cap' in criteria:
                    market_cap = info.get('marketCap', 0)
                    if market_cap < criteria['market_cap']['min']:
                        meets_criteria = False
                
                # Technical indicators
                if any(key in criteria for key in ['rsi', 'macd', 'sma']):
                    df = calculate_indicators(hist)
                    
                    if 'rsi' in criteria:
                        rsi = df['RSI'].iloc[-1]
                        if not (criteria['rsi']['min'] <= rsi <= criteria['rsi']['max']):
                            meets_criteria = False
                    
                    if 'macd' in criteria and 'MACD' in df.columns:
                        macd = df['MACD'].iloc[-1]
                        if not (criteria['macd']['min'] <= macd <= criteria['macd']['max']):
                            meets_criteria = False
                
                if meets_criteria:
                    results.append({
                        'symbol': symbol,
                        'price': hist['Close'].iloc[-1],
                        'volume': hist['Volume'].iloc[-1],
                        'market_cap': info.get('marketCap', 0),
                        'sector': info.get('sector', 'Unknown')
                    })
            
            except Exception as e:
                print(f"Error processing {symbol}: {str(e)}")
        
        return results
