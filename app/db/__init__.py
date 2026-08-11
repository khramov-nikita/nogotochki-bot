"""Слой доступа к SQLite."""

from __future__ import annotations

from .connection import Database, get_db, init_db

__all__ = ["Database", "get_db", "init_db"]
