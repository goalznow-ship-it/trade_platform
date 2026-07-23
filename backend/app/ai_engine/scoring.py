"""
Advanced AI Signal Scoring Engine

Weighted scoring formula:
  Technical Analysis     25%
  Market Structure       25%
  Futures Data           20%
  Market Sentiment       15%
  News Impact            15%
"""

from typing import Optional

class SignalScorer:
    WEIGHTS = {
        'technical': 0.25,
        'market_structure': 0.25,
        'futures': 0.20,
        'sentiment': 0.15,
        'news': 0.15,
    }

    def score_technical(self, analysis: dict) -> float:
        scores = analysis.get('scores', {})
        details = analysis.get('details', {})
        score = 0.0

        trend = scores.get('trend', 0)
        momentum = scores.get('momentum', 0)
        volume = scores.get('volume', 0)
        volatility = scores.get('volatility', 0)

        score += max(-1, min(1, trend * 0.30))
        score += max(-1, min(1, momentum * 0.25))
        score += max(-1, min(1, volume * 0.25))
        score += max(-1, min(1, volatility * 0.20))

        rsi = details.get('rsi', 50)
        if rsi and (rsi < 30 or rsi > 70):
            score += 0.1

        adx = details.get('adx', 0)
        if adx and adx > 25:
            score += 0.1 * (1 if score > 0 else -1)

        return max(-1, min(1, score))

    def score_market_structure(self, analysis: dict) -> float:
        scores = analysis.get('scores', {})
        structure = scores.get('market_structure', 0)
        smc = scores.get('smc', 0)
        return max(-1, min(1, structure * 0.5 + smc * 0.5))

    def score_sentiment(self, analysis: dict) -> float:
        fg = analysis.get('scores', {}).get('fear_greed', 0)
        news = analysis.get('scores', {}).get('news_sentiment', 0)
        return max(-1, min(1, fg * 0.5 + news * 0.5))

    def calculate(self, analysis: dict, futures_data: Optional[dict] = None,
                  news_data: Optional[dict] = None) -> dict:
        tech_score = self.score_technical(analysis)
        struct_score = self.score_market_structure(analysis)
        sent_score = self.score_sentiment(analysis)

        fut_score = 0.0
        if futures_data:
            funding = futures_data.get('funding_rate', 0)
            oi_change = futures_data.get('oi_change', 0)
            ls_ratio = futures_data.get('long_short_ratio', 1.0)
            fut_score = (max(-1, min(1, -funding * 50)) * 0.4 +
                         max(-1, min(1, oi_change * 10)) * 0.3 +
                         (0.2 if ls_ratio < 1 else -0.2) * 0.3)

        news_score = 0.0
        if news_data:
            impact = news_data.get('impact_score', 50)
            sentiment = news_data.get('sentiment', 0)
            news_score = max(-1, min(1, (impact - 50) / 50 * 0.5 + sentiment * 0.5))

        weighted = (tech_score * self.WEIGHTS['technical'] +
                    struct_score * self.WEIGHTS['market_structure'] +
                    fut_score * self.WEIGHTS['futures'] +
                    sent_score * self.WEIGHTS['sentiment'] +
                    news_score * self.WEIGHTS['news'])

        total = max(-1, min(1, weighted))
        confidence = round(abs(total) * 100, 1)
        direction = 'long' if total > 0.05 else ('short' if total < -0.05 else 'neutral')

        return {
            'total_score': round(total, 4),
            'confidence': confidence,
            'direction': direction,
            'technical_score': round(tech_score, 4),
            'structure_score': round(struct_score, 4),
            'futures_score': round(fut_score, 4),
            'sentiment_score': round(sent_score, 4),
            'news_score': round(news_score, 4),
            'weights': self.WEIGHTS,
        }
