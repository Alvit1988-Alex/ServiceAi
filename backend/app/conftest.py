"""Pytest configuration for application tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT.parent))

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/db")
os.environ.setdefault("JWT_SECRET_KEY", "test" * 8)
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "refresh" * 5)
os.environ.setdefault("CHANNEL_CONFIG_SECRET_KEY", "secret")
