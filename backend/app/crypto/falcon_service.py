"""
FALCON document signing service using liboqs-python.

This module is used by the backend to:
- generate a FALCON key pair
- sign the SHA-256 hash of a document
- verify a signature over a document hash
"""

import hashlib
from typing import Tuple

import oqs


ALGORITHM = "Falcon-512"


def generate_keypair() -> Tuple[bytes, bytes]:
    """
    Generate a FALCON key pair.

    Returns:
        (public_key, private_key)
    """
    with oqs.Signature(ALGORITHM) as signer:
        public_key = signer.generate_keypair()
        private_key = signer.export_secret_key()

    return public_key, private_key


def hash_document(pdf_bytes: bytes) -> str:
    """
    Compute SHA-256 hash of raw document bytes.

    Args:
        pdf_bytes: Raw PDF/document bytes.

    Returns:
        SHA-256 hash in hexadecimal format.
    """
    if not isinstance(pdf_bytes, bytes):
        raise TypeError("pdf_bytes must be bytes")

    return hashlib.sha256(pdf_bytes).hexdigest()


def sign_document(pdf_bytes: bytes, private_key: bytes) -> Tuple[str, bytes]:
    """
    Sign the SHA-256 hash of a document using FALCON.

    Important:
        The system signs the SHA-256 hash, not the whole PDF directly.

    Args:
        pdf_bytes: Raw PDF/document bytes.
        private_key: FALCON private key.

    Returns:
        (doc_hash_hex, signature_bytes)
    """
    if not isinstance(pdf_bytes, bytes):
        raise TypeError("pdf_bytes must be bytes")

    doc_hash_hex = hash_document(pdf_bytes)
    doc_hash_bytes = bytes.fromhex(doc_hash_hex)

    with oqs.Signature(ALGORITHM, secret_key=private_key) as signer:
        signature = signer.sign(doc_hash_bytes)

    return doc_hash_hex, signature


def verify_signature(doc_hash_hex: str, signature: bytes, public_key: bytes) -> bool:
    """
    Verify a FALCON signature over a SHA-256 document hash.

    Args:
        doc_hash_hex: SHA-256 document hash in hex.
        signature: FALCON signature bytes.
        public_key: FALCON public key.

    Returns:
        True if the signature is valid, otherwise False.
    """
    try:
        doc_hash_bytes = bytes.fromhex(doc_hash_hex)

        with oqs.Signature(ALGORITHM) as verifier:
            return verifier.verify(doc_hash_bytes, signature, public_key)

    except Exception:
        return False


def verify_document(pdf_bytes: bytes, signature: bytes, public_key: bytes) -> bool:
    """
    Verify a document directly by recomputing its SHA-256 hash.

    Args:
        pdf_bytes: Raw PDF/document bytes.
        signature: FALCON signature bytes.
        public_key: FALCON public key.

    Returns:
        True if the document is authentic and unchanged.
    """
    doc_hash_hex = hash_document(pdf_bytes)
    return verify_signature(doc_hash_hex, signature, public_key)