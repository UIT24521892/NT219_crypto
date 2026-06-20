# ML-DSA-44 vs Ed25519 vs ECDSA-P256 Benchmark Summary

ML-DSA-44 (FIPS 204) is the post-quantum primary signature. Ed25519 is the
small classical signature embedded in the self-contained offline QR. ECDSA-P256
is a classical baseline. All algorithms sign the 32-byte SHA-256 digest of the PDF.

| Algorithm | PQC | Keygen mean (ms) | Sign mean (ms) | Verify mean (ms) | Public key (B) | Signature (B) | Verify rate |
|---|:---:|---:|---:|---:|---:|---:|---:|
| ML-DSA-44 | ✔ | 0.084349 | 0.067866 | 0.026111 | 1312 | 2420 | 1.0000 |
| Ed25519 | — | 0.048837 | 0.044289 | 0.134139 | 32 | 64 | 1.0000 |
| ECDSA-P256 | — | 0.016098 | 0.028798 | 0.079522 | 91 | 71 | 1.0000 |

- Iterations: 200
- Warmup: 20
- OS: Linux-6.17.0-29-generic-x86_64-with-glibc2.39
- Python: 3.12.3 (CPython)
- cryptography: 48.0.0
- liboqs-python: 0.15.0
- liboqs: 0.15.0

Resolved liboqs mechanisms:
- ML-DSA-44: ML-DSA-44

Unavailable benchmark notes:
- None

Note: numbers depend on CPU, OS, Python version, liboqs build, and system load.
