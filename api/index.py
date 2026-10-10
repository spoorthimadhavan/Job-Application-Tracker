"""Vercel entry point: serves the FastAPI app from api/_lib/main.py."""

import pathlib
import sys

# Vercel does not put api/ on the import path, so add it before importing _lib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from _lib.main import app  # noqa: E402,F401  (Vercel looks for a top-level `app`)
