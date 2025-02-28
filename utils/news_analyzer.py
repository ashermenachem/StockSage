from newsapi import NewsApiClient
from textblob import TextBlob
from datetime import datetime, timedelta
from typing import List, Dict
import os

class NewsAnalyzer:
    def __init__(self):
        self.newsapi = NewsApiClient(api_key=os.getenv('NEWS_API_KEY'))

    def get_stock_news(self, company: str, days: int = 7) -> List[Dict]:
        """
        Fetch news articles for a company and analyze sentiment
        """
        try:
            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # Fetch news
            news = self.newsapi.get_everything(
                q=company,
                from_param=from_date,
                language='en',
                sort_by='relevancy'
            )

            # Process and analyze each article
            processed_news = []
            for article in news['articles'][:10]:  # Limit to top 10 articles
                # Analyze sentiment
                sentiment = TextBlob(article['title'] + ' ' + (article['description'] or '')).sentiment
                
                processed_news.append({
                    'title': article['title'],
                    'description': article['description'],
                    'url': article['url'],
                    'published_at': article['publishedAt'],
                    'source': article['source']['name'],
                    'sentiment_score': round(sentiment.polarity, 2),
                    'sentiment': 'Positive' if sentiment.polarity > 0 else 'Negative' if sentiment.polarity < 0 else 'Neutral',
                    'sentiment_color': '#4CAF50' if sentiment.polarity > 0 else '#FF5252' if sentiment.polarity < 0 else '#1E88E5'
                })

            return processed_news
        except Exception as e:
            print(f"Error fetching news: {str(e)}")
            return []

    def get_market_news(self) -> List[Dict]:
        """
        Fetch general market news
        """
        try:
            news = self.newsapi.get_top_headlines(
                category='business',
                language='en'
            )

            processed_news = []
            for article in news['articles']:
                sentiment = TextBlob(article['title'] + ' ' + (article['description'] or '')).sentiment
                
                processed_news.append({
                    'title': article['title'],
                    'description': article['description'],
                    'url': article['url'],
                    'published_at': article['publishedAt'],
                    'source': article['source']['name'],
                    'sentiment_score': round(sentiment.polarity, 2),
                    'sentiment': 'Positive' if sentiment.polarity > 0 else 'Negative' if sentiment.polarity < 0 else 'Neutral',
                    'sentiment_color': '#4CAF50' if sentiment.polarity > 0 else '#FF5252' if sentiment.polarity < 0 else '#1E88E5'
                })

            return processed_news
        except Exception as e:
            print(f"Error fetching market news: {str(e)}")
            return []
