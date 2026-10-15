
# Kiến trúc hệ thống

## 1. Nguyên tắc

Xây dựng theo mô hình modular monolith: một hệ thống triển khai đơn giản nhưng được chia thành các module có trách nhiệm rõ ràng.

Không tách microservices khi chưa có nhu cầu thực tế.

## 2. Các thành phần

### Frontend — `apps/web/`

- React, TypeScript và Vite.
- Hiển thị bàn cờ, menu, dashboard và biểu đồ.
- Gọi API để thực hiện các thao tác.
- Không tự quyết định luật chơi.
- Quản lý ngôn ngữ Tiếng Việt/English bằng hệ thống i18n tập trung.

### Backend API — `apps/api/`

- Python và FastAPI.
- Xác thực dữ liệu đầu vào.
- Quản lý phiên chơi.
- Gọi game engine và tác tử AI.
- Lưu các ván đấu được chọn để lưu.
- Cung cấp dữ liệu thống kê.

### Game Engine — `packages/game-engine/`

- Quản lý trạng thái bàn cờ.
- Sinh danh sách nước đi hợp lệ.
- Áp dụng nước đi.
- Kiểm tra điều kiện kết thúc và kết quả.
- Tuần tự hóa trạng thái để lưu trữ hoặc phát lại.

Đây là nguồn xác thực cuối cùng về luật chơi.

### AI Agents — `packages/agents/`

Các tác tử dự kiến:
- Random.
- Rule-based/Heuristic.
- Minimax.
- Minimax với Alpha-Beta pruning.
- MCTS/UCT.
- Tác tử học được bằng mô hình hoặc Reinforcement Learning.

Không tuyên bố tác tử đã hoàn thiện nếu chưa triển khai và kiểm thử.

### Tournament Runner — `workers/tournament-runner/`

- Chạy các trận theo cấu hình.
- Kiểm soát seed, số trận và thứ tự bên đi trước.
- Thu thập kết quả và thời gian suy nghĩ.
- Ghi lại cấu hình và lỗi.
- Không tính các trận lỗi hoặc chưa hoàn thành như một chiến thắng.

### Research — `research/`

- Cấu hình thực nghiệm.
- Môi trường huấn luyện.
- Đánh giá tác tử.
- Lưu metadata và kết quả.
- Quản lý dữ liệu và checkpoint.

## 3. Luồng dữ liệu

1. Người dùng thao tác trên frontend.
2. Frontend gửi yêu cầu đến API.
3. API xác thực yêu cầu.
4. Game engine cung cấp nước đi hợp lệ.
5. Agent lựa chọn một nước đi trong danh sách hợp lệ.
6. Engine kiểm tra và áp dụng nước đi.
7. API trả trạng thái mới cho frontend.
8. Ván đấu được lưu khi phù hợp với chính sách lưu trữ.
9. Dữ liệu thực nghiệm được dùng để tạo thống kê.

## 4. Lưu trữ

- Dùng SQLite cho phát triển cục bộ ban đầu.
- Cân nhắc PostgreSQL cho triển khai nhiều người dùng hoặc môi trường production.
- Lưu trạng thái và lịch sử nước đi theo định dạng có phiên bản.
- Lưu cấu hình, seed, phiên bản engine và metadata cho ván thực nghiệm.

## 5. Quy tắc phụ thuộc

- Frontend không được truy cập cơ sở dữ liệu trực tiếp.
- Agent không được tự áp dụng luật ngoài game engine.
- Tournament runner dùng chung giao diện engine và agent.
- Thống kê phải lấy từ dữ liệu đã lưu.
- Mọi thay đổi API phải cập nhật `docs/API_CONTRACT.md`.

## 6. Các quyết định cần xác minh

- Luật chơi chính xác.
- Định dạng trạng thái và nước đi.
- Cách biểu diễn bên chơi và các loại quân.
- Phương án lưu trạng thái.
- Chiến lược chạy tác tử tốn nhiều thời gian.
- Cấu hình triển khai production.
