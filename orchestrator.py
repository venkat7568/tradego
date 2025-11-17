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
from settings_manager import load_settings

# Setup logging with UTF-8 support
logger = setup_logging(__name__)


class Orchestrator:
    """Main trading system orchestrator"""

    def __init__(self):
        # Load settings from dashboard UI (settings_manager)
        self.settings = load_settings()
        self.trading_mode = self.settings['mode']
        self.live_type = self.settings.get('live_type', 'PAPER')

        # Initialize all modules
        self.pnl_engine = get_pnl_engine()
        self.data_layer = get_data_layer()
        self.signal_engine = get_signal_engine()
        self.risk_manager = get_risk_manager()
        self.upstox_integration = get_upstox_integration()

        # Trading state
        self.trading_enabled = True
        self.last_scan_time = None
        self.live_balance = None

        logger.info("=" * 60)
        logger.info(f"TradeGo Orchestrator Initialized")
        logger.info(f"Mode: {self.trading_mode} ({self.live_type if self.trading_mode == 'LIVE' else 'Paper Trading'})")
        logger.info(f"Settings: {self.settings}")
        logger.info("=" * 60)

    def get_capital(self) -> float:
        """Get trading capital based on mode"""
        # LIVE + REAL = Fetch from Upstox
        if self.trading_mode == 'LIVE' and self.live_type == 'REAL':
            try:
                operator = self.upstox_integration.get_operator()
                if operator:
                    funds = operator.get_funds()
                    if funds.get('status') == 'ok':
                        available = funds.get('equity', {}).get('available_margin', 0)
                        logger.info(f"💰 Live balance from Upstox: ₹{available:,.2f}")
                        self.live_balance = available
                        return available
                logger.warning("⚠️  Failed to fetch Upstox balance, using settings capital")
            except Exception as e:
                logger.error(f"❌ Error fetching live balance: {e}")

        # BACKTEST or LIVE+PAPER = Use settings capital
        return self.settings.get('capital', 1000000)

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

            # Check if market is open - ONLY for LIVE modes
            if self.trading_mode == 'LIVE' and not self.is_market_open():
                logger.info("Market is CLOSED. Skipping cycle (LIVE mode).")
                return

            # BACKTEST mode - runs anytime, doesn't check market hours
            if self.trading_mode == 'BACKTEST':
                logger.info("Running in BACKTEST mode - processing historical data")


            # Get portfolio state
            portfolio = self.pnl_engine.get_daily_pnl()
            open_trades = self.pnl_engine.get_open_trades()

            logger.info(f"Portfolio: Total P&L: ₹{portfolio.total_pnl:,.2f} ({portfolio.win_rate:.1f}% win rate)")
            logger.info(f"Open Positions: {len(open_trades)}")

            # Check circuit breaker
            capital = self.get_capital()
            daily_loss_percent = portfolio.total_pnl / capital
            max_loss_pct = self.settings.get('max_daily_loss_percent', 2.0) / 100
            if daily_loss_percent < -max_loss_pct:
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
                        max_pos = self.settings.get('max_positions', 5)
                        if len(open_trades) >= max_pos:
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

            # LIVE + REAL: Place real order through Upstox
            if self.trading_mode == 'LIVE' and self.live_type == 'REAL':
                logger.info(f"  🔴 LIVE MODE (REAL MONEY): Placing real order on Upstox...")

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
                    order_type='MARKET',
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
                # BACKTEST or LIVE+PAPER: Paper trading
                mode_str = "LIVE (PAPER)" if self.trading_mode == 'LIVE' else "BACKTEST"
                logger.info(f"  📝 {mode_str} MODE: Creating paper trade...")

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

            # Only check market hours for LIVE modes
            if self.trading_mode == 'LIVE' and not self.is_market_open():
                return

            open_trades = self.pnl_engine.get_open_trades()

            if not open_trades:
                return

            logger.debug(f"Monitoring {len(open_trades)} positions...")

            for trade in open_trades:
                try:
                    # Get current live price
                    operator = self.upstox_integration.get_operator()
                    current_price = None

                    if operator:
                        current_price = operator.get_ltp(symbol=trade.symbol)

                    if not current_price:
                        logger.debug(f"Could not get live price for {trade.symbol}, skipping...")
                        continue

                    # Update MAE/MFE
                    self.pnl_engine.update_position(trade.trade_id, current_price)

                    # Check stop-loss and target for LIVE+REAL mode
                    if self.trading_mode == 'LIVE' and self.live_type == 'REAL':
                        if trade.direction == 'BUY':
                            # Long position
                            if current_price <= trade.stop_loss:
                                logger.warning(f"⚠️ STOP-LOSS HIT: {trade.symbol} @ {current_price} (SL: {trade.stop_loss})")
                                # Square off position
                                square_result = operator.square_off(symbol=trade.symbol, live=True)
                                if square_result.get('status') == 'success':
                                    self.pnl_engine.close_trade(trade.trade_id, current_price, "STOP_LOSS")
                                    logger.info(f"  ✅ Position squared off at stop-loss")

                            elif current_price >= trade.target:
                                logger.info(f"✅ TARGET HIT: {trade.symbol} @ {current_price} (TGT: {trade.target})")
                                # Square off position
                                square_result = operator.square_off(symbol=trade.symbol, live=True)
                                if square_result.get('status') == 'success':
                                    self.pnl_engine.close_trade(trade.trade_id, current_price, "TARGET")
                                    logger.info(f"  ✅ Position squared off at target")

                        else:  # SHORT position
                            # Short position
                            if current_price >= trade.stop_loss:
                                logger.warning(f"⚠️ STOP-LOSS HIT: {trade.symbol} @ {current_price} (SL: {trade.stop_loss})")
                                square_result = operator.square_off(symbol=trade.symbol, live=True)
                                if square_result.get('status') == 'success':
                                    self.pnl_engine.close_trade(trade.trade_id, current_price, "STOP_LOSS")
                                    logger.info(f"  ✅ Position squared off at stop-loss")

                            elif current_price <= trade.target:
                                logger.info(f"✅ TARGET HIT: {trade.symbol} @ {current_price} (TGT: {trade.target})")
                                square_result = operator.square_off(symbol=trade.symbol, live=True)
                                if square_result.get('status') == 'success':
                                    self.pnl_engine.close_trade(trade.trade_id, current_price, "TARGET")
                                    logger.info(f"  ✅ Position squared off at target")

                    # Check if near EOD for intraday trades
                    if trade.product == 'I':
                        now = datetime.now()
                        if now.hour == 15 and now.minute >= 20:
                            logger.info(f"  📤 EOD Square-off: {trade.symbol}")
                            if self.trading_mode == 'LIVE' and self.live_type == 'REAL' and operator:
                                square_result = operator.square_off(symbol=trade.symbol, live=True)
                                if square_result.get('status') == 'success':
                                    self.pnl_engine.close_trade(trade.trade_id, current_price, "EOD_SQUAREOFF")
                                    logger.info(f"  ✅ Intraday position squared off before market close")
                            else:
                                # Paper trading mode
                                self.pnl_engine.close_trade(trade.trade_id, current_price, "EOD_SQUAREOFF")
                                logger.info(f"  ✅ Intraday position closed (paper)")

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

        # Display mode
        if self.trading_mode == 'LIVE' and self.live_type == 'REAL':
            logger.info(f"   Mode: 🔴 LIVE (REAL MONEY)")
        elif self.trading_mode == 'LIVE' and self.live_type == 'PAPER':
            logger.info(f"   Mode: 📝 LIVE (PAPER TRADING)")
        else:
            logger.info(f"   Mode: 📝 BACKTEST")
            if self.settings.get('backtest_from') and self.settings.get('backtest_to'):
                logger.info(f"   Date Range: {self.settings['backtest_from']} to {self.settings['backtest_to']}")

        # Display capital
        capital = self.get_capital()
        capital_source = "Upstox" if self.live_balance else "Settings"
        logger.info(f"   Capital: ₹{capital:,.2f} ({capital_source})")

        # Display settings
        logger.info(f"   Intraday: {self.settings.get('intraday_allocation', 0.7):.0%}")
        logger.info(f"   Swing: {self.settings.get('swing_allocation', 0.3):.0%}")
        logger.info(f"   Max Positions: {self.settings.get('max_positions', 5)}")
        logger.info(f"   Max Daily Loss: {self.settings.get('max_daily_loss_percent', 2)}%")

        # Schedule jobs
        schedule.every(15).minutes.do(self.main_trading_loop)
        schedule.every(30).seconds.do(self.position_monitor_loop)
        schedule.every().day.at("15:35").do(self.daily_summary)

        # Different startup message based on mode
        if self.trading_mode == 'BACKTEST':
            logger.info("\n✅ BACKTEST mode - Running immediately with historical data!\n")
            # Run immediately for backtest
            self.main_trading_loop()
        else:
            logger.info("\n✅ LIVE mode - Waiting for market hours (9:15 AM - 3:30 PM IST)...\n")
            # Run immediately if market is open
            if self.is_market_open():
                self.main_trading_loop()

        # Main loop
        while True:
            try:
                schedule.run_pending()
                time.sleep(1)
            except KeyboardInterrupt:
                logger.info("\n⏹️  System shutdown requested by user")
                self._safe_shutdown()
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}", exc_info=True)
                time.sleep(60)  # Wait 1 minute before retrying

    def _safe_shutdown(self):
        """
        Safely shutdown the system:
        - Cancel pending orders
        - Optionally square off positions (for INTRADAY only)
        - Save final state
        """
        logger.info("\n" + "=" * 60)
        logger.info("INITIATING SAFE SHUTDOWN")
        logger.info("=" * 60)

        try:
            # Get open trades
            open_trades = self.pnl_engine.get_open_trades()

            if open_trades:
                logger.info(f"\n⚠️  {len(open_trades)} open positions found")

                for trade in open_trades:
                    logger.info(f"  • {trade.symbol} ({trade.direction}) - {trade.product}")

                    # Auto square-off INTRADAY positions on shutdown
                    if trade.product == 'I' and self.trading_mode == 'LIVE' and self.live_type == 'REAL':
                        logger.warning(f"  ⚠️ Auto-squaring off INTRADAY position: {trade.symbol}")
                        operator = self.upstox_integration.get_operator()
                        if operator:
                            square_result = operator.square_off(symbol=trade.symbol, live=True)
                            if square_result.get('status') == 'success':
                                # Get final price
                                final_price = operator.get_ltp(symbol=trade.symbol) or trade.entry_price
                                self.pnl_engine.close_trade(trade.trade_id, final_price, "SHUTDOWN_SQUAREOFF")
                                logger.info(f"    ✅ Position squared off")
                            else:
                                logger.error(f"    ❌ Failed to square off: {square_result.get('error')}")
                    elif trade.product == 'D':
                        logger.info(f"  ℹ️  DELIVERY position {trade.symbol} - keeping open (will carry forward)")

            # Generate final summary
            self.daily_summary()

            logger.info("\n✅ Shutdown complete")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error during safe shutdown: {e}", exc_info=True)


if __name__ == "__main__":
    orchestrator = Orchestrator()
    orchestrator.run()
