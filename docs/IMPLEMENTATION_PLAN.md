
# Kế hoạch triển khai

## Nguyên tắc

Xây dựng từng phần có thể chạy và kiểm thử được. Không tạo toàn bộ giao diện giả trước rồi mới tìm cách kết nối backend.

## M0 — Xác minh yêu cầu
- Xác minh luật chơi.
- Chốt định dạng trạng thái và nước đi.
- Hoàn thiện kiến trúc và API contract.
- Xác định tiêu chí nghiệm thu.

Hoàn thành khi: có đặc tả đủ rõ để viết game engine và test.

## M1 — Game Engine
- Khởi tạo trạng thái.
- Sinh nước đi hợp lệ.
- Áp dụng nước đi.
- Xử lý kết thúc và kết quả.
- Tuần tự hóa trạng thái.
- Viết test luật và trường hợp biên.

Hoàn thành khi: engine có thể chạy ván đấu và test các luật đã xác minh.

## M2 — Agents cơ bản
- Random.
- Rule-based/Heuristic.
- Minimax.
- Alpha-Beta pruning.

Hoàn thành khi: agent chỉ chọn nước hợp lệ và có thể tham gia trận đấu tự động.

## M3 — Web MVP
- API cho phiên chơi.
- Bàn cờ trên trình duyệt.
- Chọn AI.
- Bắt đầu ván mới và hiển thị kết quả.
- Hỗ trợ Tiếng Việt/English.

Hoàn thành khi: người dùng có thể chơi trọn vẹn một ván qua web.

## M4 — Nghiên cứu và tác tử nâng cao
- Xây dựng pipeline thực nghiệm.
- MCTS/UCT nếu phù hợp.
- Tác tử học được hoặc RL theo yêu cầu môn học.
- Ghi lại cấu hình và seed.
- Đo hiệu năng.

Hoàn thành khi: có quy trình thực nghiệm có thể tái lập và báo cáo rõ hạn chế.

## M5 — Replays và Statistics
- Lưu các trận được chọn.
- Xem lại lịch sử nước đi.
- Tính thống kê từ dữ liệu thật.
- So sánh các tác tử.
- Xuất kết quả phục vụ báo cáo.

## M6 — Triển khai và bàn giao
- Kiểm thử tích hợp.
- Hoàn thiện Docker nếu cần.
- Viết hướng dẫn chạy.
- Kiểm tra cấu hình bảo mật cơ bản.
- Hoàn thiện README và tài liệu nghiên cứu.
- Chuẩn bị bản demo và bằng chứng kiểm thử.

## Theo dõi tiến độ

Mỗi hạng mục cần ghi:
- Trạng thái: Chưa làm / Đang làm / Đã kiểm thử / Hoàn thành.
- Người hoặc agent phụ trách.
- Tiêu chí nghiệm thu.
- Bằng chứng kiểm thử.
- Vấn đề còn tồn tại.
