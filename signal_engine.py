"""
Signal Engine - Quantitative Trading Strategies (No LLM)
Implements 3 strategies: News Momentum, Technical Breakout, Mean Reversion
All strategies are backtestable and deterministic
"""

import logging
from typing import List, Optional, Dict
from dataclasses import dataclass
from datetime import datetime
import pandas as pd
import numpy as np

from data_layer import get_data_layer, Signal
from strategy_analyzer import get_strategy_analyzer

logger = logging.getLogger(__name__)


class SignalEngine:
    """Generate trading signals using quantitative strategies"""

    def __init__(self):
        self.data_layer = get_data_layer()
        self.strategy_analyzer = get_strategy_analyzer()
        logger.info("Signal Engine initialized with strategy analyzer")

    def generate_signals(self, symbols: List[str]) -> List[Signal]:
        """
        Generate signals for all symbols using all strategies
        Applies confidence multipliers based on past performance (LEARNING)
        Returns list of high-confidence signals
        """
        all_signals = []

        # Analyze past strategy performance first
        try:
            self.strategy_analyzer.analyze_strategy_performance(days=30)
        except Exception as e:
            logger.warning(f"Could not analyze strategy performance: {e}")

        for symbol in symbols:
            try:
                # Run all 3 strategies
                signal_1 = self.news_momentum_strategy(symbol)
                signal_2 = self.technical_breakout_strategy(symbol)
                signal_3 = self.mean_reversion_strategy(symbol)

                # Collect valid signals and apply learning-based multipliers
                for signal in [signal_1, signal_2, signal_3]:
                    if signal:
                        # LEARNING: Apply confidence multiplier based on past performance
                        multiplier = self.strategy_analyzer.get_strategy_multiplier(signal.strategy)
                        original_confidence = signal.confidence
                        signal.confidence = min(0.95, signal.confidence * multiplier)  # Cap at 0.95

                        if signal.confidence != original_confidence:
                            logger.debug(f"  {signal.strategy}: confidence {original_confidence:.2f} -> {signal.confidence:.2f} (x{multiplier:.2f})")

                        # Filter by adjusted confidence
                        if signal.confidence >= 0.65:  # Minimum threshold
                            # Check if strategy should still be traded
                            if self.strategy_analyzer.should_trade_strategy(signal.strategy):
                                all_signals.append(signal)
                            else:
                                logger.debug(f"  Skipping {signal.strategy} - poor historical performance")

            except Exception as e:
                logger.error(f"Error generating signals for {symbol}: {e}")

        # Sort by confidence (highest first)
        all_signals.sort(key=lambda x: x.confidence, reverse=True)

        logger.info(f"Generated {len(all_signals)} signals from {len(symbols)} symbols (after learning adjustments)")
        return all_signals

    # ==================== STRATEGY 1: NEWS MOMENTUM ====================

    def news_momentum_strategy(self, symbol: str) -> Optional[Signal]:
        """
        Entry Conditions (ALL must be true):
        1. News sentiment > 0.6 in last 4 hours
        2. Price > VWAP (confirming momentum)
        3. Volume > 1.5x average (confirming interest)
        4. RSI < 70 (not overbought)
        5. Price above SMA(20)

        Exit:
        - Target: 1.5% gain OR resistance level
        - Stop: 0.75% loss OR VWAP breakdown
        - Time: Close at EOD if intraday
        """
        try:
            # Get data
            ohlcv_intraday = self.data_layer.get_ohlcv(symbol, '15m', 50)
            ohlcv_daily = self.data_layer.get_ohlcv(symbol, '1d', 50)
            news = self.data_layer.get_news(symbol, lookback_hours=4)

            if ohlcv_intraday is None or ohlcv_daily is None:
                return None

            # Calculate indicators
            indicators_intraday = self.data_layer.calculate_indicators(ohlcv_intraday)
            indicators_daily = self.data_layer.calculate_indicators(ohlcv_daily)

            # Calculate news sentiment
            news_score = self.data_layer.score_sentiment(news)

            current_price = indicators_intraday.get('close', 0)

            # Validate current price
            if current_price <= 0:
                logger.warning(f"Invalid current price for {symbol}: {current_price}")
                return None

            vwap = indicators_intraday.get('vwap', 0)
            rsi = indicators_intraday.get('rsi', 50)
            sma_20 = indicators_intraday.get('sma_20', 0)
            volume = ohlcv_intraday['volume'].iloc[-1]
            avg_volume = indicators_intraday.get('volume_sma', 0)

            # Entry Conditions
            conditions = {
                'news_sentiment': news_score > 0.6,
                'price_above_vwap': current_price > vwap > 0,
                'volume_spike': volume > avg_volume * 1.5 if avg_volume > 0 else False,
                'rsi_not_overbought': rsi < 70,
                'price_above_sma': current_price > sma_20 > 0
            }

            # Check if all conditions met
            if not all(conditions.values()):
                return None

            # Calculate confidence
            # Base confidence from news
            confidence = 0.65 + (news_score - 0.6) * 0.5  # 0.65 to 0.85 range

            # Boost confidence if volume is very high
            if volume > avg_volume * 2:
                confidence += 0.05

            # Boost if daily trend also strong
            if indicators_daily.get('rsi', 50) > 50 and indicators_daily.get('close', 0) > indicators_daily.get('sma_20', 0):
                confidence += 0.05

            confidence = min(confidence, 0.95)  # Cap at 0.95

            # Calculate entry, stop-loss, target
            entry_price = current_price

            # Stop-loss: 0.75% below entry or VWAP, whichever is tighter
            sl_percent = entry_price * 0.0075
            sl_vwap = vwap
            stop_loss = max(entry_price - sl_percent, sl_vwap)

            # Target: 1.5% gain
            target = entry_price * 1.015

            # Determine product (intraday or delivery)
            # News momentum is typically short-term, so intraday
            product = 'I'

            return Signal(
                symbol=symbol,
                strategy='news_momentum',
                direction='BUY',
                entry_price=entry_price,
                stop_loss=stop_loss,
                target=target,
                confidence=confidence,
                product=product,
                news_score=news_score,
                tech_score=rsi / 100.0  # Normalize to 0-1
            )

        except Exception as e:
            logger.error(f"Error in news_momentum_strategy for {symbol}: {e}")
            return None

    # ==================== STRATEGY 2: TECHNICAL BREAKOUT ====================

    def technical_breakout_strategy(self, symbol: str) -> Optional[Signal]:
        """
        Entry Conditions (ALL must be true):
        1. Price breaks above 20-day high with volume > 2x average
        2. ADX > 25 (strong trend)
        3. MACD crossover in last 3 bars
        4. Price > SMA(50) and SMA(20) > SMA(50) (uptrend structure)

        Exit:
        - Target: 2.5% gain OR previous swing high
        - Stop: 1.2% loss OR below recent swing low
        - Trailing: Move SL to breakeven after 1R gain
        """
        try:
            # Get data
            ohlcv_daily = self.data_layer.get_ohlcv(symbol, '1d', 100)
            ohlcv_intraday = self.data_layer.get_ohlcv(symbol, '30m', 50)

            if ohlcv_daily is None or ohlcv_intraday is None:
                return None

            # Calculate indicators
            indicators_daily = self.data_layer.calculate_indicators(ohlcv_daily)
            indicators_intraday = self.data_layer.calculate_indicators(ohlcv_intraday)

            current_price = indicators_intraday.get('close', 0)

            # Validate current price
            if current_price <= 0:
                logger.warning(f"Invalid current price for {symbol}: {current_price}")
                return None

            high_20d = ohlcv_daily['high'].rolling(20).max().iloc[-2]  # Previous 20-day high
            volume = ohlcv_daily['volume'].iloc[-1]
            avg_volume = indicators_daily.get('volume_sma', 0)
            adx = indicators_daily.get('adx', 0)
            sma_20 = indicators_daily.get('sma_20', 0)
            sma_50 = indicators_daily.get('sma_50', 0)
            macd = indicators_daily.get('macd', 0)
            macd_signal = indicators_daily.get('macd_signal', 0)
            macd_hist = indicators_daily.get('macd_hist', 0)

            # Check for MACD crossover in last 3 bars
            macd_crossover = False
            if len(ohlcv_daily) >= 3:
                # Recalculate MACD for previous bars
                for i in range(1, 4):
                    prev_ohlcv = ohlcv_daily.iloc[:-i]
                    if len(prev_ohlcv) >= 26:
                        prev_indicators = self.data_layer.calculate_indicators(prev_ohlcv)
                        prev_macd_hist = prev_indicators.get('macd_hist', 0)
                        if prev_macd_hist < 0 and macd_hist > 0:
                            macd_crossover = True
                            break

            # Entry Conditions
            conditions = {
                'price_breakout': current_price > high_20d > 0,
                'volume_spike': volume > avg_volume * 2 if avg_volume > 0 else False,
                'strong_trend': adx > 25,
                'macd_crossover': macd_crossover,
                'uptrend_structure': (current_price > sma_50 > 0) and (sma_20 > sma_50)
            }

            # Check if all conditions met
            if not all(conditions.values()):
                return None

            # Calculate confidence
            confidence = 0.70  # Base for breakout

            # Boost for very high volume
            if volume > avg_volume * 3:
                confidence += 0.05

            # Boost for very strong trend
            if adx > 35:
                confidence += 0.05

            # Boost if far above resistance
            breakout_strength = (current_price - high_20d) / high_20d
            if breakout_strength > 0.02:  # 2% above resistance
                confidence += 0.05

            confidence = min(confidence, 0.95)

            # Calculate entry, stop-loss, target
            entry_price = current_price

            # Stop-loss: 1.2% below entry or recent swing low
            swing_low = ohlcv_daily['low'].rolling(10).min().iloc[-1]
            sl_percent = entry_price * 0.012
            stop_loss = max(entry_price - sl_percent, swing_low)

            # Target: 2.5% gain
            target = entry_price * 1.025

            # Breakouts can be held longer (delivery)
            product = 'D'

            return Signal(
                symbol=symbol,
                strategy='technical_breakout',
                direction='BUY',
                entry_price=entry_price,
                stop_loss=stop_loss,
                target=target,
                confidence=confidence,
                product=product,
                news_score=0.0,  # Not news-based
                tech_score=min(adx / 50.0, 1.0)  # Normalize ADX to 0-1
            )

        except Exception as e:
            logger.error(f"Error in technical_breakout_strategy for {symbol}: {e}")
            return None

    # ==================== STRATEGY 3: MEAN REVERSION ====================

    def mean_reversion_strategy(self, symbol: str) -> Optional[Signal]:
        """
        Entry Conditions (ALL must be true):
        1. RSI < 30 (oversold) OR price at lower Bollinger Band
        2. ADX < 20 (weak trend, likely ranging)
        3. Price near support level (recent swing low)
        4. Volume normal (not panic selling)

        Exit:
        - Target: Middle Bollinger Band OR RSI = 50
        - Stop: 1% below support
        - Time: Close by 3:15 PM (don't hold overnight)
        """
        try:
            # Get data
            ohlcv_intraday = self.data_layer.get_ohlcv(symbol, '15m', 100)
            ohlcv_daily = self.data_layer.get_ohlcv(symbol, '1d', 50)

            if ohlcv_intraday is None or ohlcv_daily is None:
                return None

            # Calculate indicators
            indicators_intraday = self.data_layer.calculate_indicators(ohlcv_intraday)
            indicators_daily = self.data_layer.calculate_indicators(ohlcv_daily)

            current_price = indicators_intraday.get('close', 0)

            # Validate current price
            if current_price <= 0:
                logger.warning(f"Invalid current price for {symbol}: {current_price}")
                return None

            rsi = indicators_intraday.get('rsi', 50)
            bb_lower = indicators_intraday.get('bb_lower', 0)
            bb_middle = indicators_intraday.get('bb_middle', 0)
            adx = indicators_daily.get('adx', 25)
            volume = ohlcv_intraday['volume'].iloc[-1]
            avg_volume = indicators_intraday.get('volume_sma', 0)

            # Find recent support
            support = ohlcv_intraday['low'].rolling(20).min().iloc[-1]

            # Entry Conditions
            oversold = (rsi < 30) or (current_price <= bb_lower * 1.01)  # Within 1% of BB lower
            weak_trend = adx < 20
            near_support = abs(current_price - support) / current_price < 0.02  # Within 2% of support
            normal_volume = 0.7 < (volume / avg_volume) < 1.5 if avg_volume > 0 else True  # Not panic

            conditions = {
                'oversold': oversold,
                'weak_trend': weak_trend,
                'near_support': near_support,
                'normal_volume': normal_volume
            }

            # Check if all conditions met
            if not all(conditions.values()):
                return None

            # Calculate confidence
            confidence = 0.65  # Base for mean reversion

            # Boost if RSI is extremely oversold
            if rsi < 25:
                confidence += 0.05

            # Boost if price is below BB lower
            if current_price < bb_lower:
                confidence += 0.05

            # Boost if near major support (daily low)
            daily_support = ohlcv_daily['low'].rolling(20).min().iloc[-1]
            if abs(current_price - daily_support) / current_price < 0.01:
                confidence += 0.05

            confidence = min(confidence, 0.90)

            # Calculate entry, stop-loss, target
            entry_price = current_price

            # Stop-loss: 1% below support
            stop_loss = support * 0.99

            # Target: Middle Bollinger Band (mean reversion target)
            target = bb_middle if bb_middle > current_price else current_price * 1.015

            # Mean reversion is short-term (intraday)
            product = 'I'

            return Signal(
                symbol=symbol,
                strategy='mean_reversion',
                direction='BUY',
                entry_price=entry_price,
                stop_loss=stop_loss,
                target=target,
                confidence=confidence,
                product=product,
                news_score=0.0,  # Not news-based
                tech_score=(50 - rsi) / 50.0  # Normalize oversold condition to 0-1
            )

        except Exception as e:
            logger.error(f"Error in mean_reversion_strategy for {symbol}: {e}")
            return None

    # ==================== SIGNAL VALIDATION ====================

    def validate_signal(self, signal: Signal) -> bool:
        """Validate signal before execution"""
        try:
            # Check R:R ratio
            risk = abs(signal.entry_price - signal.stop_loss)
            reward = abs(signal.target - signal.entry_price)

            if risk == 0:
                return False

            rr_ratio = reward / risk

            # Minimum R:R requirements
            min_rr = 1.5 if signal.product == 'I' else 1.2

            if rr_ratio < min_rr:
                logger.warning(f"Signal {signal.symbol} rejected: R:R {rr_ratio:.2f} < {min_rr}")
                return False

            # Check stop-loss distance (not too tight, not too wide)
            sl_percent = risk / signal.entry_price

            if sl_percent < 0.005:  # Less than 0.5%
                logger.warning(f"Signal {signal.symbol} rejected: Stop-loss too tight ({sl_percent:.2%})")
                return False

            if sl_percent > 0.03:  # More than 3%
                logger.warning(f"Signal {signal.symbol} rejected: Stop-loss too wide ({sl_percent:.2%})")
                return False

            # Check confidence
            if signal.confidence < 0.65:
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating signal {signal.symbol}: {e}")
            return False


