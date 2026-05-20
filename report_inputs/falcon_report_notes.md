# Ghi Chu Report: FALCON-512

- FALCON-512 là chữ ký số hậu lượng tử dựa trên bài toán NTRU lattice.
- Hệ thống ký SHA-256 hash của PDF, không ký trực tiếp toàn bộ PDF. Cách này giữ dữ liệu ký cố định 32 bytes và phù hợp luồng xác thực QR/offline.
- Chọn FALCON-512 vì chữ ký nhỏ, phù hợp QR/verification payload hơn các thuật toán có chữ ký lớn.
- So với RSA/ECDSA, FALCON hướng tới an toàn hậu lượng tử trước mô hình tấn công có máy tính lượng tử.
- So với Dilithium/ML-DSA, Dilithium là chuẩn chính, còn FALCON/FN-DSA có lợi thế chữ ký nhỏ hơn cho bài toán nhúng chữ ký vào QR.
- Số liệu benchmark trong report lấy từ `benchmark_results.csv` hoặc `benchmark_summary.md`; không nhập tay hoặc suy diễn số liệu chưa đo.
