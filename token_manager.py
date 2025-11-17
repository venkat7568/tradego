"""
Token Manager - Handle Upstox token refresh with OAuth2 flow
Runs a callback server to catch authorization code and exchange for access token
"""

import os
import json
import logging
import requests
import threading
from datetime import datetime, timedelta
from typing import Optional, Dict
from flask import Flask, request, jsonify
import time

logger = logging.getLogger(__name__)


class TokenManager:
    """Manage Upstox API token refresh with OAuth2 flow"""

    TOKEN_FILE = "./data/upstox_token.json"

    def __init__(self, api_key: str, api_secret: str, redirect_uri: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.redirect_uri = redirect_uri

        self.access_token = None
        self.token_expiry = None
        self.authorization_code = None
        self.callback_server = None
        self.server_thread = None

        # Load existing token
        self._load_token()

        logger.info("Token Manager initialized")

    def _load_token(self):
        """Load token from file"""
        try:
            if os.path.exists(self.TOKEN_FILE):
                with open(self.TOKEN_FILE, 'r') as f:
                    data = json.load(f)

                self.access_token = data.get('access_token')
                expiry_str = data.get('expiry')

                if expiry_str:
                    self.token_expiry = datetime.fromisoformat(expiry_str)

                logger.info(f"Token loaded from file (expires: {self.token_expiry})")
        except Exception as e:
            logger.error(f"Error loading token: {e}")

    def _save_token(self):
        """Save token to file"""
        try:
            os.makedirs(os.path.dirname(self.TOKEN_FILE), exist_ok=True)

            data = {
                'access_token': self.access_token,
                'expiry': self.token_expiry.isoformat() if self.token_expiry else None,
                'updated_at': datetime.now().isoformat()
            }

            with open(self.TOKEN_FILE, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info("Token saved to file")
        except Exception as e:
            logger.error(f"Error saving token: {e}")

    def is_token_valid(self) -> bool:
        """Check if current token is valid"""
        if not self.access_token:
            return False

        if not self.token_expiry:
            return False

        # Token valid if expires more than 1 hour from now
        return datetime.now() < (self.token_expiry - timedelta(hours=1))

    def get_authorization_url(self) -> str:
        """Get Upstox authorization URL"""
        base_url = "https://api.upstox.com/v2/login/authorization/dialog"

        params = {
            'client_id': self.api_key,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code'
        }

        # Build URL
        auth_url = f"{base_url}?client_id={params['client_id']}&redirect_uri={params['redirect_uri']}&response_type={params['response_type']}"

        logger.info(f"Generated authorization URL: {auth_url}")
        return auth_url

    def exchange_code_for_token(self, authorization_code: str) -> bool:
        """Exchange authorization code for access token"""
        try:
            url = "https://api.upstox.com/v2/login/authorization/token"

            headers = {
                'accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded'
            }

            data = {
                'code': authorization_code,
                'client_id': self.api_key,
                'client_secret': self.api_secret,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code'
            }

            logger.info("Exchanging authorization code for access token...")
            response = requests.post(url, headers=headers, data=data)

            if response.status_code == 200:
                result = response.json()

                self.access_token = result.get('access_token')

                # Upstox tokens typically expire in 24 hours
                expires_in = result.get('expires_in', 86400)  # Default 24 hours
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)

                # Save token
                self._save_token()

                logger.info(f"✅ Access token obtained! Expires: {self.token_expiry}")
                return True
            else:
                logger.error(f"Token exchange failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error exchanging code for token: {e}")
            return False

    def start_callback_server(self, port: int = 8000):
        """Start Flask callback server to receive authorization code"""

        app = Flask(__name__)
        app.logger.disabled = True  # Disable Flask logs

        @app.route('/callback', methods=['GET'])
        def callback():
            """Callback endpoint for Upstox redirect"""
            code = request.args.get('code')
            error = request.args.get('error')

            if error:
                logger.error(f"Authorization error: {error}")
                return f"""
                <html>
                <body style="font-family: Arial; padding: 50px; text-align: center;">
                    <h1 style="color: red;">❌ Authorization Failed</h1>
                    <p>Error: {error}</p>
                    <p>Please try again or check your credentials.</p>
                </body>
                </html>
                """, 400

            if code:
                logger.info(f"Received authorization code: {code[:20]}...")

                # Exchange code for token
                success = self.exchange_code_for_token(code)

                if success:
                    # Schedule server shutdown
                    threading.Thread(target=self._shutdown_server, daemon=True).start()

                    return """
                    <html>
                    <body style="font-family: Arial; padding: 50px; text-align: center;">
                        <h1 style="color: green;">✅ Authorization Successful!</h1>
                        <p>TradeGo has been authorized.</p>
                        <p>Trading will resume automatically.</p>
                        <p style="color: #666; margin-top: 40px;">You can close this window.</p>
                    </body>
                    </html>
                    """
                else:
                    return """
                    <html>
                    <body style="font-family: Arial; padding: 50px; text-align: center;">
                        <h1 style="color: red;">❌ Token Exchange Failed</h1>
                        <p>Could not obtain access token.</p>
                        <p>Please check logs and try again.</p>
                    </body>
                    </html>
                    """, 500

            return "No authorization code received", 400

        @app.route('/status', methods=['GET'])
        def status():
            """Check token status"""
            return jsonify({
                'token_valid': self.is_token_valid(),
                'token_expiry': self.token_expiry.isoformat() if self.token_expiry else None
            })

        # Run server in a separate thread
        def run_server():
            logger.info(f"🌐 Starting callback server on port {port}...")
            app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

        logger.info(f"Callback server started: http://0.0.0.0:{port}/callback")

    def _shutdown_server(self):
        """Shutdown callback server after successful authorization"""
        time.sleep(2)  # Wait 2 seconds
        logger.info("Token obtained. Callback server will remain running for future refreshes.")
        # Note: We keep server running so it's always ready for next refresh

    def get_token(self) -> Optional[str]:
        """Get current valid access token"""
        if self.is_token_valid():
            return self.access_token
        else:
            logger.warning("Token is invalid or expired")
            return None

    def wait_for_authorization(self, timeout: int = 300) -> bool:
        """
        Wait for user to complete authorization
        Returns True if token obtained within timeout
        """
        logger.info(f"Waiting for authorization (timeout: {timeout}s)...")

        start_time = time.time()

        while time.time() - start_time < timeout:
            if self.is_token_valid():
                logger.info("✅ Authorization complete!")
                return True

            time.sleep(5)  # Check every 5 seconds

        logger.warning("⚠️ Authorization timeout")
        return False


# Singleton instance
_token_manager = None

def get_token_manager(api_key: str = None, api_secret: str = None, redirect_uri: str = None) -> Optional[TokenManager]:
    """Get singleton Token Manager instance"""
    global _token_manager

    if _token_manager is None:
        if all([api_key, api_secret, redirect_uri]):
            _token_manager = TokenManager(api_key, api_secret, redirect_uri)
        else:
            logger.warning("Token manager not configured")
            return None

    return _token_manager


if __name__ == "__main__":
    # Test token manager
    logging.basicConfig(level=logging.INFO)

    print("\n" + "=" * 60)
    print("TradeGo Token Manager Test")
    print("=" * 60)

    # Example configuration (replace with your actual values)
    API_KEY = "your-upstox-api-key"
    API_SECRET = "your-upstox-api-secret"
    REDIRECT_URI = "http://localhost:8000/callback"  # Or your VPS IP

    tm = TokenManager(API_KEY, API_SECRET, REDIRECT_URI)

    # Check if token is valid
    print(f"\n1. Token valid: {tm.is_token_valid()}")

    if not tm.is_token_valid():
        print("\n2. Starting callback server...")
        tm.start_callback_server(port=8000)

        print("\n3. Authorization URL:")
        auth_url = tm.get_authorization_url()
        print(f"   {auth_url}")

        print("\n4. Please:")
        print("   - Open the URL above in your browser")
        print("   - Login to Upstox")
        print("   - Enter your PIN")
        print("   - You'll be redirected to callback server")

        print("\n5. Waiting for authorization...")
        success = tm.wait_for_authorization(timeout=300)

        if success:
            print("\n✅ Token obtained successfully!")
            print(f"   Access Token: {tm.access_token[:30]}...")
            print(f"   Expires: {tm.token_expiry}")
        else:
            print("\n❌ Authorization failed or timeout")
    else:
        print("\n✅ Token is already valid!")
        print(f"   Access Token: {tm.access_token[:30] if tm.access_token else 'None'}...")
        print(f"   Expires: {tm.token_expiry}")

    print("\n" + "=" * 60)
