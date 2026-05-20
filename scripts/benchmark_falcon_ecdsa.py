#!/usr/bin/env python3
"""Benchmark FALCON-512 and ECDSA-P256 for report inputs."""

from __future__ import annotations

import argparse
import csv
import hashlib
import platform
import sys
import time
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from statistics import mean, median, pstdev
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils

try:
    import oqs
except ImportError:  # pragma: no cover - depends on local environment.
    oqs = None  # type: ignore[assignment]


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT_DIR = "report_inputs"
FALCON_LABEL = "FALCON-512"
ECDSA_LABEL = "ECDSA-P256"
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


def ns_to_ms(value_ns: int) -> float:
    return value_ns / 1_000_000


def format_ms(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.6f}"


def format_int(value: int | None) -> str:
    if value is None:
        return ""
    return str(value)


def format_rate(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.4f}"


def operation_stats(values_ns: list[int]) -> dict[str, str]:
    if not values_ns:
        return {
            "mean_ms": "",
            "median_ms": "",
            "min_ms": "",
            "max_ms": "",
            "std_ms": "",
        }

    values_ms = [ns_to_ms(value) for value in values_ns]
    return {
        "mean_ms": format_ms(mean(values_ms)),
        "median_ms": format_ms(median(values_ms)),
        "min_ms": format_ms(min(values_ms)),
        "max_ms": format_ms(max(values_ms)),
        "std_ms": format_ms(pstdev(values_ms) if len(values_ms) > 1 else 0.0),
    }


def normalize_algorithm_name(name: str) -> str:
    return name.replace("_", "-").casefold()


def enabled_oqs_signature_mechanisms() -> list[str]:
    if oqs is None:
        return []
    return list(oqs.get_enabled_sig_mechanisms())


def resolve_falcon_512(enabled: list[str] | None = None) -> str | None:
    mechanisms = enabled_oqs_signature_mechanisms() if enabled is None else enabled
    candidates = ("Falcon-512", "FALCON-512")

    for candidate in candidates:
        if candidate in mechanisms:
            return candidate

    mechanisms_by_normalized = {
        normalize_algorithm_name(mechanism): mechanism for mechanism in mechanisms
    }
    for candidate in candidates:
        resolved = mechanisms_by_normalized.get(normalize_algorithm_name(candidate))
        if resolved:
            return resolved

    return None


def unavailable_benchmark(algorithm: str, reason: str) -> AlgorithmBenchmark:
    return AlgorithmBenchmark(
        algorithm=algorithm,
        keygen_ns=[],
        sign_ns=[],
        verify_ns=[],
        public_key_size_bytes=None,
        signature_size_bytes=None,
        verify_success_rate=None,
        unavailable_reason=reason,
    )


def benchmark_falcon_512(iterations: int, warmup: int) -> AlgorithmBenchmark:
    if oqs is None:
        return unavailable_benchmark(FALCON_LABEL, "Python module oqs is not installed")

    enabled = enabled_oqs_signature_mechanisms()
    mechanism = resolve_falcon_512(enabled)
    if mechanism is None:
        return unavailable_benchmark(
            FALCON_LABEL,
            "FALCON-512/Falcon-512 is not enabled by liboqs",
        )

    for _ in range(warmup):
        with oqs.Signature(mechanism) as signer:
            public_key = signer.generate_keypair()
            private_key = signer.export_secret_key()
        with oqs.Signature(mechanism, secret_key=private_key) as signer:
            signature = signer.sign(SAMPLE_DIGEST)
        with oqs.Signature(mechanism) as verifier:
            verifier.verify(SAMPLE_DIGEST, signature, public_key)

    keygen_ns: list[int] = []
    public_key = b""
    private_key = b""
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
    success_count = 0
    with oqs.Signature(mechanism) as verifier:
        for _ in range(iterations):
            started = time.perf_counter_ns()
            is_valid = bool(verifier.verify(SAMPLE_DIGEST, signature, public_key))
            verify_ns.append(time.perf_counter_ns() - started)
            success_count += int(is_valid)

    return AlgorithmBenchmark(
        algorithm=FALCON_LABEL,
        keygen_ns=keygen_ns,
        sign_ns=sign_ns,
        verify_ns=verify_ns,
        public_key_size_bytes=len(public_key),
        signature_size_bytes=len(signature),
        verify_success_rate=success_count / iterations,
        mechanism=mechanism,
    )


