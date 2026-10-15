
# Hạ tầng và triển khai

## Mục tiêu

Tổ chức cấu hình để chạy, kiểm thử và triển khai ứng dụng.

## Phạm vi

- Docker và Docker Compose.
- Cấu hình môi trường.
- CI/CD.
- Quản lý dữ liệu bền vững.
- Cấu hình production.
- Hướng dẫn triển khai.

## Quy tắc

- Không commit secrets.
- Dùng `.env.example` để mô tả các biến môi trường.
- Phân biệt cấu hình phát triển và production.
- Kiểm tra kết nối API giữa frontend và backend.
- Kiểm tra CORS và đường dẫn dữ liệu.
- Không tuyên bố đã triển khai production khi mới chỉ chạy cục bộ.

Chỉ bổ sung cấu hình hạ tầng khi ứng dụng và các Dockerfile tương ứng đã tồn tại.
