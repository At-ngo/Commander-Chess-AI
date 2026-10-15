
# Khu vực nghiên cứu AI

## Mục tiêu

Tổ chức mã nguồn, cấu hình, dữ liệu và kết quả thực nghiệm phục vụ việc phát triển và đánh giá các tác tử AI Cờ Tư Lệnh.

## Thư mục

- `environments/`: môi trường và bộ chuyển đổi trạng thái.
- `training/`: quy trình huấn luyện.
- `evaluation/`: đánh giá tác tử.
- `experiments/configs/`: cấu hình thí nghiệm.
- `datasets/`: thông tin về dữ liệu nghiên cứu.
- `checkpoints/`: vị trí lưu checkpoint cục bộ.
- `runs/`: kết quả chạy và metadata.

## Nguyên tắc

- Không phải agent nào cũng cần huấn luyện.
- Random, Rule-based và Minimax có thể không cần dữ liệu huấn luyện.
- Không đưa dataset lớn hoặc checkpoint lớn lên Git nếu không cần thiết.
- Ghi nguồn, giấy phép và cách xử lý dữ liệu.
- Lưu cấu hình, seed, phiên bản mã nguồn và môi trường.
- Phân biệt kết quả dự kiến với kết quả thực nghiệm thật.

## Tái lập thực nghiệm

Mỗi lần chạy cần có đủ thông tin để hiểu:
- Đang đánh giá tác tử nào.
- Dùng phiên bản luật và engine nào.
- Sử dụng cấu hình nào.
- Chạy bao nhiêu trận.
- Dùng seed nào.
- Kết quả được lưu ở đâu.
