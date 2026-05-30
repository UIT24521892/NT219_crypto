#!/usr/bin/env python3
"""Benchmark project signing algorithms without fabricating unavailable results."""

from __future__ import annotations

import argparse
import csv
import hashlib
import platform
import sys
import time
from importlib import metadata
from pathlib import Path
from statistics import mean
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec, utils


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.crypto.falcon_service import available_signature_algorithms  # noqa: E402

try:
    import oqs
except ImportError:  # pragma: no cover - depends on local environment.
    oqs = None  # type: ignore[assignment]


CSV_COLUMNS = [
    "algorithm",
    "keygen_ms_avg",
    "sign_ms_avg",
    "verify_ms_avg",
    "public_key_bytes",
    "private_key_bytes",
    "signature_bytes",
    "iterations",
    "available",
]
SAMPLE_PDF_BYTES = b"%PDF-1.4\nCitizen services benchmark document\n"
SAMPLE_DIGEST = hashlib.sha256(SAMPLE_PDF_BYTES).digest()


def ns_to_ms(ns: int) -> float:
    return ns / 1_000_000


def format_ms(values_ns: list[int]) -> str:
    return f"{ns_to_ms(int(mean(values_ns))):.3f}"


def normalise_algorithm_name(name: str) -> str:
    return name.replace("_", "-").casefold()


