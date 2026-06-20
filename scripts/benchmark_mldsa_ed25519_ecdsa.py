#!/usr/bin/env python3
"""Benchmark ML-DSA-44 (FIPS 204), Ed25519 and ECDSA-P256 for report inputs.

ML-DSA-44 is the post-quantum primary signature (liboqs). Ed25519 is the small
64-byte classical signature carried in the self-contained offline QR. ECDSA-P256
is kept as a classical baseline for comparison. All three sign the SHA-256 digest
of a sample PDF (32 bytes), matching the production sign flow.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import platform
import time
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from statistics import mean, median, pstdev

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

try:
    import oqs
except ImportError:  # pragma: no cover - depends on local environment.
    oqs = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = "report_inputs"

MLDSA_LABEL = "ML-DSA-44"
ED25519_LABEL = "Ed25519"
ECDSA_LABEL = "ECDSA-P256"
MLDSA_CANDIDATES = ("ML-DSA-44", "Dilithium2")

SAMPLE_PDF_BYTES = b"%PDF-1.4\nNT219 citizen service benchmark document\n"
SAMPLE_DIGEST = hashlib.sha256(SAMPLE_PDF_BYTES).digest()

CSV_COLUMNS = [
    "algorithm",
    "operation",
    "iterations",
    "mean_ms",
    "median_ms",
    "min_ms",
    "max_ms",
    "std_ms",
    "public_key_size_bytes",
    "signature_size_bytes",
    "verify_success_rate",
]


@dataclass(frozen=True)
class AlgorithmBenchmark:
    algorithm: str
    keygen_ns: list[int]
    sign_ns: list[int]
    verify_ns: list[int]
    public_key_size_bytes: int | None
    signature_size_bytes: int | None
    verify_success_rate: float | None
    mechanism: str | None = None
    unavailable_reason: str | None = None
    post_quantum: bool = False


def ns_to_ms(value_ns: int) -> float:
    return value_ns / 1_000_000


def format_ms(value: float | None) -> str:
    return "" if value is None else f"{value:.6f}"


def format_int(value: int | None) -> str:
    return "" if value is None else str(value)


def format_rate(value: float | None) -> str:
    return "" if value is None else f"{value:.4f}"


def operation_stats(values_ns: list[int]) -> dict[str, str]:
    if not values_ns:
        return {k: "" for k in ("mean_ms", "median_ms", "min_ms", "max_ms", "std_ms")}
    values_ms = [ns_to_ms(v) for v in values_ns]
    return {
        "mean_ms": format_ms(mean(values_ms)),
        "median_ms": format_ms(median(values_ms)),
        "min_ms": format_ms(min(values_ms)),
        "max_ms": format_ms(max(values_ms)),
        "std_ms": format_ms(pstdev(values_ms) if len(values_ms) > 1 else 0.0),
    }


def normalize(name: str) -> str:
    return name.replace("_", "-").casefold()


def resolve_mldsa() -> str | None:
    if oqs is None:
        return None
    enabled = list(oqs.get_enabled_sig_mechanisms())
    for candidate in MLDSA_CANDIDATES:
        if candidate in enabled:
            return candidate
    by_norm = {normalize(m): m for m in enabled}
    for candidate in MLDSA_CANDIDATES:
        resolved = by_norm.get(normalize(candidate))
        if resolved:
            return resolved
    return None


def unavailable(label: str, reason: str) -> AlgorithmBenchmark:
    return AlgorithmBenchmark(
        algorithm=label, keygen_ns=[], sign_ns=[], verify_ns=[],
        public_key_size_bytes=None, signature_size_bytes=None,
        verify_success_rate=None, unavailable_reason=reason,
    )


def benchmark_mldsa(iterations: int, warmup: int) -> AlgorithmBenchmark:
    if oqs is None:
        return unavailable(MLDSA_LABEL, "Python module oqs is not installed")
    mechanism = resolve_mldsa()
    if mechanism is None:
        return unavailable(MLDSA_LABEL, "ML-DSA-44/Dilithium2 is not enabled by liboqs")

    for _ in range(warmup):
        with oqs.Signature(mechanism) as signer:
            public_key = signer.generate_keypair()
            private_key = signer.export_secret_key()
        with oqs.Signature(mechanism, secret_key=private_key) as signer:
            signature = signer.sign(SAMPLE_DIGEST)
        with oqs.Signature(mechanism) as verifier:
            verifier.verify(SAMPLE_DIGEST, signature, public_key)

    keygen_ns: list[int] = []
    public_key = private_key = b""
    for _ in range(iterations):
        started = time.perf_counter_ns()
        with oqs.Signature(mechanism) as signer:
            public_key = signer.generate_keypair()
            private_key = signer.export_secret_key()
        keygen_ns.append(time.perf_counter_ns() - started)

    sign_ns: list[int] = []
    signature = b""
    with oqs.Signature(mechanism, secret_key=private_key) as signer:
        for _ in range(iterations):
            started = time.perf_counter_ns()
            signature = signer.sign(SAMPLE_DIGEST)
            sign_ns.append(time.perf_counter_ns() - started)

    verify_ns: list[int] = []
    success = 0
    with oqs.Signature(mechanism) as verifier:
        for _ in range(iterations):
            started = time.perf_counter_ns()
            is_valid = bool(verifier.verify(SAMPLE_DIGEST, signature, public_key))
            verify_ns.append(time.perf_counter_ns() - started)
            success += int(is_valid)

    return AlgorithmBenchmark(
        algorithm=MLDSA_LABEL, keygen_ns=keygen_ns, sign_ns=sign_ns, verify_ns=verify_ns,
        public_key_size_bytes=len(public_key), signature_size_bytes=len(signature),
        verify_success_rate=success / iterations, mechanism=mechanism, post_quantum=True,
    )


def benchmark_ed25519(iterations: int, warmup: int) -> AlgorithmBenchmark:
    for _ in range(warmup):
        key = Ed25519PrivateKey.generate()
        sig = key.sign(SAMPLE_DIGEST)
        key.public_key().verify(sig, SAMPLE_DIGEST)

    keygen_ns: list[int] = []
    key: Ed25519PrivateKey | None = None
    for _ in range(iterations):
        started = time.perf_counter_ns()
        key = Ed25519PrivateKey.generate()
        keygen_ns.append(time.perf_counter_ns() - started)
    assert key is not None

    public_key = key.public_key()
    public_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )

    sign_ns: list[int] = []
    signature = b""
    for _ in range(iterations):
        started = time.perf_counter_ns()
        signature = key.sign(SAMPLE_DIGEST)
        sign_ns.append(time.perf_counter_ns() - started)

    verify_ns: list[int] = []
    success = 0
    for _ in range(iterations):
        started = time.perf_counter_ns()
        try:
            public_key.verify(signature, SAMPLE_DIGEST)
            is_valid = True
        except InvalidSignature:
            is_valid = False
        verify_ns.append(time.perf_counter_ns() - started)
        success += int(is_valid)

    return AlgorithmBenchmark(
        algorithm=ED25519_LABEL, keygen_ns=keygen_ns, sign_ns=sign_ns, verify_ns=verify_ns,
        public_key_size_bytes=len(public_raw), signature_size_bytes=len(signature),
        verify_success_rate=success / iterations,
    )


def _ecdsa_alg() -> ec.ECDSA:
    return ec.ECDSA(utils.Prehashed(hashes.SHA256()))


def benchmark_ecdsa(iterations: int, warmup: int) -> AlgorithmBenchmark:
    for _ in range(warmup):
        key = ec.generate_private_key(ec.SECP256R1())
        sig = key.sign(SAMPLE_DIGEST, _ecdsa_alg())
        key.public_key().verify(sig, SAMPLE_DIGEST, _ecdsa_alg())

    keygen_ns: list[int] = []
    key: ec.EllipticCurvePrivateKey | None = None
    for _ in range(iterations):
        started = time.perf_counter_ns()
        key = ec.generate_private_key(ec.SECP256R1())
        keygen_ns.append(time.perf_counter_ns() - started)
    assert key is not None

    public_key = key.public_key()
    public_der = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    sign_ns: list[int] = []
    signature = b""
    for _ in range(iterations):
        started = time.perf_counter_ns()
        signature = key.sign(SAMPLE_DIGEST, _ecdsa_alg())
        sign_ns.append(time.perf_counter_ns() - started)

    verify_ns: list[int] = []
    success = 0
    for _ in range(iterations):
        started = time.perf_counter_ns()
        try:
            public_key.verify(signature, SAMPLE_DIGEST, _ecdsa_alg())
            is_valid = True
        except InvalidSignature:
            is_valid = False
        verify_ns.append(time.perf_counter_ns() - started)
        success += int(is_valid)

    return AlgorithmBenchmark(
        algorithm=ECDSA_LABEL, keygen_ns=keygen_ns, sign_ns=sign_ns, verify_ns=verify_ns,
        public_key_size_bytes=len(public_der), signature_size_bytes=len(signature),
        verify_success_rate=success / iterations,
    )


def benchmark_all(iterations: int, warmup: int) -> list[AlgorithmBenchmark]:
    return [
        benchmark_mldsa(iterations, warmup),
        benchmark_ed25519(iterations, warmup),
        benchmark_ecdsa(iterations, warmup),
    ]


def benchmark_to_rows(result: AlgorithmBenchmark) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for operation, timings in (
        ("keygen", result.keygen_ns),
        ("sign", result.sign_ns),
        ("verify", result.verify_ns),
    ):
        row = {
            "algorithm": result.algorithm,
            "operation": operation,
            "iterations": str(len(timings)),
            "public_key_size_bytes": format_int(result.public_key_size_bytes),
            "signature_size_bytes": format_int(result.signature_size_bytes),
            "verify_success_rate": format_rate(result.verify_success_rate),
        }
        row.update(operation_stats(timings))
        rows.append(row)
    return rows


def write_csv(results: list[AlgorithmBenchmark], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows = [row for result in results for row in benchmark_to_rows(result)]
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "unavailable"


def liboqs_version() -> str:
    if oqs is None:
        return "unavailable"
    for attr_name in ("oqs_version", "get_oqs_version"):
        attr = getattr(oqs, attr_name, None)
        if callable(attr):
            try:
                return str(attr())
            except Exception:
                pass
    return "unknown"


def lookup(rows: list[dict[str, str]], algorithm: str, operation: str) -> dict[str, str] | None:
    for row in rows:
        if row["algorithm"] == algorithm and row["operation"] == operation:
            return row
    return None


def cell(row: dict[str, str] | None, key: str) -> str:
    if row is None:
        return "N/A"
    return row.get(key) or "N/A"


def write_summary(results: list[AlgorithmBenchmark], output_path: Path, iterations: int, warmup: int) -> None:
    rows = [row for result in results for row in benchmark_to_rows(result)]
    mechanisms = [f"- {r.algorithm}: {r.mechanism}" for r in results if r.mechanism]
    unavailable_notes = [
        f"- {r.algorithm}: {r.unavailable_reason}" for r in results if r.unavailable_reason
    ]
    pq_by_label = {r.algorithm: r.post_quantum for r in results}

    table_lines = [
        "| Algorithm | PQC | Keygen mean (ms) | Sign mean (ms) | Verify mean (ms) | Public key (B) | Signature (B) | Verify rate |",
        "|---|:---:|---:|---:|---:|---:|---:|---:|",
    ]
    for label in (MLDSA_LABEL, ED25519_LABEL, ECDSA_LABEL):
        keygen = lookup(rows, label, "keygen")
        sign = lookup(rows, label, "sign")
        verify = lookup(rows, label, "verify")
        table_lines.append(
            "| " + " | ".join([
                label,
                "✔" if pq_by_label.get(label) else "—",
                cell(keygen, "mean_ms"),
                cell(sign, "mean_ms"),
                cell(verify, "mean_ms"),
                cell(keygen, "public_key_size_bytes"),
                cell(sign, "signature_size_bytes"),
                cell(verify, "verify_success_rate"),
            ]) + " |"
        )

    text = "\n".join([
        "# ML-DSA-44 vs Ed25519 vs ECDSA-P256 Benchmark Summary",
        "",
        "ML-DSA-44 (FIPS 204) is the post-quantum primary signature. Ed25519 is the",
        "small classical signature embedded in the self-contained offline QR. ECDSA-P256",
        "is a classical baseline. All algorithms sign the 32-byte SHA-256 digest of the PDF.",
        "",
        *table_lines,
        "",
        f"- Iterations: {iterations}",
        f"- Warmup: {warmup}",
        f"- OS: {platform.platform()}",
        f"- Python: {platform.python_version()} ({platform.python_implementation()})",
        f"- cryptography: {package_version('cryptography')}",
        f"- liboqs-python: {package_version('liboqs-python')}",
        f"- liboqs: {liboqs_version()}",
        "",
        "Resolved liboqs mechanisms:",
        *(mechanisms or ["- N/A"]),
        "",
        "Unavailable benchmark notes:",
        *(unavailable_notes or ["- None"]),
        "",
        "Note: numbers depend on CPU, OS, Python version, liboqs build, and system load.",
        "",
    ])
    output_path.write_text(text, encoding="utf-8")


def write_notes(output_path: Path) -> None:
    text = """# Ghi Chu Report: ML-DSA-44 + Ed25519 (hybrid)

