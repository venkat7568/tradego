"""
Web Dashboard for TradeGo - Real-time monitoring and control
"""

from flask import Flask, render_template, jsonify, request
from datetime import datetime, date
import json
import config
from pnl_engine import get_pnl_engine
from risk_manager import get_risk_manager
from upstox_integration import get_upstox_integration
from logging_config import setup_logging

# Setup logging
logger = setup_logging(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'tradego-secret-key-change-this'

# Initialize modules
pnl_engine = get_pnl_engine()
risk_manager = get_risk_manager()
upstox_integration = get_upstox_integration()


@app.route('/')
def index():
    """Main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/status')
def api_status():
    """Get system status"""
    try:
        # Trading mode
        trading_mode = config.TRADING_MODE

        # Get live balance if configured
        live_balance = None
        if trading_mode == 'LIVE' and config.FETCH_LIVE_BALANCE:
            try:
                operator = upstox_integration.get_operator()
                if operator:
                    funds = operator.get_funds()
                    if funds.get('status') == 'ok':
                        live_balance = funds.get('equity', {}).get('available_margin', 0)
            except Exception as e:
                logger.error(f"Error fetching live balance: {e}")

        return jsonify({
            'success': True,
            'data': {
                'trading_mode': trading_mode,
                'is_live': trading_mode == 'LIVE',
                'capital': live_balance if live_balance else config.TOTAL_CAPITAL,
                'capital_source': 'upstox' if live_balance else 'config',
                'max_positions': risk_manager.limits.max_open_positions,
                'max_daily_loss': f"{risk_manager.limits.max_daily_loss_percent:.1%}",
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


def run_dashboard(host='0.0.0.0', port=5000, debug=False):
    """Run the dashboard server"""
    logger.info(f"🌐 Starting TradeGo Dashboard on http://{host}:{port}")
    logger.info(f"   Mode: {config.TRADING_MODE}")
    logger.info(f"   Access the dashboard in your browser")

    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    run_dashboard(debug=True)
