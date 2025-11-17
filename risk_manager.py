"""
Risk Manager - Portfolio-level and per-trade risk controls
Handles position sizing, portfolio limits, correlation checks, circuit breakers
"""

import logging
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import date
import numpy as np

from data_layer import Signal, get_data_layer
from pnl_engine import get_pnl_engine, Trade, Portfolio

logger = logging.getLogger(__name__)


@dataclass
class PositionSize:
    """Position sizing result"""
    quantity: int
    risk_amount: float
    rr_ratio: float
    margin_required: float
    capital_required: float


@dataclass
class RiskLimits:
    """Portfolio risk configuration"""
    # Capital allocation
    total_capital: float = 1_000_000  # ₹10 lakh
    intraday_allocation: float = 0.70  # 70%
    swing_allocation: float = 0.30  # 30%

    # Risk per trade
    min_risk_per_trade: float = 0.005  # 0.5%
    max_risk_per_trade: float = 0.010  # 1.0%

    # Portfolio limits
    max_open_positions: int = 5
    max_portfolio_heat: float = 0.03  # 3% total risk
    max_capital_deployed: float = 0.50  # 50%

    # Sector limits
    max_positions_per_sector: int = 2

    # Circuit breakers
    max_daily_loss_percent: float = 0.02  # 2%
    max_weekly_loss_percent: float = 0.05  # 5%

    # Correlation
    max_correlation: float = 0.7  # Reject if correlation > 0.7


