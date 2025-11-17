#!/usr/bin/env python3
"""
TradeGo Startup Script
Handles token refresh with email notifications before starting the main system
"""

import logging
import sys
import time
from datetime import datetime

# Import configuration
import config

# Import our modules
from token_manager import get_token_manager
from email_notifier import get_email_notifier

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main startup sequence"""

    print("\n" + "=" * 70)
    print("                    TradeGo Auto Trading System")
    print("=" * 70)
    print(f"  Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}")
    print(f"  Capital: ₹{config.TOTAL_CAPITAL:,.0f}")
    print(f"  Intraday: {config.INTRADAY_ALLOCATION:.0%} | Swing: {config.SWING_ALLOCATION:.0%}")
    print("=" * 70)
    print()

    # Step 1: Initialize Email Notifier
    logger.info("Step 1: Initializing Email Notifier...")

    if config.EMAIL_ENABLED:
        email_notifier = get_email_notifier(
            smtp_host=config.SMTP_HOST,
            smtp_port=config.SMTP_PORT,
            smtp_user=config.SMTP_USER,
            smtp_password=config.SMTP_PASSWORD,
            from_email=config.FROM_EMAIL,
            to_email=config.TO_EMAIL
        )

        if email_notifier:
            logger.info("✅ Email notifier configured")
        else:
            logger.warning("⚠️  Email notifier not configured (check config.py)")
    else:
        logger.info("⚠️  Email notifications disabled")
        email_notifier = None

    # Step 2: Initialize Token Manager
    logger.info("\nStep 2: Initializing Token Manager...")

    token_manager = get_token_manager(
        api_key=config.UPSTOX_API_KEY,
        api_secret=config.UPSTOX_API_SECRET,
        redirect_uri=config.UPSTOX_REDIRECT_URI
    )

    if not token_manager:
        logger.error("❌ Token manager initialization failed. Check Upstox API credentials in config.py")
        return

    # Step 3: Start Callback Server (always running)
    if config.ENABLE_CALLBACK_SERVER:
        logger.info("\nStep 3: Starting Callback Server...")
        token_manager.start_callback_server(port=config.CALLBACK_SERVER_PORT)
        logger.info(f"✅ Callback server running on port {config.CALLBACK_SERVER_PORT}")
        time.sleep(2)  # Give server time to start

    # Step 4: Check Token Validity
    logger.info("\nStep 4: Checking Upstox Access Token...")

    if token_manager.is_token_valid():
        logger.info("✅ Token is valid")
        logger.info(f"   Expires: {token_manager.token_expiry}")
    else:
        logger.warning("⚠️  Token expired or not found")
        logger.info("\nInitiating token refresh process...")

        # Generate authorization URL
        auth_url = token_manager.get_authorization_url()

        logger.info(f"\n📧 Authorization URL generated:")
        logger.info(f"   {auth_url}")

        # Send email if configured
        if email_notifier:
            logger.info("\n📧 Sending token refresh email...")

            success = email_notifier.send_token_refresh_link(
                auth_url=auth_url,
                callback_url=f"http://{config.UPSTOX_REDIRECT_URI.split('/')[2]}/callback"
            )

            if success:
                logger.info(f"✅ Email sent to: {config.TO_EMAIL}")
                logger.info("\n⏳ Please check your email and click the 'Authorize TradeGo' button")
            else:
                logger.error("❌ Failed to send email")
                logger.info("\n⏳ Please open the authorization URL manually:")
                logger.info(f"   {auth_url}")
        else:
            logger.info("\n⏳ Email not configured. Please open this URL in your browser:")
            logger.info(f"   {auth_url}")

        # Wait for authorization
        logger.info(f"\n⏳ Waiting for authorization (timeout: {config.AUTHORIZATION_TIMEOUT}s)...")
        logger.info("   After clicking the email link:")
        logger.info("   1. Login to Upstox")
        logger.info("   2. Enter your PIN")
        logger.info("   3. You'll be redirected back automatically")

        success = token_manager.wait_for_authorization(timeout=config.AUTHORIZATION_TIMEOUT)

        if not success:
            logger.error("\n❌ Authorization timeout!")
            logger.error("   Please try again or check:")
            logger.error("   1. Email was sent and link was clicked")
            logger.error("   2. Callback server is accessible")
            logger.error("   3. Redirect URI matches Upstox app settings")
            return

        logger.info("\n✅ Authorization successful!")

    # Step 5: Start Main Trading System
    logger.info("\n" + "=" * 70)
    logger.info("🚀 Starting Main Trading System...")
    logger.info("=" * 70)

    try:
        # Import and run orchestrator
        from orchestrator import Orchestrator

        orchestrator = Orchestrator()
        orchestrator.run()

    except KeyboardInterrupt:
        logger.info("\n\n⏹️  System stopped by user (Ctrl+C)")
    except Exception as e:
        logger.error(f"\n\n❌ Fatal error: {e}", exc_info=True)


if __name__ == "__main__":
    main()
