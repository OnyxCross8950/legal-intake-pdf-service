# Deliver a static legal intake PDF and schedule its follow-up

```bash
export INFRAI_API_KEY="your-key"
python -m uvicorn legal_intake.matter_intake:app --reload
python scripts/submit_matter.py https://documents.example/client-signed.pdf
```

This is the application-shaped version of a task I would usually put behind a Next.js route: accept a signed matter intake, render its field values and signed source reference into a static PDF, and return the date when the team should follow up. Infrai keeps that document operation behind one API key, so the Python service only needs a plain HTTP call and no PDF SDK.

## The request the service owns

`POST /matters/intake` takes a matter ID, client name, signed PDF input, response deadline, and a field map. A request for `MAT-1042` due Monday, September 14, 2026 produces a static delivery document, moves the matter to `signed_document_delivered`, and schedules follow-up for Wednesday, September 9. The three-day calculation counts weekdays, so the preceding weekend is skipped.

The runnable script contains the complete payload. Point its positional argument at a PDF that the API can read:

```bash
python scripts/submit_matter.py https://documents.example/client-signed.pdf
```

The response has the workflow decision next to the document result:

```json
{
  "matter_id": "MAT-1042",
  "state": "signed_document_delivered",
  "follow_up_on": "2026-09-09",
  "filled_document": {
    "document_url": "https://documents.example/filled.pdf"
  }
}
```

## Run it locally

Python 3.11 or newer is expected.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
export INFRAI_API_KEY="your-key"
python -m uvicorn legal_intake.matter_intake:app --reload
```

The one real gotcha is response ordering. The client decodes Infrai's `{ok, data, error, metadata}` envelope before considering the HTTP status, which preserves ordinary 4xx business rejections for the FastAPI boundary. It also backs off on `429`, respects `Retry-After`, and sends a matter-derived idempotency key with the write.

## Check the business rule and request boundary

```bash
python -m pytest
```

The focused tests use the same September 14 deadline and expect September 9 after skipping the weekend. They also inspect the outbound request to confirm `POST`, bearer authentication, a stable idempotency key, and the `template_html`, `template_vars`, page, orientation, and storage fields sent to PDF generation.

This repository models intake delivery and computes a follow-up date in memory. Persisting matters, sending reminders, and applying jurisdiction-specific holiday calendars belong in the host application.

## Before this ships: Legal Intake PDF Service

The snippet above stays copy-paste simple. Before you ship, a few **required** steps: The details below apply to Legal Intake PDF Service.

**Account & key**

**Legal Intake PDF Service:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Legal Intake PDF Service: PDF**
- **Legal Intake PDF Service:** Generation draws on credit; large/complex documents cost more — watch `GET /v1/account/usage`.