- ML-DSA-44 (CRYSTALS-Dilithium, chuẩn NIST FIPS 204) là chữ ký số hậu lượng tử
  dựa trên module lattice (Module-LWE/SIS). Đây là chữ ký chính, bảo đảm toàn vẹn
  + kháng lượng tử cho tài liệu PDF.
- Hệ thống ký SHA-256 hash của PDF (32 bytes), không ký trực tiếp toàn bộ file —
  giữ dữ liệu ký cố định và đồng nhất giữa luồng online và offline.
- Ed25519 là chữ ký cổ điển 64 bytes, đủ nhỏ để nhúng trong mã QR tự chứa và xác
  minh **offline** ngay tại chỗ (Web Crypto). Ed25519 KHÔNG hậu lượng tử — đây là
  lớp tiện ích UX; bảo đảm hậu lượng tử thật sự nằm ở ML-DSA-44.
- ECDSA-P256 đưa vào để so sánh baseline cổ điển: chữ ký ~64-72 bytes, khoá nhỏ,
  nhưng không kháng máy tính lượng tử.
- Chữ ký ML-DSA-44 ~2420 bytes và public key ~1312 bytes — lớn hơn nhiều so với
  ECDSA/Ed25519; đó là chi phí của an toàn hậu lượng tử (vì sao QR dùng Ed25519
  nhỏ gọn còn ML-DSA xác minh online/từ metadata PDF).
