"""Opt-in full-chain tests against a running local backend."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest


pytestmark = pytest.mark.integration
if os.environ.get("RUN_API_INTEGRATION") != "1":
    pytest.skip(
        "set RUN_API_INTEGRATION=1 to test a running local API",
        allow_module_level=True,
    )

from scripts.verify_qr import verify_package  # noqa: E402


API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADMIN_EMAIL = os.environ.get("API_ADMIN_EMAIL", "admin@example.com")
ADMIN_PASSWORD = os.environ.get("API_ADMIN_PASSWORD", "AdminPass123")
PDF_BYTES = b"%PDF-1.4\nNT219 integration test document\n"


def api_request(
    method: str,
    path: str,
    *,
    token: str | None = None,
    json_body: dict | None = None,
    body: bytes | None = None,
    content_type: str | None = None,
) -> tuple[int, object]:
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if json_body is not None:
        body = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if content_type:
        headers["Content-Type"] = content_type

    request = Request(f"{API_BASE_URL}{path}", data=body, headers=headers, method=method)
    try:
        with urlopen(request) as response:
            response_body = response.read()
            media_type = response.headers.get_content_type()
            return response.status, (
                json.loads(response_body) if media_type == "application/json" else response_body
            )
    except HTTPError as exc:
        response_body = exc.read()
        try:
            parsed_body: object = json.loads(response_body)
        except json.JSONDecodeError:
            parsed_body = response_body.decode("utf-8", errors="replace")
        return exc.code, parsed_body


def login(email: str, password: str) -> str:
    status_code, response = api_request(
        "POST",
        "/auth/login",
        json_body={"email": email, "password": password},
    )
    assert status_code == 200, response
    return response["access_token"]


def upload_pdf(token: str, pdf_bytes: bytes = PDF_BYTES) -> dict:
    boundary = f"----nt219-{uuid.uuid4().hex}"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="integration.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
    ).encode("ascii") + pdf_bytes + f"\r\n--{boundary}--\r\n".encode("ascii")
    status_code, response = api_request(
        "POST",
        "/documents/upload",
        token=token,
        body=body,
        content_type=f"multipart/form-data; boundary={boundary}",
    )
    assert status_code == 201, response
    return response


@pytest.fixture
def tokens() -> tuple[str, str]:
    citizen_email = f"citizen-{uuid.uuid4().hex[:12]}@example.com"
    citizen_password = "SecurePass123"
    status_code, response = api_request(
        "POST",
        "/auth/register",
        json_body={"email": citizen_email, "password": citizen_password},
    )
    assert status_code == 201, response
    return login(citizen_email, citizen_password), login(ADMIN_EMAIL, ADMIN_PASSWORD)


def test_full_chain_online_and_offline_verification(tokens):
    citizen_token, admin_token = tokens
    document = upload_pdf(citizen_token)
    doc_id = document["id"]

    assert api_request("POST", f"/documents/{doc_id}/sign", token=citizen_token)[0] == 403
    assert api_request("GET", "/audit", token=citizen_token)[0] == 403
    assert api_request("POST", f"/documents/{doc_id}/sign", token=admin_token)[0] == 200
    assert api_request("POST", f"/documents/{doc_id}/qr", token=citizen_token)[0] == 200

    status_code, online_result = api_request("GET", f"/verify?d={doc_id}")
    assert status_code == 200
    assert online_result["valid"] is True

    status_code, package = api_request(
        "GET",
        f"/documents/{doc_id}/verification-package",
        token=citizen_token,
    )
    assert status_code == 200
    assert verify_package(
        PDF_BYTES,
        json.dumps(package),
        now=package["issued_at"],
    )["valid"] is True

    for action in ("login", "upload", "sign", "verify_qr"):
        status_code, audit = api_request("GET", f"/audit?action={action}", token=admin_token)
        assert status_code == 200
        assert audit["entries"], f"missing audit rows for {action}"


def test_pre_sign_hash_mismatch_is_rejected_when_storage_is_local(tokens):
    citizen_token, admin_token = tokens
    storage_dir = os.environ.get("API_STORAGE_DIR")
    if not storage_dir:
        pytest.skip("set API_STORAGE_DIR for local filesystem tamper tests")

    document = upload_pdf(citizen_token)
    pdf_path = Path(storage_dir) / f"{document['id']}.pdf"
    original = pdf_path.read_bytes()
    try:
        pdf_path.write_bytes(original + b"tampered-before-sign")
        status_code, response = api_request(
            "POST",
            f"/documents/{document['id']}/sign",
            token=admin_token,
        )
        assert status_code == 409, response
    finally:
        pdf_path.write_bytes(original)


def test_tampered_signed_pdf_is_invalid_when_storage_is_local(tokens):
    citizen_token, admin_token = tokens
    storage_dir = os.environ.get("API_STORAGE_DIR")
    if not storage_dir:
        pytest.skip("set API_STORAGE_DIR for local filesystem tamper tests")

    document = upload_pdf(citizen_token)
    doc_id = document["id"]
    assert api_request("POST", f"/documents/{doc_id}/sign", token=admin_token)[0] == 200
    assert api_request("POST", f"/documents/{doc_id}/qr", token=citizen_token)[0] == 200
    pdf_path = Path(storage_dir) / f"{doc_id}.pdf"
    original = pdf_path.read_bytes()
    try:
        pdf_path.write_bytes(original + b"tampered-after-sign")
        status_code, response = api_request("GET", f"/verify?d={doc_id}")
        assert status_code == 200
        assert response["valid"] is False
    finally:
        pdf_path.write_bytes(original)
