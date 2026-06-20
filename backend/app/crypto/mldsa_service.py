"""
Citizen Services Portal — ML-DSA-44 signing service (FIPS 204, primary layer).

ML-DSA-44 (CRYSTALS-Dilithium, NIST FIPS 204) is the post-quantum signature used
as the *primary* integrity + non-repudiation layer. Signatures (~2420 B) are too
large for a QR code, so they are stored in the DB / embedded in PDF metadata and
verified online. The small offline QR layer is handled separately by
``ed25519_qr_service``.

This module is self-contained (primitives + server-key async layer) and exposes
the interface the backend expects so ``documents.py`` / ``verify.py`` only swap
the import path:

    sign_document(pdf_bytes, private_key)          -> (doc_hash_hex, signature)
    verify_document(pdf_bytes, signature, pubkey)  -> bool
    verify_signature(doc_hash_hex, sig, pubkey)    -> bool
    sign_document_async(pdf_bytes)                 -> (signature, public_key)
    get_public_key()                               -> bytes

The system signs the SHA-256 hash of the document, not the whole PDF directly.
The server holds one fixed ML-DSA keypair: the private key is stored AES-256-GCM
encrypted (``backend/keys/mldsa_private.enc.json``) and the public key raw
(``backend/keys/mldsa_public.bin``). The keypair is cached in RAM after first load.
"""
import asyncio
import hashlib
from pathlib import Path
from typing import Final, Tuple

try:
    import oqs
except ImportError:  # pragma: no cover - exercised only when dependency is absent.
    oqs = None  # type: ignore[assignment]


PREFERRED_ALGORITHM: Final[str] = "ML-DSA-44"
# liboqs >= 0.10 exposes the FIPS 204 name "ML-DSA-44". Older builds only shipped
# the round-3 name "Dilithium2"; map to it as a best-effort fallback.
_NORMALIZED_MLDSA_NAMES: Final[dict[str, tuple[str, ...]]] = {
    "ml-dsa-44": ("ML-DSA-44", "Dilithium2"),
    "ml-dsa-65": ("ML-DSA-65", "Dilithium3"),
    "ml-dsa-87": ("ML-DSA-87", "Dilithium5"),
}


def _normalise_algorithm_name(name: str) -> str:
    return name.replace("_", "-").casefold()


def _require_oqs() -> None:
    if oqs is None:
        raise RuntimeError(
            "liboqs-python is required for ML-DSA signing. Install liboqs-python "
            "and ensure the liboqs shared library is available."
        )


def available_signature_algorithms() -> list[str]:
    """Return enabled liboqs signature mechanism names."""

    if oqs is None:
        return []

    return list(oqs.get_enabled_sig_mechanisms())


def resolve_algorithm(preferred: str = PREFERRED_ALGORITHM) -> str:
    """Resolve a project algorithm name to the exact enabled liboqs mechanism name."""

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

    for alias in _NORMALIZED_MLDSA_NAMES.get(preferred_normalised, ()):
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
    """Generate an ML-DSA key pair. Returns ``(public_key, private_key)``."""

    _require_oqs()
    resolved_algorithm = resolve_algorithm(algorithm)

    with oqs.Signature(resolved_algorithm) as signer:
        public_key = signer.generate_keypair()
        private_key = signer.export_secret_key()

    return public_key, private_key


def hash_document(pdf_bytes: bytes) -> str:
    """Compute the SHA-256 hash of raw document bytes (hex)."""

    return _document_digest(pdf_bytes).hex()


def sign_document(
    pdf_bytes: bytes,
    private_key: bytes,
    algorithm: str = ALGORITHM,
) -> tuple[str, bytes]:
    """
    Sign the SHA-256 hash of a document using ML-DSA with a given private key
    (offline / test path). Returns ``(doc_hash_hex, signature_bytes)``.
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
    """Verify an ML-DSA signature over a SHA-256 document hash (hex)."""

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
    """Verify a document directly by recomputing its SHA-256 hash."""

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


# --------------------------------------------------------------------------- #
# Server keypair (online / deploy path) — cached in RAM, loaded lazily.
# --------------------------------------------------------------------------- #

from . import key_manager as km  # noqa: E402  (placed here to avoid import cycle at top)

_KEYS_DIR = Path(__file__).resolve().parent.parent.parent / "keys"
_PRIVATE_KEY_PATH = _KEYS_DIR / "mldsa_private.enc.json"
_PUBLIC_KEY_PATH = _KEYS_DIR / "mldsa_public.bin"

_keypair_cache: Tuple[bytes, bytes] | None = None  # (public_key, private_key)
_async_lock: asyncio.Lock | None = None


def _get_lock() -> asyncio.Lock:
    global _async_lock
    if _async_lock is None:
        _async_lock = asyncio.Lock()
    return _async_lock


def _blocking_load_or_create_keys() -> Tuple[bytes, bytes]:
    """CPU-bound key load/generate — runs in a thread pool executor."""
    return km.ensure_mldsa_keypair(_PRIVATE_KEY_PATH, _PUBLIC_KEY_PATH)


async def _load_or_create_keys() -> Tuple[bytes, bytes]:
    """Return the server ``(public_key, private_key)``; load+decrypt once, cache in RAM."""

    global _keypair_cache
    if _keypair_cache is not None:
        return _keypair_cache

    async with _get_lock():
        if _keypair_cache is not None:
            return _keypair_cache
        loop = asyncio.get_running_loop()
        public_key, private_key = await loop.run_in_executor(
            None, _blocking_load_or_create_keys
        )
        _keypair_cache = (public_key, private_key)
        return _keypair_cache


def get_public_key() -> bytes:
    """Sync getter — only safe after keys are cached. Use for offline scripts."""

    if _keypair_cache is None:
        raise RuntimeError("Keys not loaded yet; call sign_document_async first")
    public_key, _ = _keypair_cache
    return public_key


async def sign_document_async(
    pdf_bytes: bytes,
    algorithm: str = ALGORITHM,
) -> Tuple[bytes, bytes]:
    """
    Sign a document with the server ML-DSA keypair (online / deploy path).
    Loads/creates keys lazily; offloads CPU work to a thread pool.
    Returns ``(signature, public_key)``.
    """

    public_key, private_key = await _load_or_create_keys()
    loop = asyncio.get_running_loop()
    _doc_hash_hex, signature = await loop.run_in_executor(
        None, lambda: sign_document(pdf_bytes, private_key, algorithm)
    )
    return signature, public_key
