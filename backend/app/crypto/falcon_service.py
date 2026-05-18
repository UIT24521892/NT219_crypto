import hashlib
from typing import Final

try:
    import oqs
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    oqs = None  # type: ignore[assignment]


PREFERRED_ALGORITHM: Final[str] = "FALCON-512"
_NORMALIZED_FALCON_NAMES: Final[dict[str, tuple[str, ...]]] = {
    "falcon-512": ("Falcon-512", "FALCON-512"),
    "falcon-1024": ("Falcon-1024", "FALCON-1024"),
}


def _normalise_algorithm_name(name: str) -> str:
    return name.replace("_", "-").casefold()


def _require_oqs() -> None:
    if oqs is None:
        raise RuntimeError(
            "liboqs-python is required for FALCON signing. Install liboqs-python "
            "and ensure the liboqs shared library is available."
        )


def available_signature_algorithms() -> list[str]:
    """Return enabled liboqs signature mechanism names."""

    if oqs is None:
        return []

    return list(oqs.get_enabled_sig_mechanisms())


def resolve_algorithm(preferred: str = PREFERRED_ALGORITHM) -> str:
    """
    Resolve a project algorithm name to the exact liboqs mechanism name.

    liboqs-python 0.15 exposes Falcon names as ``Falcon-512``/``Falcon-1024``.
    The project-facing payload name remains ``FALCON-512``.
    """

    if not isinstance(preferred, str) or not preferred:
        raise ValueError("preferred algorithm must be a non-empty string")

    available = available_signature_algorithms()
    if not available:
        return preferred

    if preferred in available:
        return preferred

    preferred_normalised = _normalise_algorithm_name(preferred)
    for algorithm in available:
        if _normalise_algorithm_name(algorithm) == preferred_normalised:
            return algorithm

    for alias in _NORMALIZED_FALCON_NAMES.get(preferred_normalised, ()):
        if alias in available:
            return alias

    raise RuntimeError(
        f"Signature algorithm {preferred!r} is not enabled by liboqs. "
        f"Available algorithms: {', '.join(available)}"
    )


ALGORITHM = resolve_algorithm(PREFERRED_ALGORITHM)


def _document_digest(pdf_bytes: bytes) -> bytes:
    if not isinstance(pdf_bytes, bytes):
        raise TypeError("pdf_bytes must be bytes")

    return hashlib.sha256(pdf_bytes).digest()


def generate_keypair(algorithm: str = ALGORITHM) -> tuple[bytes, bytes]:
    """
    Generate a FALCON key pair.

    Returns:
        (public_key, private_key)
    """
    _require_oqs()
    resolved_algorithm = resolve_algorithm(algorithm)

    with oqs.Signature(resolved_algorithm) as signer:
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
    return _document_digest(pdf_bytes).hex()


def sign_document(
    pdf_bytes: bytes,
    private_key: bytes,
    algorithm: str = ALGORITHM,
) -> tuple[str, bytes]:
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
    if not isinstance(private_key, bytes):
        raise TypeError("private_key must be bytes")

    _require_oqs()
    resolved_algorithm = resolve_algorithm(algorithm)
    doc_hash_bytes = _document_digest(pdf_bytes)

    with oqs.Signature(resolved_algorithm, secret_key=private_key) as signer:
        signature = signer.sign(doc_hash_bytes)

    return doc_hash_bytes.hex(), signature


def verify_signature(
    doc_hash_hex: str,
    signature: bytes,
    public_key: bytes,
    algorithm: str = ALGORITHM,
) -> bool:
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
        if not isinstance(doc_hash_hex, str):
            return False
        if not isinstance(signature, bytes) or not isinstance(public_key, bytes):
            return False

        doc_hash_bytes = bytes.fromhex(doc_hash_hex)
        if len(doc_hash_bytes) != hashlib.sha256().digest_size:
            return False

        _require_oqs()
        resolved_algorithm = resolve_algorithm(algorithm)
        with oqs.Signature(resolved_algorithm) as verifier:
            return bool(verifier.verify(doc_hash_bytes, signature, public_key))

    except Exception:
        return False


def verify_document(
    pdf_bytes: bytes,
    signature: bytes,
    public_key: bytes,
    expected_hash_hex: str | None = None,
    algorithm: str = ALGORITHM,
) -> bool:
    """
    Verify a document directly by recomputing its SHA-256 hash.

    Args:
        pdf_bytes: Raw PDF/document bytes.
        signature: FALCON signature bytes.
        public_key: FALCON public key.
        expected_hash_hex: Optional expected SHA-256 hash in hex.

    Returns:
        True if the document is authentic and unchanged.
    """
    try:
        doc_hash_hex = hash_document(pdf_bytes)
        if expected_hash_hex is not None:
            if not isinstance(expected_hash_hex, str):
                return False
            expected_hash = bytes.fromhex(expected_hash_hex)
            if len(expected_hash) != hashlib.sha256().digest_size:
                return False
            if expected_hash.hex() != doc_hash_hex:
                return False

        return verify_signature(doc_hash_hex, signature, public_key, algorithm)
    except Exception:
        return False
