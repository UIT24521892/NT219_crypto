import json
import os
import stat

import pytest

from backend.app.crypto import key_manager


def test_encrypted_private_key_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("KEY_PASSPHRASE", "test-passphrase")
    private_key = b"demo-falcon-private-key"
    private_path = tmp_path / "keys" / "admin_private.key.enc"

    key_manager.save_encrypted_private_key(private_key, private_path)
    encrypted = private_path.read_bytes()

    assert private_key not in encrypted
    payload = json.loads(encrypted.decode("utf-8"))
    assert payload["version"] == 1
    assert payload["kdf"] == key_manager.KDF_NAME
    assert payload["algorithm"] == "FALCON-512"
    assert key_manager.load_encrypted_private_key(private_path) == private_key

    if os.name == "posix":
        assert stat.S_IMODE(private_path.stat().st_mode) == 0o600


def test_key_manager_fails_when_key_passphrase_missing(monkeypatch, tmp_path):
    monkeypatch.delenv("KEY_PASSPHRASE", raising=False)

    with pytest.raises(RuntimeError, match="KEY_PASSPHRASE"):
        key_manager.get_key_passphrase()

    with pytest.raises(RuntimeError, match="KEY_PASSPHRASE"):
        key_manager.save_encrypted_private_key(b"private", tmp_path / "private.key.enc")


def test_public_key_roundtrip(tmp_path):
    public_key = b"demo-falcon-public-key"
    public_path = tmp_path / "keys" / "admin_public.key"

    key_manager.save_public_key(public_key, public_path)

    assert key_manager.load_public_key(public_path) == public_key


def test_ensure_admin_keypair_generates_and_loads(tmp_path, monkeypatch):
    monkeypatch.setenv("KEY_PASSPHRASE", "test-passphrase")
    monkeypatch.setattr(
        key_manager,
        "generate_keypair",
        lambda algorithm=key_manager.ALGORITHM: (b"public-key", b"private-key"),
    )
    monkeypatch.setattr(
        key_manager,
        "resolve_algorithm",
        lambda preferred=key_manager.ALGORITHM: "FALCON-512",
    )

    private_path = tmp_path / "keys" / "admin_private.key.enc"
    public_path = tmp_path / "keys" / "admin_public.key"

    assert key_manager.ensure_admin_keypair(private_path, public_path) == (
        b"public-key",
        b"private-key",
    )
    assert key_manager.ensure_admin_keypair(private_path, public_path) == (
        b"public-key",
        b"private-key",
    )
