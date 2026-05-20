from scripts import benchmark


def test_unavailable_benchmark_row_has_required_columns():
    row = benchmark.unavailable_row("Missing-PQC", 5)

    assert list(row) == benchmark.CSV_COLUMNS
    assert row["available"] == "false"
    assert row["iterations"] == 5
    assert row["keygen_ms_avg"] == ""


def test_select_oqs_algorithm_matches_installed_name_case():
    enabled = ["Falcon-512", "ML-DSA-44"]

    assert benchmark.select_oqs_algorithm(["FALCON-512"], enabled) == "Falcon-512"
    assert benchmark.select_oqs_algorithm(["Dilithium2", "ML-DSA-44"], enabled) == "ML-DSA-44"
