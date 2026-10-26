"""
api/index.py - Vercel Serverless Function entry point.
Exposes the FastAPI application instance for Vercel's Python runtime.
"""

import sys
from pathlib import Path

# Resolve repository root and ensure it is in sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = ROOT_DIR / "dataset"

for path in [str(ROOT_DIR), str(DATASET_DIR)]:
    if path not in sys.path:
        sys.path.insert(0, path)

from backend.main import app  # noqa: E402, F401
