"""
Upstox Integration - Wraps upstox_operator and upstox_technical with token_manager
This ensures all Upstox API calls use the latest valid token automatically
"""

import logging
from typing import Optional

from token_manager import get_token_manager
from upstox_operator import UpstoxOperator
from upstox_technical import UpstoxTechnicalClient
import config

logger = logging.getLogger(__name__)


class UpstoxIntegration:
    """
    Integrated Upstox client that automatically uses token from token_manager
    """

    def __init__(self):
        self.token_manager = get_token_manager(
            api_key=config.UPSTOX_API_KEY,
            api_secret=config.UPSTOX_API_SECRET,
            redirect_uri=config.UPSTOX_REDIRECT_URI
        )

        # Initialize clients (they'll get the token when needed)
        self._operator = None
        self._technical = None

        logger.info("Upstox Integration initialized")

    def _get_valid_token(self) -> Optional[str]:
        """Get valid access token"""
        if not self.token_manager:
            logger.error("Token manager not initialized")
            return None

        token = self.token_manager.get_token()

        if not token:
            logger.warning("No valid token available")
            return None

        return token

    def get_operator(self) -> Optional[UpstoxOperator]:
        """
        Get UpstoxOperator instance with current valid token
        Creates new instance if token changed
        """
        token = self._get_valid_token()

        if not token:
            return None

        # Create new operator with current token
        # (We create fresh each time to ensure latest token is used)
        operator = UpstoxOperator(
            access_token=token,
            mode="live"
        )

        logger.debug("UpstoxOperator created with fresh token")
        return operator

    def get_technical(self) -> UpstoxTechnicalClient:
        """
        Get UpstoxTechnicalClient instance
        Technical client doesn't need auth for most operations
        """
        if not self._technical:
            self._technical = UpstoxTechnicalClient()

        return self._technical

    def is_token_valid(self) -> bool:
        """Check if current token is valid"""
        if not self.token_manager:
            return False

        return self.token_manager.is_token_valid()


# Singleton instance
_upstox_integration = None


def get_upstox_integration() -> UpstoxIntegration:
    """Get singleton Upstox Integration instance"""
    global _upstox_integration

    if _upstox_integration is None:
        _upstox_integration = UpstoxIntegration()

    return _upstox_integration


if __name__ == "__main__":
    # Test the integration
    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 60)
    print("Testing Upstox Integration")
    print("=" * 60)

    integration = get_upstox_integration()

    # Check token
    print(f"\n1. Token valid: {integration.is_token_valid()}")

    # Get technical client (no auth needed)
    print("\n2. Getting technical client...")
    tech = integration.get_technical()
    print(f"   ✓ Technical client: {tech}")

    # Test symbol resolution
    print("\n3. Testing symbol resolution...")
    try:
        result = tech.resolve("RELIANCE")
        if result:
            print(f"   ✓ Resolved RELIANCE: {result.get('trading_symbol')}")
        else:
            print("   ✗ Could not resolve RELIANCE")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Get operator (needs auth)
    print("\n4. Getting operator client...")
    operator = integration.get_operator()

    if operator:
        print(f"   ✓ Operator client: {operator}")

        # Test get funds
        print("\n5. Testing get_funds()...")
        try:
            funds = operator.get_funds()
            print(f"   ✓ Funds retrieved: {funds}")
        except Exception as e:
            print(f"   ✗ Error: {e}")
    else:
        print("   ✗ Operator client not available (token invalid)")
        print("   Run: python start_tradego.py to refresh token")

    print("\n" + "=" * 60)
    print("✅ Integration test complete!")
    print("=" * 60)
