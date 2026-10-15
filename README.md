# Commander Chess AI — Nền tảng nghiên cứu AI Cờ Tư Lệnh

## Dự án

Saigon University, Ho Chi Minh City, Vietnam  
**2026 Trí Tuệ Nhân Tạo Nâng Cao**  
Professor: **Đỗ Như Tài**  
Student: **Ngô Đông Ất - 3123410014**

**Target:**

Xây dựng nền tảng web để phát triển, trình diễn và đánh giá các tác tử trí tuệ nhân tạo cho trò chơi Cờ Tư Lệnh (*Commander Chess*). Dự án hướng đến một sản phẩm có thể chạy thực tế trên trình duyệt, hỗ trợ người dùng chơi với AI, xem lại các ván đấu, tổ chức thực nghiệm và so sánh hiệu quả giữa các phương pháp AI. Kết quả thực nghiệm sẽ được sử dụng để phân tích, viết báo cáo và trình bày nghiên cứu trong khuôn khổ môn Trí tuệ nhân tạo nâng cao.

## 1. Giới thiệu

Commander Chess AI là dự án xây dựng nền tảng web để chơi, phát triển và đánh giá các tác tử trí tuệ nhân tạo cho trò chơi Cờ Tư Lệnh.

Dự án phục vụ môn Trí tuệ nhân tạo nâng cao, đồng thời hướng đến một sản phẩm có thể chạy thực tế, trình diễn trên trình duyệt và hỗ trợ thực nghiệm có thể tái lập.

## 2. Mục tiêu

- Xây dựng bộ máy trò chơi tuân thủ luật Cờ Tư Lệnh đã được xác minh.
- Phát triển các tác tử AI có nhiều mức độ.
- Cho phép người dùng chơi với AI trên giao diện web.
- Lưu và xem lại các ván đấu thực nghiệm.
- Tổ chức giải đấu tự động giữa các tác tử.
- Tổng hợp thống kê từ kết quả thực nghiệm thực tế.
- Hỗ trợ giao diện Tiếng Việt và English.
- Cung cấp dữ liệu để phân tích, viết báo cáo và trình bày kết quả nghiên cứu.

## 3. Các chức năng dự kiến

- **Dashboard:** Tổng quan hệ thống và các kết quả đã ghi nhận.
- **Play:** Chơi Cờ Tư Lệnh với các tác tử AI đã triển khai.
- **Replays:** Xem lại các ván đấu được lưu.
- **Statistics:** Xem thống kê và so sánh các tác tử.
- **Rules:** Đọc luật chơi và hướng dẫn.
- **Research:** Quản lý cấu hình thực nghiệm và kết quả giải đấu khi chức năng này được triển khai.

Các phương pháp AI có thể được phát triển theo từng giai đoạn, từ Random và Rule-based đến Minimax, Alpha-Beta, MCTS/UCT và các phương pháp học máy phù hợp với yêu cầu học phần. Đây là định hướng phát triển, không phải danh sách các tính năng đã hoàn thành.

## 4. Ngôn ngữ giao diện

Website hỗ trợ:
- Tiếng Việt.
- English.

Bộ chọn ngôn ngữ phải xuất hiện ở góc trên bên phải của giao diện. Khi đổi ngôn ngữ, toàn bộ nội dung giao diện phải cập nhật tương ứng, bao gồm menu, nút bấm, biểu mẫu, thông báo lỗi, hộp thoại, trạng thái tải dữ liệu, nội dung trống và nhãn biểu đồ.

## 5. Cấu trúc dự án

```text
Commander-Chess-AI/
├── AGENTS.md
├── README.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── apps/
│   ├── web/
│   │   └── README.md
│   └── api/
│       └── README.md
│
├── packages/
│   ├── game-engine/
│   │   └── README.md
│   └── agents/
│       ├── README.md
│       └── agent_protocol.md
│
├── workers/
│   └── tournament-runner/
│       └── README.md
│
├── research/
│   ├── README.md
│   ├── environments/README.md
│   ├── training/README.md
│   ├── evaluation/README.md
│   ├── experiments/configs/README.md
│   ├── datasets/README.md
│   ├── checkpoints/.gitkeep
│   └── runs/README.md
│
├── tests/
│   └── README.md
│
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── GAME_RULES.md
│   ├── API_CONTRACT.md
│   ├── DEVELOPMENT.md
│   └── IMPLEMENTATION_PLAN.md
│
├── infra/
│   └── README.md
│
├── scripts/
│   └── README.md
│
└── data/
    └── local/
        └── .gitkeep
```

Các thư mục và tài liệu có vai trò như sau:

- `apps/web/`: Giao diện web, bàn cờ, lựa chọn AI, xem lại ván đấu và thống kê.
- `apps/api/`: Máy chủ API, xử lý yêu cầu và kết nối các thành phần hệ thống.
- `packages/game-engine/`: Bộ máy luật chơi, trạng thái bàn cờ, nước đi hợp lệ và điều kiện kết thúc.
- `packages/agents/`: Giao diện chung và các tác tử AI.
- `workers/tournament-runner/`: Tổ chức và thực thi các trận đấu giữa các tác tử.
- `research/`: Môi trường nghiên cứu, huấn luyện, đánh giá, cấu hình thực nghiệm, dữ liệu và kết quả.
- `tests/`: Tổ chức kiểm thử đơn vị, kiểm thử tích hợp và kiểm thử hồi quy.
- `docs/`: Tài liệu yêu cầu, kiến trúc, luật chơi, API, hướng dẫn phát triển và kế hoạch triển khai.
- `infra/`: Cấu hình hạ tầng và triển khai.
- `scripts/`: Các script phục vụ phát triển, kiểm thử và thực nghiệm.
- `data/local/`: Dữ liệu cục bộ phục vụ phát triển; không mặc định đưa dữ liệu phát sinh lên Git.