- Số liệu benchmark trong report lấy từ `benchmark_results.csv` /
  `benchmark_summary.md`; không nhập tay hoặc suy diễn số liệu chưa đo.
"""
    output_path.write_text(text, encoding="utf-8")


def write_report_inputs(results: list[AlgorithmBenchmark], out_dir: Path, iterations: int, warmup: int) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": out_dir / "benchmark_results.csv",
        "summary": out_dir / "benchmark_summary.md",
        "notes": out_dir / "mldsa_report_notes.md",
    }
    write_csv(results, paths["csv"])
    write_summary(results, paths["summary"], iterations, warmup)
    write_notes(paths["notes"])
    return paths


def print_console_summary(results: list[AlgorithmBenchmark], paths: dict[str, Path]) -> None:
    rows = [row for result in results for row in benchmark_to_rows(result)]
    widths = {c: max(len(c), *(len(str(row[c])) for row in rows)) for c in CSV_COLUMNS}
    print("  ".join(c.ljust(widths[c]) for c in CSV_COLUMNS))
    print("  ".join("-" * widths[c] for c in CSV_COLUMNS))
    for row in rows:
        print("  ".join(row[c].ljust(widths[c]) for c in CSV_COLUMNS))
    for result in results:
        if result.unavailable_reason:
            print(f"\nSkipped {result.algorithm}: {result.unavailable_reason}")
    print("\nSaved outputs:")
    for path in paths.values():
        print(f"- {path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark ML-DSA-44, Ed25519 and ECDSA-P256 for NT219 report inputs."
    )
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--warmup", type=int, default=10)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    args = parser.parse_args(argv)
    if args.iterations <= 0:
        parser.error("--iterations must be a positive integer")
    if args.warmup < 0:
        parser.error("--warmup must be zero or a positive integer")
    return args


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = REPO_ROOT / out_dir
    results = benchmark_all(args.iterations, args.warmup)
    paths = write_report_inputs(results, out_dir, args.iterations, args.warmup)
    print_console_summary(results, paths)


if __name__ == "__main__":
    main()
