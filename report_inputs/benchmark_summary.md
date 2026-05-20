# FALCON-512 vs ECDSA-P256 Benchmark Summary

| Algorithm | Keygen mean (ms) | Sign mean (ms) | Verify mean (ms) | Public key (B) | Signature (B) | Verify success rate |
|---|---:|---:|---:|---:|---:|---:|
| FALCON-512 | 6.748589 | 0.204934 | 0.039381 | 897 | 654 | 1.0000 |
| ECDSA-P256 | 0.013230 | 0.023947 | 0.064125 | 91 | 71 | 1.0000 |

- Iterations: 20
- Warmup: 3
- OS: Linux-6.17.0-23-generic-x86_64-with-glibc2.39
- Python: 3.12.3 (CPython)
- cryptography: 48.0.0
- liboqs-python: 0.15.0
- liboqs: 0.15.0

Resolved liboqs mechanisms:
- FALCON-512: Falcon-512

Unavailable benchmark notes:
- None

Note: Benchmark numbers depend on CPU, OS, Python version, liboqs build, and current system load.
