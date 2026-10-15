
# Giao diện web

## Mục tiêu

Xây dựng giao diện web cho phép chơi Cờ Tư Lệnh, xem lại ván đấu và theo dõi kết quả thực nghiệm.

## Công nghệ

- React.
- TypeScript.
- Vite.
- Thư viện giao diện và i18n được chọn dựa trên nhu cầu thực tế.

## Các trang

- Dashboard: tổng quan hệ thống.
- Play: bàn cờ và chơi với AI.
- Replays: danh sách và trình phát lại ván đấu.
- Statistics: biểu đồ và thống kê.
- Rules: luật chơi và hướng dẫn.
- Research: chỉ bổ sung khi có nhu cầu quản lý thực nghiệm trên web.

## Bộ chọn ngôn ngữ

Đặt bộ chọn ngôn ngữ ở góc trên bên phải của thanh điều hướng chính.

Ngôn ngữ:
- Tiếng Việt (`vi`)
- English (`en`)

Yêu cầu:
- Có nhãn dễ hiểu; có thể dùng menu thả xuống.
- Chuyển ngôn ngữ không cần tải lại trang.
- Lưu lựa chọn để giữ nguyên sau khi tải lại.
- Mặc định Tiếng Việt khi chưa có lựa chọn được lưu.
- Dịch toàn bộ nội dung giao diện, kể cả lỗi, biểu mẫu, hộp thoại, thông báo, trạng thái chờ và biểu đồ.
- Không chỉ dịch menu điều hướng.
- Không hardcode nội dung dịch rải rác trong component.
- Có kiểm thử cho thao tác đổi ngôn ngữ và lưu lựa chọn.

## Quy tắc giao diện

- Dùng API làm nguồn dữ liệu.
- Không tự tạo kết quả thắng thua để làm đẹp dashboard.
- Hiển thị rõ trạng thái tải, lỗi và dữ liệu trống.
- Phân biệt tác tử khả dụng và tác tử chưa triển khai.
- Hỗ trợ màn hình nhỏ và bàn phím khi phù hợp.
- Bàn cờ phải phản ánh trạng thái thật từ game engine.

## Tiêu chí nghiệm thu

- Có thể bắt đầu và hoàn thành ván chơi qua web.
- Có thể chọn AI khả dụng.
- Có thể đổi qua lại Tiếng Việt và English.
- Có thể xem ván đã lưu và thống kê thật.
- Các lỗi từ API được xử lý rõ ràng.
