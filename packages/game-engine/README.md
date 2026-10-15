
# Game Engine — Bộ máy luật Cờ Tư Lệnh

## Mục tiêu

Cung cấp một nguồn xác thực duy nhất cho trạng thái bàn cờ, nước đi hợp lệ và kết quả ván đấu.

## Trách nhiệm

- Khởi tạo bàn cờ.
- Biểu diễn trạng thái trò chơi.
- Sinh nước đi hợp lệ.
- Áp dụng nước đi.
- Kiểm tra kết thúc.
- Xác định kết quả.
- Sao chép hoặc tuần tự hóa trạng thái.
- Hỗ trợ phát lại ván đấu.

## API nội bộ dự kiến

Các tên dưới đây chỉ là đề xuất; cần chốt cùng thiết kế thật:

- `initial_state()`
- `legal_actions(state)`
- `apply_action(state, action)`
- `is_terminal(state)`
- `result(state)`
- `serialize_state(state)`

Chỉ bổ sung `clone()` hoặc `undo()` nếu thuật toán và kiến trúc thực sự cần.

## Nguyên tắc

- Chỉ triển khai luật đã xác minh.
- Không để frontend tự xác định nước đi hợp lệ.
- Kiểm tra nước đi trước khi áp dụng.
- Xác định rõ trạng thái ban đầu và trạng thái kết thúc.
- Tránh thay đổi trạng thái gốc ngoài ý muốn.
- Có phiên bản luật hoặc engine để truy xuất nguồn gốc thực nghiệm.

## Kiểm thử bắt buộc

- Trạng thái ban đầu.
- Nước đi hợp lệ và không hợp lệ.
- Di chuyển và ăn quân.
- Các luật đặc biệt đã xác minh.
- Điều kiện thắng, thua và hòa.
- Trạng thái kết thúc.
- Tính nhất quán khi tuần tự hóa.
- Các trường hợp biên.
