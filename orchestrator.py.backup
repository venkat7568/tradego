"""
Orchestrator - Main trading loop that coordinates all modules
Runs 24/7, executes trades during market hours, monitors positions
"""

import time
import schedule
from datetime import datetime, time as dt_time
from typing import List

from logging_config import setup_logging
from pnl_engine import get_pnl_engine, Trade
from data_layer import get_data_layer
from signal_engine import get_signal_engine
from risk_manager import get_risk_manager, RiskLimits
from upstox_integration import get_upstox_integration
import config

# Setup logging with UTF-8 support
logger = setup_logging(__name__)


class Orchestrator:
    """Main trading system orchestrator"""

    def __init__(self, trading_mode: str = None):
        # Trading mode: LIVE or BACKTEST
        self.trading_mode = trading_mode or config.TRADING_MODE
        self.fetch_live_balance = config.FETCH_LIVE_BALANCE if self.trading_mode == 'LIVE' else False

        # Initialize all modules
        self.pnl_engine = get_pnl_engine()
        self.data_layer = get_data_layer()
        self.signal_engine = get_signal_engine()
        self.risk_manager = get_risk_manager()
        self.upstox_integration = get_upstox_integration()

        # Trading state
        self.trading_enabled = True
        self.last_scan_time = None
        self.live_balance = None  # Will be fetched from broker in LIVE mode

        logger.info("=" * 60)
        logger.info(f"TradeGo Orchestrator Initialized - Mode: {self.trading_mode}")
        logger.info("=" * 60)

    def fetch_live_balance(self) -> float:
        """
        Fetch available balance from Upstox broker
        Returns the available margin for trading
        """
        if self.trading_mode != 'LIVE' or not self.fetch_live_balance:
            return config.TOTAL_CAPITAL

        try:
            operator = self.upstox_integration.get_operator()
            if not operator:
                logger.warning("⚠️  Unable to get Upstox operator. Using config capital.")
                return config.TOTAL_CAPITAL

            funds = operator.get_funds()
            if funds.get('status') == 'ok':
                equity = funds.get('equity', {})
                available = equity.get('available_margin', 0)
                logger.info(f"💰 Live balance fetched: ₹{available:,.2f}")
                self.live_balance = available
                return available
            else:
                logger.warning(f"⚠️  Failed to fetch funds: {funds.get('error')}")
                return config.TOTAL_CAPITAL

        except Exception as e:
            logger.error(f"❌ Error fetching live balance: {e}")
            return config.TOTAL_CAPITAL

    def is_market_open(self) -> bool:
        """Check if market is open"""
        now = datetime.now()

        # Market hours: 9:15 AM to 3:30 PM IST (Monday-Friday)
        if now.weekday() >= 5:  # Saturday=5, Sunday=6
            return False

        market_open = dt_time(9, 15)
        market_close = dt_time(15, 30)

        current_time = now.time()

        return market_open <= current_time <= market_close

    def main_trading_loop(self):
        """Main trading loop - runs every 15 minutes"""
        try:
            logger.info("\n" + "=" * 60)
            logger.info("MAIN TRADING LOOP STARTED")
            logger.info("=" * 60)

            # Check if trading is enabled
            if not self.trading_enabled:
                logger.info("Trading is DISABLED. Skipping cycle.")
                return

            # Check if market is open
            if not self.is_market_open():
                logger.info("Market is CLOSED. Skipping cycle.")
                return

            # Get portfolio state
            portfolio = self.pnl_engine.get_daily_pnl()
            open_trades = self.pnl_engine.get_open_trades()

            logger.info(f"Portfolio: Total P&L: ₹{portfolio.total_pnl:,.2f} ({portfolio.win_rate:.1f}% win rate)")
            logger.info(f"Open Positions: {len(open_trades)}")

            # Check circuit breaker
            daily_loss_percent = portfolio.total_pnl / self.risk_manager.limits.total_capital
            if daily_loss_percent < -self.risk_manager.limits.max_daily_loss_percent:
                logger.warning(f"⚠️  CIRCUIT BREAKER TRIGGERED: {daily_loss_percent:.2%} daily loss")
                self.trading_enabled = False
                return

            # Get hybrid watchlist
            logger.info("\nFetching watchlist...")
            watchlist = self.data_layer.get_watchlist()
            logger.info(f"Watchlist: {len(watchlist)} symbols")

            # Generate signals
            logger.info("\nGenerating signals...")
            signals = self.signal_engine.generate_signals(watchlist)
            logger.info(f"Generated {len(signals)} signals")

            # Execute top signals
            executed_count = 0
            for signal in signals:
                try:
                    # Validate signal
                    if not self.signal_engine.validate_signal(signal):
                        continue

                    # Check if we already have position in this symbol
                    if any(t.symbol == signal.symbol for t in open_trades):
                        logger.info(f"  ⏭️  Skipping {signal.symbol}: Already have position")
                        continue

                    # Calculate position size
                    available_capital = self.risk_manager.get_available_capital(signal.product, portfolio)
                    position_size = self.risk_manager.calculate_position_size(signal, available_capital)

                    if not position_size:
                        logger.info(f"  ⏭️  Skipping {signal.symbol}: Position sizing failed")
                        continue

                    # Check portfolio limits
                    allowed, reason = self.risk_manager.check_portfolio_limits(
                        signal, position_size, open_trades, portfolio
                    )

                    if not allowed:
                        logger.info(f"  ⏭️  Skipping {signal.symbol}: {reason}")
                        continue

                    # Check correlation
                    allowed, reason = self.risk_manager.check_correlation(signal.symbol, open_trades)

                    if not allowed:
                        logger.info(f"  ⏭️  Skipping {signal.symbol}: {reason}")
                        continue

                    # Execute trade
                    logger.info(f"\n  🎯 EXECUTING TRADE:")
                    logger.info(f"     Symbol: {signal.symbol}")
                    logger.info(f"     Strategy: {signal.strategy}")
                    logger.info(f"     Direction: {signal.direction}")
                    logger.info(f"     Quantity: {position_size.quantity}")
                    logger.info(f"     Entry: ₹{signal.entry_price:.2f}")
                    logger.info(f"     Stop Loss: ₹{signal.stop_loss:.2f}")
                    logger.info(f"     Target: ₹{signal.target:.2f}")
                    logger.info(f"     Confidence: {signal.confidence:.1%}")
                    logger.info(f"     Risk: ₹{position_size.risk_amount:,.2f} (R:R={position_size.rr_ratio:.2f})")

                    success = self.place_trade(signal, position_size)

                    if success:
                        executed_count += 1
                        open_trades = self.pnl_engine.get_open_trades()  # Refresh list

                        # Stop if we've reached max positions
                        if len(open_trades) >= self.risk_manager.limits.max_open_positions:
                            logger.info(f"\n  ✅ Max positions reached. Stopping execution.")
                            break

                except Exception as e:
                    logger.error(f"  ❌ Error executing signal for {signal.symbol}: {e}")

            logger.info(f"\n✅ Trading cycle complete: {executed_count} trades executed")
            self.last_scan_time = datetime.now()

        except Exception as e:
            logger.error(f"❌ Error in main trading loop: {e}", exc_info=True)

    def place_trade(self, signal, position_size) -> bool:
        """
        Place trade - LIVE mode places real orders, BACKTEST mode creates paper trades
        Returns True if successful
        """
        try:
            entry_order_id = None
            target_order_id = None
            sl_order_id = None

            # LIVE MODE: Place real order through Upstox
            if self.trading_mode == 'LIVE':
                logger.info(f"  🔴 LIVE MODE: Placing real order on Upstox...")

                operator = self.upstox_integration.get_operator()
                if not operator:
                    logger.error("  ❌ Cannot place live order: Upstox operator not available")
                    return False

                # Place order with mandatory stop-loss
                result = operator.place_order(
                    symbol=signal.symbol,
                    side=signal.direction,
                    qty=position_size.quantity,
                    price=signal.entry_price if signal.entry_price else None,
                    order_type='MARKET',  # Can be made configurable
                    product=signal.product,
                    stop_loss=signal.stop_loss,
                    target=signal.target,
                    live=True,  # Execute real order
                    tag=f"{signal.strategy}"
                )

                if result.get('status') == 'success':
                    entry_order_id = result.get('entry', {}).get('order_id')
                    target_order_id = result.get('exits', {}).get('target', {}).get('order_id')
                    sl_order_id = result.get('exits', {}).get('stop_loss', {}).get('order_id')

                    logger.info(f"  ✅ Live order placed successfully!")
                    logger.info(f"     Entry Order ID: {entry_order_id}")
                    logger.info(f"     Target Order ID: {target_order_id}")
                    logger.info(f"     SL Order ID: {sl_order_id}")
                else:
                    logger.error(f"  ❌ Live order failed: {result.get('error')}")
                    return False

            else:
                # BACKTEST MODE: Paper trading
                logger.info(f"  📝 BACKTEST MODE: Creating paper trade...")

            # Create trade record in database (for both LIVE and BACKTEST)
            trade = self.pnl_engine.create_trade(
                symbol=signal.symbol,
                strategy=signal.strategy,
                direction=signal.direction,
                quantity=position_size.quantity,
                entry_price=signal.entry_price,
                stop_loss=signal.stop_loss,
                target=signal.target,
                product=signal.product,
                risk_amount=position_size.risk_amount,
                confidence=signal.confidence,
                news_score=signal.news_score,
                tech_score=signal.tech_score,
                entry_order_id=entry_order_id,
                target_order_id=target_order_id,
                sl_order_id=sl_order_id
            )

            logger.info(f"  ✅ Trade recorded: {trade.trade_id} | Mode: {self.trading_mode}")
            return True

        except Exception as e:
            logger.error(f"  ❌ Error placing trade: {e}", exc_info=True)
            return False

    def position_monitor_loop(self):
        """Monitor open positions every 30 seconds"""
        try:
            if not self.trading_enabled:
                return

            if not self.is_market_open():
                return

            open_trades = self.pnl_engine.get_open_trades()

            if not open_trades:
                return

            logger.debug(f"Monitoring {len(open_trades)} positions...")

            for trade in open_trades:
                try:
                    # Get current price (TODO: Replace with real Upstox price)
                    # For now, use a dummy price
                    # current_price = self.upstox.get_ltp(trade.symbol)

                    # Update MAE/MFE
                    # self.pnl_engine.update_position(trade.trade_id, current_price)

                    # Check if near EOD for intraday trades
                    if trade.product == 'I':
                        now = datetime.now()
                        if now.hour == 15 and now.minute >= 20:
                            logger.info(f"  📤 EOD Square-off: {trade.symbol}")
                            # TODO: Square off intraday position
                            # self.pnl_engine.close_trade(trade.trade_id, current_price, "EOD_SQUAREOFF")

                except Exception as e:
                    logger.error(f"Error monitoring {trade.trade_id}: {e}")

        except Exception as e:
            logger.error(f"Error in position monitor: {e}")

    def daily_summary(self):
        """Generate daily summary report"""
        try:
            logger.info("\n" + "=" * 60)
            logger.info("DAILY SUMMARY")
            logger.info("=" * 60)

            portfolio = self.pnl_engine.get_daily_pnl()

            logger.info(f"Total P&L: ₹{portfolio.total_pnl:,.2f}")
            logger.info(f"  Intraday: ₹{portfolio.intraday_pnl:,.2f} ({portfolio.intraday_trades} trades)")
            logger.info(f"  Swing: ₹{portfolio.swing_pnl:,.2f} ({portfolio.swing_trades} trades)")
            logger.info(f"Win Rate: {portfolio.win_rate:.1f}%")
            logger.info(f"Profit Factor: {portfolio.profit_factor:.2f}")

            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error generating daily summary: {e}")

    def run(self):
        """Start the orchestrator"""
        logger.info("\n🚀 TradeGo System Starting...")
        logger.info(f"   Mode: {'🔴 LIVE TRADING' if self.trading_mode == 'LIVE' else '📝 BACKTEST (Paper Trading)'}")

        # Fetch live balance if in LIVE mode
        if self.trading_mode == 'LIVE' and self.fetch_live_balance:
            live_capital = self.fetch_live_balance()
            logger.info(f"   Capital: ₹{live_capital:,.2f} (fetched from Upstox)")
        else:
            logger.info(f"   Capital: ₹{self.risk_manager.limits.total_capital:,.0f} (config)")

        logger.info(f"   Intraday: {self.risk_manager.limits.intraday_allocation:.0%}")
        logger.info(f"   Swing: {self.risk_manager.limits.swing_allocation:.0%}")
        logger.info(f"   Max Positions: {self.risk_manager.limits.max_open_positions}")
        logger.info(f"   Max Daily Loss: {self.risk_manager.limits.max_daily_loss_percent:.0%}")

        # Schedule jobs
        schedule.every(15).minutes.do(self.main_trading_loop)
        schedule.every(30).seconds.do(self.position_monitor_loop)
        schedule.every().day.at("15:35").do(self.daily_summary)

        logger.info("\n✅ System ready. Waiting for market hours...\n")

        # Run immediately if market is open
        if self.is_market_open():
            self.main_trading_loop()

        # Main loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\n⏹️  System stopped by user")
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(60)  # Wait 1 minute before retrying


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()
