"""Клиент API ЮKassa."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

YOOKASSA_API = "https://api.yookassa.ru/v3"


@dataclass(frozen=True)
class PaymentInfo:
    id: str
    status: str
    confirmation_url: str
    paid: bool


class PaymentClient(Protocol):
    async def create_payment(
        self,
        amount_kopecks: int,
        description: str,
        return_url: str,
        metadata: dict[str, str] | None = None,
    ) -> PaymentInfo: ...

    async def get_payment(self, payment_id: str) -> PaymentInfo: ...

    async def close(self) -> None: ...


class YooKassaClient:
    """HTTP-клиент ЮKassa (Basic Auth shopId:secretKey)."""

    def __init__(self, shop_id: str, secret_key: str) -> None:
        self._auth = (shop_id, secret_key)
        self._client = httpx.AsyncClient(
            base_url=YOOKASSA_API,
            auth=self._auth,
            timeout=30.0,
            headers={"Content-Type": "application/json"},
        )

    async def create_payment(
        self,
        amount_kopecks: int,
        description: str,
        return_url: str,
        metadata: dict[str, str] | None = None,
    ) -> PaymentInfo:
        rubles = f"{amount_kopecks / 100:.2f}"
        payload: dict[str, Any] = {
            "amount": {"value": rubles, "currency": "RUB"},
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "capture": True,
            "description": description[:128],
        }
        if metadata:
            payload["metadata"] = metadata

        response = await self._client.post(
            "/payments",
            json=payload,
            headers={"Idempotence-Key": str(uuid.uuid4())},
        )
        response.raise_for_status()
        data = response.json()
        return self._parse(data)

    async def get_payment(self, payment_id: str) -> PaymentInfo:
        response = await self._client.get(f"/payments/{payment_id}")
        response.raise_for_status()
        return self._parse(response.json())

    async def close(self) -> None:
        await self._client.aclose()

    @staticmethod
    def _parse(data: dict[str, Any]) -> PaymentInfo:
        confirmation = data.get("confirmation") or {}
        return PaymentInfo(
            id=str(data["id"]),
            status=str(data.get("status") or "pending"),
            confirmation_url=str(confirmation.get("confirmation_url") or ""),
            paid=bool(data.get("paid")),
        )


class MockPaymentClient:
    """Мок для автотестов и локальной разработки без ключей ЮKassa."""

    def __init__(self) -> None:
        self._payments: dict[str, PaymentInfo] = {}
        self._next_status: str = "pending"

    def set_next_status(self, status: str) -> None:
        self._next_status = status

    def set_payment_status(self, payment_id: str, status: str) -> None:
        current = self._payments.get(payment_id)
        if current is None:
            return
        self._payments[payment_id] = PaymentInfo(
            id=current.id,
            status=status,
            confirmation_url=current.confirmation_url,
            paid=status == "succeeded",
        )

    async def create_payment(
        self,
        amount_kopecks: int,
        description: str,
        return_url: str,
        metadata: dict[str, str] | None = None,
    ) -> PaymentInfo:
        payment_id = str(uuid.uuid4())
        info = PaymentInfo(
            id=payment_id,
            status=self._next_status,
            confirmation_url=f"https://mock.yookassa.local/pay/{payment_id}",
            paid=self._next_status == "succeeded",
        )
        self._payments[payment_id] = info
        logger.info(
            "Mock payment created: %s amount=%s desc=%s return=%s meta=%s",
            payment_id,
            amount_kopecks,
            description,
            return_url,
            metadata,
        )
        return info

    async def get_payment(self, payment_id: str) -> PaymentInfo:
        if payment_id not in self._payments:
            return PaymentInfo(
                id=payment_id,
                status="canceled",
                confirmation_url="",
                paid=False,
            )
        return self._payments[payment_id]

    async def close(self) -> None:
        return None
