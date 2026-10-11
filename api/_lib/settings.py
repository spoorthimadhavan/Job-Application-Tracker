import base64
import hashlib
import hmac
import os

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
# SECRET_KEY encrypts the login cookie. If you don't set one, derive a stable one from the Google client secret
# (stable across serverless instances and restarts, and as secret as that value). Local runs fall back to a dev key.
SECRET_KEY = os.getenv("SECRET_KEY") or (
    hmac.new(GOOGLE_CLIENT_SECRET.encode(), b"jobtracker-session-key", hashlib.sha256).hexdigest() if GOOGLE_CLIENT_SECRET else "dev-only-change-me"
)
REDIRECT_URI = os.getenv("REDIRECT_URI", "")
SINCE = os.getenv("SINCE", "2026/05/01")
# Set COOKIE_SECURE=false only for plain-http local runs (Docker on a LAN IP, for example)
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "true").lower() != "false"
WEB_DIST = os.getenv("WEB_DIST", "")
GOOGLE_CONFIGURED = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
FERNET_KEY = base64.urlsafe_b64encode(hashlib.sha256(SECRET_KEY.encode()).digest())
# An application with no reply after this many days counts as "rejected, no response"
NO_RESPONSE_DAYS = 42
# Welcome email (Resend, https://resend.com). Leave RESEND_API_KEY empty to disable emails.
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
# Must be an address on a domain you verified in Resend (the test sender onboarding@resend.dev only delivers to your own Resend account email)
MAIL_FROM = os.getenv("MAIL_FROM", "Job Application Tracker <onboarding@resend.dev>")

# Vercel sets this to the stable production domain; sign-in is always started there because only that redirect URI is registered with Google
PRODUCTION_HOST = os.getenv("VERCEL_PROJECT_PRODUCTION_URL", "")