def _ecdsa_public_key_der(private_key: ec.EllipticCurvePrivateKey) -> bytes:
    return private_key.public_key().public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )


def _ecdsa_algorithm() -> ec.ECDSA:
    return ec.ECDSA(utils.Prehashed(hashes.SHA256()))


def benchmark_ecdsa_p256(iterations: int, warmup: int) -> AlgorithmBenchmark:
    for _ in range(warmup):
        private_key = ec.generate_private_key(ec.SECP256R1())
        signature = private_key.sign(SAMPLE_DIGEST, _ecdsa_algorithm())
        private_key.public_key().verify(signature, SAMPLE_DIGEST, _ecdsa_algorithm())

    keygen_ns: list[int] = []
    private_key: ec.EllipticCurvePrivateKey | None = None
    for _ in range(iterations):
        started = time.perf_counter_ns()
        private_key = ec.generate_private_key(ec.SECP256R1())
        keygen_ns.append(time.perf_counter_ns() - started)

    if private_key is None:
        raise RuntimeError("iterations must be greater than zero")

    public_key = private_key.public_key()
    public_key_bytes = _ecdsa_public_key_der(private_key)

    sign_ns: list[int] = []
    signature = b""
    for _ in range(iterations):
        started = time.perf_counter_ns()
        signature = private_key.sign(SAMPLE_DIGEST, _ecdsa_algorithm())
        sign_ns.append(time.perf_counter_ns() - started)

    verify_ns: list[int] = []
    success_count = 0
    for _ in range(iterations):
        started = time.perf_counter_ns()
        try:
            public_key.verify(signature, SAMPLE_DIGEST, _ecdsa_algorithm())
            is_valid = True
        except InvalidSignature:
            is_valid = False
        verify_ns.append(time.perf_counter_ns() - started)
        success_count += int(is_valid)

    return AlgorithmBenchmark(
        algorithm=ECDSA_LABEL,
        keygen_ns=keygen_ns,
        sign_ns=sign_ns,
        verify_ns=verify_ns,
        public_key_size_bytes=len(public_key_bytes),
        signature_size_bytes=len(signature),
        verify_success_rate=success_count / iterations,
    )


def benchmark_all(iterations: int, warmup: int) -> list[AlgorithmBenchmark]:
    return [
        benchmark_falcon_512(iterations, warmup),
        benchmark_ecdsa_p256(iterations, warmup),
    ]


