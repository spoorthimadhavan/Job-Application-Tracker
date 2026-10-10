"""Vercel entry point: serves the FastAPI app from api/_lib/main.py."""

import pathlib
import sys
import traceback

# Make `_lib` importable however the platform sets the working directory
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

try:
    from _lib.main import app  # noqa: F401
except Exception:  # surface startup errors in the response instead of an opaque 500 (temporary, while debugging the deploy)
    _tb = traceback.format_exc()
    print(_tb, file=sys.stderr)

    async def app(scope, receive, send):  # minimal ASGI app
        if scope["type"] != "http":
            return
        body = ("Startup error (temporary debug page):\n\n" + _tb).encode()
        await send({"type": "http.response.start", "status": 500, "headers": [(b"content-type", b"text/plain; charset=utf-8")]})
        await send({"type": "http.response.body", "body": body})
