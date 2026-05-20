import csv
import subprocess
import sys

import pytest

from scripts import benchmark_falcon_ecdsa as benchmark


def test_resolve_falcon_512_matches_enabled_name_case():
    assert benchmark.resolve_falcon_512(["Falcon-512"]) == "Falcon-512"
    assert benchmark.resolve_falcon_512(["FALCON-512"]) == "FALCON-512"


def test_ecdsa_benchmark_records_success_rate():
    result = benchmark.benchmark_ecdsa_p256(iterations=3, warmup=1)
    rows = benchmark.benchmark_to_rows(result)

    assert result.algorithm == "ECDSA-P256"
    assert result.public_key_size_bytes
    assert result.signature_size_bytes
    assert result.verify_success_rate == 1.0
    assert {row["operation"] for row in rows} == {"keygen", "sign", "verify"}


def test_cli_writes_report_inputs_when_falcon_available(tmp_path):
    if benchmark.resolve_falcon_512() is None:
        pytest.skip("liboqs-python/oqs with FALCON-512 is not available")

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/benchmark_falcon_ecdsa.py",
            "--iterations",
            "3",
            "--warmup",
            "1",
            "--out-dir",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    csv_path = tmp_path / "benchmark_results.csv"
    assert "FALCON-512" in completed.stdout
    assert csv_path.exists()
    assert (tmp_path / "benchmark_summary.md").exists()
    assert (tmp_path / "liboqs_ubuntu_install.md").exists()
    assert (tmp_path / "falcon_report_notes.md").exists()

    with csv_path.open(newline="", encoding="utf-8") as csv_file:
        rows = list(csv.DictReader(csv_file))

    assert set(rows[0]) == set(benchmark.CSV_COLUMNS)
    assert {row["algorithm"] for row in rows} == {"FALCON-512", "ECDSA-P256"}
