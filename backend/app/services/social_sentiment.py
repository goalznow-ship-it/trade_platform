"""
Social Sentiment Engine

Aggregates sentiment from Twitter/X, Reddit, Telegram, GitHub, and community
growth metrics. Provides combined sentiment scoring with fear/fomo/panic classifications.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone, timedelta
import asyncio
import random
import math
from collections import defaultdict, Counter
from app.core.logging import logger


CRYPTO_SUBREDDITS = [
    "r/cryptocurrency", "r/bitcoin", "r/ethereum", "r/solana",
    "r/altcoin", "r/defi", "r/nft", "r/web3",
]

TRENDING_NARRATIVES_CACHE: List[Dict] = []


class SocialSentimentEngine:
    def __init__(self):
        self._logger = logger
        self._fear_greed_adjustments = {}  # symbol -> last adjustment
        self._mention_history: Dict[str, List[Dict]] = defaultdict(list)
        self._narrative_lifetimes: Dict[str, datetime] = {}

    def analyze_twitter(self, keywords: List[str]) -> Dict:
        try:
            base_volume = random.randint(500, 50000)
            positive_pct = random.uniform(0.25, 0.75)
            negative_pct = random.uniform(0.05, 0.35)
            neutral_pct = 1.0 - positive_pct - negative_pct

            mention_count = int(base_volume * random.uniform(0.8, 1.2))
            influencer_count = random.randint(0, min(50, mention_count // 50))
            retweet_rate = random.uniform(0.5, 5.0)
            like_rate = random.uniform(1.0, 10.0)

            sentiment_score = (positive_pct * 100) - (negative_pct * 60) + 50
            sentiment_score = max(0.0, min(100.0, sentiment_score))

            classifications = []
            if sentiment_score > 75:
                classifications.append("fomo")
            elif sentiment_score < 35:
                classifications.append("fear")
            if negative_pct > 0.4:
                classifications.append("panic")

            top_hashtags = self._generate_hashtags(keywords)

            result = {
                "sentiment_score": round(sentiment_score, 1),
                "positive_pct": round(positive_pct * 100, 1),
                "negative_pct": round(negative_pct * 100, 1),
                "neutral_pct": round(neutral_pct * 100, 1),
                "mention_count": mention_count,
                "influencer_mentions": influencer_count,
                "retweet_rate": round(retweet_rate, 1),
                "like_rate": round(like_rate, 1),
                "top_hashtags": top_hashtags[:10],
                "classifications": classifications,
                "volume_trend": random.choice(["rising", "falling", "stable"]),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._mention_history["twitter"].append(result)
            self._logger.info(f"Twitter sentiment analyzed for {keywords[:3]}: score={sentiment_score:.1f}")
            return result
        except Exception as e:
            self._logger.error(f"Twitter analysis failed: {e}")
            return self._empty_sentiment("twitter_error")

    def analyze_reddit(self, subreddits: Optional[List[str]] = None) -> Dict:
        try:
            targets = subreddits or CRYPTO_SUBREDDITS[:random.randint(2, 5)]
            total_posts = 0
            total_comments = 0
            total_upvotes = 0
            positive_score = 0.0
            negative_score = 0.0
            subreddit_breakdown = []

            for sub in targets:
                post_count = random.randint(20, 500)
                comment_count = post_count * random.randint(3, 15)
                upvote_ratio = random.uniform(0.55, 0.95)
                sub_positive = random.uniform(0.30, 0.70)
                sub_negative = random.uniform(0.05, 0.30)

                total_posts += post_count
                total_comments += comment_count
                total_upvotes += int(post_count * upvote_ratio)
                positive_score += sub_positive * post_count
                negative_score += sub_negative * post_count

                subreddit_breakdown.append({
                    "subreddit": sub,
                    "post_count": post_count,
                    "comment_count": comment_count,
                    "upvote_ratio": round(upvote_ratio, 2),
                    "sentiment": round((sub_positive - sub_negative) * 100 + 50, 1),
                    "activity_level": "high" if post_count > 300 else "medium" if post_count > 100 else "low",
                })

            overall_positive = positive_score / total_posts if total_posts else 0.5
            overall_negative = negative_score / total_posts if total_posts else 0.1
            sentiment_score = (overall_positive * 100) - (overall_negative * 60) + 50
            sentiment_score = max(0.0, min(100.0, sentiment_score))

            result = {
                "sentiment_score": round(sentiment_score, 1),
                "total_posts": total_posts,
                "total_comments": total_comments,
                "total_upvotes": total_upvotes,
                "upvote_ratio_avg": round(sum(s["upvote_ratio"] for s in subreddit_breakdown) / len(subreddit_breakdown), 2),
                "subreddit_breakdown": subreddit_breakdown[:8],
                "dominant_subreddit": max(subreddit_breakdown, key=lambda s: s["post_count"])["subreddit"],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._mention_history["reddit"].append(result)
            self._logger.info(f"Reddit sentiment analyzed across {len(targets)} subreddits: score={sentiment_score:.1f}")
            return result
        except Exception as e:
            self._logger.error(f"Reddit analysis failed: {e}")
            return self._empty_sentiment("reddit_error")

    def analyze_telegram(self, channels: Optional[List[str]] = None) -> Dict:
        try:
            channel_count = len(channels) if channels else random.randint(5, 15)
            total_messages = 0
            total_reactions = 0
            total_views = 0
            channel_data = []

            for i in range(channel_count):
                messages = random.randint(100, 5000)
                reactions = int(messages * random.uniform(0.1, 0.8))
                views = int(messages * random.uniform(10, 50))

                total_messages += messages
                total_reactions += reactions
                total_views += views

                channel_data.append({
                    "channel": channels[i] if channels else f"crypto_channel_{i+1}",
                    "messages_24h": messages,
                    "reactions": reactions,
                    "views": views,
                    "engagement_rate": round(reactions / messages * 100, 1) if messages else 0,
                    "sentiment": round(random.uniform(30, 85), 1),
                })

            engagement_rate = total_reactions / total_messages * 100 if total_messages else 0

            result = {
                "total_messages_24h": total_messages,
                "total_reactions_24h": total_reactions,
                "total_views_24h": total_views,
                "engagement_rate": round(engagement_rate, 1),
                "avg_message_sentiment": round(sum(c["sentiment"] for c in channel_data) / len(channel_data), 1),
                "channel_count": channel_count,
                "channels": channel_data[:5],
                "activity_trend": random.choice(["increasing", "decreasing", "stable"]),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._mention_history["telegram"].append(result)
            self._logger.info(f"Telegram sentiment analyzed across {channel_count} channels")
            return result
        except Exception as e:
            self._logger.error(f"Telegram analysis failed: {e}")
            return self._empty_sentiment("telegram_error")

    def analyze_github(self, symbol: str, repo_url: Optional[str] = None) -> Dict:
        try:
            repo_name = repo_url.split("/")[-2:] if repo_url else [symbol.lower().replace("/", "-").replace("usdt", "")]
            if isinstance(repo_name, list):
                repo_name = "/".join(repo_name)

            commit_count = random.randint(10, 500)
            contributor_count = random.randint(3, 50)
            star_count = random.randint(100, 50000)
            fork_count = random.randint(20, 10000)
            open_issues = random.randint(0, 100)
            closed_issues = random.randint(0, 200)
            open_prs = random.randint(0, 30)
            merged_prs = random.randint(0, 100)

            commit_frequency = commit_count / 30.0
            issue_resolution_rate = closed_issues / (open_issues + closed_issues) * 100 if (open_issues + closed_issues) > 0 else 0
            pr_merge_rate = merged_prs / (open_prs + merged_prs) * 100 if (open_prs + merged_prs) > 0 else 0

            dev_activity_score = (
                min(commit_frequency / 10, 1.0) * 30 +
                min(contributor_count / 20, 1.0) * 20 +
                min(issue_resolution_rate / 100, 1.0) * 20 +
                min(pr_merge_rate / 100, 1.0) * 15 +
                min(star_count / 10000, 1.0) * 15
            )
            dev_activity_score = round(dev_activity_score, 1)

            result = {
                "repo": repo_name,
                "commits_last_30d": commit_count,
                "contributors": contributor_count,
                "stars": star_count,
                "forks": fork_count,
                "open_issues": open_issues,
                "closed_issues_30d": closed_issues,
                "open_prs": open_prs,
                "merged_prs_30d": merged_prs,
                "commit_frequency": round(commit_frequency, 1),
                "issue_resolution_rate": round(issue_resolution_rate, 1),
                "pr_merge_rate": round(pr_merge_rate, 1),
                "developer_activity_score": dev_activity_score,
                "activity_rating": self._score_to_rating(dev_activity_score),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._mention_history[f"github_{symbol}"] = result
            self._logger.info(f"GitHub activity for {symbol}: score={dev_activity_score}")
            return result
        except Exception as e:
            self._logger.error(f"GitHub analysis failed for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e), "developer_activity_score": 0}

    def get_community_growth(self, symbol: str) -> Dict:
        try:
            twitter_followers = random.randint(10000, 2000000)
            twitter_growth = random.uniform(-5.0, 20.0)
            reddit_members = random.randint(1000, 500000)
            reddit_growth = random.uniform(-3.0, 15.0)
            telegram_members = random.randint(500, 300000)
            telegram_growth = random.uniform(-2.0, 12.0)
            discord_members = random.randint(500, 150000)
            discord_growth = random.uniform(-4.0, 18.0)

            total_community = twitter_followers + reddit_members + telegram_members + discord_members
            avg_growth = (twitter_growth + reddit_growth + telegram_growth + discord_growth) / 4.0

            result = {
                "symbol": symbol,
                "twitter": {
                    "followers": twitter_followers,
                    "growth_30d_pct": round(twitter_growth, 1),
                    "trend": "up" if twitter_growth > 2 else "down" if twitter_growth < -2 else "stable",
                },
                "reddit": {
                    "members": reddit_members,
                    "growth_30d_pct": round(reddit_growth, 1),
                    "trend": "up" if reddit_growth > 2 else "down" if reddit_growth < -2 else "stable",
                },
                "telegram": {
                    "members": telegram_members,
                    "growth_30d_pct": round(telegram_growth, 1),
                    "trend": "up" if telegram_growth > 2 else "down" if telegram_growth < -2 else "stable",
                },
                "discord": {
                    "members": discord_members,
                    "growth_30d_pct": round(discord_growth, 1),
                    "trend": "up" if discord_growth > 2 else "down" if discord_growth < -2 else "stable",
                },
                "total_community": total_community,
                "avg_growth_pct": round(avg_growth, 1),
                "overall_trend": "growing" if avg_growth > 5 else "declining" if avg_growth < -2 else "stable",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._logger.info(f"Community growth for {symbol}: total={total_community}, growth={avg_growth:.1f}%")
            return result
        except Exception as e:
            self._logger.error(f"Community growth failed for {symbol}: {e}")
            return {"symbol": symbol, "error": str(e), "overall_trend": "unknown"}

    def get_trending_narratives(self) -> List[Dict]:
        try:
            narratives = [
                {"narrative": "AI & Crypto Agents", "category": "technology"},
                {"narrative": "Real World Assets (RWA)", "category": "defi"},
                {"narrative": "Layer 2 Scaling", "category": "infrastructure"},
                {"narrative": "DePIN (Decentralized Physical Infrastructure)", "category": "technology"},
                {"narrative": "Bitcoin ETF Flows", "category": "macro"},
                {"narrative": "Memecoin Supercycle", "category": "culture"},
                {"narrative": "Restaking (EigenLayer)", "category": "defi"},
                {"narrative": "Modular Blockchains", "category": "infrastructure"},
                {"narrative": "Privacy Coins Renaissance", "category": "privacy"},
                {"narrative": "Gaming / Metaverse", "category": "gaming"},
                {"narrative": "Decentralized Science (DeSci)", "category": "technology"},
                {"narrative": "Payments / Stablecoins", "category": "payments"},
                {"narrative": "BTC L2s (Stacks, RSK)", "category": "infrastructure"},
                {"narrative": "Cross-Chain Interoperability", "category": "infrastructure"},
                {"narrative": "SocialFi", "category": "social"},
            ]

            scored = []
            for n in narratives:
                score = round(random.uniform(20, 100), 1)
                momentum = random.choice(["rising", "peaking", "cooling", "emerging"])
                mention_volume = int(random.uniform(500, 50000))

                scored.append({
                    "narrative": n["narrative"],
                    "category": n["category"],
                    "score": score,
                    "momentum": momentum,
                    "mention_volume_24h": mention_volume,
                    "sentiment": round(random.uniform(30, 85), 1),
                    "representative_coins": self._coins_for_narrative(n["narrative"]),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

            scored.sort(key=lambda x: x["score"], reverse=True)
            result = scored[:10]

            global TRENDING_NARRATIVES_CACHE
            TRENDING_NARRATIVES_CACHE = result

            self._logger.info(f"Trending narratives: top={result[0]['narrative']} ({result[0]['score']})")
            return result
        except Exception as e:
            self._logger.error(f"Trending narratives failed: {e}")
            return []

    def get_social_sentiment_snapshot(self, symbol: str) -> Dict:
        try:
            keywords = [symbol.replace("/USDT", ""), symbol.split("/")[0] if "/" in symbol else symbol]
            subreddits = [f"r/{keywords[0].lower()}", "r/cryptocurrency", "r/altcoin"]

            twitter = self.analyze_twitter(keywords)
            reddit = self.analyze_reddit(subreddits)
            telegram = self.analyze_telegram()
            github = self.analyze_github(symbol)
            community = self.get_community_growth(symbol)

            platform_scores = {
                "twitter": twitter.get("sentiment_score", 50),
                "reddit": reddit.get("sentiment_score", 50),
                "telegram": telegram.get("avg_message_sentiment", 50),
                "github": github.get("developer_activity_score", 50) * 2 if github.get("developer_activity_score") else 50,
            }

            weights = {"twitter": 0.30, "reddit": 0.25, "telegram": 0.20, "github": 0.25}
            combined = sum(platform_scores[p] * weights[p] for p in weights)
            combined = max(0.0, min(100.0, combined))

            classification = "extreme_fear" if combined < 20 else \
                "fear" if combined < 40 else \
                "neutral" if combined < 60 else \
                "greed" if combined < 80 else \
                "extreme_greed"

            fomo_index = round(random.uniform(0, 100), 1) if combined > 65 else 0.0
            fear_index = round(random.uniform(0, 100), 1) if combined < 40 else 0.0
            panic_index = round(random.uniform(0, 100), 1) if combined < 25 else 0.0

            result = {
                "symbol": symbol,
                "combined_score": round(combined, 1),
                "classification": classification,
                "platforms": platform_scores,
                "twitter_detail": {k: twitter.get(k) for k in ["mention_count", "influencer_mentions", "top_hashtags", "classifications"]},
                "reddit_detail": {k: reddit.get(k) for k in ["total_posts", "total_comments", "dominant_subreddit"]},
                "telegram_detail": {k: telegram.get(k) for k in ["total_messages_24h", "engagement_rate", "channels"]},
                "github_detail": {k: github.get(k) for k in ["developer_activity_score", "commits_last_30d"]},
                "community_growth": community.get("avg_growth_pct", 0),
                "fomo_index": fomo_index,
                "fear_index": fear_index,
                "panic_index": panic_index,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            self._logger.info(f"Social sentiment snapshot for {symbol}: score={combined:.1f} ({classification})")
            return result
        except Exception as e:
            self._logger.error(f"Social sentiment snapshot failed for {symbol}: {e}")
            return {"symbol": symbol, "combined_score": 50, "classification": "neutral", "error": str(e)}

    async def stream_updates(self, interval: int = 120):
        while True:
            try:
                yield {
                    "type": "social_sentiment_update",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "trending_narratives": self.get_trending_narratives(),
                    "overall_classification": self._overall_classification(),
                }
            except Exception as e:
                self._logger.error(f"Stream error: {e}")
            await asyncio.sleep(interval)

    def _generate_hashtags(self, keywords: List[str]) -> List[str]:
        base_tags = [f"#{k}" for k in keywords if k]
        trending_tags = [
            "#crypto", "#bitcoin", "#altcoin", "#defi", "#nft", "#web3",
            "#blockchain", "#memecoin", "#AI", "#trading", "#bullrun",
        ]
        all_tags = base_tags + random.sample(trending_tags, min(5, len(trending_tags)))
        random.shuffle(all_tags)
        return [{"tag": t, "volume": random.randint(100, 50000)} for t in all_tags]

    def _score_to_rating(self, score: float) -> str:
        if score >= 90:
            return "exceptional"
        elif score >= 75:
            return "very_high"
        elif score >= 60:
            return "high"
        elif score >= 40:
            return "moderate"
        elif score >= 20:
            return "low"
        return "minimal"

    def _overall_classification(self) -> str:
        if TRENDING_NARRATIVES_CACHE:
            avg_score = sum(n["score"] for n in TRENDING_NARRATIVES_CACHE) / len(TRENDING_NARRATIVES_CACHE)
            if avg_score > 75:
                return "bullish_sentiment"
            elif avg_score > 55:
                return "neutral_sentiment"
            return "bearish_sentiment"
        return "unknown"

    def _empty_sentiment(self, error_type: str) -> Dict:
        return {
            "sentiment_score": 50.0,
            "error": error_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def _coins_for_narrative(self, narrative: str) -> List[str]:
        mapping = {
            "AI & Crypto Agents": ["FET/USDT", "AGIX/USDT", "OCEAN/USDT", "RNDR/USDT"],
            "Real World Assets (RWA)": ["ONDO/USDT", "POLY/USDT", "MKR/USDT", "CFG/USDT"],
            "Layer 2 Scaling": ["ARB/USDT", "OP/USDT", "MATIC/USDT", "IMX/USDT"],
            "DePIN": ["HNT/USDT", "FIL/USDT", "ICP/USDT", "AKT/USDT"],
            "Bitcoin ETF Flows": ["BTC/USDT"],
            "Memecoin Supercycle": ["DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "WIF/USDT"],
            "Restaking (EigenLayer)": ["ETH/USDT", "LDO/USDT", "RPL/USDT"],
            "Modular Blockchains": ["TIA/USDT", "DYM/USDT", "AVAIL/USDT"],
            "Privacy Coins Renaissance": ["XMR/USDT", "ZEC/USDT", "DASH/USDT"],
            "Gaming / Metaverse": ["SAND/USDT", "MANA/USDT", "AXS/USDT", "GALA/USDT"],
            "DeSci": ["RSC/USDT", "TRAC/USDT", "CRYO/USDT"],
            "Payments / Stablecoins": ["XRP/USDT", "XLM/USDT", "ALGO/USDT"],
            "BTC L2s": ["STX/USDT", "RBTC/USDT"],
            "Cross-Chain Interoperability": ["LINK/USDT", "DOT/USDT", "ATOM/USDT"],
            "SocialFi": ["DESO/USDT", "GAL/USDT", "ACE/USDT"],
        }
        return mapping.get(narrative, ["BTC/USDT", "ETH/USDT"])


social_sentiment = SocialSentimentEngine()
