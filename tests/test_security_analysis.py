from scripts.security_analysis import bit_difference, flip_bit, sha256_avalanche, shannon_entropy


def test_flip_bit_changes_exactly_one_bit():
    original = b"\x00\x00"
    changed = flip_bit(original, 9)

    assert bit_difference(original, changed) == 1


def test_sha256_avalanche_returns_digest_bit_counts():
    changed_bits = sha256_avalanche(samples=8)

    assert len(changed_bits) == 8
    assert all(0 < value <= 256 for value in changed_bits)


def test_entropy_handles_uniform_and_varied_bytes():
    assert shannon_entropy(b"\x00" * 10) == 0.0
    assert shannon_entropy(bytes(range(256))) == 8.0
