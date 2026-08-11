"""Сервис корзины."""

from __future__ import annotations

from app.data.knowledge import SERVICES_BY_KEY, Service, format_price_rub
from app.db.repository import CartItem, CartRepository, UserRepository


class CartService:
    def __init__(
        self,
        users: UserRepository,
        cart: CartRepository,
    ) -> None:
        self._users = users
        self._cart = cart

    async def ensure_user(
        self,
        telegram_id: int,
        username: str | None,
        full_name: str | None,
    ) -> int:
        return await self._users.upsert(telegram_id, username, full_name)

    async def add_service(self, user_id: int, service: Service) -> None:
        await self._cart.add_item(
            user_id=user_id,
            service_key=service.key,
            title=service.title,
            price_kopecks=service.price_kopecks,
            qty=1,
        )

    async def add_by_key(self, user_id: int, service_key: str) -> Service | None:
        service = SERVICES_BY_KEY.get(service_key)
        if service is None:
            return None
        await self.add_service(user_id, service)
        return service

    async def remove_item(self, user_id: int, item_id: int) -> bool:
        return await self._cart.remove_item(user_id, item_id)

    async def get_items(self, user_id: int) -> list[CartItem]:
        return await self._cart.list_items(user_id)

    async def total_kopecks(self, user_id: int) -> int:
        return await self._cart.total_kopecks(user_id)

    async def clear(self, user_id: int) -> None:
        await self._cart.clear(user_id)

    def format_cart_text(self, items: list[CartItem]) -> str:
        if not items:
            return "Корзина пуста. Добавьте услуги из раздела «Услуги и цены»."
        lines = ["<b>Корзина</b>\n"]
        for item in items:
            lines.append(
                f"• {item.title} × {item.qty} — "
                f"{format_price_rub(item.line_total)}"
            )
        total = sum(i.line_total for i in items)
        lines.append(f"\n<b>Итого: {format_price_rub(total)}</b>")
        return "\n".join(lines)
