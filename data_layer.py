"""
Data Layer - Unified data fetching with caching and quality checks
Handles: Market data, Technical indicators, News, Watchlist management
"""

import re
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np
from functools import lru_cache
import requests
from bs4 import BeautifulSoup

# Import existing modules
from upstox_technical import UpstoxTechnicalClient
from news_client import NewsClient

logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """News article data"""
    title: str
    timestamp: datetime
    url: str
    source: str
    symbol: Optional[str] = None


@dataclass
class Signal:
    """Trading signal"""
    symbol: str
    strategy: str
    direction: str  # 'BUY' or 'SELL'
    entry_price: float
    stop_loss: float
    target: float
    confidence: float
    product: str  # 'I' or 'D'
    news_score: float = 0.0
    tech_score: float = 0.0


class DataLayer:
    """Unified data layer for market data, news, and watchlist management"""

    # Nifty 50 stocks (core watchlist)
    NIFTY_50_SYMBOLS = [
        'NSE_EQ|RELIANCE-EQ', 'NSE_EQ|TCS-EQ', 'NSE_EQ|HDFCBANK-EQ',
        'NSE_EQ|INFY-EQ', 'NSE_EQ|ICICIBANK-EQ', 'NSE_EQ|HINDUNILVR-EQ',
        'NSE_EQ|SBIN-EQ', 'NSE_EQ|BHARTIARTL-EQ', 'NSE_EQ|KOTAKBANK-EQ',
        'NSE_EQ|LT-EQ', 'NSE_EQ|AXISBANK-EQ', 'NSE_EQ|ITC-EQ',
        'NSE_EQ|ASIANPAINT-EQ', 'NSE_EQ|MARUTI-EQ', 'NSE_EQ|TITAN-EQ',
        'NSE_EQ|SUNPHARMA-EQ', 'NSE_EQ|WIPRO-EQ', 'NSE_EQ|ULTRACEMCO-EQ',
        'NSE_EQ|NESTLEIND-EQ', 'NSE_EQ|POWERGRID-EQ', 'NSE_EQ|NTPC-EQ',
        'NSE_EQ|ONGC-EQ', 'NSE_EQ|M&M-EQ', 'NSE_EQ|TATAMOTORS-EQ',
        'NSE_EQ|TATASTEEL-EQ', 'NSE_EQ|BAJFINANCE-EQ', 'NSE_EQ|BAJAJFINSV-EQ',
        'NSE_EQ|HCLTECH-EQ', 'NSE_EQ|TECHM-EQ', 'NSE_EQ|ADANIENT-EQ',
        'NSE_EQ|ADANIPORTS-EQ', 'NSE_EQ|COALINDIA-EQ', 'NSE_EQ|DIVISLAB-EQ',
        'NSE_EQ|DRREDDY-EQ', 'NSE_EQ|EICHERMOT-EQ', 'NSE_EQ|GRASIM-EQ',
        'NSE_EQ|HEROMOTOCO-EQ', 'NSE_EQ|HINDALCO-EQ', 'NSE_EQ|INDUSINDBK-EQ',
        'NSE_EQ|JSWSTEEL-EQ', 'NSE_EQ|TATACONSUM-EQ', 'NSE_EQ|BRITANNIA-EQ',
        'NSE_EQ|CIPLA-EQ', 'NSE_EQ|APOLLOHOSP-EQ', 'NSE_EQ|BPCL-EQ',
        'NSE_EQ|UPL-EQ', 'NSE_EQ|SBILIFE-EQ', 'NSE_EQ|HDFCLIFE-EQ',
        'NSE_EQ|BAJAJ-AUTO-EQ', 'NSE_EQ|SHREECEM-EQ'
    ]

    # Liquid midcaps (additional opportunities)
    LIQUID_MIDCAPS = [
        'NSE_EQ|GODREJCP-EQ', 'NSE_EQ|INDIGO-EQ', 'NSE_EQ|PIDILITIND-EQ',
        'NSE_EQ|PAGEIND-EQ', 'NSE_EQ|MARICO-EQ', 'NSE_EQ|BERGEPAINT-EQ',
        'NSE_EQ|DABUR-EQ', 'NSE_EQ|HAVELLS-EQ', 'NSE_EQ|MUTHOOTFIN-EQ',
        'NSE_EQ|VOLTAS-EQ', 'NSE_EQ|LUPIN-EQ', 'NSE_EQ|TORNTPHARM-EQ',
        'NSE_EQ|CONCOR-EQ', 'NSE_EQ|INDUSTOWER-EQ', 'NSE_EQ|VEDL-EQ',
        'NSE_EQ|ADANIGREEN-EQ', 'NSE_EQ|ADANIPWR-EQ', 'NSE_EQ|TATAPOWER-EQ',
        'NSE_EQ|SAIL-EQ', 'NSE_EQ|NMDC-EQ'
    ]

    # Sentiment keywords with weights
    POSITIVE_KEYWORDS = {
        'upgrade': 0.25, 'upgraded': 0.25, 'outperform': 0.20,
        'beat': 0.20, 'beats': 0.20, 'strong': 0.15, 'surge': 0.20,
        'rally': 0.15, 'gain': 0.10, 'profit': 0.15, 'dividend': 0.15,
        'buy': 0.20, 'accumulate': 0.15, 'target': 0.10, 'expansion': 0.15,
        'growth': 0.10, 'positive': 0.10, 'bullish': 0.20, 'breakout': 0.15
    }

    NEGATIVE_KEYWORDS = {
        'downgrade': -0.25, 'downgraded': -0.25, 'underperform': -0.20,
        'miss': -0.20, 'misses': -0.20, 'weak': -0.15, 'fall': -0.15,
        'drop': -0.15, 'loss': -0.20, 'concern': -0.10, 'decline': -0.15,
        'sell': -0.20, 'exit': -0.15, 'cut': -0.15, 'reduce': -0.10,
        'bearish': -0.20, 'negative': -0.10, 'warning': -0.15, 'risk': -0.10
    }

    def __init__(self):
        self.upstox_client = UpstoxTechnicalClient()
        self.news_client = NewsClient()
        self._symbol_cache = {}  # Cache for symbol resolution
        self._ohlcv_cache = {}   # Cache for OHLCV data
        self._news_cache = {}     # Cache for news
        logger.info("Data Layer initialized")

    # ==================== WATCHLIST MANAGEMENT ====================

    def get_watchlist(self) -> List[str]:
        """
        Get hybrid watchlist: Nifty 50 + liquid midcaps + news-discovered symbols
        Returns top 30 most relevant symbols
        """
        logger.info("Building hybrid watchlist...")

        # 1. Core watchlist (always included)
        core_symbols = self.NIFTY_50_SYMBOLS.copy()

        # 2. Add liquid midcaps
        core_symbols.extend(self.LIQUID_MIDCAPS)

        # 3. Discover symbols from news (dynamic)
        news_symbols = self.discover_symbols_from_news()

        # 4. Merge and deduplicate
        all_symbols = list(set(news_symbols + core_symbols))

        # 5. Rank by relevance and return top 30
        ranked_symbols = self.rank_by_relevance(all_symbols)

        logger.info(f"Watchlist: {len(ranked_symbols)} symbols (top 30)")
        return ranked_symbols[:30]

    def discover_symbols_from_news(self) -> List[str]:
        """
        Discover trending stocks from news headlines
        Returns list of NSE_EQ symbols
        """
        logger.info("Discovering symbols from news...")

        discovered_symbols = []

        # Scrape news from multiple sources
        news_sources = [
            'https://www.moneycontrol.com/news/business/stocks/',
            'https://economictimes.indiatimes.com/markets/stocks/news'
        ]

        all_headlines = []

        # Also use existing news client
        try:
            # Get latest market news
            news_items = self.news_client.get_latest_news(max_results=50)
            all_headlines.extend([item.get('title', '') for item in news_items])
        except Exception as e:
            logger.warning(f"Error fetching news from client: {e}")

        # Scrape additional sources
        for source_url in news_sources:
            try:
                headlines = self._scrape_headlines(source_url)
                all_headlines.extend(headlines)
            except Exception as e:
                logger.warning(f"Error scraping {source_url}: {e}")

        # Extract company names from headlines
        for headline in all_headlines:
            companies = self._extract_company_names(headline)

            for company in companies:
                # Resolve to NSE symbol
                symbol = self.resolve_symbol(company)

                if symbol and self._is_liquid_and_tradeable(symbol):
                    discovered_symbols.append(symbol)

        # Deduplicate
        discovered_symbols = list(set(discovered_symbols))

        logger.info(f"Discovered {len(discovered_symbols)} symbols from news")
        return discovered_symbols

    def _scrape_headlines(self, url: str) -> List[str]:
        """Scrape headlines from a news URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.content, 'html.parser')

            headlines = []

            # Find headline elements (adjust selectors based on site)
            for tag in soup.find_all(['h2', 'h3', 'h4'], limit=50):
                text = tag.get_text(strip=True)
                if len(text) > 20:  # Filter out short text
                    headlines.append(text)

            return headlines
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return []

    def _extract_company_names(self, text: str) -> List[str]:
        """Extract company names from text using patterns"""
        companies = []

        # Pattern 1: Explicit company names (capitalize words)
        # Reliance, TCS, Infosys, HDFC Bank, etc.
        known_companies = {
            'Reliance': 'RELIANCE', 'TCS': 'TCS', 'Infosys': 'INFY',
            'HDFC Bank': 'HDFCBANK', 'ICICI Bank': 'ICICIBANK',
            'State Bank': 'SBIN', 'SBI': 'SBIN', 'Bharti Airtel': 'BHARTIARTL',
            'Airtel': 'BHARTIARTL', 'Tata Motors': 'TATAMOTORS',
            'Tata Steel': 'TATASTEEL', 'Maruti': 'MARUTI', 'Asian Paints': 'ASIANPAINT',
            'Wipro': 'WIPRO', 'HCL Tech': 'HCLTECH', 'Tech Mahindra': 'TECHM',
            'Adani': 'ADANIENT', 'Adani Ports': 'ADANIPORTS', 'Adani Green': 'ADANIGREEN',
            'Bajaj Finance': 'BAJFINANCE', 'Bajaj Finserv': 'BAJAJFINSV',
            'ITC': 'ITC', 'Hindustan Unilever': 'HINDUNILVR', 'HUL': 'HINDUNILVR',
            'Titan': 'TITAN', 'IndusInd Bank': 'INDUSINDBK', 'Axis Bank': 'AXISBANK',
            'Kotak Bank': 'KOTAKBANK', 'Sun Pharma': 'SUNPHARMA', 'Dr Reddy': 'DRREDDY',
            'Cipla': 'CIPLA', 'Lupin': 'LUPIN', 'JSW Steel': 'JSWSTEEL',
            'Hindalco': 'HINDALCO', 'Coal India': 'COALINDIA', 'NTPC': 'NTPC',
            'Power Grid': 'POWERGRID', 'ONGC': 'ONGC', 'BPCL': 'BPCL',
            'UPL': 'UPL', 'Grasim': 'GRASIM', 'UltraTech': 'ULTRACEMCO',
            'Shree Cement': 'SHREECEM', 'Nestle': 'NESTLEIND', 'Britannia': 'BRITANNIA',
            'Dabur': 'DABUR', 'Marico': 'MARICO', 'Godrej': 'GODREJCP',
            'IndiGo': 'INDIGO', 'Vedanta': 'VEDL'
        }

        for company_name, symbol_hint in known_companies.items():
            if company_name.lower() in text.lower():
                companies.append(symbol_hint)

        return companies

    def resolve_symbol(self, hint: str) -> Optional[str]:
        """
        Resolve company name/hint to NSE_EQ symbol
        Uses caching to avoid repeated lookups
        """
        # Check cache
        if hint in self._symbol_cache:
            return self._symbol_cache[hint]

        try:
            # Use existing upstox_technical resolve method
            symbol = self.upstox_client.resolve(hint)

            # Cache the result
            if symbol:
                self._symbol_cache[hint] = symbol
                return symbol
        except Exception as e:
            logger.debug(f"Error resolving symbol {hint}: {e}")

        return None

    def _is_liquid_and_tradeable(self, symbol: str) -> bool:
        """Check if symbol is liquid and tradeable"""
        try:
            # Get recent volume data
            ohlcv = self.get_ohlcv(symbol, interval='1d', bars=20)

            if ohlcv is None or len(ohlcv) < 5:
                return False

            # Check average volume
            avg_volume = ohlcv['volume'].mean()

            # Minimum 1 lakh shares per day
            if avg_volume < 100_000:
                return False

            # Check if not in circuit (price not constant)
            price_std = ohlcv['close'].std()
            if price_std == 0:
                return False

            return True
        except Exception as e:
            logger.debug(f"Error checking liquidity for {symbol}: {e}")
            return False

    def rank_by_relevance(self, symbols: List[str]) -> List[str]:
        """
        Rank symbols by relevance based on:
        - News mentions (recent 2 hours)
        - Volume
        - Price change today
        """
        scored_symbols = []

        for symbol in symbols:
            try:
                score = 0.0

                # 1. News mentions (weight: 0.5)
                news_count = self._count_recent_news_mentions(symbol)
                news_score = min(news_count * 0.1, 0.5)
                score += news_score * 0.5

                # 2. Volume (weight: 0.3)
                ohlcv = self.get_ohlcv(symbol, interval='1d', bars=2)
                if ohlcv is not None and len(ohlcv) >= 2:
                    volume_ratio = ohlcv['volume'].iloc[-1] / ohlcv['volume'].iloc[-2]
                    volume_score = min(volume_ratio - 1, 0.5)  # 0 to 0.5
                    score += volume_score * 0.3

                # 3. Price change % today (weight: 0.2)
                if ohlcv is not None and len(ohlcv) >= 2:
                    price_change = (ohlcv['close'].iloc[-1] - ohlcv['close'].iloc[-2]) / ohlcv['close'].iloc[-2]
                    price_score = abs(price_change) * 10  # Convert to 0-0.5 range
                    price_score = min(price_score, 0.5)
                    score += price_score * 0.2

                scored_symbols.append((symbol, score))
            except Exception as e:
                logger.debug(f"Error scoring {symbol}: {e}")
                scored_symbols.append((symbol, 0.0))

        # Sort by score descending
        scored_symbols.sort(key=lambda x: x[1], reverse=True)

        return [symbol for symbol, score in scored_symbols]

    def _count_recent_news_mentions(self, symbol: str) -> int:
        """Count news mentions for symbol in last 2 hours"""
        try:
            # Extract company name from symbol
            company = symbol.split('|')[1].replace('-EQ', '')

            # Search news
            news_items = self.get_news(symbol, lookback_hours=2)

            return len(news_items)
        except Exception as e:
            return 0

    # ==================== MARKET DATA ====================

    def get_ohlcv(self, symbol: str, interval: str, bars: int) -> Optional[pd.DataFrame]:
        """
        Get OHLCV data with caching and validation
        Returns DataFrame with columns: timestamp, open, high, low, close, volume
        """
        cache_key = f"{symbol}_{interval}_{bars}"

        # Check cache (5-minute validity)
        if cache_key in self._ohlcv_cache:
            cached_data, cache_time = self._ohlcv_cache[cache_key]
            if (datetime.now() - cache_time).seconds < 300:  # 5 minutes
                return cached_data

        try:
            # Fetch from Upstox
            df = self.upstox_client.get_ohlc(symbol, interval, bars)

            if df is None or len(df) == 0:
                return None

            # Validate data
            if not self._validate_ohlcv(df):
                logger.warning(f"Invalid OHLCV data for {symbol}")
                return None

            # Cache it
            self._ohlcv_cache[cache_key] = (df, datetime.now())

            return df
        except Exception as e:
            logger.error(f"Error fetching OHLCV for {symbol}: {e}")
            return None

    def _validate_ohlcv(self, df: pd.DataFrame) -> bool:
        """Validate OHLCV data quality"""
        if df is None or len(df) == 0:
            return False

        # Check for required columns
        required_cols = ['open', 'high', 'low', 'close', 'volume']
        if not all(col in df.columns for col in required_cols):
            return False

        # Check for null values
        if df[required_cols].isnull().any().any():
            return False

        # Check for zero volume
        if (df['volume'] == 0).all():
            return False

        # Check OHLC relationships
        if not ((df['high'] >= df['low']).all() and
                (df['high'] >= df['open']).all() and
                (df['high'] >= df['close']).all() and
                (df['low'] <= df['open']).all() and
                (df['low'] <= df['close']).all()):
            return False

        return True

    # ==================== TECHNICAL INDICATORS ====================

    def calculate_indicators(self, ohlcv: pd.DataFrame) -> Dict:
        """Calculate all technical indicators (vectorized)"""
        if ohlcv is None or len(ohlcv) < 50:
            return {}

        indicators = {}

        try:
            # Moving averages
            indicators['sma_20'] = ohlcv['close'].rolling(20).mean().iloc[-1]
            indicators['sma_50'] = ohlcv['close'].rolling(50).mean().iloc[-1]
            indicators['ema_9'] = ohlcv['close'].ewm(span=9).mean().iloc[-1]
            indicators['ema_21'] = ohlcv['close'].ewm(span=21).mean().iloc[-1]

            # RSI (14)
            indicators['rsi'] = self._calculate_rsi(ohlcv['close'], 14)

            # MACD
            macd, signal, hist = self._calculate_macd(ohlcv['close'])
            indicators['macd'] = macd
            indicators['macd_signal'] = signal
            indicators['macd_hist'] = hist

            # ATR (14)
            indicators['atr'] = self._calculate_atr(ohlcv, 14)

            # VWAP
            indicators['vwap'] = self._calculate_vwap(ohlcv)

            # Bollinger Bands
            bb_upper, bb_middle, bb_lower = self._calculate_bollinger_bands(ohlcv['close'], 20, 2)
            indicators['bb_upper'] = bb_upper
            indicators['bb_middle'] = bb_middle
            indicators['bb_lower'] = bb_lower

            # ADX (14)
            indicators['adx'] = self._calculate_adx(ohlcv, 14)

            # Volume SMA
            indicators['volume_sma'] = ohlcv['volume'].rolling(20).mean().iloc[-1]

            # Current price
            indicators['close'] = ohlcv['close'].iloc[-1]

        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")

        return indicators

    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    def _calculate_macd(self, prices: pd.Series, fast=12, slow=26, signal=9) -> Tuple[float, float, float]:
        """Calculate MACD"""
        ema_fast = prices.ewm(span=fast).mean()
        ema_slow = prices.ewm(span=slow).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal).mean()
        histogram = macd_line - signal_line
        return macd_line.iloc[-1], signal_line.iloc[-1], histogram.iloc[-1]

    def _calculate_atr(self, ohlcv: pd.DataFrame, period: int = 14) -> float:
        """Calculate ATR"""
        high = ohlcv['high']
        low = ohlcv['low']
        close = ohlcv['close']

        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())

        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean()

        return atr.iloc[-1]

    def _calculate_vwap(self, ohlcv: pd.DataFrame) -> float:
        """Calculate VWAP for today"""
        typical_price = (ohlcv['high'] + ohlcv['low'] + ohlcv['close']) / 3
        vwap = (typical_price * ohlcv['volume']).sum() / ohlcv['volume'].sum()
        return vwap

    def _calculate_bollinger_bands(self, prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[float, float, float]:
        """Calculate Bollinger Bands"""
        sma = prices.rolling(period).mean()
        std = prices.rolling(period).std()
        upper = sma + (std * std_dev)
        lower = sma - (std * std_dev)
        return upper.iloc[-1], sma.iloc[-1], lower.iloc[-1]

    def _calculate_adx(self, ohlcv: pd.DataFrame, period: int = 14) -> float:
        """Calculate ADX"""
        high = ohlcv['high']
        low = ohlcv['low']
        close = ohlcv['close']

        plus_dm = high.diff()
        minus_dm = -low.diff()

        plus_dm[plus_dm < 0] = 0
        minus_dm[minus_dm < 0] = 0

        tr = self._calculate_atr(ohlcv, 1) * period

        plus_di = 100 * (plus_dm.rolling(period).mean() / tr)
        minus_di = 100 * (minus_dm.rolling(period).mean() / tr)

        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.rolling(period).mean()

        return adx.iloc[-1] if not np.isnan(adx.iloc[-1]) else 0.0

    # ==================== NEWS & SENTIMENT ====================

    def get_news(self, symbol: str, lookback_hours: int = 24) -> List[NewsItem]:
        """Get news for symbol with caching"""
        cache_key = f"{symbol}_{lookback_hours}"

        # Check cache (30-minute validity)
        if cache_key in self._news_cache:
            cached_news, cache_time = self._news_cache[cache_key]
            if (datetime.now() - cache_time).seconds < 1800:  # 30 minutes
                return cached_news

        try:
            # Extract company name
            company = symbol.split('|')[1].replace('-EQ', '')

            # Get news from news client
            raw_news = self.news_client.get_recent_news(company, lookback_days=2)

            # Convert to NewsItem objects
            news_items = []
            for item in raw_news:
                # Parse timestamp (if available)
                timestamp = item.get('timestamp', datetime.now())

                # Filter by lookback hours
                if isinstance(timestamp, datetime):
                    hours_ago = (datetime.now() - timestamp).total_seconds() / 3600
                    if hours_ago > lookback_hours:
                        continue

                news_items.append(NewsItem(
                    title=item.get('title', ''),
                    timestamp=timestamp,
                    url=item.get('url', ''),
                    source=item.get('source', 'Unknown'),
                    symbol=symbol
                ))

            # Cache the results
            self._news_cache[cache_key] = (news_items, datetime.now())

            logger.info(f"Found {len(news_items)} news items for {symbol}")
            return news_items

        except Exception as e:
            logger.error(f"Error fetching news for {symbol}: {e}")
            return []

    def score_sentiment(self, news_items: List[NewsItem]) -> float:
        """
        Score sentiment from news items
        Returns: -1.0 (very bearish) to +1.0 (very bullish)
        """
        if not news_items:
            return 0.0

        total_score = 0.0
        total_weight = 0.0

        for item in news_items:
            # Calculate time decay (4-hour half-life for intraday)
            hours_ago = (datetime.now() - item.timestamp).total_seconds() / 3600
            time_decay = 0.5 ** (hours_ago / 4)  # Exponential decay

            # Score based on keywords
            headline = item.title.lower()
            item_score = 0.0

            # Check positive keywords
            for keyword, weight in self.POSITIVE_KEYWORDS.items():
                if keyword in headline:
                    item_score += weight

            # Check negative keywords
            for keyword, weight in self.NEGATIVE_KEYWORDS.items():
                if keyword in headline:
                    item_score += weight  # weight is already negative

            # Apply time decay
            weighted_score = item_score * time_decay

            total_score += weighted_score
            total_weight += time_decay

        # Normalize to -1.0 to +1.0 range
        if total_weight > 0:
            final_score = total_score / total_weight
            final_score = max(-1.0, min(1.0, final_score))
        else:
            final_score = 0.0

        return final_score


# Singleton instance
_data_layer = None

def get_data_layer() -> DataLayer:
    """Get singleton Data Layer instance"""
    global _data_layer
    if _data_layer is None:
        _data_layer = DataLayer()
    return _data_layer


if __name__ == "__main__":
    # Test the data layer
    logging.basicConfig(level=logging.INFO)

    data = get_data_layer()

    # Test 1: Get watchlist
    print("\n=== TEST 1: Hybrid Watchlist ===")
    watchlist = data.get_watchlist()
    print(f"Watchlist size: {len(watchlist)}")
    print(f"Top 10 symbols: {watchlist[:10]}")

    # Test 2: Get OHLCV data
    print("\n=== TEST 2: OHLCV Data ===")
    symbol = 'NSE_EQ|RELIANCE-EQ'
    ohlcv = data.get_ohlcv(symbol, '30m', 50)
    if ohlcv is not None:
        print(f"Fetched {len(ohlcv)} bars for {symbol}")
        print(f"Latest close: ₹{ohlcv['close'].iloc[-1]:.2f}")

    # Test 3: Calculate indicators
    print("\n=== TEST 3: Technical Indicators ===")
    if ohlcv is not None:
        indicators = data.calculate_indicators(ohlcv)
        print(f"RSI: {indicators.get('rsi', 0):.2f}")
        print(f"MACD: {indicators.get('macd', 0):.2f}")
        print(f"ATR: {indicators.get('atr', 0):.2f}")
        print(f"ADX: {indicators.get('adx', 0):.2f}")

    # Test 4: Get news and sentiment
    print("\n=== TEST 4: News & Sentiment ===")
    news = data.get_news(symbol, lookback_hours=24)
    print(f"Found {len(news)} news items")
    if news:
        print(f"Latest: {news[0].title}")

    sentiment = data.score_sentiment(news)
    print(f"Sentiment score: {sentiment:.2f} ({'Bullish' if sentiment > 0 else 'Bearish'})")

    print("\n✅ Data Layer test complete!")
