#!/usr/bin/env python3
"""
Smoke test for AI Contract Analyzer agent workflow against a running API.

Requires: httpx (pip install -r backend/requirements.txt)
Optional: OPENROUTER_API_KEY for full analyze + Q&A (LLM steps).
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

TESTS_ROOT = BACKEND_ROOT / "tests"
if str(TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(TESTS_ROOT))

from helpers.demo_contract import demo_contract_path, write_demo_contract  # noqa: E402
from helpers.report_validation import (  # noqa: E402
    validate_legal_sources_state,
    validate_report_schema,
)

DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_PASSWORD = "SmokeTestPass123!"


class SmokeError(Exception):
    """Non-zero exit smoke failure."""


class SmokeSkipLLM(Exception):
    """LLM-dependent steps skipped (not a server failure)."""


def _api(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}{path}"


def check_health(client: httpx.Client, base_url: str) -> None:
    response = client.get(_api(base_url, "/api/health"), timeout=30.0)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "ok":
        raise SmokeError(f"Unexpected health payload: {payload}")
    print("[ok] GET /api/health")


def obtain_token(client: httpx.Client, base_url: str, username: str, password: str) -> str:
    register_payload = {
        "username": username,
        "email": f"{username}@smoke.local",
        "password": password,
    }
    register_response = client.post(
        _api(base_url, "/api/auth/register"),
        json=register_payload,
        timeout=30.0,
    )
    if register_response.status_code not in {200, 400}:
        register_response.raise_for_status()

    login_response = client.post(
        _api(base_url, "/api/auth/login"),
        json={"username": username, "password": password},
        timeout=30.0,
    )
    if login_response.status_code != 200:
        raise SmokeError(
            f"Auth failed ({login_response.status_code}): {login_response.text}"
        )
    token = login_response.json().get("access_token")
    if not token:
        raise SmokeError("Login response missing access_token")
    print(f"[ok] Auth token for user {username}")
    return str(token)


def upload_demo_document(
    client: httpx.Client,
    base_url: str,
    headers: dict[str, str],
    demo_path: Path,
) -> str:
    if not demo_path.is_file():
        write_demo_contract(demo_path)
        print(f"[info] Created demo file at {demo_path}")

    with demo_path.open("rb") as handle:
        response = client.post(
            _api(base_url, "/api/documents"),
            headers=headers,
            files={
                "file": (
                    demo_path.name,
                    handle,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                )
            },
            timeout=120.0,
        )
    if response.status_code != 200:
        raise SmokeError(f"Upload failed ({response.status_code}): {response.text}")

    document_id = response.json().get("document_id")
    if not document_id:
        raise SmokeError(f"Upload response missing document_id: {response.text}")
    print(f"[ok] POST /api/documents -> {document_id}")
    return str(document_id)


def run_analyze(
    client: httpx.Client,
    base_url: str,
    headers: dict[str, str],
    document_id: str,
) -> dict:
    response = client.post(
        _api(base_url, f"/api/documents/{document_id}/analyze"),
        headers=headers,
        timeout=600.0,
    )
    if response.status_code == 503 and "OPENROUTER" in response.text.upper():
        raise SmokeSkipLLM(f"Analyze unavailable (503): {response.text}")
    if response.status_code != 200:
        raise SmokeError(f"Analyze failed ({response.status_code}): {response.text}")
    print(f"[ok] POST /api/documents/{document_id}/analyze")
    return response.json()


def check_status(
    client: httpx.Client,
    base_url: str,
    headers: dict[str, str],
    document_id: str,
) -> None:
    response = client.get(
        _api(base_url, f"/api/documents/{document_id}/status"),
        headers=headers,
        timeout=30.0,
    )
    if response.status_code != 200:
        raise SmokeError(f"Status failed ({response.status_code}): {response.text}")
    payload = response.json()
    print(f"[ok] GET /api/documents/{document_id}/status -> {payload.get('status')}")


def check_report(
    client: httpx.Client,
    base_url: str,
    headers: dict[str, str],
    document_id: str,
    report: dict | None = None,
) -> dict:
    if report is None:
        response = client.get(
            _api(base_url, f"/api/documents/{document_id}/report"),
            headers=headers,
            timeout=30.0,
        )
        if response.status_code != 200:
            raise SmokeError(f"Report failed ({response.status_code}): {response.text}")
        report = response.json()
        print(f"[ok] GET /api/documents/{document_id}/report")
    else:
        print(f"[ok] Report from analyze response")

    errors = validate_report_schema(report)
    if errors:
        raise SmokeError("Report schema validation failed:\n- " + "\n- ".join(errors))

    for field in (
        "summary",
        "overall_risk",
        "risks",
        "key_terms",
        "legal_sources",
        "disclaimer",
    ):
        if field not in report:
            raise SmokeError(f"Report missing field: {field}")

    legal_errors = validate_legal_sources_state(report)
    if legal_errors:
        raise SmokeError(
            "Legal sources validation failed:\n- " + "\n- ".join(legal_errors)
        )

    sources = report.get("legal_sources", [])
    warnings = report.get("warnings", [])
    if sources:
        print(f"[ok] legal_sources: {len(sources)} item(s)")
    else:
        print(f"[ok] legal_sources empty with {len(warnings)} warning(s)")

    return report


def check_legal_sources_endpoint(
    client: httpx.Client,
    base_url: str,
    headers: dict[str, str],
    document_id: str,
) -> None:
    response = client.get(
        _api(base_url, f"/api/documents/{document_id}/legal-sources"),
        headers=headers,
        timeout=30.0,
    )
    if response.status_code != 200:
        raise SmokeError(
            f"Legal sources endpoint failed ({response.status_code}): {response.text}"
        )
    payload = response.json()
    sources = payload.get("legal_sources", [])
    warnings = payload.get("warnings", [])
    if sources:
        print(f"[ok] GET legal-sources -> {len(sources)} source(s)")
    else:
        print(f"[ok] GET legal-sources -> empty, warnings={len(warnings)}")


def run_ask(
    client: httpx.Client,
    base_url: str,
    headers: dict[str, str],
    document_id: str,
    question: str,
) -> None:
    response = client.post(
        _api(base_url, f"/api/documents/{document_id}/ask"),
        headers=headers,
        json={"question": question},
        timeout=180.0,
    )
    if response.status_code == 503 and "OPENROUTER" in response.text.upper():
        raise SmokeSkipLLM(f"Ask unavailable (503): {response.text}")
    if response.status_code != 200:
        raise SmokeError(f"Ask failed ({response.status_code}): {response.text}")

    payload = response.json()
    citations = payload.get("citations", [])
    if not isinstance(citations, list):
        raise SmokeError("citations must be a list")

    # citations may be empty if no chunks, but after analyze we expect some
    if citations:
        first = citations[0]
        if not str(first.get("quote", "")).strip():
            raise SmokeError("citation missing quote")
        print(
            f"[ok] POST /api/documents/{document_id}/ask -> "
            f"{len(citations)} citation(s), confidence={payload.get('confidence')}"
        )
    else:
        print(
            f"[warn] POST /ask returned no citations "
            f"(answer={payload.get('answer', '')[:80]!r})"
        )


def llm_enabled(explicit_skip: bool) -> bool:
    if explicit_skip:
        return False
    if os.getenv("SMOKE_SKIP_LLM", "").strip().lower() in {"1", "true", "yes"}:
        return False
    return bool(os.getenv("OPENROUTER_API_KEY", "").strip())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backend agent workflow smoke test")
    parser.add_argument(
        "--base-url",
        default=os.getenv("SMOKE_BASE_URL", DEFAULT_BASE_URL),
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--demo-file",
        type=Path,
        default=Path(os.getenv("SMOKE_DEMO_FILE", str(demo_contract_path()))),
        help="Path to demo DOCX/PDF for upload",
    )
    parser.add_argument(
        "--username",
        default=os.getenv("SMOKE_USERNAME", f"smoke_{int(time.time())}"),
    )
    parser.add_argument(
        "--password",
        default=os.getenv("SMOKE_PASSWORD", DEFAULT_PASSWORD),
    )
    parser.add_argument(
        "--question",
        default="Какой срок оплаты по договору?",
        help="Question for /ask endpoint",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip analyze and ask even if OPENROUTER_API_KEY is set",
    )
    args = parser.parse_args(argv)

    run_llm = llm_enabled(args.skip_llm)
    if not run_llm:
        print(
            "[info] OPENROUTER_API_KEY not set or SMOKE_SKIP_LLM=1 — "
            "LLM steps (analyze, ask) will be skipped."
        )

    try:
        with httpx.Client() as client:
            check_health(client, args.base_url)
            token = obtain_token(
                client, args.base_url, args.username, args.password
            )
            headers = {"Authorization": f"Bearer {token}"}

            document_id = upload_demo_document(
                client, args.base_url, headers, args.demo_file
            )

            report: dict | None = None
            if run_llm:
                try:
                    report = run_analyze(
                        client, args.base_url, headers, document_id
                    )
                except SmokeSkipLLM as exc:
                    print(f"[skip] analyze: {exc}")
                    run_llm = False
            else:
                print("[skip] POST /api/documents/{id}/analyze (no API key)")

            if report is not None:
                check_status(client, args.base_url, headers, document_id)
                check_report(client, args.base_url, headers, document_id, report=report)
                check_legal_sources_endpoint(
                    client, args.base_url, headers, document_id
                )
                try:
                    run_ask(
                        client,
                        args.base_url,
                        headers,
                        document_id,
                        args.question,
                    )
                except SmokeSkipLLM as exc:
                    print(f"[skip] ask: {exc}")
            elif not run_llm:
                print(
                    "[done] Infra smoke passed (health, auth, upload). "
                    "Set OPENROUTER_API_KEY for full workflow."
                )
                return 2

        print("[done] Smoke test completed successfully.")
        return 0
    except SmokeError as exc:
        print(f"[fail] {exc}", file=sys.stderr)
        return 1
    except httpx.HTTPError as exc:
        print(
            f"[fail] HTTP error: {exc}. Is the API running at {args.base_url}?",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
