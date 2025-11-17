"""
P&L Engine - Centralized Trade Lifecycle and Profit Tracking
Handles all trade state management, P&L calculations, and performance metrics
"""

import sqlite3
import json
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class TradeDirection(Enum):
    BUY = "BUY"
    SELL = "SELL"


class TradeProduct(Enum):
    INTRADAY = "I"  # Intraday with margin
    DELIVERY = "D"  # Delivery/Swing (no margin)


class TradeStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class ExitReason(Enum):
    TARGET = "TARGET"
    STOP_LOSS = "STOP_LOSS"
    MANUAL = "MANUAL"
    EOD_SQUAREOFF = "EOD_SQUAREOFF"
    TRAILING_STOP = "TRAILING_STOP"


@dataclass
class Trade:
    """Complete trade record with all lifecycle data"""
    # Identity
    trade_id: str
    symbol: str
    strategy: str  # 'news_momentum', 'technical_breakout', 'mean_reversion'

    # Entry
    entry_time: datetime
    entry_price: float
    quantity: int
    product: str  # 'I' or 'D'
    direction: str  # 'BUY' or 'SELL'

    # Risk Plan
    stop_loss: float
    target: float
    risk_amount: float  # Amount risked (in rupees)

    # Exit
    exit_time: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None

    # P&L
    gross_pnl: float = 0.0
    brokerage: float = 0.0
    net_pnl: float = 0.0
    pnl_percent: float = 0.0

    # Performance Metrics
    mae: float = 0.0  # Maximum Adverse Excursion
    mfe: float = 0.0  # Maximum Favorable Excursion
    holding_minutes: int = 0

    # Attribution
    news_score: float = 0.0
    tech_score: float = 0.0
    confidence: float = 0.0

    # Order IDs (for reconciliation)
    entry_order_id: Optional[str] = None
    target_order_id: Optional[str] = None
    sl_order_id: Optional[str] = None

    # Status
    status: str = "OPEN"

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        d = asdict(self)
        # Convert datetime to ISO format
        if isinstance(d['entry_time'], datetime):
            d['entry_time'] = d['entry_time'].isoformat()
        if d['exit_time'] and isinstance(d['exit_time'], datetime):
            d['exit_time'] = d['exit_time'].isoformat()
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'Trade':
        """Create Trade from dictionary"""
        # Convert ISO strings back to datetime
        if isinstance(d['entry_time'], str):
            d['entry_time'] = datetime.fromisoformat(d['entry_time'])
        if d.get('exit_time') and isinstance(d['exit_time'], str):
            d['exit_time'] = datetime.fromisoformat(d['exit_time'])
        return cls(**d)


@dataclass
class Portfolio:
    """Daily portfolio snapshot"""
    date: date

    # Capital
    starting_capital: float
    available_capital: float
    deployed_capital: float

    # Daily P&L
    realized_pnl: float
    unrealized_pnl: float
    total_pnl: float

    # Short-term (Intraday)
    intraday_pnl: float
    intraday_trades: int
    intraday_wins: int
    intraday_losses: int

    # Long-term (Swing/Delivery)
    swing_pnl: float
    swing_trades: int
    swing_wins: int
    swing_losses: int

    # Risk
    max_drawdown: float
    current_drawdown: float
    portfolio_heat: float  # % of capital at risk

    # Performance
    win_rate: float
    profit_factor: float
    sharpe_ratio: float

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        d = asdict(self)
        if isinstance(d['date'], date):
            d['date'] = d['date'].isoformat()
        return d


