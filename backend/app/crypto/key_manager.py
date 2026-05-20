"""Encrypted file-based admin key storage for the crypto demo."""

from __future__ import annotations

import base64
import binascii
import json
import os
import time
from pathlib import Path
from typing import Any, Final

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from backend.app.crypto.falcon_service import ALGORITHM, generate_keypair, resolve_algorithm


KEY_PASSPHRASE_ENV: Final[str] = "KEY_PASSPHRASE"
PRIVATE_KEY_METADATA_VERSION: Final[int] = 1
KDF_NAME: Final[str] = "PBKDF2HMAC-SHA256"
KDF_ITERATIONS: Final[int] = 1_200_000
SALT_BYTES: Final[int] = 16
AES_GCM_NONCE_BYTES: Final[int] = 12
AES_KEY_BYTES: Final[int] = 32


def _b64_encode(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _b64_decode(value: Any, field_name: str) -> bytes:
    if not isinstance(value, str):
        raise RuntimeError(f"Invalid encrypted key file: {field_name} must be a string")

    try:
        return base64.b64decode(value.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError) as exc:
        raise RuntimeError(f"Invalid encrypted key file: {field_name} is not base64") from exc


def _private_key_aad(version: int, algorithm: str) -> bytes:
    return f"admin-falcon-private-key:v{version}:{algorithm}".encode("utf-8")


def _derive_aes_key(
    passphrase: bytes,
    salt: bytes,
    iterations: int = KDF_ITERATIONS,
) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_BYTES,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(passphrase)


def _prepare_private_path(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass


def get_key_passphrase() -> bytes:
    """
    Return the admin key passphrase from ``KEY_PASSPHRASE``.

    The passphrase is intentionally read only from the environment so it is not
    committed, stored in the database, or hardcoded in source.
    """

    passphrase = os.environ.get(KEY_PASSPHRASE_ENV)
    if not passphrase:
        raise RuntimeError(
            f"{KEY_PASSPHRASE_ENV} environment variable is required for admin key storage"
        )

    return passphrase.encode("utf-8")


def derive_aes_key(passphrase: bytes, salt: bytes) -> bytes:
    """Derive a 32-byte AES key from a passphrase and salt using PBKDF2-HMAC-SHA256."""

    if not isinstance(passphrase, bytes):
        raise TypeError("passphrase must be bytes")
    if not isinstance(salt, bytes):
        raise TypeError("salt must be bytes")

    return _derive_aes_key(passphrase, salt)


def save_encrypted_private_key(
    private_key: bytes,
    path: str | Path,
    algorithm: str = "FALCON-512",
) -> None:
    """Encrypt and save an admin FALCON private key using AES-256-GCM."""

    if not isinstance(private_key, bytes):
        raise TypeError("private_key must be bytes")

    private_path = Path(path)
    _prepare_private_path(private_path)

    version = PRIVATE_KEY_METADATA_VERSION
    salt = os.urandom(SALT_BYTES)
    nonce = os.urandom(AES_GCM_NONCE_BYTES)
    passphrase = get_key_passphrase()
    aes_key = derive_aes_key(passphrase, salt)
    ciphertext = AESGCM(aes_key).encrypt(
        nonce,
        private_key,
        _private_key_aad(version, algorithm),
    )

    payload = {
        "version": version,
        "kdf": KDF_NAME,
        "kdf_iterations": KDF_ITERATIONS,
        "salt": _b64_encode(salt),
        "nonce": _b64_encode(nonce),
        "ciphertext": _b64_encode(ciphertext),
        "created_at": int(time.time()),
        "algorithm": algorithm,
    }

    temp_path = private_path.with_name(f"{private_path.name}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    try:
        temp_path.chmod(0o600)
    except OSError:
        pass
    temp_path.replace(private_path)
    try:
        private_path.chmod(0o600)
    except OSError:
        pass


def load_encrypted_private_key(path: str | Path) -> bytes:
    """Load and decrypt an AES-256-GCM encrypted admin private key."""

    private_path = Path(path)
    try:
        payload = json.loads(private_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Encrypted private key file not found: {private_path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid encrypted key file JSON: {private_path}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError("Invalid encrypted key file: root value must be an object")

    version = payload.get("version")
    if version != PRIVATE_KEY_METADATA_VERSION:
        raise RuntimeError(f"Unsupported encrypted key version: {version!r}")

    if payload.get("kdf") != KDF_NAME:
        raise RuntimeError(f"Unsupported encrypted key KDF: {payload.get('kdf')!r}")

    iterations = payload.get("kdf_iterations", KDF_ITERATIONS)
    if not isinstance(iterations, int) or iterations <= 0:
        raise RuntimeError("Invalid encrypted key file: kdf_iterations must be positive")

    algorithm = payload.get("algorithm")
    if not isinstance(algorithm, str) or not algorithm:
        raise RuntimeError("Invalid encrypted key file: algorithm must be a non-empty string")

    salt = _b64_decode(payload.get("salt"), "salt")
    nonce = _b64_decode(payload.get("nonce"), "nonce")
    ciphertext = _b64_decode(payload.get("ciphertext"), "ciphertext")
    passphrase = get_key_passphrase()
    aes_key = _derive_aes_key(passphrase, salt, iterations)

    try:
        return AESGCM(aes_key).decrypt(
            nonce,
            ciphertext,
            _private_key_aad(version, algorithm),
        )
    except Exception as exc:
        raise RuntimeError("Failed to decrypt admin private key") from exc


def save_public_key(public_key: bytes, path: str | Path) -> None:
    """Save a public key as raw bytes."""

    if not isinstance(public_key, bytes):
        raise TypeError("public_key must be bytes")

    public_path = Path(path)
    public_path.parent.mkdir(parents=True, exist_ok=True)
    public_path.write_bytes(public_key)


def load_public_key(path: str | Path) -> bytes:
    """Load a raw public key from disk."""

    public_path = Path(path)
    try:
        return public_path.read_bytes()
    except FileNotFoundError as exc:
        raise RuntimeError(f"Public key file not found: {public_path}") from exc


def ensure_admin_keypair(
    private_path: str | Path,
    public_path: str | Path,
) -> tuple[bytes, bytes]:
    """
    Load the admin keypair if both files exist, otherwise generate and save one.

    Returns:
        (public_key, private_key)
    """

    private_key_path = Path(private_path)
    public_key_path = Path(public_path)
    private_exists = private_key_path.exists()
    public_exists = public_key_path.exists()

    if private_exists and public_exists:
        return load_public_key(public_key_path), load_encrypted_private_key(private_key_path)

    if private_exists != public_exists:
        raise RuntimeError(
            "Admin keypair is incomplete. Refusing to overwrite only one key file."
        )

    resolved_algorithm = resolve_algorithm(ALGORITHM)
    public_key, private_key = generate_keypair(resolved_algorithm)
    save_encrypted_private_key(private_key, private_key_path, resolved_algorithm)
    save_public_key(public_key, public_key_path)
    return public_key, private_key
