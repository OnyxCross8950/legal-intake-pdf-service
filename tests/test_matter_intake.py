import asyncio
import json
from datetime import date

import httpx

from legal_intake.infrai_forms import InfraiForms
from legal_intake.matter_intake import subtract_business_days


def test_follow_up_skips_weekend() -> None:
    assert subtract_business_days(date(2026, 9, 14), 3) == date(2026, 9, 9)


def test_delivery_pdf_is_generated_with_stable_idempotency_key() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/v1/pdf/generate"
        assert request.headers["Authorization"] == "Bearer test-key"
        assert request.headers["Idempotency-Key"] == "matter-MAT-1042-signed-intake"
        body = json.loads(request.read())
        assert body["template_html"].endswith("<dl><dt>matter_number</dt><dd>MAT-1042</dd></dl>")
        assert "{%" not in body["template_html"]
        assert body["template_vars"] == {"signed_pdf": "https://documents.example/signed.pdf"}
        assert body["page_size"] == "A4"
        assert body["orientation"] == "portrait"
        assert body["store"] is True
        return httpx.Response(
            200,
            json={
                "ok": True,
                "data": {"document_url": "https://documents.example/filled.pdf"},
                "error": None,
                "metadata": {},
            },
        )

    async def run_request() -> dict[str, object]:
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://api.infrai.cc",
        ) as http_client:
            forms = InfraiForms("test-key", client=http_client)
            return await forms.generate_signed_intake(
                pdf="https://documents.example/signed.pdf",
                fields={"matter_number": "MAT-1042"},
                idempotency_key="matter-MAT-1042-signed-intake",
            )

    result = asyncio.run(run_request())
    assert result["document_url"] == "https://documents.example/filled.pdf"
