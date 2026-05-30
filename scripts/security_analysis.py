#!/usr/bin/env python3
"""Generate SHA-256 avalanche and FALCON signature-byte analysis artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.app.crypto.falcon_service import (  # noqa: E402
    available_signature_algorithms,
    generate_keypair,
    sign_document,
)


SAMPLE_DOCUMENT = b"%PDF-1.4\nNT219 citizen portal security analysis\n"


def bit_difference(left: bytes, right: bytes) -> int:
    """Count differing bits between equal-length byte strings."""

    if len(left) != len(right):
        raise ValueError("inputs must have equal length")
    return sum((a ^ b).bit_count() for a, b in zip(left, right))


def flip_bit(data: bytes, bit_index: int) -> bytes:
    """Return a copy with one selected bit flipped."""

    if bit_index < 0 or bit_index >= len(data) * 8:
        raise ValueError("bit_index is out of range")
    changed = bytearray(data)
    byte_index, offset = divmod(bit_index, 8)
    changed[byte_index] ^= 1 << offset
    return bytes(changed)


def sha256_avalanche(samples: int) -> list[int]:
    """Measure changed SHA-256 digest bits after one input-bit flip."""

    original_hash = hashlib.sha256(SAMPLE_DOCUMENT).digest()
    available_bits = len(SAMPLE_DOCUMENT) * 8
    return [
        bit_difference(
            original_hash,
            hashlib.sha256(flip_bit(SAMPLE_DOCUMENT, index % available_bits)).digest(),
        )
        for index in range(samples)
    ]


def shannon_entropy(data: bytes) -> float:
    """Compute Shannon entropy in bits per byte."""

    if not data:
        return 0.0
    counts = Counter(data)
    length = len(data)
    return -sum(
        (count / length) * math.log2(count / length)
        for count in counts.values()
    )


def collect_falcon_signatures(samples: int) -> list[bytes]:
    """Generate FALCON signatures when liboqs is available."""

    if not available_signature_algorithms():
        return []
    _, private_key = generate_keypair()
    return [
        sign_document(SAMPLE_DOCUMENT + str(index).encode("ascii"), private_key)[1]
        for index in range(samples)
    ]


def flatten(chunks: Iterable[bytes]) -> bytes:
    return b"".join(chunks)


def write_frequency_csv(signature_bytes: bytes, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    counts = Counter(signature_bytes)
    total = len(signature_bytes)
    with output_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=["byte_value", "count", "frequency"])
        writer.writeheader()
        for value in range(256):
            count = counts.get(value, 0)
            writer.writerow(
                {
                    "byte_value": value,
                    "count": count,
                    "frequency": f"{count / total:.8f}" if total else "",
                }
            )


def build_summary(
    samples: int,
    signatures: list[bytes] | None = None,
) -> dict[str, object]:
    avalanche = sha256_avalanche(samples)
    if signatures is None:
        signatures = collect_falcon_signatures(samples)
    signature_bytes = flatten(signatures)
    return {
        "sha256_avalanche": {
            "samples": samples,
            "mean_changed_bits": round(mean(avalanche), 3),
            "min_changed_bits": min(avalanche),
            "max_changed_bits": max(avalanche),
            "digest_bits": 256,
        },
        "falcon_signature_bytes": {
            "available": bool(signatures),
            "samples": len(signatures),
            "total_bytes": len(signature_bytes),
            "entropy_bits_per_byte": (
                round(shannon_entropy(signature_bytes), 6)
                if signature_bytes
                else None
            ),
        },
    }


def write_summary_markdown(summary: dict[str, object], output_path: Path) -> None:
    avalanche = summary["sha256_avalanche"]
    signature = summary["falcon_signature_bytes"]
    text = "\n".join(
        [
            "# Security Analysis Summary",
            "",
            "## SHA-256 Avalanche Effect",
            "",
            f"- Samples: {avalanche['samples']}",
            f"- Mean changed digest bits: {avalanche['mean_changed_bits']} / 256",
            f"- Minimum changed digest bits: {avalanche['min_changed_bits']}",
            f"- Maximum changed digest bits: {avalanche['max_changed_bits']}",
            "",
            "## FALCON Signature Byte Distribution",
            "",
            f"- Available: {signature['available']}",
            f"- Signature samples: {signature['samples']}",
            f"- Total signature bytes: {signature['total_bytes']}",
            f"- Shannon entropy: {signature['entropy_bits_per_byte']} bits/byte",
            "",
            "Raw byte frequencies: `security_analysis_frequency.csv`.",
            "",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate crypto security analysis artifacts.")
    parser.add_argument("--samples", type=int, default=100)
    parser.add_argument("--out-dir", default=str(REPO_ROOT / "report_inputs"))
    args = parser.parse_args()
    if args.samples <= 0:
        parser.error("--samples must be positive")
    return args


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    signatures = collect_falcon_signatures(args.samples)
    summary = build_summary(args.samples, signatures)
    write_frequency_csv(flatten(signatures), out_dir / "security_analysis_frequency.csv")
    write_summary_markdown(summary, out_dir / "security_analysis_summary.md")
    print(json.dumps(summary, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