class PnLEngine:
    """Centralized P&L tracking and trade lifecycle management"""

    def __init__(self, db_path: str = "./data/tradego.db"):
        self.db_path = db_path
        self.conn = None
        self._ensure_database()

    def _ensure_database(self):
        """Create database and tables if they don't exist"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Create trades table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                symbol TEXT NOT NULL,
                strategy TEXT NOT NULL,

                entry_time TEXT NOT NULL,
                entry_price REAL NOT NULL,
                quantity INTEGER NOT NULL,
                product TEXT NOT NULL,
                direction TEXT NOT NULL,

                stop_loss REAL NOT NULL,
                target REAL NOT NULL,
                risk_amount REAL NOT NULL,

                exit_time TEXT,
                exit_price REAL,
                exit_reason TEXT,

                gross_pnl REAL DEFAULT 0.0,
                brokerage REAL DEFAULT 0.0,
                net_pnl REAL DEFAULT 0.0,
                pnl_percent REAL DEFAULT 0.0,

                mae REAL DEFAULT 0.0,
                mfe REAL DEFAULT 0.0,
                holding_minutes INTEGER DEFAULT 0,

                news_score REAL DEFAULT 0.0,
                tech_score REAL DEFAULT 0.0,
                confidence REAL DEFAULT 0.0,

                entry_order_id TEXT,
                target_order_id TEXT,
                sl_order_id TEXT,

                status TEXT DEFAULT 'OPEN',

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create daily portfolio table
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS daily_portfolio (
                date TEXT PRIMARY KEY,

                starting_capital REAL NOT NULL,
                available_capital REAL NOT NULL,
                deployed_capital REAL NOT NULL,

                realized_pnl REAL DEFAULT 0.0,
                unrealized_pnl REAL DEFAULT 0.0,
                total_pnl REAL DEFAULT 0.0,

                intraday_pnl REAL DEFAULT 0.0,
                intraday_trades INTEGER DEFAULT 0,
                intraday_wins INTEGER DEFAULT 0,
                intraday_losses INTEGER DEFAULT 0,

                swing_pnl REAL DEFAULT 0.0,
                swing_trades INTEGER DEFAULT 0,
                swing_wins INTEGER DEFAULT 0,
                swing_losses INTEGER DEFAULT 0,

                max_drawdown REAL DEFAULT 0.0,
                current_drawdown REAL DEFAULT 0.0,
                portfolio_heat REAL DEFAULT 0.0,

                win_rate REAL DEFAULT 0.0,
                profit_factor REAL DEFAULT 0.0,
                sharpe_ratio REAL DEFAULT 0.0,

                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create reconciliation log
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS reconciliation_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                trade_id TEXT NOT NULL,
                discrepancy_type TEXT NOT NULL,
                db_value TEXT,
                broker_value TEXT,
                resolved BOOLEAN DEFAULT FALSE,
                notes TEXT
            )
        """)

        # Create indexes
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_status ON trades(status)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_strategy ON trades(strategy)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_trades_entry_time ON trades(entry_time)")

        self.conn.commit()
        logger.info(f"Database initialized at {self.db_path}")

    def create_trade(self,
                    symbol: str,
                    strategy: str,
                    direction: str,
                    quantity: int,
                    entry_price: float,
                    stop_loss: float,
                    target: float,
                    product: str,
                    risk_amount: float,
                    confidence: float,
                    news_score: float = 0.0,
                    tech_score: float = 0.0,
                    entry_order_id: str = None,
                    target_order_id: str = None,
                    sl_order_id: str = None) -> Trade:
        """Create a new trade entry"""

        # Generate unique trade ID
        trade_id = f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        trade = Trade(
            trade_id=trade_id,
            symbol=symbol,
            strategy=strategy,
            entry_time=datetime.now(),
            entry_price=entry_price,
            quantity=quantity,
            product=product,
            direction=direction,
            stop_loss=stop_loss,
            target=target,
            risk_amount=risk_amount,
            confidence=confidence,
            news_score=news_score,
            tech_score=tech_score,
            entry_order_id=entry_order_id,
            target_order_id=target_order_id,
            sl_order_id=sl_order_id,
            status="OPEN"
        )

        # Insert into database
        self.conn.execute("""
            INSERT INTO trades (
                trade_id, symbol, strategy, entry_time, entry_price, quantity,
                product, direction, stop_loss, target, risk_amount,
                news_score, tech_score, confidence,
                entry_order_id, target_order_id, sl_order_id, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trade.trade_id, trade.symbol, trade.strategy,
            trade.entry_time.isoformat(), trade.entry_price, trade.quantity,
            trade.product, trade.direction, trade.stop_loss, trade.target,
            trade.risk_amount, trade.news_score, trade.tech_score,
            trade.confidence, trade.entry_order_id, trade.target_order_id,
            trade.sl_order_id, trade.status
        ))
        self.conn.commit()

        logger.info(f"Created trade: {trade_id} | {symbol} {direction} {quantity} @ {entry_price}")
        return trade

    def update_position(self, trade_id: str, current_price: float) -> None:
        """Update MAE/MFE and unrealized P&L for open position"""

        trade = self.get_trade(trade_id)
        if not trade or trade.status != "OPEN":
            return

        # Calculate unrealized P&L
        if trade.direction == "BUY":
            unrealized_pnl = (current_price - trade.entry_price) * trade.quantity
        else:
            unrealized_pnl = (trade.entry_price - current_price) * trade.quantity

        # Update MAE (Maximum Adverse Excursion)
        if unrealized_pnl < trade.mae:
            trade.mae = unrealized_pnl

        # Update MFE (Maximum Favorable Excursion)
        if unrealized_pnl > trade.mfe:
            trade.mfe = unrealized_pnl

        # Update in database
        self.conn.execute("""
            UPDATE trades
            SET mae = ?, mfe = ?, updated_at = ?
            WHERE trade_id = ?
        """, (trade.mae, trade.mfe, datetime.now().isoformat(), trade_id))
        self.conn.commit()

    def close_trade(self,
                   trade_id: str,
                   exit_price: float,
                   exit_reason: str,
                   brokerage: float = 0.0) -> Trade:
        """Close a trade and calculate final P&L"""

        trade = self.get_trade(trade_id)
        if not trade:
            raise ValueError(f"Trade {trade_id} not found")

        if trade.status == "CLOSED":
            logger.warning(f"Trade {trade_id} already closed")
            return trade

        # Update trade
        trade.exit_time = datetime.now()
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason
        trade.status = "CLOSED"

        # Calculate holding time
        trade.holding_minutes = int((trade.exit_time - trade.entry_time).total_seconds() / 60)

        # Calculate P&L
        if trade.direction == "BUY":
            trade.gross_pnl = (exit_price - trade.entry_price) * trade.quantity
        else:
            trade.gross_pnl = (trade.entry_price - exit_price) * trade.quantity

        # Apply brokerage
        trade.brokerage = brokerage
        trade.net_pnl = trade.gross_pnl - brokerage

        # Calculate P&L percentage
        capital_used = trade.entry_price * trade.quantity
        if trade.product == "I":  # Intraday with 5x margin
            capital_used = capital_used / 5
        trade.pnl_percent = (trade.net_pnl / capital_used) * 100 if capital_used > 0 else 0

        # Update in database
        self.conn.execute("""
            UPDATE trades
            SET exit_time = ?, exit_price = ?, exit_reason = ?,
                gross_pnl = ?, brokerage = ?, net_pnl = ?, pnl_percent = ?,
                holding_minutes = ?, status = ?, updated_at = ?
            WHERE trade_id = ?
        """, (
            trade.exit_time.isoformat(), trade.exit_price, trade.exit_reason,
            trade.gross_pnl, trade.brokerage, trade.net_pnl, trade.pnl_percent,
            trade.holding_minutes, trade.status, datetime.now().isoformat(),
            trade_id
        ))
        self.conn.commit()

        logger.info(f"Closed trade: {trade_id} | P&L: ₹{trade.net_pnl:.2f} ({trade.pnl_percent:.2f}%) | Reason: {exit_reason}")
        return trade

    def get_trade(self, trade_id: str) -> Optional[Trade]:
        """Get trade by ID"""
        cursor = self.conn.execute("SELECT * FROM trades WHERE trade_id = ?", (trade_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return self._row_to_trade(row)

    def get_open_trades(self) -> List[Trade]:
        """Get all open trades"""
        cursor = self.conn.execute("SELECT * FROM trades WHERE status = 'OPEN' ORDER BY entry_time DESC")
        return [self._row_to_trade(row) for row in cursor.fetchall()]

    def get_trades(self,
                   days: int = None,
                   strategy: str = None,
                   symbol: str = None,
                   outcome: str = None,
                   product: str = None,
                   start_date: date = None,
                   end_date: date = None) -> List[Trade]:
        """Get trades with filters"""

        query = "SELECT * FROM trades WHERE status = 'CLOSED'"
        params = []

        if days:
            start_date = date.today() - timedelta(days=days)
            query += " AND date(entry_time) >= ?"
            params.append(start_date.isoformat())

        if start_date and end_date:
            query += " AND date(entry_time) BETWEEN ? AND ?"
            params.extend([start_date.isoformat(), end_date.isoformat()])

        if strategy:
            query += " AND strategy = ?"
            params.append(strategy)

        if symbol:
            query += " AND symbol = ?"
            params.append(symbol)

        if outcome == 'win':
            query += " AND net_pnl > 0"
        elif outcome == 'loss':
            query += " AND net_pnl < 0"
        elif outcome == 'breakeven':
            query += " AND net_pnl = 0"

        if product:
            query += " AND product = ?"
            params.append(product)

        query += " ORDER BY entry_time DESC"

        cursor = self.conn.execute(query, params)
        return [self._row_to_trade(row) for row in cursor.fetchall()]

    def get_daily_pnl(self, target_date: date = None) -> Portfolio:
        """Calculate daily portfolio metrics"""

        if target_date is None:
            target_date = date.today()

        # Get trades for the day
        day_trades = self.get_trades(start_date=target_date, end_date=target_date)
        open_trades = self.get_open_trades()

        # Calculate metrics
        realized_pnl = sum(t.net_pnl for t in day_trades)
        unrealized_pnl = sum(self._calculate_unrealized_pnl(t) for t in open_trades)
        total_pnl = realized_pnl + unrealized_pnl

        # Intraday metrics
        intraday_trades = [t for t in day_trades if t.product == "I"]
        intraday_pnl = sum(t.net_pnl for t in intraday_trades)
        intraday_wins = len([t for t in intraday_trades if t.net_pnl > 0])
        intraday_losses = len([t for t in intraday_trades if t.net_pnl < 0])

        # Swing metrics
        swing_trades = [t for t in day_trades if t.product == "D"]
        swing_pnl = sum(t.net_pnl for t in swing_trades)
        swing_wins = len([t for t in swing_trades if t.net_pnl > 0])
        swing_losses = len([t for t in swing_trades if t.net_pnl < 0])

        # Capital calculation
        starting_capital = 1000000  # ₹10 lakh (should come from config)
        deployed_capital = sum(t.entry_price * t.quantity / (5 if t.product == "I" else 1)
                              for t in open_trades)
        available_capital = starting_capital - deployed_capital

        # Risk metrics
        portfolio_heat = sum(t.risk_amount for t in open_trades) / starting_capital * 100

        # Performance metrics
        total_trades = len(day_trades)
        win_rate = ((intraday_wins + swing_wins) / total_trades * 100) if total_trades > 0 else 0.0

        # Profit factor
        total_wins = sum(t.net_pnl for t in day_trades if t.net_pnl > 0)
        total_losses = abs(sum(t.net_pnl for t in day_trades if t.net_pnl < 0))
        profit_factor = (total_wins / total_losses) if total_losses > 0 else 0.0

        portfolio = Portfolio(
            date=target_date,
            starting_capital=starting_capital,
            available_capital=available_capital,
            deployed_capital=deployed_capital,
            realized_pnl=realized_pnl,
            unrealized_pnl=unrealized_pnl,
            total_pnl=total_pnl,
            intraday_pnl=intraday_pnl,
            intraday_trades=len(intraday_trades),
            intraday_wins=intraday_wins,
            intraday_losses=intraday_losses,
            swing_pnl=swing_pnl,
            swing_trades=len(swing_trades),
            swing_wins=swing_wins,
            swing_losses=swing_losses,
            max_drawdown=0.0,  # TODO: Calculate
            current_drawdown=0.0,  # TODO: Calculate
            portfolio_heat=portfolio_heat,
            win_rate=win_rate,
            profit_factor=profit_factor,
            sharpe_ratio=0.0  # TODO: Calculate
        )

        # Save to database
        self._save_daily_portfolio(portfolio)

        return portfolio

    def _calculate_unrealized_pnl(self, trade: Trade) -> float:
        """Calculate unrealized P&L for open trade (placeholder - needs live price)"""
        # TODO: Get current market price
        # For now, return 0
        return 0.0

    def _save_daily_portfolio(self, portfolio: Portfolio):
        """Save or update daily portfolio snapshot"""
        self.conn.execute("""
            INSERT OR REPLACE INTO daily_portfolio (
                date, starting_capital, available_capital, deployed_capital,
                realized_pnl, unrealized_pnl, total_pnl,
                intraday_pnl, intraday_trades, intraday_wins, intraday_losses,
                swing_pnl, swing_trades, swing_wins, swing_losses,
                max_drawdown, current_drawdown, portfolio_heat,
                win_rate, profit_factor, sharpe_ratio, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            portfolio.date.isoformat(),
            portfolio.starting_capital,
            portfolio.available_capital,
            portfolio.deployed_capital,
            portfolio.realized_pnl,
            portfolio.unrealized_pnl,
            portfolio.total_pnl,
            portfolio.intraday_pnl,
            portfolio.intraday_trades,
            portfolio.intraday_wins,
            portfolio.intraday_losses,
            portfolio.swing_pnl,
            portfolio.swing_trades,
            portfolio.swing_wins,
            portfolio.swing_losses,
            portfolio.max_drawdown,
            portfolio.current_drawdown,
            portfolio.portfolio_heat,
            portfolio.win_rate,
            portfolio.profit_factor,
            portfolio.sharpe_ratio,
            datetime.now().isoformat()
        ))
        self.conn.commit()

    def _row_to_trade(self, row) -> Trade:
        """Convert database row to Trade object"""
        return Trade(
            trade_id=row['trade_id'],
            symbol=row['symbol'],
            strategy=row['strategy'],
            entry_time=datetime.fromisoformat(row['entry_time']),
            entry_price=row['entry_price'],
            quantity=row['quantity'],
            product=row['product'],
            direction=row['direction'],
            stop_loss=row['stop_loss'],
            target=row['target'],
            risk_amount=row['risk_amount'],
            exit_time=datetime.fromisoformat(row['exit_time']) if row['exit_time'] else None,
            exit_price=row['exit_price'],
            exit_reason=row['exit_reason'],
            gross_pnl=row['gross_pnl'],
            brokerage=row['brokerage'],
            net_pnl=row['net_pnl'],
            pnl_percent=row['pnl_percent'],
            mae=row['mae'],
            mfe=row['mfe'],
            holding_minutes=row['holding_minutes'],
            news_score=row['news_score'],
            tech_score=row['tech_score'],
            confidence=row['confidence'],
            entry_order_id=row['entry_order_id'],
            target_order_id=row['target_order_id'],
            sl_order_id=row['sl_order_id'],
            status=row['status']
        )

    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()


