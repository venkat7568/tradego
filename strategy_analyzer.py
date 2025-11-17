#!/usr/bin/env python3
"""
Strategy Performance Analyzer
Tracks and learns from past trading performance to optimize future decisions
"""

import sqlite3
from typing import Dict, List, Any
from datetime import datetime, timedelta
from dataclasses import dataclass

from logging_config import setup_logging

logger = setup_logging(__name__)


@dataclass
class StrategyPerformance:
    """Performance metrics for a strategy"""
    strategy: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    total_pnl: float
    avg_holding_time: float  # hours
    best_trade: float
    worst_trade: float
    avg_mae: float  # Maximum Adverse Excursion
    avg_mfe: float  # Maximum Favorable Excursion
    confidence_multiplier: float


class StrategyAnalyzer:
    """
    Analyzes past trades to learn which strategies work best
    and provides confidence multipliers for future trades
    """

    def __init__(self, db_path: str = "./data/tradego.db"):
        self.db_path = db_path
        self.performance_cache: Dict[str, StrategyPerformance] = {}
        self.last_analysis_time = None

    def _get_conn(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def analyze_strategy_performance(self, days: int = 30) -> Dict[str, StrategyPerformance]:
        """
        Analyze performance of each strategy over the last N days

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary of strategy -> StrategyPerformance
        """
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        conn = self._get_conn()
        cursor = conn.cursor()

        strategies = ['news_momentum', 'technical_breakout', 'mean_reversion']
        results = {}

        for strategy in strategies:
            # Get closed trades for this strategy
            cursor.execute("""
                SELECT
                    trade_id,
                    symbol,
                    entry_price,
                    exit_price,
                    quantity,
                    realized_pnl,
                    mae,
                    mfe,
                    entry_time,
                    exit_time
                FROM trades
                WHERE strategy = ?
                  AND status = 'closed'
                  AND entry_time >= ?
                ORDER BY entry_time DESC
            """, (strategy, cutoff_date))

            trades = cursor.fetchall()

            if not trades:
                logger.debug(f"No trades found for strategy: {strategy}")
                results[strategy] = StrategyPerformance(
                    strategy=strategy,
                    total_trades=0,
                    winning_trades=0,
                    losing_trades=0,
                    win_rate=0.0,
                    avg_profit=0.0,
                    avg_loss=0.0,
                    profit_factor=0.0,
                    total_pnl=0.0,
                    avg_holding_time=0.0,
                    best_trade=0.0,
                    worst_trade=0.0,
                    avg_mae=0.0,
                    avg_mfe=0.0,
                    confidence_multiplier=1.0  # Neutral for new strategies
                )
                continue

            # Calculate metrics
            total_trades = len(trades)
            winning_trades = [t for t in trades if t[5] > 0]  # realized_pnl > 0
            losing_trades = [t for t in trades if t[5] <= 0]

            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            win_rate = win_count / total_trades if total_trades > 0 else 0

            # P&L metrics
            total_pnl = sum(t[5] for t in trades)
            avg_profit = sum(t[5] for t in winning_trades) / win_count if win_count > 0 else 0
            avg_loss = abs(sum(t[5] for t in losing_trades) / loss_count) if loss_count > 0 else 0
            profit_factor = (win_count * avg_profit) / (loss_count * avg_loss) if loss_count > 0 and avg_loss > 0 else 0

            # Excursion metrics
            avg_mae = sum(abs(t[6] or 0) for t in trades) / total_trades
            avg_mfe = sum(abs(t[7] or 0) for t in trades) / total_trades

            # Best/worst trades
            best_trade = max(t[5] for t in trades)
            worst_trade = min(t[5] for t in trades)

            # Holding time (hours)
            holding_times = []
            for t in trades:
                if t[8] and t[9]:  # entry_time and exit_time
                    try:
                        entry = datetime.fromisoformat(t[8])
                        exit = datetime.fromisoformat(t[9])
                        hours = (exit - entry).total_seconds() / 3600
                        holding_times.append(hours)
                    except:
                        pass
            avg_holding_time = sum(holding_times) / len(holding_times) if holding_times else 0

            # Calculate confidence multiplier based on performance
            confidence_multiplier = self._calculate_confidence_multiplier(
                win_rate, profit_factor, total_trades
            )

            results[strategy] = StrategyPerformance(
                strategy=strategy,
                total_trades=total_trades,
                winning_trades=win_count,
                losing_trades=loss_count,
                win_rate=win_rate,
                avg_profit=avg_profit,
                avg_loss=avg_loss,
                profit_factor=profit_factor,
                total_pnl=total_pnl,
                avg_holding_time=avg_holding_time,
                best_trade=best_trade,
                worst_trade=worst_trade,
                avg_mae=avg_mae,
                avg_mfe=avg_mfe,
                confidence_multiplier=confidence_multiplier
            )

        conn.close()

        # Cache results
        self.performance_cache = results
        self.last_analysis_time = datetime.now()

        # Log summary
        logger.info("\n" + "=" * 60)
        logger.info("STRATEGY PERFORMANCE ANALYSIS (Last 30 days)")
        logger.info("=" * 60)
        for strategy, perf in results.items():
            logger.info(f"\n{strategy.upper()}:")
            logger.info(f"  Trades: {perf.total_trades} ({perf.winning_trades}W / {perf.losing_trades}L)")
            logger.info(f"  Win Rate: {perf.win_rate:.1%}")
            logger.info(f"  Profit Factor: {perf.profit_factor:.2f}")
            logger.info(f"  Total P&L: ₹{perf.total_pnl:,.2f}")
            logger.info(f"  Confidence Multiplier: {perf.confidence_multiplier:.2f}x")
        logger.info("=" * 60)

        return results

    def _calculate_confidence_multiplier(
        self, win_rate: float, profit_factor: float, trade_count: int
    ) -> float:
        """
        Calculate confidence multiplier based on strategy performance

        Good performance -> multiplier > 1.0 (boost confidence)
        Poor performance -> multiplier < 1.0 (reduce confidence)
        """
        # Need minimum sample size
        if trade_count < 10:
            return 1.0  # Neutral until we have enough data

        # Base multiplier on win rate and profit factor
        multiplier = 1.0

        # Win rate adjustment (-0.3 to +0.3)
        if win_rate > 0.6:
            multiplier += 0.3
        elif win_rate > 0.55:
            multiplier += 0.15
        elif win_rate < 0.45:
            multiplier -= 0.2
        elif win_rate < 0.5:
            multiplier -= 0.1

        # Profit factor adjustment (-0.2 to +0.2)
        if profit_factor > 2.0:
            multiplier += 0.2
        elif profit_factor > 1.5:
            multiplier += 0.1
        elif profit_factor < 1.0:
            multiplier -= 0.2
        elif profit_factor < 1.2:
            multiplier -= 0.1

        # Clamp between 0.5 and 1.5
        return max(0.5, min(1.5, multiplier))

    def get_strategy_multiplier(self, strategy: str) -> float:
        """
        Get confidence multiplier for a strategy

        Args:
            strategy: Strategy name

        Returns:
            Multiplier (0.5 to 1.5) to apply to base confidence
        """
        # Re-analyze if cache is stale (>1 hour)
        if (not self.last_analysis_time or
            (datetime.now() - self.last_analysis_time).total_seconds() > 3600):
            self.analyze_strategy_performance()

        if strategy in self.performance_cache:
            return self.performance_cache[strategy].confidence_multiplier

        return 1.0  # Neutral for unknown strategies

    def get_best_performing_strategies(self, top_n: int = 2) -> List[str]:
        """
        Get the top N performing strategies

        Args:
            top_n: Number of top strategies to return

        Returns:
            List of strategy names sorted by performance
        """
        if not self.performance_cache:
            self.analyze_strategy_performance()

        # Sort by profit factor * win_rate (combined metric)
        sorted_strategies = sorted(
            self.performance_cache.items(),
            key=lambda x: x[1].profit_factor * x[1].win_rate if x[1].total_trades >= 10 else 0,
            reverse=True
        )

        return [s[0] for s in sorted_strategies[:top_n]]

    def should_trade_strategy(self, strategy: str) -> bool:
        """
        Determine if a strategy should be traded based on past performance

        Args:
            strategy: Strategy name

        Returns:
            True if strategy has good performance, False otherwise
        """
        if strategy not in self.performance_cache:
            return True  # Allow new strategies

        perf = self.performance_cache[strategy]

        # Require minimum sample size
        if perf.total_trades < 20:
            return True  # Still learning

        # Disable if consistently losing
        if perf.win_rate < 0.4 and perf.profit_factor < 1.0:
            logger.warning(f"⚠️ Strategy {strategy} has poor performance - reducing trades")
            return False

        return True


# Singleton instance
_analyzer = None


def get_strategy_analyzer() -> StrategyAnalyzer:
    """Get singleton strategy analyzer instance"""
    global _analyzer
    if _analyzer is None:
        _analyzer = StrategyAnalyzer()
    return _analyzer