# Singleton instance
_signal_engine = None

def get_signal_engine() -> SignalEngine:
    """Get singleton Signal Engine instance"""
    global _signal_engine
    if _signal_engine is None:
        _signal_engine = SignalEngine()
    return _signal_engine


if __name__ == "__main__":
    # Test the signal engine
    logging.basicConfig(level=logging.INFO)

    engine = get_signal_engine()

    # Test with a few symbols
    test_symbols = [
        'NSE_EQ|RELIANCE-EQ',
        'NSE_EQ|TCS-EQ',
        'NSE_EQ|INFY-EQ'
    ]

    print("\n=== TESTING SIGNAL ENGINE ===\n")

    for symbol in test_symbols:
        print(f"\nAnalyzing {symbol}...")

        # Test each strategy
        signal_1 = engine.news_momentum_strategy(symbol)
        signal_2 = engine.technical_breakout_strategy(symbol)
        signal_3 = engine.mean_reversion_strategy(symbol)

        signals = [s for s in [signal_1, signal_2, signal_3] if s is not None]

        if signals:
            for signal in signals:
                print(f"\n  ✓ {signal.strategy.upper()} Signal:")
                print(f"    Direction: {signal.direction}")
                print(f"    Entry: ₹{signal.entry_price:.2f}")
                print(f"    Stop Loss: ₹{signal.stop_loss:.2f}")
                print(f"    Target: ₹{signal.target:.2f}")
                print(f"    Confidence: {signal.confidence:.2%}")
                print(f"    Product: {'Intraday' if signal.product == 'I' else 'Delivery'}")

                # Validate
                valid = engine.validate_signal(signal)
                print(f"    Valid: {'✓ YES' if valid else '✗ NO'}")
        else:
            print("  No signals generated")

    print("\n✅ Signal Engine test complete!")
