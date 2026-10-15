
# Hướng dẫn phát triển

## 1. Công cụ cần có

- Git.
- Python phiên bản phù hợp với dependencies.
- Node.js phiên bản LTS phù hợp với frontend.
- Docker và Docker Compose nếu chạy bằng container.
- Trình soạn thảo mã nguồn.

Phiên bản chính xác phải được chốt trong cấu hình dự án khi bắt đầu triển khai.

## 2. Quy trình phát triển

### Bước 1: Kiểm tra repository
- Xem nhánh hiện tại và trạng thái Git.
- Đọc `AGENTS.md`.
- Kiểm tra những file đã tồn tại.
- Không ghi đè công việc có sẵn mà chưa xem xét.

### Bước 2: Xác minh luật
- Đọc `GAME_RULES.md`.
- Bổ sung nguồn và trường hợp chưa rõ.
- Không bắt đầu xây dựng AI hoàn chỉnh khi luật nền tảng còn sai lệch.

### Bước 3: Xây dựng game engine
- Thiết kế trạng thái.
- Sinh nước đi hợp lệ.
- Áp dụng nước đi.
- Kiểm tra kết thúc.
- Viết test.

### Bước 4: Xây dựng agents
- Bắt đầu với Random.
- Tiếp theo Rule-based và Minimax.
- Bổ sung các phương pháp nâng cao theo kế hoạch.
- Đo thời gian và kiểm tra tính hợp lệ.

### Bước 5: Xây dựng API
- Tạo phiên chơi.
- Nhận nước đi.
- Trả trạng thái.
- Lưu ván đấu và kết quả.

### Bước 6: Xây dựng frontend
- Bàn cờ và điều khiển.
- Bộ chọn AI.
- Dashboard, Replays, Statistics và Rules.
- Bộ chọn ngôn ngữ Tiếng Việt/English.
- Kiểm tra khả năng hiển thị trên nhiều kích thước màn hình.

### Bước 7: Tích hợp
- Kiểm thử API và frontend.
- Kiểm thử toàn bộ luồng chơi.
- Kiểm tra lưu và phát lại ván.
- Chạy thử giải đấu nhỏ.

## 3. Quy tắc kiểm thử

Không tuyên bố test đã qua nếu chưa thực sự chạy.

Khi báo cáo cần ghi:
- Lệnh đã chạy.
- Số test thành công và thất bại nếu công cụ cung cấp.
- Lỗi còn tồn tại.
- Các chức năng chưa được kiểm thử.

## 4. Quản lý Git

- Commit theo từng chức năng nhỏ.
- Không commit secrets, database cục bộ hoặc checkpoint lớn.
- Cập nhật `.env.example` khi bổ sung biến môi trường.
- Giữ lịch sử thay đổi để truy xuất nguồn gốc.

## 5. Chạy ứng dụng

Các lệnh chạy chính thức phải được cập nhật sau khi dependencies, scripts và cấu hình thật đã được tạo.

Không sao chép lệnh giả định rồi xem đó là quy trình đã được kiểm chứng.
