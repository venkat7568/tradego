"""
Email Notifier - Send alerts and token refresh links via SMTP
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Send email notifications via SMTP"""

    def __init__(self, smtp_host: str, smtp_port: int, smtp_user: str, smtp_password: str, from_email: str, to_email: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email
        self.to_email = to_email

        logger.info(f"Email Notifier initialized: {from_email} → {to_email}")

    def send_email(self, subject: str, body: str, is_html: bool = False) -> bool:
        """Send email"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = self.to_email
            msg['Subject'] = subject

            # Add body
            if is_html:
                msg.attach(MIMEText(body, 'html'))
            else:
                msg.attach(MIMEText(body, 'plain'))

            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)

            logger.info(f"Email sent: {subject}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def send_token_refresh_link(self, auth_url: str, callback_url: str) -> bool:
        """Send token refresh email with authorization link"""
        subject = "🔑 TradeGo - Upstox Token Refresh Required"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #2196F3;">TradeGo Token Refresh</h2>

            <p>Your Upstox access token has expired.</p>

            <p><strong>Action Required:</strong> Click the button below to authorize TradeGo.</p>

            <div style="margin: 30px 0;">
                <a href="{auth_url}"
                   style="background-color: #4CAF50;
                          color: white;
                          padding: 15px 32px;
                          text-align: center;
                          text-decoration: none;
                          display: inline-block;
                          font-size: 16px;
                          border-radius: 4px;">
                    🔓 Authorize TradeGo
                </a>
            </div>

            <p><strong>What will happen:</strong></p>
            <ol>
                <li>You'll be redirected to Upstox login page</li>
                <li>Enter your Upstox credentials and PIN</li>
                <li>Upstox will redirect back to TradeGo</li>
                <li>Trading will resume automatically</li>
            </ol>

            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                <strong>Note:</strong> The trading system is paused until authorization is complete.<br>
                After authorization, trading will resume automatically during market hours.
            </p>

            <p style="color: #666; font-size: 12px;">
                Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}<br>
                Callback URL: {callback_url}
            </p>
        </body>
        </html>
        """

        return self.send_email(subject, body, is_html=True)

    def send_daily_report(self, portfolio_data: dict) -> bool:
        """Send daily P&L report"""
        subject = f"📊 TradeGo Daily Report - {datetime.now().strftime('%Y-%m-%d')}"

        # Extract data
        total_pnl = portfolio_data.get('total_pnl', 0)
        intraday_pnl = portfolio_data.get('intraday_pnl', 0)
        swing_pnl = portfolio_data.get('swing_pnl', 0)
        win_rate = portfolio_data.get('win_rate', 0)
        trades = portfolio_data.get('total_trades', 0)

        pnl_color = "#4CAF50" if total_pnl >= 0 else "#F44336"
        pnl_emoji = "📈" if total_pnl >= 0 else "📉"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #2196F3;">TradeGo Daily Report</h2>

            <div style="background-color: #f5f5f5; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="margin: 0; color: {pnl_color};">
                    {pnl_emoji} Total P&L: ₹{total_pnl:,.2f}
                </h3>
            </div>

            <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                <tr style="background-color: #f5f5f5;">
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Metric</strong></td>
                    <td style="padding: 10px; border: 1px solid #ddd;"><strong>Value</strong></td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Intraday P&L</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">₹{intraday_pnl:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Swing P&L</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">₹{swing_pnl:,.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Total Trades</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{trades}</td>
                </tr>
                <tr>
                    <td style="padding: 10px; border: 1px solid #ddd;">Win Rate</td>
                    <td style="padding: 10px; border: 1px solid #ddd;">{win_rate:.1f}%</td>
                </tr>
            </table>

            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                Date: {datetime.now().strftime('%Y-%m-%d')}<br>
                Time: {datetime.now().strftime('%H:%M:%S IST')}
            </p>
        </body>
        </html>
        """

        return self.send_email(subject, body, is_html=True)

    def send_alert(self, alert_type: str, message: str) -> bool:
        """Send alert (circuit breaker, error, etc)"""
        emoji_map = {
            'circuit_breaker': '⚠️',
            'error': '❌',
            'warning': '⚡',
            'success': '✅'
        }

        emoji = emoji_map.get(alert_type, '📢')
        subject = f"{emoji} TradeGo Alert: {alert_type.replace('_', ' ').title()}"

        body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #F44336;">{emoji} TradeGo Alert</h2>

            <div style="background-color: #fff3cd; padding: 20px; border-radius: 8px; border-left: 4px solid #ff9800;">
                <p style="margin: 0; font-size: 16px;">
                    <strong>{alert_type.replace('_', ' ').title()}</strong>
                </p>
                <p style="margin: 10px 0 0 0;">
                    {message}
                </p>
            </div>

            <p style="color: #666; font-size: 12px; margin-top: 30px;">
                Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}
            </p>
        </body>
        </html>
        """

        return self.send_email(subject, body, is_html=True)


# Singleton instance
_email_notifier = None

def get_email_notifier(smtp_host: str = None, smtp_port: int = None,
                       smtp_user: str = None, smtp_password: str = None,
                       from_email: str = None, to_email: str = None) -> Optional[EmailNotifier]:
    """Get singleton Email Notifier instance"""
    global _email_notifier

    if _email_notifier is None:
        if all([smtp_host, smtp_port, smtp_user, smtp_password, from_email, to_email]):
            _email_notifier = EmailNotifier(smtp_host, smtp_port, smtp_user, smtp_password, from_email, to_email)
        else:
            logger.warning("Email notifier not configured")
            return None

    return _email_notifier


if __name__ == "__main__":
    # Test email notifier
    logging.basicConfig(level=logging.INFO)

    # Example configuration (replace with your SMTP settings)
    notifier = EmailNotifier(
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        smtp_user="your-email@gmail.com",
        smtp_password="your-app-password",  # Use app password, not regular password
        from_email="your-email@gmail.com",
        to_email="your-email@gmail.com"
    )

    # Test 1: Send token refresh link
    print("\nTest 1: Token Refresh Email")
    auth_url = "https://api.upstox.com/v2/login/authorization/dialog?client_id=xxx&redirect_uri=xxx"
    callback_url = "http://your-vps-ip:8000/callback"
    success = notifier.send_token_refresh_link(auth_url, callback_url)
    print(f"  Result: {'✓ Sent' if success else '✗ Failed'}")

    # Test 2: Send daily report
    print("\nTest 2: Daily Report Email")
    portfolio_data = {
        'total_pnl': 12450.50,
        'intraday_pnl': 11600.00,
        'swing_pnl': 850.50,
        'win_rate': 75.0,
        'total_trades': 8
    }
    success = notifier.send_daily_report(portfolio_data)
    print(f"  Result: {'✓ Sent' if success else '✗ Failed'}")

    # Test 3: Send alert
    print("\nTest 3: Alert Email")
    success = notifier.send_alert('circuit_breaker', 'Daily loss limit of 2% reached. Trading paused.')
    print(f"  Result: {'✓ Sent' if success else '✗ Failed'}")

    print("\n✅ Email notifier test complete!")
