# Commander Chess AI — Nền tảng Nghiên cứu & Trải nghiệm AI Cờ Tư Lệnh

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-61DAFB.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0-3178C6.svg)](https://www.typescriptlang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Dự án nghiên cứu, hiện thực hóa và đánh giá thực nghiệm các thuật toán Trí tuệ Nhân tạo đối kháng trên trò chơi chiến thuật **Cờ Tư Lệnh** (*Commander Chess*) — môn cờ quân sự độc đáo của Việt Nam. Hệ thống kết hợp giữa **Game Engine thẩm quyền chuẩn mực**, **hệ sinh thái Tác tử AI đa cấp độ**, **khung thực nghiệm khoa học có khả năng tái lập cao**, cùng **nền tảng Web trực quan đa ngôn ngữ (Tiếng Việt & English)**.

---

## Thông tin Đồ án & Tác giả

* **Đơn vị đào tạo:** Trường Đại học Sài Gòn (Saigon University — SGU), TP. Hồ Chí Minh, Việt Nam
* **Học phần:** Trí Tuệ Nhân Tạo Nâng Cao (Advanced Artificial Intelligence) — Năm học 2026
* **Giảng viên hướng dẫn:** **TS. Đỗ Như Tài** (*dnt@sgu.edu.vn*)
* **Sinh viên thực hiện:** **Ngô Đông Ất** — MSSV: **3123410014**

---

## Mục tiêu Dự án

1. **Chuẩn hóa Luật chơi Cờ Tư Lệnh:** Xây dựng Game Engine thẩm quyền duy nhất (*single source of truth*) tuân thủ thể thức Cơ bản – Tổng lực, bàn cờ $11 \times 12$ ô, 11 binh chủng quân sự (Bộ binh, Xe tăng, Pháo binh, Tên lửa, Phòng không, Máy bay, Hải quân...), mô phỏng chính xác tương tác địa hình (Sông, Biển, Đất liền, Vùng cản) và cơ chế vận tải quân.
2. **Hiện thực hóa Hệ sinh thái AI đa tầng:** Phát triển từ các tác tử nền tảng (Random, Rule-Based), tìm kiếm heuristic (CCHEF 6 đặc trưng), tìm kiếm đối kháng cổ điển (Minimax, Alpha-Beta Pruning với Move Ordering) đến tìm kiếm ngẫu nhiên có định hướng (MCTS / UCT).
3. **Thực nghiệm Đánh giá Khoa học Khắt khe:** Thực hiện chuỗi 13 bài thực nghiệm kiểm chứng chức năng, giải đấu đối đầu cân bằng màu quân (*side balance*), phân tích triệt tiêu (*ablation studies*), phân tích độ nhạy (*sensitivity analysis*), ghi nhận log và biểu đồ chuẩn ấn phẩm 300 DPI đồng bộ với Weights & Biases (W&B).
4. **Trải nghiệm Web Thống nhất & Trực quan:** Nền tảng Web hiện đại cho phép Người chơi đấu với AI, AI đấu với AI, xem lại ván đấu (*replay*), trực quan hóa cây tìm kiếm đối kháng và bảng số liệu phân tích chuyên sâu.

---

## Cấu trúc Toàn diện của Repository

Dự án được cấu trúc theo mô hình **Modular Monorepo**, phân định ranh giới nghiêm ngặt giữa bộ máy luật chơi, tác tử AI, không gian thực nghiệm khoa học và ứng dụng web người dùng:

```text
Commander-Chess-AI/
├── AGENTS.md                                # Quy chuẩn chỉ đạo phát triển, bảo vệ Game Engine và tính trung thực học thuật
├── README.md                                # Tài liệu giới thiệu tổng quan và cấu trúc repository
├── pyproject.toml                           # Cấu hình gói và dependencies của dự án Python
├── pytest.ini                              # Cấu hình kiểm thử tự động pytest
├── docker-compose.yml                       # Cấu hình container hóa dịch vụ Web & API
├── .env.example                             # Mẫu biến môi trường (W&B API Key, Port, v.v.)
│
├── packages/                                # CÁC GÓI MÃ NGUỒN CỐT LÕI (CORE PACKAGES)
│   ├── commander_game_engine/               # Bộ máy luật chơi thẩm quyền duy nhất (Authoritative Game Engine)
│   │   ├── board.py                         # Bàn cờ 11x12, hệ tọa độ và phân vùng địa hình (Đất, Sông, Biển)
│   │   ├── game_state.py                    # Mô hình trạng thái GameState, Quân cờ (Piece), Người chơi, validation bất biến
│   │   ├── actions.py                       # Định nghĩa các loại hành động (Di chuyển, Tấn công, Bắn hỏa lực, Tải quân...)
│   │   ├── move_generator.py                # Sinh danh sách nước đi hợp lệ (Strict legal move generation)
│   │   ├── rules.py                         # Hệ thống quy tắc ràng buộc (Vùng cản, tầm bắn, phòng không, tải quân)
│   │   ├── engine.py                        # Bộ thực thi chuyển đổi trạng thái (apply_action, preview_action)
│   │   └── initial_setup.py                 # Thiết lập bàn cờ ban đầu (19 quân Đỏ vs 19 quân Xanh)
│   │
│   └── agents/                              # Thư viện Tác tử AI (AI Agents Library)
│       ├── base.py                          # Giao thức BaseAgent chuẩn hóa, đo đạc thời gian và kiểm soát ngoại lệ
│       ├── agent_protocol.md                # Bản đặc tả kỹ thuật giao thức tương tác giữa Agent và Engine
│       ├── random_agent.py                  # Tác tử Cấp 0: Chọn nước đi ngẫu nhiên đồng đều (Baseline)
│       ├── rule_based_agent.py              # Tác tử Cấp 1: Hệ luật chuyên gia ưu tiên (Chiếu bắt Tư lệnh > Bắt quân)
│       ├── heuristic_agent.py               # Tác tử Cấp 2: Đánh giá vị thế dựa trên hàm mục tiêu CCHEF
│       ├── minimax_agent.py                 # Tác tử Cấp 3: Tìm kiếm đối kháng Minimax kết hợp cắt tỉa ứng viên
│       ├── alpha_beta_agent.py              # Tác tử Cấp 4: Cắt tỉa Alpha-Beta Pruning tối ưu hóa bằng Move Ordering
│       ├── tree_exporter.py                 # Trích xuất cây tìm kiếm ra JSON và vẽ sơ đồ cây cắt tỉa nhánh
│       └── evaluation/                      # Mô-đun lượng giá vị thế
│           └── cchef.py                     # Hàm đánh giá CCHEF 6 nhóm đặc trưng chiến thuật
│
├── research/                                # KHÔNG GIAN THỰC NGHIỆM KHOA HỌC (RESEARCH LAB)
│   ├── experiments/                         # Chuỗi Notebook thực nghiệm theo tiến trình nghiên cứu
│   │   ├── 01_board_testing.ipynb           # Khảo sát bàn cờ, hệ tọa độ và thuộc tính địa hình
│   │   ├── 02_game_state_testing.ipynb      # Kiểm thử tính toàn vẹn GameState, deepcopy và cơ chế chở quân
│   │   ├── 03_action_testing.ipynb          # Kiểm thử phân loại và đóng gói hành động
│   │   ├── 04_rules_testing.ipynb           # Kiểm chứng quy tắc di chuyển, cản trở và tầm tác chiến
│   │   ├── 05_move_generator_testing.ipynb  # Đo lường hiệu năng và tính đúng đắn của bộ sinh nước đi
│   │   ├── 06_engine_testing.ipynb          # Kiểm thử chuyển đổi trạng thái và điều kiện phân định thắng thua
│   │   ├── 07_test_random_agent.ipynb       # Thực nghiệm đánh giá Random Agent & tính ngẫu nhiên
│   │   ├── 08_test_rules_agent.ipynb        # Thực nghiệm đánh giá Rule-Based Agent & so sánh baseline
│   │   ├── 09_test_heuristic_agent.ipynb    # Thực nghiệm Heuristic CCHEF & Phân tích Ablation trọng số đặc trưng
│   │   ├── 10_test_minimax_agent.ipynb      # Thực nghiệm Minimax ($d=1, 2$) & Khảo sát bùng nổ phân nhánh
│   │   ├── 11_test_alphabeta_agent.ipynb    # Thực nghiệm Alpha-Beta ($d=2, 3$), đo lường hiệu quả cắt tỉa
│   │   ├── 12_test_mcts.ipynb               # Thực nghiệm Monte Carlo Tree Search (MCTS/UCT)
│   │   ├── 13_compare_agents.ipynb          # Đại giải đấu tổng kết toàn bộ tác tử, xếp hạng Elo & Meta-analysis
│   │   └── common/                          # Bộ công cụ phục vụ thực nghiệm dùng chung
│   │       ├── agent_factory.py             # Nhà máy khởi tạo và ánh xạ cấu hình tác tử
│   │       ├── experiment_logger.py         # Ghi nhận kết quả, ván cờ (moves/games CSV) và checkpointing
│   │       ├── head_to_head.py              # Điều phối trận đấu đối đầu, luân phiên màu quân, kiểm soát timeout
│   │       ├── plotters.py                  # Vẽ biểu đồ khoa học chuẩn 300 DPI (Win rate, WDL, NPS, Tree)
│   │       ├── statistics.py                # Kiểm định thống kê (Wilson CI, Bootstrap CI, Chi-square)
│   │       └── wandb_integration.py         # Đồng bộ thông số và tạo artifact lưu trữ trên W&B
│   │
│   └── results/                             # Dữ liệu kết quả thực nghiệm thực tế đã kiểm chứng
│       ├── 07_test_random_agent/            # Dữ liệu ván đấu, đồ thị và bảng tóm tắt của Random Agent
│       ├── 08_test_rules_agent/             # Dữ liệu ván đấu và đồ thị của Rule-Based Agent
│       ├── 09_test_heuristic_agent/         # Dữ liệu ván đấu, tương quan CCHEF và biểu đồ Heuristic Agent
│       ├── 10_test_minimax_agent/           # Dữ liệu giải đấu Minimax và biểu đồ cây quyết định
│       ├── 11_test_alphabeta_agent/         # Dữ liệu giải đấu Alpha-Beta và sơ đồ nhánh bị cắt tỉa
│       └── nhat_ky_thi_nghiem_wandb.xlsx    # Nhật ký tổng hợp dữ liệu ván đấu và siêu tham số thực nghiệm
│
├── apps/                                    # ỨNG DỤNG TƯƠNG TÁC (APPLICATIONS)
│   ├── web/                                 # Giao diện người dùng Web (Frontend)
│   │   ├── src/                             # Mã nguồn React + TypeScript
│   │   │   ├── components/                  # Bàn cờ SVG/Canvas, quân cờ, danh sách nước đi, bảng điều khiển
│   │   │   ├── pages/                       # Dashboard, Màn chơi Play, Replay Viewer, Thống kê Tournament
│   │   │   ├── i18n/                        # Hệ thống dịch thuật song ngữ Tiếng Việt - English
│   │   │   └── services/                    # Kết nối REST API và mô phỏng State
│   │   ├── package.json                     # Quản lý thư viện UI (Tailwind CSS, Lucide Icons, Vite)
│   │   └── vite.config.ts                   # Cấu hình biên dịch Vite
│   │
│   └── api/                                 # Máy chủ ứng dụng (Backend API)
│       ├── src/                             # Mã nguồn Python + FastAPI
│       │   ├── routes/                      # Định tuyến API: khởi tạo ván đấu, đi nước cờ, truy vấn replay
│       │   ├── schemas/                     # Khung dữ liệu Pydantic trao đổi theo chuẩn API_CONTRACT.md
│       │   └── main.py                      # Điểm khởi chạy ứng dụng FastAPI
│       └── tests/                           # Kiểm thử tích hợp API endpoints
│
├── workers/                                 # TIẾN TRÌNH NỀN (BACKGROUND WORKERS)
│   └── tournament-runner/                   # Trình chạy tự động giải đấu quy mô lớn (Batch Tournament Runner)
│
├── tests/                                   # BỘ KIỂM THỬ HỆ THỐNG ĐỘC LẬP (INTEGRATION & FUZZ TESTS)
│   ├── test_rule_scenarios.py               # Kiểm thử kịch bản luật đặc biệt (chở quân, bắn vượt địa hình, phong tỏa)
│   ├── test_agents.py                       # Kiểm thử tính hợp lệ và thời gian đáp ứng của các Agent
│   ├── test_heuristic_cchef.py              # Kiểm thử tính đơn điệu và tính cân đối của hàm mục tiêu CCHEF
│   └── test_invariant_fuzzing.py            # Fuzzing tự động phát hiện vi phạm bất biến trạng thái
│
└── docs/                                    # HỆ THỐNG TÀI LIỆU KỸ THUẬT VÀ QUY CHUẨN
    ├── PRD.md                               # Yêu cầu sản phẩm chi tiết (Product Requirement Document)
    ├── ARCHITECTURE.md                      # Kiến trúc tổng thể Monorepo, luồng dữ liệu và phân tách trách nhiệm
    ├── GAME_RULES.md                        # Đặc tả toàn diện luật chơi Cờ Tư Lệnh đã được nghiệm thu
    ├── API_CONTRACT.md                      # Hợp đồng giao tiếp dữ liệu chuẩn giữa Web UI và Backend API
    ├── CCHEF_Heuristic_Co_Tu_Lenh.md        # Cơ sở lý thuyết và công thức toán học của hàm lượng giá CCHEF
    ├── DECISIONS.md                         # Quyết định kiến trúc kỹ thuật và giải quyết xung đột luật chơi
    └── DEVELOPMENT.md                       # Hướng dẫn chi tiết thiết lập môi trường và quy trình đóng góp
```

---

## Hệ thống Tác tử AI (AI Agents Hierarchy)

Các tác tử được xây dựng và phân cấp theo độ phức tạp lý thuyết và năng lực chiến thuật:

| Cấp độ | Tác tử | Phương pháp thuật toán | Đặc điểm chính |
| :--- | :--- | :--- | :--- |
| **Level 0** | `RandomAgent` | Ngẫu nhiên phân phối đều | Chọn ngẫu nhiên trong tập nước đi hợp lệ; dùng làm Baseline tối thiểu |
| **Level 1** | `RuleBasedAgent` | Hệ chuyên gia (*Rule-based System*) | Ưu tiên theo bậc: Sát ván Tư lệnh $\rightarrow$ Bảo vệ Tư lệnh $\rightarrow$ Ăn quân có lời $\rightarrow$ Phát triển lực lượng |
| **Level 2** | `HeuristicAgent` | Tìm kiếm nông kết hợp hàm CCHEF | Tối ưu hóa hàm đánh giá 6 thành phần: Chênh lệch quân lực, Đe dọa Tư lệnh, An toàn phòng thủ, Khả năng cơ động, Hậu cần chở quân và Kiểm soát đường sông |
| **Level 3** | `MinimaxAgent` | Tìm kiếm đối kháng Minimax | Duyệt toàn bộ không gian trạng thái ở độ sâu $d=1, 2$, hỗ trợ cắt tỉa nhánh hẹp (*Candidate Pruning $k$*) |
| **Level 4** | `AlphaBetaAgent` | Tìm kiếm đối kháng với $\alpha$-$\beta$ Cutoff | Cắt tỉa nhánh không triển vọng ($\beta \le \alpha$), tăng tốc bằng kỹ thuật **Sắp xếp nước đi (Move Ordering)**, mở rộng an toàn lên độ sâu $d=3$ |
| **Level 5** | `MCTSAgent` | Monte Carlo Tree Search (UCT) | Tìm kiếm cây Monte Carlo cân bằng giữa Khai phá (*Exploration*) và Khai thác (*Exploitation*), áp dụng Rollout đánh giá ngẫu nhiên có dẫn dắt |

---

## Tiến trình Thực nghiệm Khoa học (Research & Experiments)

Mỗi bài thực nghiệm trong thư mục `research/experiments/` được thiết kế theo đúng quy trình nghiên cứu khoa học chuẩn:

1. **Kiểm thử chức năng bắt buộc:** Đảm bảo 100% nước đi trả về nằm trong danh sách nước đi hợp lệ (`legal_actions`), trạng thái không bị đột biến ngoài ý muốn (*immutability*), và kết quả tái lập tuyệt đối với cùng một bộ hạt giống (*deterministic reproducibility*).
2. **Giải đấu đối đầu chính thức (*Head-to-head Tournament*):** Tổ chức thi đấu với tất cả các đối thủ nền tảng ở hai chế độ ngân sách:
   * **Default:** Tự do theo tài nguyên tính toán mặc định.
   * **Controlled (1000 ms):** Khống chế trần thời gian thực thi nghiêm ngặt nhằm kiểm tra độ ổn định dưới áp lực thời gian.
3. **Phân tích Triệt tiêu & Độ nhạy (*Ablation & Sensitivity Analysis*):** Tách biệt từng đóng góp của độ sâu tìm kiếm, kỹ thuật sắp xếp nước đi, ngân sách số nút tối đa (`max_nodes`), và ma trận trọng số hàm đánh giá.
4. **Trực quan hóa Dữ liệu & Xuất bản:** Toàn bộ dữ liệu được trích xuất thành bảng số liệu thống kê (điểm số, tỷ lệ thắng/hòa/thua, khoảng tin cậy Wilson 95%, NPS, thời gian ra quyết định trung vị và P95) cùng hệ thống biểu đồ chất lượng cao 300 DPI và sơ đồ cây tìm kiếm trực quan.

---

## Hướng dẫn Cài đặt & Khởi chạy Nhanh

### Yêu cầu Tiên quyết
* Python 3.10 trở lên
* Node.js 18+ và npm / pnpm
* Git

### 1. Thiết lập Môi trường Python
```bash
# Khởi tạo và kích hoạt môi trường ảo
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Linux / macOS:
# source .venv/bin/activate

# Nâng cấp pip và cài đặt gói dự án ở chế độ phát triển (editable mode)
pip install --upgrade pip
pip install -e .
pip install -r research/requirements.txt
```

### 2. Khởi chạy Ứng dụng Web & API Backend

#### Chạy Backend API (FastAPI):
```bash
# Khởi chạy máy chủ API tại http://localhost:8000
python -m uvicorn apps.api.src.main:app --reload --host 127.0.0.1 --port 8000
```
Tài liệu tương tác Swagger UI có thể truy cập tại: `http://localhost:8000/docs`.

#### Chạy Frontend Web (React + Vite):
```bash
cd apps/web
npm install
npm run dev
```
Truy cập giao diện tại: `http://localhost:5173`. Giao diện hỗ trợ chuyển đổi ngôn ngữ **Tiếng Việt** và **English** tức thì ở góc trên bên phải.

### 3. Chạy Kiểm thử Tự động (Test Suite)
```bash
# Chạy toàn bộ các ca kiểm thử tích hợp và kiểm thử luật chơi
pytest -v
```

### 4. Thực thi Thực nghiệm Khoa học
Khởi chạy Jupyter Notebook hoặc JupyterLab để quan sát và chạy các bài thực nghiệm:
```bash
jupyter lab
```
Mở các notebook trong thư mục `research/experiments/` (ví dụ: `10_test_minimax_agent.ipynb` hoặc `11_test_alphabeta_agent.ipynb`) và thực thi từng bước. Toàn bộ tiến trình sẽ được tự động lưu checkpoint để có thể khôi phục bất cứ lúc nào.

---

## Tài liệu Kỹ thuật Tham khảo

Để nắm rõ các khía cạnh chuyên sâu của dự án, vui lòng đọc các tài liệu kỹ thuật trong thư mục `docs/`:

* [`docs/GAME_RULES.md`](docs/GAME_RULES.md): Toàn bộ luật Cờ Tư Lệnh (đặc tính quân cờ, tầm bắn, phòng không, quy tắc sông biển, chuyên chở quân).
* [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md): Kiến trúc Monorepo, hợp đồng phân quyền và nguyên tắc thiết kế dữ liệu.
* [`docs/API_CONTRACT.md`](docs/API_CONTRACT.md): Hợp đồng giao tiếp chi tiết giữa Web Frontend và Backend API.
* [`packages/agents/agent_protocol.md`](packages/agents/agent_protocol.md): Chuẩn giao thức thiết kế lớp Tác tử AI.
* [`docs/CCHEF_Heuristic_Co_Tu_Lenh.md`](docs/CCHEF_Heuristic_Co_Tu_Lenh.md): Công thức toán học và trọng số của hàm đánh giá CCHEF.
* [`docs/PRD.md`](docs/PRD.md): Yêu cầu kỹ thuật và lộ trình phát triển sản phẩm.

---

## Giấy phép & Bản quyền (License)

Dự án được phân phối dưới giấy phép [MIT License](LICENSE).  
Mọi nghiên cứu và ứng dụng kế thừa xin vui lòng ghi rõ nguồn trích dẫn từ đề tài nghiên cứu môn **Trí Tuệ Nhân Tạo Nâng Cao (2026) — Trường Đại học Sài Gòn**.
