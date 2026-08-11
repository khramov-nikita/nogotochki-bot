"""SQL-схема базы данных бота."""

from __future__ import annotations

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    full_name TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS dialog_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_dialog_user_created
    ON dialog_messages(user_id, created_at);

CREATE TABLE IF NOT EXISTS cart_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    service_key TEXT NOT NULL,
    title TEXT NOT NULL,
    price_kopecks INTEGER NOT NULL CHECK (price_kopecks >= 0),
    qty INTEGER NOT NULL DEFAULT 1 CHECK (qty > 0),
    UNIQUE(user_id, service_key)
);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (
        status IN ('pending', 'awaiting_payment', 'paid', 'cancelled')
    ),
    total_kopecks INTEGER NOT NULL CHECK (total_kopecks >= 0),
    yookassa_payment_id TEXT,
    confirmation_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_user_status
    ON orders(user_id, status);

CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    service_key TEXT NOT NULL,
    title TEXT NOT NULL,
    price_kopecks INTEGER NOT NULL CHECK (price_kopecks >= 0),
    qty INTEGER NOT NULL DEFAULT 1 CHECK (qty > 0)
);
"""
