# Full Signature Benchmark Summary

This is a cross-family comparison benchmark. The system's chosen primary
signature is ML-DSA-44 (CRYSTALS-Dilithium, NIST FIPS 204, Module-LWE/SIS
lattice; sig ~2420 B, public key ~1312 B), verified online / from PDF metadata;
the offline QR layer uses a small classical Ed25519 signature (not shown here).
FALCON-512/1024 (NTRU lattice) rows are included only for comparison — they are
not the deployed scheme. ECDSA-P256 is a classical baseline.

| Algorithm | Keygen (ms) | Sign (ms) | Verify (ms) | Public key (B) | Private key (B) | Signature (B) | Available |
|---|---:|---:|---:|---:|---:|---:|---|
| Falcon-512 | 7.196 | 0.216 | 0.051 | 897 | 1281 | 655 | true |
| Falcon-1024 | 21.012 | 0.407 | 0.079 | 1793 | 2305 | 1269 | true |
| ML-DSA-44 | 0.558 | 0.042 | 0.018 | 1312 | 2560 | 2420 | true |
| ECDSA-P256 | 0.049 | 0.036 | 0.057 | 91 | 138 | 72 | true |

- Iterations: 20
- OS: Linux-6.17.0-29-generic-x86_64-with-glibc2.39
- CPU: x86_64
- Python: 3.12.3 (CPython)
- cryptography: 48.0.0
- liboqs-python: 0.15.0
- liboqs: 0.15.0
