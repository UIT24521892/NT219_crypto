# Crypto Implementation Notes

## Implemented Files

- `backend/app/crypto/mldsa_service.py`: ML-DSA-44 (CRYSTALS-Dilithium, FIPS 204) signing helpers over `SHA-256(pdf_bytes)` using liboqs-python `oqs.Signature`. This is the primary post-quantum layer (sig ~2420 B, public key ~1312 B), verified online / from PDF metadata.
- `backend/app/crypto/ed25519_qr_service.py`: classical Ed25519 (64-byte signature, 32-byte public key) for the self-contained offline QR. Ed25519 is NOT post-quantum; it is an offline-UX convenience while ML-DSA-44 provides the quantum-resistance guarantee.
- `backend/app/crypto/key_manager.py`: encrypted file-based admin key storage using AES-256-GCM and a key derived from `KEY_PASSPHRASE`.
- `backend/app/crypto/qr_builder.py`: compact deterministic JSON payload builder/parser for the offline verification package (`alg` = `ML-DSA-44`).
- `scripts/benchmark.py`: CSV benchmark for FALCON-512, FALCON-1024 when available, Dilithium2/ML-DSA-44 equivalent when available, and ECDSA-P256 (comparison across families).
- `scripts/benchmark_mldsa_ed25519_ecdsa.py`: final report benchmark for the hybrid scheme — ML-DSA-44 (PQC), Ed25519 (offline QR) and the ECDSA-P256 classical baseline.
- `scripts/verify_qr.py`: offline CLI verifier for the verification-package payload JSON, PDF bytes, and raw ML-DSA-44 public key bytes.
- `scripts/attack_forgery.py`: demo showing that a tampered PDF fails signature verification.
- `scripts/attack_replay.py`: demo showing that an expired QR payload is rejected as replay.
- `tests/`: focused pytest coverage for ML-DSA-44 signing, the Ed25519 hybrid QR, encrypted key storage, QR payload encoding, and benchmark row helpers.

## Official Sources Used

- Open Quantum Safe liboqs official repository and documentation: <https://github.com/open-quantum-safe/liboqs>, <https://openquantumsafe.org/liboqs/>
- liboqs-python official repository and examples: <https://github.com/open-quantum-safe/liboqs-python>
- NIST FIPS 204 (ML-DSA / CRYSTALS-Dilithium) standard: <https://csrc.nist.gov/pubs/fips/204/final>
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

The service signs the SHA-256 digest of the PDF bytes, not the full PDF bytes directly. `mldsa_service.sign_document()` computes `hashlib.sha256(pdf_bytes).digest()` and signs that 32-byte digest with `oqs.Signature` (ML-DSA-44). The returned document hash is the same digest encoded as a lowercase hex string.

## Algorithm Choices (Hybrid)

The primary signature is ML-DSA-44 (CRYSTALS-Dilithium, NIST FIPS 204): a Module-LWE/SIS lattice scheme with ~2420-byte signatures and ~1312-byte public keys. Because that signature is far too large to fit in a scannable QR code, the verification-package payload (`"alg":"ML-DSA-44"`) is verified online or from the PDF metadata rather than from a raw QR.

For genuinely offline, on-the-spot verification the project embeds a *separate* self-contained QR carrying a classical Ed25519 signature (64 bytes, 32-byte public key). The small size is exactly why Ed25519 was chosen for the QR layer. Honesty note for the report: Ed25519 is NOT post-quantum — it is an offline-UX convenience only; the real post-quantum guarantee remains ML-DSA-44. (The earlier design used FALCON-512, an NTRU-lattice scheme with ~652-byte signatures, but the system now standardizes on ML-DSA-44 for the FIPS-204-compliant PQC layer and Ed25519 for the compact offline QR.)

## Admin Key Protection

Admin private keys are never stored in plaintext by `key_manager.py`. The private key is encrypted at rest with AES-256-GCM. The AES key is derived from the `KEY_PASSPHRASE` environment variable using PBKDF2-HMAC-SHA256 with a random salt. Each saved key file also uses a random AES-GCM nonce and stores the metadata needed to decrypt later: version, KDF name, KDF iterations, salt, nonce, ciphertext, creation timestamp, and algorithm. The private key file is chmod `600` where the OS supports it.

The passphrase is not hardcoded and is not read from source files. Generated keys, `.env` files, and benchmark output are ignored by git.

## Commands

```bash
python -m pytest tests/test_mldsa.py tests/test_qr_hybrid.py tests/test_key_manager.py tests/test_qr_builder.py -q
python scripts/benchmark.py --iterations 20
python scripts/benchmark_mldsa_ed25519_ecdsa.py --iterations 20 --warmup 3
python scripts/attack_forgery.py
python scripts/attack_replay.py
```
