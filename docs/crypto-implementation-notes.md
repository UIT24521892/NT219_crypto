# Crypto Implementation Notes

## Implemented Files

- `backend/app/crypto/falcon_service.py`: FALCON signing helpers over `SHA-256(pdf_bytes)` using liboqs-python `oqs.Signature`.
- `backend/app/crypto/key_manager.py`: encrypted file-based admin key storage using AES-256-GCM and a key derived from `KEY_PASSPHRASE`.
- `backend/app/crypto/qr_builder.py`: compact deterministic JSON payload builder/parser for offline QR verification.
- `scripts/benchmark.py`: CSV benchmark for FALCON-512, FALCON-1024 when available, Dilithium2/ML-DSA equivalent when available, and ECDSA-P256.
- `scripts/benchmark_falcon_ecdsa.py`: final report benchmark for only FALCON-512 and ECDSA-P256.
- `scripts/verify_qr.py`: offline CLI verifier for QR payload JSON, PDF bytes, and raw FALCON public key bytes.
- `scripts/attack_forgery.py`: demo showing that a tampered PDF fails QR signature verification.
- `scripts/attack_replay.py`: demo showing that an expired QR payload is rejected as replay.
- `tests/`: focused pytest coverage for Falcon signing, encrypted key storage, QR payload encoding, and benchmark row helpers.

## Official Sources Used

- Open Quantum Safe liboqs official repository and documentation: <https://github.com/open-quantum-safe/liboqs>, <https://openquantumsafe.org/liboqs/>
- liboqs-python official repository and examples: <https://github.com/open-quantum-safe/liboqs-python>
- FALCON official specification site: <https://falcon-sign.info/>
- Python `hashlib` documentation for SHA-256 digest/hexdigest: <https://docs.python.org/3/library/hashlib.html>
- Python `base64` documentation for URL-safe Base64: <https://docs.python.org/3/library/base64.html>
- Python `json` documentation for compact `separators=(",", ":")` JSON: <https://docs.python.org/3/library/json.html>
- PyCA cryptography AES-GCM documentation: <https://cryptography.io/en/latest/hazmat/primitives/aead/>
- PyCA cryptography PBKDF2HMAC documentation: <https://cryptography.io/en/latest/hazmat/primitives/key-derivation-functions/#pbkdf2>
- PyCA cryptography elliptic curve/ECDSA documentation: <https://cryptography.io/en/latest/hazmat/primitives/asymmetric/ec/>
- pytest official documentation for `tmp_path` and `monkeypatch`: <https://docs.pytest.org/en/stable/>

## Dependency Note

`backend/requirements.txt` lists `liboqs-python`, the official Python wrapper that imports as `oqs`. The liboqs C shared library is still the underlying Open Quantum Safe dependency for Ubuntu 22.04 bare-metal deployment and should be installed/configured according to the official liboqs and liboqs-python documentation, without Docker.

## Signing Model

The service signs the SHA-256 digest of the PDF bytes, not the full PDF bytes directly. `falcon_service.sign_document()` computes `hashlib.sha256(pdf_bytes).digest()` and signs that 32-byte digest with `oqs.Signature`. The returned document hash is the same digest encoded as a lowercase hex string.

## QR Algorithm Choice

The demo QR payload uses `"alg":"FALCON-512"` because it is the main project algorithm and has smaller signatures than FALCON-1024. The official FALCON site lists Falcon-512 signatures as 666 bytes and Falcon-1024 signatures as 1280 bytes, so Falcon-512 is the better fit for compact QR payloads.

## Admin Key Protection

Admin private keys are never stored in plaintext by `key_manager.py`. The private key is encrypted at rest with AES-256-GCM. The AES key is derived from the `KEY_PASSPHRASE` environment variable using PBKDF2-HMAC-SHA256 with a random salt. Each saved key file also uses a random AES-GCM nonce and stores the metadata needed to decrypt later: version, KDF name, KDF iterations, salt, nonce, ciphertext, creation timestamp, and algorithm. The private key file is chmod `600` where the OS supports it.

The passphrase is not hardcoded and is not read from source files. Generated keys, `.env` files, and benchmark output are ignored by git.

## Commands

```bash
python -m pytest tests/test_falcon.py tests/test_key_manager.py tests/test_qr_builder.py -q
python scripts/benchmark.py --iterations 20
python scripts/benchmark_falcon_ecdsa.py --iterations 20 --warmup 3
python scripts/attack_forgery.py
python scripts/attack_replay.py
```
