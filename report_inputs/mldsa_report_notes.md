# Ghi Chu Report: ML-DSA-44 + Ed25519 (hybrid)

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