class RiskManager:
    """Manage portfolio and per-trade risk"""

    # Sector mapping (simplified)
    SECTOR_MAP = {
        'RELIANCE': 'Energy', 'ONGC': 'Energy', 'BPCL': 'Energy', 'NTPC': 'Energy',
        'POWERGRID': 'Energy', 'TATAPOWER': 'Energy', 'ADANIGREEN': 'Energy',
        'ADANIPWR': 'Energy', 'COALINDIA': 'Energy',

        'TCS': 'IT', 'INFY': 'IT', 'WIPRO': 'IT', 'HCLTECH': 'IT', 'TECHM': 'IT',

        'HDFCBANK': 'Banking', 'ICICIBANK': 'Banking', 'SBIN': 'Banking',
        'AXISBANK': 'Banking', 'KOTAKBANK': 'Banking', 'INDUSINDBK': 'Banking',

        'BAJFINANCE': 'Financial', 'BAJAJFINSV': 'Financial', 'SBILIFE': 'Financial',
        'HDFCLIFE': 'Financial', 'MUTHOOTFIN': 'Financial',

        'BHARTIARTL': 'Telecom', 'INDUSTOWER': 'Telecom',

        'MARUTI': 'Auto', 'TATAMOTORS': 'Auto', 'BAJAJ-AUTO': 'Auto',
        'HEROMOTOCO': 'Auto', 'EICHERMOT': 'Auto', 'M&M': 'Auto',

        'SUNPHARMA': 'Pharma', 'DRREDDY': 'Pharma', 'CIPLA': 'Pharma',
        'LUPIN': 'Pharma', 'DIVISLAB': 'Pharma', 'TORNTPHARM': 'Pharma',
        'APOLLOHOSP': 'Pharma',

        'TATASTEEL': 'Metals', 'JSWSTEEL': 'Metals', 'HINDALCO': 'Metals',
        'VEDL': 'Metals', 'SAIL': 'Metals', 'NMDC': 'Metals',

        'HINDUNILVR': 'FMCG', 'ITC': 'FMCG', 'NESTLEIND': 'FMCG',
        'BRITANNIA': 'FMCG', 'DABUR': 'FMCG', 'MARICO': 'FMCG',
        'GODREJCP': 'FMCG', 'TATACONSUM': 'FMCG',

        'LT': 'Infrastructure', 'ULTRACEMCO': 'Infrastructure',
        'GRASIM': 'Infrastructure', 'SHREECEM': 'Infrastructure',
        'ADANIPORTS': 'Infrastructure', 'CONCOR': 'Infrastructure',

        'ASIANPAINT': 'Materials', 'BERGEPAINT': 'Materials',
        'PIDILITIND': 'Materials',

        'TITAN': 'Retail', 'INDIGO': 'Retail', 'PAGEIND': 'Retail',
        'VOLTAS': 'Retail', 'HAVELLS': 'Retail'
    }

    def __init__(self, limits: RiskLimits = None):
        self.limits = limits or RiskLimits()
        self.pnl_engine = get_pnl_engine()
        self.data_layer = get_data_layer()
        logger.info(f"Risk Manager initialized: Max positions={self.limits.max_open_positions}, "
                   f"Portfolio heat limit={self.limits.max_portfolio_heat:.1%}")

    # ==================== POSITION SIZING ====================

    def calculate_position_size(self, signal: Signal, available_capital: float) -> Optional[PositionSize]:
        """
        Calculate position size based on risk and capital
        Returns PositionSize or None if position cannot be sized
        """
        try:
            # Determine risk per trade based on confidence
            # Higher confidence = higher risk
            risk_percent = self.limits.min_risk_per_trade + \
                          (signal.confidence - 0.65) * \
                          (self.limits.max_risk_per_trade - self.limits.min_risk_per_trade) / 0.35

            risk_percent = min(risk_percent, self.limits.max_risk_per_trade)

            # Calculate risk amount in rupees
            risk_amount = self.limits.total_capital * risk_percent

            # Calculate quantity based on stop-loss distance
            risk_per_share = abs(signal.entry_price - signal.stop_loss)

            if risk_per_share == 0:
                logger.warning(f"Invalid stop-loss for {signal.symbol}")
                return None

            quantity = int(risk_amount / risk_per_share)

            if quantity <= 0:
                logger.warning(f"Calculated quantity is 0 for {signal.symbol}")
                return None

            # Calculate position value
            position_value = quantity * signal.entry_price

            # Calculate margin required
            if signal.product == 'I':  # Intraday with 5x leverage
                margin_required = position_value / 5
                capital_required = margin_required
            else:  # Delivery, no margin
                margin_required = position_value
                capital_required = position_value

            # Check if we have enough capital
            if capital_required > available_capital:
                # Reduce quantity to fit available capital
                if signal.product == 'I':
                    quantity = int((available_capital * 5) / signal.entry_price)
                else:
                    quantity = int(available_capital / signal.entry_price)

                # Recalculate
                position_value = quantity * signal.entry_price
                margin_required = position_value / 5 if signal.product == 'I' else position_value
                capital_required = margin_required if signal.product == 'I' else position_value
                risk_amount = quantity * risk_per_share

            if quantity <= 0:
                logger.warning(f"Insufficient capital for {signal.symbol}")
                return None

            # Calculate R:R ratio
            reward = abs(signal.target - signal.entry_price) * quantity
            risk = risk_amount
            rr_ratio = reward / risk if risk > 0 else 0

            # Check minimum R:R
            min_rr = 1.5 if signal.product == 'I' else 1.2
            if rr_ratio < min_rr:
                logger.warning(f"R:R ratio {rr_ratio:.2f} < {min_rr} for {signal.symbol}")
                return None

            # Check maximum position size (10% of total capital)
            max_position_value = self.limits.total_capital * 0.10
            if position_value > max_position_value:
                # Scale down
                scale_factor = max_position_value / position_value
                quantity = int(quantity * scale_factor)

                if quantity <= 0:
                    return None

                # Recalculate
                position_value = quantity * signal.entry_price
                margin_required = position_value / 5 if signal.product == 'I' else position_value
                capital_required = margin_required if signal.product == 'I' else position_value
                risk_amount = quantity * risk_per_share

            return PositionSize(
                quantity=quantity,
                risk_amount=risk_amount,
                rr_ratio=rr_ratio,
                margin_required=margin_required,
                capital_required=capital_required
            )

        except Exception as e:
            logger.error(f"Error calculating position size for {signal.symbol}: {e}")
            return None

    # ==================== PORTFOLIO LIMITS ====================

    def check_portfolio_limits(self, new_signal: Signal, position_size: PositionSize,
                               open_trades: List[Trade], portfolio: Portfolio) -> Tuple[bool, str]:
        """
        Check if new trade passes portfolio-level limits
        Returns (allowed, reason)
        """
        try:
            # Limit 1: Max open positions
            if len(open_trades) >= self.limits.max_open_positions:
                return False, f"Max open positions reached ({self.limits.max_open_positions})"

            # Limit 2: Portfolio heat (total risk)
            current_heat = sum(t.risk_amount for t in open_trades)
            new_heat = current_heat + position_size.risk_amount
            heat_percent = new_heat / self.limits.total_capital

            if heat_percent > self.limits.max_portfolio_heat:
                return False, f"Portfolio heat {heat_percent:.1%} > {self.limits.max_portfolio_heat:.1%}"

            # Limit 3: Capital deployed
            deployed_percent = portfolio.deployed_capital / self.limits.total_capital

            if deployed_percent > self.limits.max_capital_deployed:
                return False, f"Capital deployed {deployed_percent:.1%} > {self.limits.max_capital_deployed:.1%}"

            # Limit 4: Sector concentration
            new_sector = self.get_sector(new_signal.symbol)
            same_sector_count = sum(1 for t in open_trades if self.get_sector(t.symbol) == new_sector)

            if same_sector_count >= self.limits.max_positions_per_sector:
                return False, f"Max positions in {new_sector} sector reached ({self.limits.max_positions_per_sector})"

            # Limit 5: Product-specific capital allocation
            if new_signal.product == 'I':
                # Check intraday allocation
                intraday_capital_used = sum(
                    t.entry_price * t.quantity / 5  # Margin calculation
                    for t in open_trades if t.product == 'I'
                )
                intraday_limit = self.limits.total_capital * self.limits.intraday_allocation

                if intraday_capital_used + position_size.capital_required > intraday_limit:
                    return False, f"Intraday allocation limit reached"
            else:
                # Check swing allocation
                swing_capital_used = sum(
                    t.entry_price * t.quantity
                    for t in open_trades if t.product == 'D'
                )
                swing_limit = self.limits.total_capital * self.limits.swing_allocation

                if swing_capital_used + position_size.capital_required > swing_limit:
                    return False, f"Swing allocation limit reached"

            # Limit 6: Circuit breaker - daily loss
            daily_loss_percent = portfolio.total_pnl / self.limits.total_capital

            if daily_loss_percent < -self.limits.max_daily_loss_percent:
                return False, f"Daily circuit breaker triggered ({daily_loss_percent:.2%} loss)"

            return True, "All checks passed"

        except Exception as e:
            logger.error(f"Error checking portfolio limits: {e}")
            return False, f"Error: {e}"

    def get_sector(self, symbol: str) -> str:
        """Get sector for symbol"""
        try:
            # Extract symbol name from NSE_EQ|SYMBOL-EQ format
            symbol_name = symbol.split('|')[1].replace('-EQ', '')

            return self.SECTOR_MAP.get(symbol_name, 'Other')
        except:
            return 'Other'

    # ==================== CORRELATION CHECK ====================

    def check_correlation(self, new_symbol: str, open_trades: List[Trade]) -> Tuple[bool, str]:
        """
        Check correlation between new symbol and open positions
        Returns (allowed, reason)
        """
        if not open_trades:
            return True, "No open positions"

        try:
            # Get price data for new symbol
            new_ohlcv = self.data_layer.get_ohlcv(new_symbol, '1d', 30)

            if new_ohlcv is None or len(new_ohlcv) < 20:
                # Cannot calculate correlation, allow trade
                return True, "Insufficient data for correlation check"

            new_returns = new_ohlcv['close'].pct_change().dropna()

            # Check correlation with each open position
            for trade in open_trades:
                try:
                    trade_ohlcv = self.data_layer.get_ohlcv(trade.symbol, '1d', 30)

                    if trade_ohlcv is None or len(trade_ohlcv) < 20:
                        continue

                    trade_returns = trade_ohlcv['close'].pct_change().dropna()

                    # Align the returns
                    min_len = min(len(new_returns), len(trade_returns))
                    if min_len < 10:
                        continue

                    new_returns_aligned = new_returns.iloc[-min_len:]
                    trade_returns_aligned = trade_returns.iloc[-min_len:]

                    # Calculate correlation
                    correlation = np.corrcoef(new_returns_aligned, trade_returns_aligned)[0, 1]

                    if abs(correlation) > self.limits.max_correlation:
                        return False, f"High correlation ({correlation:.2f}) with {trade.symbol}"

                except Exception as e:
                    logger.debug(f"Error checking correlation with {trade.symbol}: {e}")
                    continue

            return True, "Correlation checks passed"

        except Exception as e:
            logger.error(f"Error in correlation check: {e}")
            # On error, allow trade (fail open)
            return True, "Correlation check error"

    # ==================== AVAILABLE CAPITAL ====================

    def get_available_capital(self, product: str, portfolio: Portfolio) -> float:
        """Get available capital for intraday or swing trading"""
        try:
            if product == 'I':  # Intraday
                intraday_limit = self.limits.total_capital * self.limits.intraday_allocation

                # Get intraday trades
                open_trades = self.pnl_engine.get_open_trades()
                intraday_trades = [t for t in open_trades if t.product == 'I']

                # Calculate used capital (considering 5x margin)
                used_capital = sum(t.entry_price * t.quantity / 5 for t in intraday_trades)

                available = intraday_limit - used_capital

            else:  # Swing/Delivery
                swing_limit = self.limits.total_capital * self.limits.swing_allocation

                # Get swing trades
                open_trades = self.pnl_engine.get_open_trades()
                swing_trades = [t for t in open_trades if t.product == 'D']

                # Calculate used capital (no margin)
                used_capital = sum(t.entry_price * t.quantity for t in swing_trades)

                available = swing_limit - used_capital

            return max(available, 0)

        except Exception as e:
            logger.error(f"Error calculating available capital: {e}")
            return 0.0


