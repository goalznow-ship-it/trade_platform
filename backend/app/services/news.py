import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Optional
from textblob import TextBlob
from app.core.logging import logger

class NewsService:
    def __init__(self):
        self.logger = logger
        self.sources = {
            'cointelegraph': 'https://cointelegraph.com/news',
            'coindesk': 'https://www.coindesk.com/markets/',
            'cryptopanic': 'https://cryptopanic.com/api/v1/posts/',
        }

    async def fetch_all(self) -> list:
        all_news = []
        ct = await self._fetch_cointelegraph()
        all_news.extend(ct)
        return sorted(all_news, key=lambda x: x.get('published_at', ''), reverse=True)[:50]

    async def _fetch_cointelegraph(self) -> list:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(self.sources['cointelegraph'])
                soup = BeautifulSoup(resp.text, 'html.parser')
                articles = []
                for item in soup.select('.post-card')[:15]:
                    title_el = item.select_one('.post-card__title')
                    if not title_el:
                        continue
                    title = title_el.get_text(strip=True)
                    link = title_el.find('a')
                    url = f"https://cointelegraph.com{link['href']}" if link else ''
                    summary_el = item.select_one('.post-card__description')
                    summary = summary_el.get_text(strip=True) if summary_el else ''
                    analysis = self._analyze_sentiment(title + ' ' + summary)
                    articles.append({
                        'title': title,
                        'url': url,
                        'source': 'cointelegraph',
                        'category': 'crypto',
                        'summary': summary,
                        'published_at': datetime.now(timezone.utc).isoformat(),
                        **analysis,
                    })
                return articles
        except Exception:
            return []

    def _analyze_sentiment(self, text: str) -> dict:
        blob = TextBlob(text)
        polarity = blob.sentiment.polarity
        subjectivity = blob.sentiment.subjectivity

        if polarity > 0.2:
            sentiment = 'bullish'
            impact = 'positive'
        elif polarity < -0.2:
            sentiment = 'bearish'
            impact = 'negative'
        else:
            sentiment = 'neutral'
            impact = 'neutral'

        return {
            'sentiment': sentiment,
            'sentiment_score': round(polarity, 3),
            'impact_score': round(abs(polarity) * 10, 1),
            'market_impact': impact,
        }

news_service = NewsService()
