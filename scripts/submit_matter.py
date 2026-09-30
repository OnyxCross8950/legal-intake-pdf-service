from __future__ import annotations

import argparse
import json

import httpx


def main() -> None:
    parser = argparse.ArgumentParser(description="Submit a signed matter intake")
    parser.add_argument("signed_pdf", help="URL or accepted PDF input")
    parser.add_argument("--service", default="http://127.0.0.1:8000")
    args = parser.parse_args()

    payload = {
        "matter_id": "MAT-1042",
        "client_name": "Jordan Lee",
        "signed_pdf": args.signed_pdf,
        "response_due_on": "2026-09-14",
        "form_fields": {
            "client_full_name": "Jordan Lee",
            "matter_number": "MAT-1042",
            "delivery_status": "Signed copy received",
        },
    }
    response = httpx.request(
        method="POST",
        url=f"{args.service}/matters/intake",
        json=payload,
        timeout=30.0,
    )
    response.raise_for_status()
    print(json.dumps(response.json(), indent=2))


if __name__ == "__main__":
    main()

