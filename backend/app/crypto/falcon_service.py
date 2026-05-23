"""
Citizen Services Portal — FALCON-512 signing service (adapter v2).

Boc 2 module cua Member A:
  - falcon_primitives.py : primitives FALCON dung liboqs (sign/verify SHA-256 hash)
  - key_manager.py       : luu private key MA HOA AES-256-GCM (PBKDF2-HMAC-SHA256),
                           passphrase tu env KEY_PASSPHRASE

va expose interface ma backend mong doi (documents.py / verify.py khong doi):

    sign_document(pdf_bytes)                       -> (signature, public_key)
    verify_signature(pdf_bytes, signature, pubkey) -> bool
    get_public_key()                               -> bytes

Key management: server co 1 keypair FALCON co dinh. Lan dau ensure_admin_keypair()
sinh keypair, luu private key MA HOA (backend/keys/falcon_private.enc.json) +
public key raw (backend/keys/falcon_public.bin). Cac lan sau load + giai ma lai.
Cache trong RAM (co Lock) de khoi giai ma moi request.
"""
from pathlib import Path
from threading import Lock
from typing import Tuple

from app.crypto import falcon_primitives as fp
from app.crypto import key_manager as km

# keys/ nam o backend/keys/ (cung cap voi app/)
_KEYS_DIR = Path(__file__).resolve().parent.parent.parent / "keys"
_PRIVATE_KEY_PATH = _KEYS_DIR / "falcon_private.enc.json"
_PUBLIC_KEY_PATH = _KEYS_DIR / "falcon_public.bin"

_keypair_cache: Tuple[bytes, bytes] | None = None  # (public_key, private_key)
_lock = Lock()


def _load_or_create_keys() -> Tuple[bytes, bytes]:
    """
    Tra ve (public_key, private_key) cua server.

    Lan dau: ensure_admin_keypair sinh keypair, luu private key ma hoa + public raw.
    Cac lan sau: load + giai ma. Cache trong RAM.
    """
    global _keypair_cache
    if _keypair_cache is not None:
        return _keypair_cache

    with _lock:
        if _keypair_cache is not None:
            return _keypair_cache
        # ensure_admin_keypair tra ve (public_key, private_key)
        public_key, private_key = km.ensure_admin_keypair(
            _PRIVATE_KEY_PATH, _PUBLIC_KEY_PATH
        )
        _keypair_cache = (public_key, private_key)
        return _keypair_cache


def get_public_key() -> bytes:
    """Tra ve FALCON public key cua server (897 bytes voi Falcon-512)."""
    public_key, _ = _load_or_create_keys()
    return public_key


def sign_document(pdf_bytes: bytes) -> Tuple[bytes, bytes]:
    """
    Ky document bang private key cua server.

    A's sign_document(pdf_bytes, private_key) -> (doc_hash_hex, signature).
    Adapter dung private key da giai ma, tra (signature, public_key) cho backend.
    """
    public_key, private_key = _load_or_create_keys()
    _doc_hash_hex, signature = fp.sign_document(pdf_bytes, private_key)
    return signature, public_key


def verify_signature(pdf_bytes: bytes, signature: bytes, public_key: bytes) -> bool:
    """
    Verify chu ky FALCON tren document.

    Dung A's verify_document (tu recompute SHA-256 hash cua pdf roi verify).
    True neu hop le (document khong bi sua), False neu sai/tampered.
    """
    return fp.verify_document(pdf_bytes, signature, public_key)