## 6. Kiến trúc và nguyên tắc phát triển

Dự án được định hướng theo kiến trúc mô-đun, tách biệt các thành phần để thuận tiện cho phát triển và kiểm thử.

- **Game Engine:** Quản lý trạng thái và thực thi luật chơi; là thành phần có thẩm quyền xác định nước đi hợp lệ.
- **AI Agents:** Nhận trạng thái trò chơi và lựa chọn hành động hợp lệ theo phương pháp tương ứng.
- **Backend API:** Cung cấp giao tiếp giữa giao diện web và các thành phần xử lý.
- **Web Application:** Cung cấp giao diện chơi game và theo dõi kết quả.
- **Research & Evaluation:** Hỗ trợ chạy thực nghiệm, lưu cấu hình và phân tích kết quả.

Các thành phần cần được kiểm thử độc lập. Không triển khai luật chơi dựa trên suy đoán; các quy tắc chưa được xác minh phải được ghi rõ trong `docs/GAME_RULES.md`.

## 7. Tình trạng dự án

Các tài liệu ban đầu là bộ khung, không đồng nghĩa các chức năng đã được lập trình.

Chỉ đánh dấu một chức năng hoàn thành sau khi đã có triển khai, kiểm thử và bằng chứng phù hợp.

Các giai đoạn phát triển dự kiến:

1. Xác định yêu cầu và xác minh luật chơi.
2. Xây dựng Game Engine và bộ kiểm thử.
3. Phát triển các tác tử AI cơ bản.
4. Xây dựng API và giao diện web.
5. Tích hợp các tác tử nâng cao và chức năng thực nghiệm.
6. Đánh giá kết quả, phân tích hạn chế và hoàn thiện báo cáo.

## 8. Quy tắc về dữ liệu nghiên cứu

- Không tạo số liệu giả để minh họa như kết quả thực tế.
- Phân biệt rõ kết quả đo được, kết quả dự kiến và ví dụ minh họa.
- Ghi lại cấu hình, seed, phiên bản mã nguồn và thông số thực nghiệm.
- Lưu nguồn tham khảo và thông tin giấy phép của dữ liệu hoặc mã nguồn được sử dụng.
- Cân bằng lượt đi trước và lượt đi sau khi thiết kế các trận đấu so sánh.
- Chỉ tính toán thống kê từ dữ liệu ván đấu hoặc thực nghiệm đã được ghi nhận.
- Nêu rõ số lượng trận đấu, phương pháp đánh giá và hạn chế khi diễn giải kết quả.

Các chỉ số có thể sử dụng khi đã có dữ liệu phù hợp:

- Số trận thắng, hòa và thua.
- Tỷ lệ điểm: `(số trận thắng + 0.5 × số trận hòa) / tổng số trận`.
- Thời gian ra quyết định.
- Số nút tìm kiếm hoặc số mô phỏng, tùy thuật toán.
- Thời gian huấn luyện và thông số mô hình đối với tác tử học máy.

## 9. Bắt đầu phát triển

Đọc các tài liệu sau trước khi triển khai:

1. `AGENTS.md`
2. `docs/PRD.md`
3. `docs/ARCHITECTURE.md`
4. `docs/GAME_RULES.md`
5. `docs/API_CONTRACT.md`
6. `docs/DEVELOPMENT.md`
7. `docs/IMPLEMENTATION_PLAN.md`

Chỉ chạy các lệnh cài đặt và khởi động sau khi các tệp cấu hình, dependencies và ứng dụng tương ứng đã được tạo đầy đủ.

Tham khảo hướng dẫn phát triển tại [`docs/DEVELOPMENT.md`](docs/DEVELOPMENT.md).

## 10. Nguồn tham khảo

Nguồn khởi đầu để nghiên cứu luật chơi:

- [Hướng dẫn cách chơi Cờ Tư Lệnh — Thủ Thuật Chơi](https://thuthuatchoi.com/huong-dan-cach-choi-co-tu-lenh.html)

Nguồn này là điểm bắt đầu cho quá trình khảo sát, không mặc nhiên được xem là đặc tả luật chơi đầy đủ hoặc nguồn có thẩm quyền duy nhất. Các quy tắc được triển khai cần được kiểm tra và ghi nhận trong `docs/GAME_RULES.md`.

Các thư viện, tài liệu, mã nguồn kế thừa và công cụ AI được sử dụng cần được ghi nhận theo yêu cầu của học phần.

## Personal Information

**Đỗ Như Tài**  
**Saigon University, Vietnam**  
E-mail: dnt@sgu.edu.vn

---

*Advanced Artificial Intelligence — Saigon University, 2026.*