def select_oqs_algorithm(candidates: list[str], enabled: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in enabled:
            return candidate

    enabled_by_normalised = {normalise_algorithm_name(name): name for name in enabled}
    for candidate in candidates:
        resolved = enabled_by_normalised.get(normalise_algorithm_name(candidate))
        if resolved:
            return resolved

    return None


def unavailable_row(algorithm: str, iterations: int) -> dict[str, Any]:
    return {
        "algorithm": algorithm,
        "keygen_ms_avg": "",
        "sign_ms_avg": "",
        "verify_ms_avg": "",
        "public_key_bytes": "",
        "private_key_bytes": "",
        "signature_bytes": "",
        "iterations": iterations,
        "available": "false",
    }


def benchmark_oqs_algorithm(algorithm: str, iterations: int) -> dict[str, Any]:
    if oqs is None:
        return unavailable_row(algorithm, iterations)

    keygen_times: list[int] = []
    public_key = b""
    private_key = b""
    for _ in range(iterations):
        started = time.perf_counter_ns()
        with oqs.Signature(algorithm) as signer:
            public_key = signer.generate_keypair()
            private_key = signer.export_secret_key()
        keygen_times.append(time.perf_counter_ns() - started)

    sign_times: list[int] = []
    signature = b""
    with oqs.Signature(algorithm, secret_key=private_key) as signer:
        for _ in range(iterations):
            started = time.perf_counter_ns()
            signature = signer.sign(SAMPLE_DIGEST)
            sign_times.append(time.perf_counter_ns() - started)

    verify_times: list[int] = []
    with oqs.Signature(algorithm) as verifier:
        for _ in range(iterations):
            started = time.perf_counter_ns()
            is_valid = verifier.verify(SAMPLE_DIGEST, signature, public_key)
            verify_times.append(time.perf_counter_ns() - started)
            if not is_valid:
                raise RuntimeError(f"{algorithm} failed to verify its own benchmark signature")

    return {
        "algorithm": algorithm,
        "keygen_ms_avg": format_ms(keygen_times),
        "sign_ms_avg": format_ms(sign_times),
        "verify_ms_avg": format_ms(verify_times),
        "public_key_bytes": len(public_key),
        "private_key_bytes": len(private_key),
        "signature_bytes": len(signature),
        "iterations": iterations,
        "available": "true",
    }


def benchmark_ecdsa_p256(iterations: int) -> dict[str, Any]:
    keygen_times: list[int] = []
    private_key = None
    for _ in range(iterations):
        started = time.perf_counter_ns()
        private_key = ec.generate_private_key(ec.SECP256R1())
        keygen_times.append(time.perf_counter_ns() - started)

    if private_key is None:
        raise RuntimeError("iterations must be greater than zero")

    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    private_key_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.DER,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    sign_times: list[int] = []
    signature = b""
    ecdsa_sha256 = ec.ECDSA(utils.Prehashed(hashes.SHA256()))
    for _ in range(iterations):
        started = time.perf_counter_ns()
        signature = private_key.sign(SAMPLE_DIGEST, ecdsa_sha256)
        sign_times.append(time.perf_counter_ns() - started)

    verify_times: list[int] = []
    for _ in range(iterations):
        started = time.perf_counter_ns()
        try:
            public_key.verify(signature, SAMPLE_DIGEST, ecdsa_sha256)
        except InvalidSignature as exc:
            raise RuntimeError("ECDSA-P256 failed to verify its own benchmark signature") from exc
        verify_times.append(time.perf_counter_ns() - started)

    return {
        "algorithm": "ECDSA-P256",
        "keygen_ms_avg": format_ms(keygen_times),
        "sign_ms_avg": format_ms(sign_times),
        "verify_ms_avg": format_ms(verify_times),
        "public_key_bytes": len(public_key_bytes),
        "private_key_bytes": len(private_key_bytes),
        "signature_bytes": len(signature),
        "iterations": iterations,
        "available": "true",
    }


def benchmark_all(iterations: int) -> list[dict[str, Any]]:
    enabled = available_signature_algorithms()
    targets = [
        ("FALCON-512", ["FALCON-512", "Falcon-512"]),
        ("FALCON-1024", ["FALCON-1024", "Falcon-1024"]),
        ("Dilithium2/ML-DSA-44", ["ML-DSA-44", "Dilithium2", "Dilithium2-AES"]),
    ]

    rows: list[dict[str, Any]] = []
    for label, candidates in targets:
        algorithm = select_oqs_algorithm(candidates, enabled)
        if algorithm is None:
            rows.append(unavailable_row(label, iterations))
            continue
        rows.append(benchmark_oqs_algorithm(algorithm, iterations))

    rows.append(benchmark_ecdsa_p256(iterations))
    return rows


def write_csv(rows: list[dict[str, Any]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_COLUMNS)
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
    for attribute_name in ("oqs_version", "get_oqs_version"):
        attribute = getattr(oqs, attribute_name, None)
        if callable(attribute):
            try:
                return str(attribute())
            except Exception:
                pass
    return "unknown"


def write_summary(rows: list[dict[str, Any]], output_path: Path, iterations: int) -> None:
    """Write reproducibility metadata and measured rows for the report."""

    table_lines = [
        "| Algorithm | Keygen (ms) | Sign (ms) | Verify (ms) | Public key (B) | Private key (B) | Signature (B) | Available |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    table_lines.extend(
        "| "
        + " | ".join(
            str(row[column]) or "N/A"
            for column in (
                "algorithm",
                "keygen_ms_avg",
                "sign_ms_avg",
                "verify_ms_avg",
                "public_key_bytes",
                "private_key_bytes",
                "signature_bytes",
                "available",
            )
        )
        + " |"
        for row in rows
    )
    text = "\n".join(
        [
            "# Full Signature Benchmark Summary",
            "",
            *table_lines,
            "",
            f"- Iterations: {iterations}",
            f"- OS: {platform.platform()}",
            f"- CPU: {platform.processor() or 'unknown'}",
            f"- Python: {platform.python_version()} ({platform.python_implementation()})",
            f"- cryptography: {package_version('cryptography')}",
            f"- liboqs-python: {package_version('liboqs-python')}",
            f"- liboqs: {liboqs_version()}",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def print_summary(rows: list[dict[str, Any]]) -> None:
    widths = {
        column: max(len(column), *(len(str(row[column])) for row in rows))
        for column in CSV_COLUMNS
    }
    header = "  ".join(column.ljust(widths[column]) for column in CSV_COLUMNS)
    print(header)
    print("  ".join("-" * widths[column] for column in CSV_COLUMNS))
    for row in rows:
        print("  ".join(str(row[column]).ljust(widths[column]) for column in CSV_COLUMNS))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark crypto signature algorithms.")
    parser.add_argument("--iterations", type=int, default=20)
    args = parser.parse_args()
    if args.iterations <= 0:
        parser.error("--iterations must be a positive integer")
    return args


def main() -> None:
    args = parse_args()
    rows = benchmark_all(args.iterations)
    output_path = REPO_ROOT / "results" / "benchmark.csv"
    report_csv_path = REPO_ROOT / "report_inputs" / "full_benchmark.csv"
    report_summary_path = REPO_ROOT / "report_inputs" / "full_benchmark_summary.md"
    write_csv(rows, output_path)
    write_csv(rows, report_csv_path)
    write_summary(rows, report_summary_path, args.iterations)
    print_summary(rows)
    print(f"\nSaved CSV: {output_path}")
    print(f"Saved report CSV: {report_csv_path}")
    print(f"Saved report summary: {report_summary_path}")


if __name__ == "__main__":
    main()
