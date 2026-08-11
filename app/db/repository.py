"""Репозитории: пользователи, диалог, корзина, заказы."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from app.db.connection import Database

HISTORY_LIMIT = 20


@dataclass(frozen=True)
class CartItem:
    id: int
    service_key: str
    title: str
    price_kopecks: int
    qty: int

    @property
    def line_total(self) -> int:
        return self.price_kopecks * self.qty


@dataclass(frozen=True)
class OrderItem:
    service_key: str
    title: str
    price_kopecks: int
    qty: int


@dataclass(frozen=True)
class Order:
    id: int
    user_id: int
    status: str
    total_kopecks: int
    yookassa_payment_id: str | None
    confirmation_url: str | None
    items: tuple[OrderItem, ...] = ()


class UserRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def upsert(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
    ) -> int:
        await self._db.execute(
            """
            INSERT INTO users (telegram_id, username, full_name)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                full_name = excluded.full_name,
                updated_at = datetime('now')
            """,
            (telegram_id, username, full_name),
        )
        row = await self._db.fetchone(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        assert row is not None
        return int(row["id"])

    async def get_id_by_telegram(self, telegram_id: int) -> int | None:
        row = await self._db.fetchone(
            "SELECT id FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        return int(row["id"]) if row else None


class DialogRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def add_message(self, user_id: int, role: str, content: str) -> None:
        await self._db.execute(
            """
            INSERT INTO dialog_messages (user_id, role, content)
            VALUES (?, ?, ?)
            """,
            (user_id, role, content),
        )
        # Храним только последние HISTORY_LIMIT сообщений на пользователя
        await self._db.execute(
            """
            DELETE FROM dialog_messages
            WHERE user_id = ?
              AND id NOT IN (
                  SELECT id FROM dialog_messages
                  WHERE user_id = ?
                  ORDER BY id DESC
                  LIMIT ?
              )
            """,
            (user_id, user_id, HISTORY_LIMIT),
        )

    async def get_history(
        self, user_id: int, limit: int = HISTORY_LIMIT
    ) -> list[dict[str, str]]:
        rows = await self._db.fetchall(
            """
            SELECT role, content FROM (
                SELECT id, role, content
                FROM dialog_messages
                WHERE user_id = ?
                ORDER BY id DESC
                LIMIT ?
            )
            ORDER BY id ASC
            """,
            (user_id, limit),
        )
        return [{"role": str(r["role"]), "content": str(r["content"])} for r in rows]


class CartRepository:
    def __init__(self, db: Database) -> None:
        self._db = db

    async def list_items(self, user_id: int) -> list[CartItem]:
        rows = await self._db.fetchall(
            """
            SELECT id, service_key, title, price_kopecks, qty
            FROM cart_items
            WHERE user_id = ?
            ORDER BY id ASC
            """,
            (user_id,),
        )
        return [
            CartItem(
                id=int(r["id"]),
                service_key=str(r["service_key"]),
                title=str(r["title"]),
                price_kopecks=int(r["price_kopecks"]),
                qty=int(r["qty"]),
            )
            for r in rows
        ]

    async def add_item(
        self,
        user_id: int,
        service_key: str,
        title: str,
        price_kopecks: int,
        qty: int = 1,
    ) -> None:
        await self._db.execute(
            """
            INSERT INTO cart_items (user_id, service_key, title, price_kopecks, qty)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, service_key) DO UPDATE SET
                qty = cart_items.qty + excluded.qty,
                title = excluded.title,
                price_kopecks = excluded.price_kopecks
            """,
            (user_id, service_key, title, price_kopecks, qty),
        )

    async def remove_item(self, user_id: int, item_id: int) -> bool:
        cur = await self._db.execute(
            "DELETE FROM cart_items WHERE id = ? AND user_id = ?",
            (item_id, user_id),
        )
        return cur.rowcount > 0

    async def clear(self, user_id: int) -> None:
        await self._db.execute(
            "DELETE FROM cart_items WHERE user_id = ?",
            (user_id,),
        )

    async def total_kopecks(self, user_id: int) -> int:
        row = await self._db.fetchone(
            """
            SELECT COALESCE(SUM(price_kopecks * qty), 0) AS total
            FROM cart_items
            WHERE user_id = ?
            """,
            (user_id,),
        )
        return int(row["total"]) if row else 0


class OrderRepository:
    def __init__(self, db: Database) -> None:
        self._db = db
        # Защита от двойного нажатия «Оформить заказ» в одном процессе бота
        self._checkout_lock = asyncio.Lock()

    async def get_active_awaiting(self, user_id: int) -> Order | None:
        row = await self._db.fetchone(
            """
            SELECT id, user_id, status, total_kopecks,
                   yookassa_payment_id, confirmation_url
            FROM orders
            WHERE user_id = ? AND status = 'awaiting_payment'
            ORDER BY id DESC
            LIMIT 1
            """,
            (user_id,),
        )
        if not row:
            return None
        return await self._load_order(int(row["id"]))

    async def get_by_id(self, order_id: int) -> Order | None:
        return await self._load_order(order_id)

    async def create_from_cart(
        self, user_id: int, items: list[CartItem]
    ) -> Order | None:
        """Создаёт заказ из корзины. None, если корзина пуста. Идемпотентно."""
        if not items:
            return None

        total = sum(i.line_total for i in items)
        async with self._checkout_lock:
            existing = await self.get_active_awaiting(user_id)
            if existing is not None:
                return existing

            # Повторная проверка корзины внутри лока
            current = await self._db.fetchall(
                """
                SELECT id, service_key, title, price_kopecks, qty
                FROM cart_items
                WHERE user_id = ?
                """,
                (user_id,),
            )
            if not current:
                return None

            cart_items = [
                CartItem(
                    id=int(r["id"]),
                    service_key=str(r["service_key"]),
                    title=str(r["title"]),
                    price_kopecks=int(r["price_kopecks"]),
                    qty=int(r["qty"]),
                )
                for r in current
            ]
            total = sum(i.line_total for i in cart_items)

            cur = await self._db.execute(
                """
                INSERT INTO orders (user_id, status, total_kopecks)
                VALUES (?, 'awaiting_payment', ?)
                """,
                (user_id, total),
            )
            order_id = int(cur.lastrowid)
            await self._db.executemany(
                """
                INSERT INTO order_items
                    (order_id, service_key, title, price_kopecks, qty)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (order_id, i.service_key, i.title, i.price_kopecks, i.qty)
                    for i in cart_items
                ],
            )
            await self._db.execute(
                "DELETE FROM cart_items WHERE user_id = ?",
                (user_id,),
            )
            return await self._load_order(order_id)

    async def set_payment(
        self,
        order_id: int,
        payment_id: str,
        confirmation_url: str,
    ) -> None:
        await self._db.execute(
            """
            UPDATE orders
            SET yookassa_payment_id = ?,
                confirmation_url = ?,
                updated_at = datetime('now')
            WHERE id = ?
            """,
            (payment_id, confirmation_url, order_id),
        )

    async def mark_paid(self, order_id: int) -> bool:
        cur = await self._db.execute(
            """
            UPDATE orders
            SET status = 'paid', updated_at = datetime('now')
            WHERE id = ? AND status = 'awaiting_payment'
            """,
            (order_id,),
        )
        return cur.rowcount > 0

    async def count_for_user(self, user_id: int) -> int:
        row = await self._db.fetchone(
            "SELECT COUNT(*) AS c FROM orders WHERE user_id = ?",
            (user_id,),
        )
        return int(row["c"]) if row else 0

    async def _load_order(self, order_id: int) -> Order | None:
        row = await self._db.fetchone(
            """
            SELECT id, user_id, status, total_kopecks,
                   yookassa_payment_id, confirmation_url
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        )
        if not row:
            return None
        item_rows = await self._db.fetchall(
            """
            SELECT service_key, title, price_kopecks, qty
            FROM order_items
            WHERE order_id = ?
            ORDER BY id ASC
            """,
            (order_id,),
        )
        items = tuple(
            OrderItem(
                service_key=str(r["service_key"]),
                title=str(r["title"]),
                price_kopecks=int(r["price_kopecks"]),
                qty=int(r["qty"]),
            )
            for r in item_rows
        )
        return Order(
            id=int(row["id"]),
            user_id=int(row["user_id"]),
            status=str(row["status"]),
            total_kopecks=int(row["total_kopecks"]),
            yookassa_payment_id=(
                str(row["yookassa_payment_id"])
                if row["yookassa_payment_id"]
                else None
            ),
            confirmation_url=(
                str(row["confirmation_url"]) if row["confirmation_url"] else None
            ),
            items=items,
        )
