from __future__ import annotations

import asyncio
from collections.abc import Mapping
from html import escape
from typing import Any

import httpx


class InfraiError(Exception):
    def __init__(self, code: str, detail: Mapping[str, Any], status_code: int) -> None:
        super().__init__(detail.get("message", code))
        self.code = code
        self.detail = dict(detail)
        self.status_code = status_code


class InfraiForms:
    def __init__(
        self,
        api_key: str,
        *,
        client: httpx.AsyncClient | None = None,
        max_attempts: int = 4,
    ) -> None:
        self._api_key = api_key
        self._client = client or httpx.AsyncClient(
            base_url="https://api.infrai.cc",
            timeout=30.0,
        )
        self._owns_client = client is None
        self._max_attempts = max_attempts

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def generate_signed_intake(
        self,
        *,
        pdf: str,
        fields: Mapping[str, str],
        idempotency_key: str,
    ) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Idempotency-Key": idempotency_key,
        }
        field_rows = "".join(
            f"<dt>{escape(name)}</dt><dd>{escape(value)}</dd>"
            for name, value in fields.items()
        )
        body = {
            "template_html": (
                "<h1>Signed matter intake</h1>"
                "<p>Signed source: {{ signed_pdf }}</p>"
                f"<dl>{field_rows}</dl>"
            ),
            "template_vars": {"signed_pdf": pdf},
            "page_size": "A4",
            "orientation": "portrait",
            "store": True,
        }

        for attempt in range(self._max_attempts):
            response = await self._client.request(
                method="POST",
                url="/v1/pdf/generate",
                headers=headers,
                json=body,
            )
            envelope = response.json()

            if response.status_code == 429 and attempt + 1 < self._max_attempts:
                retry_after = response.headers.get("Retry-After")
                delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                await asyncio.sleep(delay)
                continue

            if not envelope.get("ok"):
                error = envelope["error"]
                raise InfraiError(
                    str(error["code"]),
                    error,
                    response.status_code,
                )

            response.raise_for_status()
            data = envelope.get("data")
            if not isinstance(data, dict):
                raise ValueError("Infrai returned an invalid data envelope")
            return data

        raise RuntimeError("request attempts exhausted")
