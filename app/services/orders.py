"""Сервис заказов и проверки оплаты."""

from __future__ import annotations

from dataclasses import dataclass

from app.data.knowledge import format_price_rub
from app.db.repository import CartRepository, Order, OrderRepository
from app.services.payments import PaymentClient, PaymentInfo


@dataclass(frozen=True)
class CheckoutResult:
    order: Order | None
    created: bool
    empty_cart: bool
    already_exists: bool


@dataclass(frozen=True)
class PaymentCheckResult:
    order: Order | None
    paid: bool
    message: str


class OrderService:
    def __init__(
        self,
        cart: CartRepository,
        orders: OrderRepository,
        payments: PaymentClient,
        return_url: str,
    ) -> None:
        self._cart = cart
        self._orders = orders
        self._payments = payments
        self._return_url = return_url

    async def get_active_order(self, user_id: int) -> Order | None:
        return await self._orders.get_active_awaiting(user_id)

    async def get_order(self, order_id: int) -> Order | None:
        return await self._orders.get_by_id(order_id)

    async def checkout(self, user_id: int) -> CheckoutResult:
        existing = await self._orders.get_active_awaiting(user_id)
        if existing is not None:
            return CheckoutResult(
                order=existing,
                created=False,
                empty_cart=False,
                already_exists=True,
            )

        items = await self._cart.list_items(user_id)
        if not items:
            return CheckoutResult(
                order=None,
                created=False,
                empty_cart=True,
                already_exists=False,
            )

        before_count = await self._orders.count_for_user(user_id)
        order = await self._orders.create_from_cart(user_id, items)
        if order is None:
            return CheckoutResult(
                order=None,
                created=False,
                empty_cart=True,
                already_exists=False,
            )

        after_count = await self._orders.count_for_user(user_id)
        created = after_count > before_count
        return CheckoutResult(
            order=order,
            created=created,
            empty_cart=False,
            already_exists=not created,
        )

    async def ensure_payment_link(self, order: Order) -> Order:
        if order.confirmation_url and order.yookassa_payment_id:
            return order

        description = f"Заказ #{order.id} — студия «Ноготочки»"
        return_url = self._return_url
        if "{order_id}" in return_url:
            return_url = return_url.format(order_id=order.id)

        payment = await self._payments.create_payment(
            amount_kopecks=order.total_kopecks,
            description=description,
            return_url=return_url,
            metadata={"order_id": str(order.id)},
        )
        await self._orders.set_payment(
            order.id, payment.id, payment.confirmation_url
        )
        updated = await self._orders.get_by_id(order.id)
        assert updated is not None
        return updated

    async def check_payment(self, order_id: int, user_id: int) -> PaymentCheckResult:
        order = await self._orders.get_by_id(order_id)
        if order is None or order.user_id != user_id:
            return PaymentCheckResult(
                order=None,
                paid=False,
                message="Заказ не найден.",
            )
        if order.status == "paid":
            return PaymentCheckResult(
                order=order,
                paid=True,
                message=(
                    f"Заказ #{order.id} уже оплачен. "
                    "Мастер свяжется с вами, чтобы согласовать время."
                ),
            )
        if order.status != "awaiting_payment":
            return PaymentCheckResult(
                order=order,
                paid=False,
                message=f"Заказ #{order.id} в статусе «{order.status}».",
            )
        if not order.yookassa_payment_id:
            return PaymentCheckResult(
                order=order,
                paid=False,
                message=(
                    "Ссылка на оплату ещё не создана. "
                    "Сначала нажмите «Оплатить»."
                ),
            )

        info: PaymentInfo = await self._payments.get_payment(
            order.yookassa_payment_id
        )
        if info.status == "succeeded":
            await self._orders.mark_paid(order.id)
            paid_order = await self._orders.get_by_id(order.id)
            return PaymentCheckResult(
                order=paid_order,
                paid=True,
                message=(
                    f"Оплата подтверждена! Заказ #{order.id} на сумму "
                    f"{format_price_rub(order.total_kopecks)} оплачен.\n"
                    "Мастер свяжется с вами, чтобы согласовать дату и время."
                ),
            )

        return PaymentCheckResult(
            order=order,
            paid=False,
            message=(
                "Платёж ещё не прошёл. Если вы уже оплатили, подождите минуту "
                "и нажмите «Я оплатил» снова. Заказ не подтверждён."
            ),
        )

    def format_order_text(self, order: Order) -> str:
        lines = [
            f"<b>Заказ #{order.id}</b>",
            f"Статус: {self._status_label(order.status)}",
            "",
        ]
        for item in order.items:
            lines.append(
                f"• {item.title} × {item.qty} — "
                f"{format_price_rub(item.price_kopecks * item.qty)}"
            )
        lines.append(f"\n<b>Итого: {format_price_rub(order.total_kopecks)}</b>")
        return "\n".join(lines)

    @staticmethod
    def _status_label(status: str) -> str:
        labels = {
            "pending": "черновик",
            "awaiting_payment": "ожидает оплаты",
            "paid": "оплачен",
            "cancelled": "отменён",
        }
        return labels.get(status, status)
