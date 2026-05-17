import time
from config import settings


class TokenManager:
    """Wraps the Upstox analytics token and tracks expiry.

    For MVP1 (research-only), the analytics token is a 1-year JWT.
    Provides a unified interface for token retrieval and basic expiry warnings.
    """

    def __init__(self):
        self._token = settings.upstox_analytics_token
        self._api_key = settings.upstox_api_key

    def get_token(self) -> str:
        return self._token

    def get_headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._token}",
            "Accept": "application/json",
            "Api-Version": "v3",
        }

    def days_until_expiry(self) -> int:
        """Return approximate days until token expiry."""
        try:
            import jwt
            payload = jwt.decode(self._token, options={"verify_signature": False})
            exp = payload.get("exp", 0)
            now = time.time()
            return max(0, int((exp - now) / 86400))
        except Exception:
            return 365

    def is_near_expiry(self, threshold_days: int = 7) -> bool:
        return self.days_until_expiry() <= threshold_days


token_manager = TokenManager()
