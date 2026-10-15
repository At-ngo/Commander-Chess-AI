
# Tài liệu yêu cầu sản phẩm (PRD)

## 1. Mục đích

Xây dựng ứng dụng web cho phép chơi Cờ Tư Lệnh với AI, quan sát các ván đấu, tổ chức thực nghiệm và đánh giá hiệu quả của những phương pháp AI khác nhau.

## 2. Đối tượng sử dụng

- Sinh viên phát triển và kiểm thử tác tử AI.
- Giảng viên đánh giá sản phẩm.
- Người dùng muốn chơi thử với AI.
- Người nghiên cứu cần xem kết quả thực nghiệm.

## 3. Chức năng

### 3.1. Dashboard

- Hiển thị tình trạng hệ thống.
- Hiển thị các tác tử đã triển khai.
- Tóm tắt số trận thực nghiệm đã lưu.
- Hiển thị một số chỉ số tổng quan khi có dữ liệu thực tế.
- Không hiển thị số liệu giả khi chưa có dữ liệu.

### 3.2. Play

- Cho phép chọn chơi với AI.
- Hỗ trợ các tác tử đã triển khai và kiểm thử.
- Hiển thị bàn cờ, lượt chơi, trạng thái ván đấu và kết quả.
- Hiển thị thông báo khi nước đi không hợp lệ.
- Có chức năng bắt đầu ván mới.
- Phân biệt tác tử đã hoàn thiện với tác tử đang phát triển.

### 3.3. Replays

- Hiển thị danh sách các ván đấu được lựa chọn để lưu.
- Cho phép xem lại các nước đi theo thứ tự.
- Hỗ trợ tiến, lùi, phát lại và tạm dừng nếu phù hợp.
- Hiển thị tác tử, cấu hình, kết quả và thông tin thực nghiệm.
- Ưu tiên lưu dữ liệu nước đi; chỉ xuất video khi được yêu cầu.
- Không tự động lưu mọi ván chơi thông thường vào kho thực nghiệm.

### 3.4. Statistics

- Thống kê thắng, hòa, thua.
- Tính tỷ lệ điểm số.
- So sánh các cặp tác tử.
- Hiển thị thời gian suy nghĩ trung bình và p95 khi có dữ liệu đo.
- Hiển thị số nút tìm kiếm hoặc số mô phỏng nếu tác tử hỗ trợ.
- Cho phép lọc theo tác tử, cấu hình và khoảng thời gian khi dữ liệu đủ.
- Có thể xuất dữ liệu thực nghiệm để phục vụ báo cáo.

### 3.5. Rules

- Hiển thị luật chơi đã xác minh.
- Giải thích cách chơi và điều kiện kết thúc.
- Đánh dấu rõ các quy tắc chưa được xác minh.
- Không trình bày giả định thành luật chính thức.

### 3.6. Research và Tournament

Khi được triển khai:
- Cấu hình các cặp tác tử cần so sánh.
- Thiết lập số trận, seed và giới hạn thời gian.
- Theo dõi trạng thái giải đấu.
- Lưu kết quả và cấu hình để tái lập.
- Không làm treo các yêu cầu chơi cờ thông thường trong lúc chạy giải đấu.

## 4. Hệ thống ngôn ngữ

- Hỗ trợ Tiếng Việt và English.
- Bộ chọn ngôn ngữ đặt ở góc trên bên phải của thanh điều hướng.
- Lựa chọn hiển thị rõ `Tiếng Việt` và `English`.
- Khi đổi ngôn ngữ, mọi nội dung giao diện phải cập nhật ngay.
- Ghi nhớ lựa chọn sau khi tải lại trang.
- Mặc định Tiếng Việt nếu người dùng chưa chọn ngôn ngữ.
- Dịch cả trạng thái tải, thông báo lỗi, biểu mẫu, hộp thoại, biểu đồ và trang trống.
- Không dịch tên biến, mã tác tử hoặc dữ liệu kỹ thuật vốn cần giữ nguyên.

## 5. Yêu cầu phi chức năng

- Giao diện tương thích màn hình máy tính và thiết bị di động.
- API kiểm tra dữ liệu đầu vào và nước đi.
- Có kiểm thử cho luật chơi, tác tử và API.
- Có nhật ký lỗi hữu ích.
- Không lưu bí mật trong mã nguồn.
- Có hướng dẫn chạy cục bộ.
- Dữ liệu thực nghiệm phải có thể truy xuất nguồn gốc.

## 6. Ngoài phạm vi ban đầu

- Chơi trực tuyến nhiều người theo thời gian thực.
- Hệ thống tài khoản và phân quyền phức tạp.
- Mạng xã hội hoặc bảng xếp hạng công khai.
- Hệ thống huấn luyện phân tán quy mô lớn.

Chỉ bổ sung nếu có yêu cầu và nguồn lực phù hợp.

## 7. Tiêu chí nghiệm thu

- Người dùng mở được ứng dụng và bắt đầu một ván chơi.
- Mọi nước đi được xác thực bởi game engine.
- Các tác tử được công bố là khả dụng thực sự chạy được.
- Có thể xem lại một ván đấu đã lưu.
- Thống kê được tính từ dữ liệu thật.
- Chuyển đổi Tiếng Việt/English hoạt động trên toàn giao diện.
- Các chức năng chính có kiểm thử.
- Có hướng dẫn cài đặt và chạy ứng dụng.
