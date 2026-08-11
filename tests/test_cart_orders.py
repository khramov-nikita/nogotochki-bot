"""Автотесты корзины, заказов и статусов оплаты."""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path

from app.data.knowledge import SERVICES_BY_KEY
from app.db.connection import Database
from app.db.repository import (
    CartRepository,
    DialogRepository,
    OrderRepository,
    UserRepository,
)
from app.services.cart import CartService
from app.services.orders import OrderService
from app.services.payments import MockPaymentClient


class CartOrdersTestCase(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "test.db"
        self.db = Database(db_path)
        await self.db.connect()
        self.users = UserRepository(self.db)
        self.cart_repo = CartRepository(self.db)
        self.order_repo = OrderRepository(self.db)
        self.dialog = DialogRepository(self.db)
        self.payments = MockPaymentClient()
        self.cart = CartService(self.users, self.cart_repo)
        self.orders = OrderService(
            self.cart_repo,
            self.order_repo,
            self.payments,
            return_url="https://t.me/testbot?start=paid_{order_id}",
        )
        self.user_id = await self.users.upsert(1001, "client", "Test Client")

    async def asyncTearDown(self) -> None:
        await self.db.close()
        self._tmpdir.cleanup()

    async def test_add_remove_and_total(self) -> None:
        service = SERVICES_BY_KEY["manicure_gel"]
        await self.cart.add_service(self.user_id, service)
        items = await self.cart.get_items(self.user_id)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0].service_key, "manicure_gel")
        self.assertEqual(await self.cart.total_kopecks(self.user_id), 180_000)

        await self.cart.add_service(self.user_id, service)
        items = await self.cart.get_items(self.user_id)
        self.assertEqual(items[0].qty, 2)
        self.assertEqual(await self.cart.total_kopecks(self.user_id), 360_000)

        removed = await self.cart.remove_item(self.user_id, items[0].id)
        self.assertTrue(removed)
        self.assertEqual(await self.cart.get_items(self.user_id), [])
        self.assertEqual(await self.cart.total_kopecks(self.user_id), 0)

    async def test_checkout_empty_cart_does_not_create_order(self) -> None:
        result = await self.orders.checkout(self.user_id)
        self.assertTrue(result.empty_cart)
        self.assertIsNone(result.order)
        self.assertEqual(await self.order_repo.count_for_user(self.user_id), 0)

    async def test_double_checkout_creates_single_order(self) -> None:
        await self.cart.add_by_key(self.user_id, "brows_color")
        first = await self.orders.checkout(self.user_id)
        self.assertTrue(first.created)
        self.assertIsNotNone(first.order)
        assert first.order is not None

        # Корзина очищена — повтор без товаров не создаёт новый заказ,
        # а возвращает уже существующий awaiting_payment
        second = await self.orders.checkout(self.user_id)
        self.assertTrue(second.already_exists)
        self.assertFalse(second.created)
        assert second.order is not None
        self.assertEqual(first.order.id, second.order.id)
        self.assertEqual(await self.order_repo.count_for_user(self.user_id), 1)

    async def test_double_checkout_race_single_order(self) -> None:
        await self.cart.add_by_key(self.user_id, "extensions")
        items = await self.cart.get_items(self.user_id)

        async def _create() -> int:
            order = await self.order_repo.create_from_cart(self.user_id, items)
            assert order is not None
            return order.id

        ids = await asyncio.gather(_create(), _create())
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(await self.order_repo.count_for_user(self.user_id), 1)

    async def test_payment_succeeded_marks_paid(self) -> None:
        await self.cart.add_by_key(self.user_id, "manicure_gel")
        checkout = await self.orders.checkout(self.user_id)
        assert checkout.order is not None
        order = await self.orders.ensure_payment_link(checkout.order)
        assert order.yookassa_payment_id is not None
        self.payments.set_payment_status(order.yookassa_payment_id, "succeeded")

        result = await self.orders.check_payment(order.id, self.user_id)
        self.assertTrue(result.paid)
        paid = await self.orders.get_order(order.id)
        assert paid is not None
        self.assertEqual(paid.status, "paid")

    async def test_payment_pending_does_not_confirm(self) -> None:
        await self.cart.add_by_key(self.user_id, "design")
        checkout = await self.orders.checkout(self.user_id)
        assert checkout.order is not None
        order = await self.orders.ensure_payment_link(checkout.order)
        assert order.yookassa_payment_id is not None
        self.payments.set_payment_status(order.yookassa_payment_id, "pending")

        result = await self.orders.check_payment(order.id, self.user_id)
        self.assertFalse(result.paid)
        self.assertIn("не прошёл", result.message.lower())
        still = await self.orders.get_order(order.id)
        assert still is not None
        self.assertEqual(still.status, "awaiting_payment")

    async def test_dialog_history_persisted(self) -> None:
        await self.dialog.add_message(self.user_id, "user", "Привет")
        await self.dialog.add_message(self.user_id, "assistant", "Здравствуйте!")
        history = await self.dialog.get_history(self.user_id)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["role"], "user")
        self.assertEqual(history[1]["content"], "Здравствуйте!")


if __name__ == "__main__":
    unittest.main()
