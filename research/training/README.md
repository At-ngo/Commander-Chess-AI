
# Training — Huấn luyện tác tử

## Mục tiêu

Tổ chức các quy trình huấn luyện dành cho tác tử thực sự cần học từ dữ liệu hoặc tương tác với môi trường.

## Trước khi huấn luyện

- Xác minh game engine.
- Chốt biểu diễn trạng thái và hành động.
- Xác định mục tiêu huấn luyện.
- Chọn thuật toán và baseline.
- Xác định tài nguyên tính toán.
- Thiết lập đánh giá độc lập.

## Metadata bắt buộc

Mỗi lần huấn luyện nên ghi:
- Run ID.
- Thời điểm chạy.
- Git revision.
- Phiên bản engine và luật.
- Thuật toán và cấu hình.
- Seed.
- Số bước hoặc số ván huấn luyện.
- Phần cứng và thời gian chạy.
- Vị trí checkpoint.
- Kết quả đánh giá.

## Nguyên tắc

- Không khẳng định đã huấn luyện nếu chưa chạy thực tế.
- Không dùng dữ liệu đánh giá để điều chỉnh mô hình mà không ghi nhận.
- Giữ baseline để so sánh.
- Ghi lại lỗi và các lần chạy thất bại.
- Không commit checkpoint lớn nếu không có lý do.