# Singleton instance
_risk_manager = None

def get_risk_manager(limits: RiskLimits = None) -> RiskManager:
    """Get singleton Risk Manager instance"""
    global _risk_manager
    if _risk_manager is None:
        _risk_manager = RiskManager(limits)
    return _risk_manager


if __name__ == "__main__":
    # Test the risk manager
    logging.basicConfig(level=logging.INFO)

    from data_layer import Signal

    rm = get_risk_manager()

    # Create a test signal
    test_signal = Signal(
        symbol='NSE_EQ|RELIANCE-EQ',
        strategy='news_momentum',
        direction='BUY',
        entry_price=2500.0,
        stop_loss=2475.0,
        target=2550.0,
        confidence=0.78,
        product='I',
        news_score=0.65,
        tech_score=0.72
    )

    print("\n=== TESTING RISK MANAGER ===\n")

    # Test 1: Calculate position size
    print("Test 1: Position Sizing")
    available = 700_000  # ₹7L for intraday
    position_size = rm.calculate_position_size(test_signal, available)

    if position_size:
        print(f"  ✓ Quantity: {position_size.quantity} shares")
        print(f"  ✓ Risk Amount: ₹{position_size.risk_amount:,.2f}")
        print(f"  ✓ R:R Ratio: {position_size.rr_ratio:.2f}")
        print(f"  ✓ Margin Required: ₹{position_size.margin_required:,.2f}")
        print(f"  ✓ Capital Required: ₹{position_size.capital_required:,.2f}")
    else:
        print("  ✗ Position sizing failed")

    # Test 2: Check portfolio limits
    print("\nTest 2: Portfolio Limits")
    open_trades = []
    portfolio = rm.pnl_engine.get_daily_pnl(date.today())

    allowed, reason = rm.check_portfolio_limits(test_signal, position_size, open_trades, portfolio)
    print(f"  {'✓' if allowed else '✗'} {reason}")

    # Test 3: Sector check
    print("\nTest 3: Sector Classification")
    sector = rm.get_sector(test_signal.symbol)
    print(f"  ✓ {test_signal.symbol} → {sector}")

    print("\n✅ Risk Manager test complete!")