def benchmark_to_rows(result: AlgorithmBenchmark) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for operation, timings in (
        ("keygen", result.keygen_ns),
        ("sign", result.sign_ns),
        ("verify", result.verify_ns),
    ):
        row: dict[str, str] = {
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


def package_version(package_name: str) -> str:
    try:
        return metadata.version(package_name)
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

    for attr_name in ("OQS_VERSION", "LIBOQS_VERSION", "__liboqs_version__"):
        attr = getattr(oqs, attr_name, None)
        if attr:
            return str(attr)

    return "unknown"


def lookup_row(
    rows: list[dict[str, str]],
    algorithm: str,
    operation: str,
) -> dict[str, str] | None:
    for row in rows:
        if row["algorithm"] == algorithm and row["operation"] == operation:
            return row
    return None


def table_value(row: dict[str, str] | None, key: str) -> str:
    if row is None:
        return "N/A"
    return row.get(key) or "N/A"


def write_summary(
    results: list[AlgorithmBenchmark],
    output_path: Path,
    iterations: int,
    warmup: int,
) -> None:
    rows = [row for result in results for row in benchmark_to_rows(result)]
    unavailable_notes = [
        f"- {result.algorithm}: {result.unavailable_reason}"
        for result in results
        if result.unavailable_reason
    ]
    mechanisms = [
        f"- {result.algorithm}: {result.mechanism}"
        for result in results
        if result.mechanism
    ]

    table_lines = [
        "| Algorithm | Keygen mean (ms) | Sign mean (ms) | Verify mean (ms) | Public key (B) | Signature (B) | Verify success rate |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for algorithm in (FALCON_LABEL, ECDSA_LABEL):
        keygen = lookup_row(rows, algorithm, "keygen")
        sign = lookup_row(rows, algorithm, "sign")
        verify = lookup_row(rows, algorithm, "verify")
        table_lines.append(
            "| "
            + " | ".join(
                [
                    algorithm,
                    table_value(keygen, "mean_ms"),
                    table_value(sign, "mean_ms"),
                    table_value(verify, "mean_ms"),
                    table_value(keygen, "public_key_size_bytes"),
                    table_value(sign, "signature_size_bytes"),
                    table_value(verify, "verify_success_rate"),
                ]
            )
            + " |"
        )

    text = "\n".join(
        [
            "# FALCON-512 vs ECDSA-P256 Benchmark Summary",
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
            "Note: Benchmark numbers depend on CPU, OS, Python version, liboqs build, and current system load.",
            "",
        ]
    )
    output_path.write_text(text, encoding="utf-8")


def write_liboqs_install(output_path: Path) -> None:
    text = """# liboqs-python Ubuntu Install Notes

Install system dependencies:

```bash
sudo apt update
sudo apt install -y build-essential cmake ninja-build libssl-dev python3-dev python3-venv git
```

Create and activate a local virtual environment:

```bash
python3 -m venv .venv
PATH=.venv/bin:$PATH python -m pip install -U pip
PATH=.venv/bin:$PATH python -m pip install -r backend/requirements.txt
```

If the project requirements file is not available, install the Python binding directly:

```bash
PATH=.venv/bin:$PATH python -m pip install liboqs-python
```

The Python import name is `import oqs`. Test the installation with:

```bash
PATH=.venv/bin:$PATH python -c "import oqs; print(oqs.get_enabled_sig_mechanisms())"
```
"""
    output_path.write_text(text, encoding="utf-8")


def write_falcon_notes(output_path: Path) -> None:
    text = """# Ghi Chu Report: FALCON-512

- FALCON-512 là chữ ký số hậu lượng tử dựa trên bài toán NTRU lattice.
- Hệ thống ký SHA-256 hash của PDF, không ký trực tiếp toàn bộ PDF. Cách này giữ dữ liệu ký cố định 32 bytes và phù hợp luồng xác thực QR/offline.
- Chọn FALCON-512 vì chữ ký nhỏ, phù hợp QR/verification payload hơn các thuật toán có chữ ký lớn.
- So với RSA/ECDSA, FALCON hướng tới an toàn hậu lượng tử trước mô hình tấn công có máy tính lượng tử.
- So với Dilithium/ML-DSA, Dilithium là chuẩn chính, còn FALCON/FN-DSA có lợi thế chữ ký nhỏ hơn cho bài toán nhúng chữ ký vào QR.
- Số liệu benchmark trong report lấy từ `benchmark_results.csv` hoặc `benchmark_summary.md`; không nhập tay hoặc suy diễn số liệu chưa đo.
"""
    output_path.write_text(text, encoding="utf-8")


def write_report_inputs(
    results: list[AlgorithmBenchmark],
    out_dir: Path,
    iterations: int,
    warmup: int,
) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": out_dir / "benchmark_results.csv",
        "summary": out_dir / "benchmark_summary.md",
        "install": out_dir / "liboqs_ubuntu_install.md",
        "notes": out_dir / "falcon_report_notes.md",
    }
    write_csv(results, paths["csv"])
    write_summary(results, paths["summary"], iterations, warmup)
    write_liboqs_install(paths["install"])
    write_falcon_notes(paths["notes"])
    return paths


def print_console_summary(results: list[AlgorithmBenchmark], paths: dict[str, Path]) -> None:
    rows = [row for result in results for row in benchmark_to_rows(result)]
    widths = {
        column: max(len(column), *(len(str(row[column])) for row in rows))
        for column in CSV_COLUMNS
    }
    header = "  ".join(column.ljust(widths[column]) for column in CSV_COLUMNS)
    print(header)
    print("  ".join("-" * widths[column] for column in CSV_COLUMNS))
    for row in rows:
        print("  ".join(row[column].ljust(widths[column]) for column in CSV_COLUMNS))

    for result in results:
        if result.unavailable_reason:
            print(f"\nSkipped {result.algorithm}: {result.unavailable_reason}")

    print("\nSaved outputs:")
    for path in paths.values():
        print(f"- {path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark FALCON-512 and ECDSA-P256 for NT219 report inputs."
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
