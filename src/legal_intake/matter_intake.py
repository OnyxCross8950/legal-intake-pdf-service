from __future__ import annotations

import os
from datetime import date, timedelta
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from .infrai_forms import InfraiError, InfraiForms


class MatterIntake(BaseModel):
    matter_id: str = Field(min_length=1)
    client_name: str = Field(min_length=1)
    signed_pdf: str = Field(min_length=1)
    response_due_on: date
    form_fields: dict[str, str] = Field(min_length=1)


class DeliveryResult(BaseModel):
    matter_id: str
    state: str
    follow_up_on: date
    filled_document: dict[str, Any]


def subtract_business_days(day: date, count: int) -> date:
    cursor = day
    remaining = count
    while remaining:
        cursor -= timedelta(days=1)
        if cursor.weekday() < 5:
            remaining -= 1
    return cursor


def forms_client() -> InfraiForms:
    api_key = os.environ.get("INFRAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set INFRAI_API_KEY before starting the service")
    return InfraiForms(api_key)


app = FastAPI(title="Legal intake PDF service")


@app.post("/matters/intake", response_model=DeliveryResult)
async def deliver_signed_intake(
    intake: MatterIntake,
    forms: InfraiForms = Depends(forms_client),
) -> DeliveryResult:
    try:
        document = await forms.generate_signed_intake(
            pdf=intake.signed_pdf,
            fields=intake.form_fields,
            idempotency_key=f"matter-{intake.matter_id}-signed-intake",
        )
    except InfraiError as exc:
        client_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=client_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    finally:
        await forms.close()

    return DeliveryResult(
        matter_id=intake.matter_id,
        state="signed_document_delivered",
        follow_up_on=subtract_business_days(intake.response_due_on, 3),
        filled_document=document,
    )
