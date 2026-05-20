import pytest

from backend.app.crypto.falcon_service import (
    ALGORITHM,
    available_signature_algorithms,
    generate_keypair,
    resolve_algorithm,
    sign_document,
    verify_document,
    verify_signature,
    hash_document,
)

pytestmark = pytest.mark.skipif(
    not available_signature_algorithms(),
    reason="liboqs-python/oqs is not installed or no signature mechanisms are enabled",
)


def test_algorithm_resolves_to_enabled_falcon_name():
    assert resolve_algorithm("FALCON-512") == ALGORITHM
    assert ALGORITHM in available_signature_algorithms()


def test_valid_document_signature():
    public_key, private_key = generate_keypair()

    pdf_bytes = b"%PDF-1.4\nCitizen service document A\n"
    doc_hash_hex, signature = sign_document(pdf_bytes, private_key)

    assert isinstance(doc_hash_hex, str)
    assert len(doc_hash_hex) == 64
    assert isinstance(signature, bytes)

    assert verify_signature(doc_hash_hex, signature, public_key) is True
    assert verify_document(pdf_bytes, signature, public_key, doc_hash_hex) is True


def test_tampered_document_must_fail():
    public_key, private_key = generate_keypair()

    original_pdf = b"%PDF-1.4\nCitizen ID renewal request: Nguyen Van A\n"
    tampered_pdf = b"%PDF-1.4\nCitizen ID renewal request: Nguyen Van B\n"

    _, signature = sign_document(original_pdf, private_key)

    assert verify_document(original_pdf, signature, public_key) is True
    assert verify_document(tampered_pdf, signature, public_key) is False
    assert verify_document(original_pdf, signature, public_key, hash_document(tampered_pdf)) is False


def test_wrong_public_key_must_fail():
    public_key_1, private_key_1 = generate_keypair()
    public_key_2, _ = generate_keypair()

    pdf_bytes = b"%PDF-1.4\nPublic administrative service document\n"

    doc_hash_hex, signature = sign_document(pdf_bytes, private_key_1)

    assert verify_signature(doc_hash_hex, signature, public_key_1) is True
    assert verify_signature(doc_hash_hex, signature, public_key_2) is False


def test_hash_changes_when_document_changes():
    original_pdf = b"%PDF-1.4\nOriginal document\n"
    tampered_pdf = b"%PDF-1.4\nOriginal document changed\n"

    assert hash_document(original_pdf) != hash_document(tampered_pdf)


def test_invalid_signature_inputs_return_false():
    public_key, private_key = generate_keypair()
    pdf_bytes = b"%PDF-1.4\nInvalid input handling\n"
    doc_hash_hex, signature = sign_document(pdf_bytes, private_key)

    assert verify_signature("not-a-hex-digest", signature, public_key) is False
    assert verify_signature(doc_hash_hex, b"invalid-signature", public_key) is False
    assert verify_document("not bytes", signature, public_key) is False
