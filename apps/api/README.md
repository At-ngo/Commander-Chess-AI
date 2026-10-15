
# Backend API

## Mục tiêu

Cung cấp API cho giao diện web, quản lý phiên chơi, gọi AI, lưu dữ liệu và phục vụ thống kê.

## Công nghệ

- Python.
- FastAPI.
- Pydantic để kiểm tra dữ liệu.
- SQLite ban đầu; có thể chuyển sang PostgreSQL khi cần.

## Trách nhiệm

- Tạo và truy xuất phiên chơi.
- Kiểm tra yêu cầu và nước đi.
- Gọi game engine để lấy trạng thái hợp lệ.
- Gọi agent để lựa chọn nước đi.
- Trả kết quả và trạng thái cho frontend.
- Lưu các ván đấu được chọn để lưu.
- Cung cấp API xem lại và thống kê.
- Ghi log lỗi có ích cho việc gỡ lỗi.

## Quy tắc

- Không tin trạng thái bàn cờ do client gửi lên.
- Không cho phép agent tự vượt qua kiểm tra của engine.
- Không tính trận lỗi hoặc chưa hoàn thành như trận thắng.
- Không chặn lâu các yêu cầu chơi thông thường để chờ một giải đấu lớn.
- Tách xử lý giải đấu dài khỏi luồng request thông thường khi cần.
- Không ghi secrets vào log.

## Kiểm thử

- Kiểm thử dữ liệu đầu vào.
- Kiểm thử endpoint.
- Kiểm thử lỗi và trạng thái không hợp lệ.
- Kiểm thử lưu và truy xuất dữ liệu.
- Kiểm thử tích hợp với engine và agent.
