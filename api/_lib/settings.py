import base64
import hashlib
import os

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-change-me")
REDIRECT_URI = os.getenv("REDIRECT_URI", "")
SINCE = os.getenv("SINCE", "2026/05/01")
# Set COOKIE_SECURE=false only for plain-http local runs (Docker on a LAN IP, for example)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() != "false"
WEB_DIST = os.getenv("WEB_DIST", "")
GOOGLE_CONFIGURED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest())
# An application with no reply after this many days counts as "rejected, no response"
NO_RESPONSE_DAYS = 42
