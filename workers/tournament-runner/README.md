
# Tournament Runner — Bộ chạy giải đấu

## Mục tiêu

Tự động chạy nhiều ván đấu giữa các tác tử AI theo cấu hình xác định, lưu kết quả và cung cấp dữ liệu phục vụ nghiên cứu.

## Trách nhiệm

- Đọc và xác thực cấu hình giải đấu.
- Khởi tạo các trận đấu.
- Luân phiên bên đi trước để hạn chế thiên lệch.
- Thiết lập seed và giới hạn tài nguyên.
- Ghi lại kết quả từng trận.
- Tổng hợp thống kê.
- Lưu phiên bản engine, agent và cấu hình.
- Báo cáo lỗi và các trận chưa hoàn thành.

## Thông tin cần ghi

- ID giải đấu và trận đấu.
- Tác tử của mỗi bên.
- Bên đi trước.
- Seed.
- Cấu hình tìm kiếm.
- Kết quả.
- Thời gian suy nghĩ.
- Số nút tìm kiếm hoặc mô phỏng nếu có.
- Phiên bản engine và luật.
- Trạng thái hoàn thành hoặc lỗi.

## Quy tắc

- Không tính trận chưa hoàn thành thành chiến thắng.
- Không bỏ qua lỗi mà không ghi nhận.
- Không tạo kết quả giả khi tác tử gặp lỗi.
- Giới hạn thời gian và bộ nhớ.
- Có thể tái lập giải đấu từ cấu hình đã lưu.
- Không làm gián đoạn các ván chơi thông thường khi chạy thử nghiệm dài.
