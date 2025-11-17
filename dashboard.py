"""
Web Dashboard for TradeGo - Real-time monitoring and control
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime, date
import json
import subprocess
import psutil
import signal
from pnl_engine import get_pnl_engine
from upstox_integration import get_upstox_integration
from settings_manager import load_settings, save_settings
from logging_config import setup_logging

# Setup logging
logger = setup_logging(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tradego-secret-key-change-this'

# Initialize modules
pnl_engine = get_pnl_engine()
upstox_integration = get_upstox_integration()

# Trading system process
trading_process = None


def is_trading_system_running() -> bool:
    """Check if orchestrator is running"""
    for proc in psutil.process_iter(['name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and 'orchestrator.py' in ' '.join(cmdline):
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def start_trading_system():
    """Start the trading system"""
    global trading_process
    try:
        if is_trading_system_running():
            return {'success': False, 'error': 'Trading system already running'}

        # Start orchestrator in background
        trading_process = subprocess.Popen(
            ['python', 'orchestrator.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        logger.info(f"Trading system started with PID: {trading_process.pid}")
        return {'success': True, 'pid': trading_process.pid}

    except Exception as e:
        logger.error(f"Error starting trading system: {e}")
        return {'success': False, 'error': str(e)}


def stop_trading_system():
    """Stop the trading system"""
    global trading_process
    try:
        stopped = False

        # Try to stop the process we started
        if trading_process and trading_process.poll() is None:
            trading_process.terminate()
            trading_process.wait(timeout=5)
            stopped = True

        # Also check for any running orchestrator processes
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                cmdline = proc.info['cmdline']
                if cmdline and 'orchestrator.py' in ' '.join(cmdline):
                    proc.terminate()
                    proc.wait(timeout=5)
                    stopped = True
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.TimeoutExpired):
                pass

        if stopped:
            logger.info("Trading system stopped")
            return {'success': True}
        else:
            return {'success': False, 'error': 'No trading system process found'}

    except Exception as e:
        logger.error(f"Error stopping trading system: {e}")
        return {'success': False, 'error': str(e)}


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/settings', methods=['GET'])
def api_get_settings():
    """Get current trading settings"""
    try:
        settings = load_settings()

        # Check if trading system is running
        is_running = is_trading_system_running()

        return jsonify({
            'success': True,
            'data': {
                **settings,
                'system_running': is_running
            }
        })
    except Exception as e:
        logger.error(f"Error in api_get_settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/settings', methods=['POST'])
def api_update_settings():
    """Update trading settings"""
    try:
        new_settings = request.get_json()

        # Validate settings
        if 'mode' in new_settings and new_settings['mode'] not in ['LIVE', 'BACKTEST']:
            return jsonify({'success': False, 'error': 'Invalid mode'}), 400

        if 'live_type' in new_settings and new_settings['live_type'] not in ['PAPER', 'REAL']:
            return jsonify({'success': False, 'error': 'Invalid live_type'}), 400

        if 'capital' in new_settings:
            try:
                new_settings['capital'] = float(new_settings['capital'])
            except:
                return jsonify({'success': False, 'error': 'Invalid capital amount'}), 400

        # Save settings
        current = load_settings()
        updated = {**current, **new_settings}

        if save_settings(updated):
            logger.info(f"Settings updated: {new_settings}")
            return jsonify({'success': True, 'data': updated})
        else:
            return jsonify({'success': False, 'error': 'Failed to save settings'}), 500

    except Exception as e:
        logger.error(f"Error in api_update_settings: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/status')
def api_status():
    """Get system status"""
    try:
        settings = load_settings()

        # Get live balance if in LIVE mode with REAL money
        live_balance = None
        if settings['mode'] == 'LIVE' and settings['live_type'] == 'REAL':
            try:
                operator = upstox_integration.get_operator()
                if operator:
                    funds = operator.get_funds()
                    if funds.get('status') == 'ok':
                        live_balance = funds.get('equity', {}).get('available_margin', 0)
            except Exception as e:
                logger.error(f"Error fetching live balance: {e}")

        capital = live_balance if live_balance else settings['capital']

        return jsonify({
            'success': True,
            'data': {
                'trading_mode': settings['mode'],
                'live_type': settings['live_type'],
                'is_live': settings['mode'] == 'LIVE',
                'is_real_money': settings['mode'] == 'LIVE' and settings['live_type'] == 'REAL',
                'capital': capital,
                'capital_source': 'upstox' if live_balance else 'settings',
                'max_positions': settings['max_positions'],
                'max_daily_loss': f"{settings['max_daily_loss_percent']:.1f}%",
                'auto_trade': settings.get('auto_trade', False),
                'system_running': is_trading_system_running(),
                'timestamp': datetime.now().isoformat()
            }
        })
    except Exception as e:
        logger.error(f"Error in api_status: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/portfolio')
def api_portfolio():
    """Get portfolio metrics"""
    try:
        portfolio = pnl_engine.get_daily_pnl()

        return jsonify({
            'success': True,
            'data': {
                'date': portfolio.date.isoformat(),
                'total_pnl': portfolio.total_pnl,
                'realized_pnl': portfolio.realized_pnl,
                'unrealized_pnl': portfolio.unrealized_pnl,
                'intraday': {
                    'pnl': portfolio.intraday_pnl,
                    'trades': portfolio.intraday_trades,
                    'wins': portfolio.intraday_wins,
                    'losses': portfolio.intraday_losses
                },
                'swing': {
                    'pnl': portfolio.swing_pnl,
                    'trades': portfolio.swing_trades,
                    'wins': portfolio.swing_wins,
                    'losses': portfolio.swing_losses
                },
                'win_rate': portfolio.win_rate,
                'profit_factor': portfolio.profit_factor,
                'portfolio_heat': portfolio.portfolio_heat,
                'available_capital': portfolio.available_capital,
                'deployed_capital': portfolio.deployed_capital
            }
        })
    except Exception as e:
        logger.error(f"Error in api_portfolio: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trades/open')
def api_open_trades():
    """Get open trades"""
    try:
        trades = pnl_engine.get_open_trades()

        trades_data = []
        for trade in trades:
            trades_data.append({
                'trade_id': trade.trade_id,
                'symbol': trade.symbol,
                'strategy': trade.strategy,
                'direction': trade.direction,
                'quantity': trade.quantity,
                'entry_price': trade.entry_price,
                'entry_time': trade.entry_time.isoformat(),
                'stop_loss': trade.stop_loss,
                'target': trade.target,
                'product': trade.product,
                'risk_amount': trade.risk_amount,
                'mfe': trade.mfe,
                'mae': trade.mae,
                'confidence': trade.confidence
            })

        return jsonify({
            'success': True,
            'data': {
                'trades': trades_data,
                'count': len(trades_data)
            }
        })
    except Exception as e:
        logger.error(f"Error in api_open_trades: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/trades/closed')
def api_closed_trades():
    """Get recent closed trades"""
    try:
        days = request.args.get('days', default=7, type=int)
        trades = pnl_engine.get_trades(days=days)

        trades_data = []
        for trade in trades:
            trades_data.append({
                'trade_id': trade.trade_id,
                'symbol': trade.symbol,
                'strategy': trade.strategy,
                'direction': trade.direction,
                'quantity': trade.quantity,
                'entry_price': trade.entry_price,
                'exit_price': trade.exit_price,
                'entry_time': trade.entry_time.isoformat(),
                'exit_time': trade.exit_time.isoformat() if trade.exit_time else None,
                'exit_reason': trade.exit_reason,
                'net_pnl': trade.net_pnl,
                'pnl_percent': trade.pnl_percent,
                'product': trade.product,
                'holding_minutes': trade.holding_minutes
            })

        return jsonify({
            'success': True,
            'data': {
                'trades': trades_data,
                'count': len(trades_data)
            }
        })
    except Exception as e:
        logger.error(f"Error in api_closed_trades: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/upstox/balance')
def api_upstox_balance():
    """Get live balance from Upstox"""
    try:
        operator = upstox_integration.get_operator()
        if not operator:
            return jsonify({
                'success': False,
                'error': 'Upstox operator not available. Check token.'
            }), 400

        funds = operator.get_funds()

        if funds.get('status') == 'ok':
            return jsonify({
                'success': True,
                'data': funds.get('equity', {})
            })
        else:
            return jsonify({
                'success': False,
                'error': funds.get('error', 'Unknown error')
            }), 500

    except Exception as e:
        logger.error(f"Error in api_upstox_balance: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/upstox/positions')
def api_upstox_positions():
    """Get live positions from Upstox"""
    try:
        operator = upstox_integration.get_operator()
        if not operator:
            return jsonify({
                'success': False,
                'error': 'Upstox operator not available. Check token.'
            }), 400

        positions = operator.get_positions()

        if positions.get('status') == 'ok':
            return jsonify({
                'success': True,
                'data': {
                    'positions': positions.get('positions', []),
                    'count': positions.get('count', 0),
                    'total_pnl': positions.get('total_pnl', 0),
                    'total_value': positions.get('total_value', 0)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': positions.get('error', 'Unknown error')
            }), 500

    except Exception as e:
        logger.error(f"Error in api_upstox_positions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system/start', methods=['POST'])
def api_start_system():
    """Start the trading system"""
    try:
        result = start_trading_system()
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error in api_start_system: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/system/stop', methods=['POST'])
def api_stop_system():
    """Stop the trading system"""
    try:
        result = stop_trading_system()
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 400
    except Exception as e:
        logger.error(f"Error in api_stop_system: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """Run the dashboard server"""
    settings = load_settings()
    logger.info(f"🌐 Starting TradeGo Dashboard on http://{host}:{port}")
    logger.info(f"   Mode: {settings['mode']}")
    logger.info(f"   Access the dashboard in your browser")

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_dashboard(debug=True)
