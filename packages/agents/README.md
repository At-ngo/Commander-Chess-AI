
# AI Agents — Các tác tử trí tuệ nhân tạo

## Mục tiêu

Xây dựng các tác tử có thể chơi cùng một game engine và được đánh giá bằng cùng một quy trình thực nghiệm.

## Các tác tử dự kiến

### Level 1 — Random
Chọn ngẫu nhiên một nước đi trong danh sách nước hợp lệ.

### Level 2 — Rule-based/Heuristic
Chọn nước đi dựa trên các quy tắc hoặc hàm đánh giá được định nghĩa rõ.

### Level 3 — Minimax
Tìm kiếm cây trò chơi bằng thuật toán Minimax.

### Level 4 — Alpha-Beta
Tối ưu tìm kiếm Minimax bằng cắt tỉa Alpha-Beta.

### Level 5+ — Tác tử nâng cao
Nghiên cứu MCTS/UCT, mô hình học được hoặc Reinforcement Learning tùy yêu cầu và nguồn lực.

Các mức trên là lộ trình tham khảo, không phải khẳng định về chất lượng hoặc độ mạnh của tác tử.

## Giao diện chung

Mỗi agent cần:
- Nhận trạng thái và danh sách nước đi hợp lệ.
- Trả về một nước đi.
- Có cấu hình rõ ràng.
- Hỗ trợ seed nếu có tính ngẫu nhiên.
- Cung cấp metadata về thuật toán và phiên bản.
- Đo thời gian suy nghĩ.
- Báo lỗi khi không thể chọn nước đi.

## Quy tắc

- Không tự sửa trạng thái trò chơi.
- Không trả về nước đi ngoài danh sách hợp lệ.
- Có giới hạn thời gian và tài nguyên.
- Tách thuật toán khỏi giao diện web.
- Không tuyên bố tác tử đã triển khai nếu mới chỉ có placeholder.

## Đánh giá

- Tỷ lệ thắng, hòa, thua.
- Tỷ lệ điểm số.
- Thời gian quyết định.
- Số nút tìm kiếm hoặc số mô phỏng khi có.
- Kết quả theo từng đối thủ.
- Độ ổn định qua nhiều seed.