# Singleton instance
_pnl_engine = None

def get_pnl_engine(db_path: str = "./data/tradego.db") -> PnLEngine:
    """Get singleton PnL engine instance"""
    global _pnl_engine
    if _pnl_engine is None:
        _pnl_engine = PnLEngine(db_path)
    return _pnl_engine


if __name__ == "__main__":
    # Test the P&L engine
    import sys
    import io

    # Set UTF-8 encoding for print() on Windows
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

    from logging_config import setup_logging
    setup_logging(__name__, log_file='./data/test_tradego.log')

    engine = get_pnl_engine("./data/test_tradego.db")

    # Create a test trade
    trade = engine.create_trade(
        symbol="NSE_EQ|RELIANCE-EQ",
        strategy="news_momentum",
        direction="BUY",
        quantity=100,
        entry_price=2500.0,
        stop_loss=2475.0,
        target=2550.0,
        product="I",
        risk_amount=2500.0,
        confidence=0.78,
        news_score=0.65,
        tech_score=0.72
    )

    print(f"\n✅ Created trade: {trade.trade_id}")
    print(f"   Entry: {trade.quantity} shares @ ₹{trade.entry_price}")
    print(f"   Risk: ₹{trade.risk_amount} | Target: ₹{trade.target} | SL: ₹{trade.stop_loss}")

    # Simulate price movement
    engine.update_position(trade.trade_id, 2530.0)  # Price goes up
    print(f"\n📈 Price moved to ₹2530")

    # Close trade at target
    closed_trade = engine.close_trade(trade.trade_id, 2550.0, "TARGET", brokerage=50.0)
    print(f"\n💰 Trade closed:")
    print(f"   Gross P&L: ₹{closed_trade.gross_pnl:.2f}")
    print(f"   Brokerage: ₹{closed_trade.brokerage:.2f}")
    print(f"   Net P&L: ₹{closed_trade.net_pnl:.2f} ({closed_trade.pnl_percent:.2f}%)")
    print(f"   MFE: ₹{closed_trade.mfe:.2f} | MAE: ₹{closed_trade.mae:.2f}")

    # Get daily P&L
    portfolio = engine.get_daily_pnl()
    print(f"\n📊 Daily Portfolio:")
    print(f"   Realized P&L: ₹{portfolio.realized_pnl:.2f}")
    print(f"   Win Rate: {portfolio.win_rate:.1f}%")
    print(f"   Profit Factor: {portfolio.profit_factor:.2f}")

    engine.close()
    print("\n✅ P&L Engine test complete!")
