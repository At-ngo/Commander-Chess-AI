
# Cấu hình thực nghiệm

## Mục tiêu

Mỗi thực nghiệm phải được mô tả bằng một cấu hình rõ ràng để có thể kiểm tra và chạy lại.

## Trường cấu hình đề xuất

- `experiment_id`
- `rules_version`
- `engine_version`
- `agent_a`
- `agent_b`
- `games_per_pair`
- `side_balance`
- `seeds`
- `agent_configs`
- `time_limit`
- `search_budget`
- `metrics`
- `output_location`

Tên trường cuối cùng cần thống nhất với mã nguồn.

## Quy tắc

- Dùng YAML hoặc JSON.
- Kiểm tra cấu hình trước khi chạy.
- Ghi mặc định một cách rõ ràng.
- Không để bí mật trong cấu hình.
- Ghi lại cấu hình thực tế đã dùng, không chỉ cấu hình dự kiến.
- Không ghi đè kết quả cũ mà không có chủ đích.
