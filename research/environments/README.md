
# Research Environments

## Mục tiêu

Cung cấp các bộ chuyển đổi giữa game engine và công cụ thực nghiệm hoặc huấn luyện.

## Trách nhiệm

- Chuyển trạng thái engine sang biểu diễn mà thuật toán cần.
- Chuyển hành động của thuật toán về định dạng của engine.
- Kiểm tra tính nhất quán giữa hai biểu diễn.
- Hỗ trợ reset, quan sát trạng thái và kết thúc ván.

## Tương thích

Có thể xây dựng adapter theo phong cách Gymnasium nếu phương pháp học tăng cường cần đến.

Không bắt buộc tích hợp Gymnasium nếu agent và pipeline hiện tại không cần.

## Nguyên tắc

- Game engine vẫn là nguồn xác thực luật.
- Không sao chép một bộ luật độc lập vào adapter.
- Kiểm thử trạng thái và hành động ở cả hai chiều.
- Ghi rõ cách biểu diễn quan sát và phần thưởng nếu dùng RL.
