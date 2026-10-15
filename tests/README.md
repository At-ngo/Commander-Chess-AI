
# Kiểm thử hệ thống

## 1. Mục tiêu

Đảm bảo game engine, các tác tử, API và frontend hoạt động đúng theo đặc tả.

## 2. Các nhóm kiểm thử

### Game Engine
- Trạng thái ban đầu.
- Nước đi hợp lệ và không hợp lệ.
- Áp dụng nước đi.
- Điều kiện kết thúc.
- Kết quả ván đấu.
- Các trường hợp biên.

### AI Agents
- Agent chỉ trả nước đi hợp lệ.
- Agent xử lý trạng thái kết thúc.
- Kiểm tra seed và tính tái lập khi áp dụng.
- Kiểm tra giới hạn thời gian.

### API
- Kiểm tra request và response.
- Kiểm tra dữ liệu không hợp lệ.
- Kiểm tra tài nguyên không tồn tại.
- Kiểm tra lưu và truy xuất dữ liệu.
- Kiểm tra lỗi từ engine hoặc agent.

### Frontend
- Các trang chính hiển thị đúng.
- Bắt đầu và hoàn thành ván chơi.
- Trạng thái tải, lỗi và dữ liệu trống.
- Chuyển đổi Tiếng Việt/English.
- Ngôn ngữ đã chọn được giữ sau khi tải lại.
- Nội dung biểu đồ và thống kê được cập nhật đúng.

### Integration
- Frontend gọi API.
- API gọi engine và agent.
- Lưu ván đấu.
- Phát lại ván đã lưu.
- Thống kê từ dữ liệu thực nghiệm.

## 3. Nguyên tắc

- Không tuyên bố kiểm thử thành công nếu chưa chạy.
- Ghi rõ lệnh, kết quả và lỗi.
- Ưu tiên kiểm thử tự động cho luật chơi.
- Không bỏ qua test thất bại chỉ để hoàn thành báo cáo.
