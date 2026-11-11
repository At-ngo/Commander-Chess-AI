# KẾ HOẠCH KIỂM THỬ VÀ THỰC NGHIỆM: RANDOM, RULE-BASED, HEURISTIC AGENTS

**Dự án:** AI Cờ Tư Lệnh  
**Phạm vi:** `test_random_agent.ipynb`, `test_rules_agent.ipynb`, `test_heuristic_agent.ipynb`  
**Trạng thái:** Checklist triển khai, **không phải kết quả đã chạy**.

> **Nguồn yêu cầu:** Tài liệu *Đề tài cuối kỳ môn Trí tuệ nhân tạo nâng cao – Xây dựng và đánh giá Game AI đa cấp độ*, chủ yếu các mục 3.2, 3.4–3.6, 3.7 và Chương 4. Trong đó: Random phải chọn đều nước hợp lệ; Rule-based/Heuristic cần ưu tiên thắng, chặn, kiểm soát và giải thích xung đột luật. Giải đối kháng cần round-robin ít nhất **200 ván/cặp**, chia đều quyền đi trước, dùng nhiều seed, báo cáo W/D/L, Score, mean/p95, ma trận, khoảng tin cậy và có **ít nhất 2 ablation/sensitivity analysis trong toàn đồ án**. Các con số cấu hình dưới đây là **đề xuất**.

## 0. Quy ước chung trước khi thử nghiệm

### 0.1. Điều kiện bắt đầu

- [ ] Game Engine ổn định, có `reset()`, `legal_actions()`, `step(action)`, `is_terminal()`, `result()` và clone/cơ chế bảo vệ state.
- [ ] Test luật và trạng thái kết thúc của Cờ Tư Lệnh đã đạt; xác nhận đội hình ban đầu, quân Đỏ đi trước, luật hòa và điểm.
- [ ] Có API chung cho Agent nhận `GameState` và `legal_actions`, trả về **một action hợp lệ** và (nếu hỗ trợ) metadata đo lường.
- [ ] Quy ước rõ **một nước/hành động** và **một lượt**: với hành động ghép/vận tải, không được đánh đồng số hành động nguyên tử và số lượt người chơi.
- [ ] Agent không tự sửa đổi `GameState`, không trả nước nằm ngoài `legal_actions`; danh sách rỗng/trạng thái kết thúc được xử lý rõ.
- [ ] Có cách xác định chiến thắng/thua/hòa và nguyên nhân kết thúc (`termination_reason`).
- [ ] Không tự gán hòa khi đạt `max_moves`/timeout kiểm thử; phải phân loại `truncated`/`timeout` riêng, trừ khi luật game đã quy định kết quả tương ứng.
- [ ] Cố định mã Git commit, phiên bản luật/engine, Python, thư viện và phần cứng.

### 0.2. Cấu hình cho mỗi lượt chạy

| Trường | Nội dung cần lưu |
|---|---|
| `experiment_id`, `run_id` | Định danh thực nghiệm và lần chạy |
| `agent_name`, `agent_version` | Tên, phiên bản/commit Agent |
| `opponent_name`, `opponent_version` | Đối thủ |
| `agent_config` | Seed, ưu tiên luật hoặc trọng số |
| `engine_version`, `rules_version`, `git_commit` | Khả năng tái lập |
| `python_version`, `dependencies` | Môi trường phần mềm |
| `cpu`, `gpu`, `ram_total`, `device` | Môi trường phần cứng |
| `seed`, `opening_config` | Hạt giống và thiết lập thế cờ |
| `games_per_pair`, `color_assignment` | Số ván và đảo màu |
| `budget_mode`, `time_budget_ms` | Chế độ mặc định hoặc giới hạn tính toán |
| `move_limit`, `time_control` | Giới hạn áp dụng, nếu có |

**Lưu ý:** Đề bài yêu cầu **hai chế độ đánh giá**: (A) cấu hình mặc định minh bạch và (B) ngân sách tính toán quy định rõ. Với Random/Rule-based/Heuristic, ngân sách suy luận có thể không phải yếu tố chi phối; vẫn cần ghi thời gian thực tế và mô tả cách áp dụng chế độ B, không ép các Agent phải tiêu hết thời gian cho phép.

### 0.3. Quy ước số ván và seed

- [ ] Cho từng cặp Agent 200 ván.
- [ ] Cân bằng đi trước: 50% Agent A Đỏ, 50% Agent A Xanh.
- [ ] Có nhiều seed; lưu seed từng ván. Có thể thiết kế các **cặp ván cùng seed, đảo màu** để so sánh.
- [ ] Nếu một Agent dùng seed thì cần xác định seed điều khiển Agent nào, engine nào và cách tránh hai RNG gây ảnh hưởng nhau.
- [ ] Quy định trước chính sách xử lý ván lỗi, timeout, huỷ giữa chừng; không loại bỏ chỉ vì kết quả không thuận lợi.
- [ ] Không dùng kết quả **test cuối cùng** để điều chỉnh trọng số heuristic hoặc ưu tiên rule. Dùng tập tuning/validation riêng.

### 0.4. Schema log tối thiểu

**`moves.csv`** — một dòng cho **một lần ra quyết định**:

| Cột | Giải thích |
|---|---|
| `run_id`, `game_id`, `decision_index` | Liên kết kết quả |
| `side`, `agent_name`, `agent_config_id` | Ai quyết định |
| `state_hash`, `legal_action_count` | Vị trí và branching factor (khuyến nghị) |
| `selected_action` | Biểu diễn có thể replay |
| `decision_time_ms` | Phép đo chính của mean/p95 |
| `rule_triggered` | Với Rule-based; có thể rỗng với Random |
| `heuristic_score`, `heuristic_components` | Với Heuristic; có thể rỗng |
| `nodes_visited`, `simulations` | Để trống/NA nếu không áp dụng, **không ghi 0 gây hiểu nhầm** |
| `valid_action`, `error` | Kiểm tra hợp lệ, lỗi phát sinh |

**`games.csv`** — một dòng cho một ván:

`run_id,game_id,seed,agent_red,agent_blue,winner,result_status,termination_reason,total_decisions,total_atomic_actions,duration_sec,red_game_points,blue_game_points,game_record_path`

`result_status` nên phân biệt `completed`, `timeout`, `truncated`, `error`. Chỉ tính Score 1/0.5/0 theo quy ước kết quả hợp lệ đã công bố; trường hợp chưa xác định cần được báo cáo riêng.

**`pair_results.csv`** — một dòng cho một cặp Agent và chế độ:

`run_id,agent_a,agent_b,budget_mode,games_completed,wins_a,draws,losses_a,win_rate_a,draw_rate,loss_rate_a,score_a,score_ci_low,score_ci_high,mean_decision_ms_a,p95_decision_ms_a,mean_decision_ms_b,p95_decision_ms_b`

**Công thức:** `score = (wins + 0.5 * draws) / games_completed`. Có thể dùng Wilson 95% CI cho **tỷ lệ thắng nhị phân** và Bootstrap 95% CI cho **Score (1/0.5/0)**. Nếu ghép seed/đảo màu, ưu tiên bootstrap theo cặp ván/cluster phù hợp; lưu phương pháp CI và số mẫu bootstrap.

### 0.5. Mỗi notebook cần có cùng 8 phần

1. **I. Import thư viện** — import Python, Engine, Agent và `research.common`.
2. **II. Cấu hình thực nghiệm** — mục tiêu, giả thuyết, seed, đối thủ, số ván, ngân sách và cấu hình chung ở `config.py`.
3. **III. Khởi tạo Engine và Agent** — tạo state, Agent và smoke test.
4. **IV. Kiểm thử chức năng** — unit/scenario/invariant tests riêng Agent.
5. **V. Chạy thực nghiệm** — một ván để debug, sau đó nhiều ván; đổi màu và nhiều seed.
6. **VI. Thu thập và lưu dữ liệu** — moves/games/pairs/config/log lỗi.
7. **VII. Trực quan hóa** — W/D/L, mean/p95, biểu đồ đặc thù.
8. **VIII. Nhận xét và kết luận** — trả lời giả thuyết, hạn chế, tình huống điển hình.

---

## 1. `05_test_random_agent.ipynb`

**Mục tiêu:** Xác nhận Random Agent **chọn đều trong danh sách nước đi hợp lệ** và làm baseline đối chứng trung thực.

**Giả thuyết cần kiểm chứng:** (H1) Mọi action được chọn đều hợp lệ; (H2) cùng seed/cùng chuỗi đầu vào tái lập được; (H3) phân phối lựa chọn gần đều trong mẫu đủ lớn; (H4) state không bị thay đổi bởi bước chọn action.

### I. Import thư viện
- [ ] Cell Markdown: `I. IMPORT THƯ VIỆN`
- [ ] Cell Code: **Code** — `random`, `time`, `numpy`, `pandas`, Engine, RandomAgent, common metrics/logging/visualization.

### II. Cấu hình thực nghiệm
- [ ] Cell Markdown: `II. CẤU HÌNH THỰC NGHIỆM`
- [ ] Cell Code: **Code** — seed list, số lần lấy mẫu phân phối, 100/200 ván/cặp, giới hạn chạy an toàn, chế độ ngân sách.

### III. Khởi tạo Engine và Random Agent
- [ ] Cell Markdown: `III. KHỞI TẠO ENGINE VÀ RANDOM AGENT`
- [ ] Cell Code: **Code** — state hợp lệ, danh sách legal actions, Agent seeded.

### IV. Kiểm thử chức năng
- [ ] `4.1. Legal action`: tại nhiều trạng thái, action trả về thuộc `legal_actions`.
- [ ] `4.2. Empty/terminal state`: xử lý đúng khi không còn action; không trả action giả.
- [ ] `4.3. Không đột biến`: state và `legal_actions` đầu vào không bị sửa.
- [ ] `4.4. Seed reproducibility`: cùng seed + cùng chuỗi trạng thái → cùng chuỗi lựa chọn; seed khác không bắt buộc cho kết quả khác trong mọi lần.
- [ ] `4.5. Uniform distribution`: cố định một trạng thái có nhiều action; thử nhiều lần; đếm tần suất, vẽ histogram, cân nhắc kiểm định chi-square với điều kiện tần suất kỳ vọng phù hợp.
- [ ] `4.6. Compound action`: xác nhận action ghép là một lựa chọn hợp lệ khi engine có hỗ trợ.
- [ ] `4.7. Full-game invariant`: Random vs Random nhiều ván; không xuất hiện action bất hợp lệ, trùng vị trí không hợp lệ, thay đổi số quân vô cớ hay trạng thái bất nhất.

### V. Chạy thực nghiệm
- [ ] Một ván `Random vs Random` để kiểm tra replay và kết thúc.
- [ ] Nhiều ván `Random vs Random` với nhiều seed (self-play baseline); lưu cả hai vai trò.
- [ ] Khi Rule-based và Heuristic đã hoàn thiện: `Random vs Rule-based`, `Random vs Heuristic` theo round-robin và đổi màu.
- [ ] Chạy chế độ default và chế độ ngân sách có mô tả rõ.

### VI. Thu thập kết quả
- [ ] `moves.csv`: action, latency, legal count, seed, valid_action.
- [ ] `games.csv`: winner, termination reason, số lượt, duration, seed, replay path.
- [ ] `pair_results.csv`: W/D/L, Score, CI, mean/p95 theo Agent.
- [ ] `uniformity_test.json`: số action, tần suất, số mẫu, p-value (nếu dùng), seed.
- [ ] Ghi số lần error/timeout/truncated riêng, không giấu hoặc ép thành hòa.

### VII. Trực quan hóa
- [ ] Tần suất chọn từng action (trên một trạng thái cố định).
- [ ] W/D/L, Score kèm CI.
- [ ] Phân phối số lượt mỗi ván, `decision_time_ms` và p95.
- [ ] Tỷ lệ thắng theo màu Đỏ/Xanh (khi đấu với Agent khác).

### VIII. Nhận xét
- [ ] Random chọn đều **trên action hợp lệ**, không có nghĩa mọi quân cờ được chọn đều nhau.
- [ ] Ghi các lỗi engine/Agent phát hiện được và cách tái lập.
- [ ] Kết luận Random đạt/không đạt vai trò baseline; không khẳng định thông minh chỉ vì một chuỗi thắng.

**Điều kiện nghiệm thu:** Tất cả test chức năng pass; có file log có thể replay; có bảng metric baseline; code chạy lại được từ seed/config.

---

## 2. `06_test_rules_agent.ipynb`

**Mục tiêu:** Chứng minh Rule-based Agent ra quyết định theo **thứ tự ưu tiên luật minh bạch**, xử lý xung đột đúng, thực hiện các quyết định chiến thuật cơ bản và đánh giá ảnh hưởng của **quy tắc chiếu Tư lệnh đối phương** thông qua Ablation Study.

**Câu hỏi nghiên cứu:**

1. Rule-based Agent có cải thiện kết quả thi đấu so với Random Agent không?
2. Việc bổ sung quy tắc ưu tiên chiếu Tư lệnh có cải thiện Score và Win Rate không?
3. Quy tắc chiếu có khiến Agent mất quân hoặc bỏ lỡ các cơ hội chiến thuật khác không?

### I–III. Import, cấu hình, khởi tạo

- [ ] Cell Markdown: I. IMPORT THƯ VIỆN → Cell Code: **Code**.
- [ ] Cell Markdown: II. CẤU HÌNH → Cell Code: **Code**.
- [ ] Cell Markdown: III. KHỞI TẠO RULE-BASED AGENT → Cell Code: **Code**.
- [ ] Thiết lập seed, tie-breaking, fallback, phiên bản ruleset.
- [ ] Hỗ trợ `enable_check_rule = True/False`.
- [ ] Khởi tạo hai cấu hình `Ruleset_A` và `Ruleset_B`.
- [ ] Lưu phiên bản ruleset và cấu hình trong log.
- [ ] Phân biệt **quy tắc lựa chọn nước đi của Agent** với **luật hợp lệ của Game Engine**.

### IV. Kiểm thử chức năng

**4.1. Luật 1 – Thắng ngay (chiếu hết)**

- [ ] Dựng trạng thái có ít nhất một nước thắng ngay hợp lệ.
- [ ] Agent phải ưu tiên nước thắng ngay.
- [ ] Không nhầm nước chiếu thông thường với nước chiếu hết.
- [ ] Kiểm tra theo điều kiện kết thúc thực tế của Game Engine.

**4.2. Luật 2 – Bảo vệ Tư lệnh**

- [ ] Dựng trạng thái Tư lệnh đang bị chiếu hoặc bị đe dọa.
- [ ] Kiểm tra Agent lựa chọn hành động phòng thủ phù hợp.
- [ ] Không chọn nước khiến Tư lệnh rơi vào trạng thái bất hợp lệ.
- [ ] Nếu nhiều cách phòng thủ, kiểm tra cơ chế lựa chọn giữa các phương án.
- [ ] Trường hợp không thể phòng thủ, phải xử lý đúng điều kiện kết thúc.

**4.3. Luật 3 – Chiếu Tư lệnh đối phương (chỉ Ruleset B)**

- [ ] Dựng trạng thái có nước chiếu hợp lệ.
- [ ] Kiểm tra Agent phát hiện và ưu tiên nước chiếu.
- [ ] Phân biệt nước chiếu an toàn và nước chiếu khiến quân tấn công bị ăn ngay.
- [ ] Kiểm tra trạng thái có nhiều nước chiếu khác nhau.
- [ ] Kiểm tra nước chiếu đồng thời ăn quân.
- [ ] Kiểm tra tình huống chiếu nhưng bỏ lỡ cơ hội ăn quân giá trị cao.
- [ ] Khi `enable_check_rule = False`, xác nhận Luật 3 không tham gia lựa chọn.
- [ ] Ghi nhận kết quả sau nước chiếu: đối phương phản ứng ra sao, quân chiếu có bị mất không.

**4.4. Luật 4 – Ăn quân có giá trị cao**

- [ ] Dựng trạng thái có nhiều hành động ăn quân.
- [ ] Kiểm tra Agent ưu tiên quân có giá trị cao nhất theo bảng giá trị công bố.
- [ ] Xử lý trường hợp hai quân có cùng giá trị.
- [ ] Kiểm tra tình huống ăn quân nhưng quân tấn công có nguy cơ bị ăn lại.
- [ ] Xác định rõ cách xử lý khi một nước ăn đồng thời tạo chiếu.

**4.5. Luật 5 – Chạy quân giá trị cao khi bị đe dọa**

- [ ] Dựng trạng thái một quân giá trị cao có nguy cơ bị ăn.
- [ ] Kiểm tra Agent nhận diện nguy cơ.
- [ ] Kiểm tra Agent lựa chọn nước tránh mất quân theo quy tắc.
- [ ] Kiểm tra tình huống có nhiều quân cùng bị đe dọa.
- [ ] Kiểm tra tình huống chạy quân làm mất cơ hội tấn công.

**4.6. Luật 6 – Đi ngẫu nhiên (Fallback)**

- [ ] Khi không có quy tắc chiến thuật nào kích hoạt, Agent chọn ngẫu nhiên trong các nước hợp lệ.
- [ ] Kiểm tra tái lập kết quả bằng seed.
- [ ] Không trả về nước bất hợp lệ.
- [ ] Ghi `rule_triggered = FALLBACK`.

**4.7. Kiểm tra xung đột và thứ tự ưu tiên**

- [ ] Thắng ngay và chiếu thông thường cùng xuất hiện.
- [ ] Bảo vệ Tư lệnh và ăn quân cùng xuất hiện.
- [ ] Chiếu Tư lệnh và ăn quân có giá trị cao cùng xuất hiện.
- [ ] Chiếu Tư lệnh và chạy quân có giá trị cao cùng xuất hiện.
- [ ] Nhiều quy tắc cùng kích hoạt nhưng Agent tuân thủ thứ tự ưu tiên.
- [ ] Ghi lại danh sách quy tắc thỏa mãn và quy tắc được chọn.

**4.8. Kiểm thử chung**

- [ ] Empty/terminal state.
- [ ] Không đột biến GameState.
- [ ] Không chọn ngoài danh sách legal actions.
- [ ] Tie-breaking nhất quán với cấu hình.
- [ ] Xử lý hành động đặc thù: máy bay, phòng không, hải quân, vận tải.
- [ ] Ghi trace giải thích nguyên nhân chọn nước đi.

### V. Chạy thực nghiệm

**5.1. Smoke Test**

- [ ] Chạy một ván Ruleset A vs Random.
- [ ] Chạy một ván Ruleset B vs Random.
- [ ] Kiểm tra kết thúc ván, log nước đi và kết quả.

**5.2. Benchmark: Rule-based vs Random**

- [ ] Ruleset A vs Random: tối thiểu 100 ván.
- [ ] Ruleset B vs Random: tối thiểu 100 ván.
- [ ] Mỗi cấu hình chia đều 50% Đỏ và 50% Xanh.
- [ ] Sử dụng danh sách seed xác định trước.
- [ ] Giữ nguyên Game Engine và điều kiện thi đấu.

**5.3. Ablation Study – Ảnh hưởng của Luật 3**

**Giả thuyết H1:** Bật Luật 3 có thể giúp Agent tạo thêm áp lực lên Tư lệnh đối phương và cải thiện kết quả thi đấu.

- [ ] Cấu hình A: `enable_check_rule = False`.
- [ ] Cấu hình B: `enable_check_rule = True`.
- [ ] Giữ nguyên tất cả các quy tắc và tham số còn lại.
- [ ] Đánh giá A và B trước cùng đối thủ Random.
- [ ] Sử dụng cùng danh sách seed và cân bằng màu quân.
- [ ] Đối đầu trực tiếp Ruleset A vs Ruleset B, tối thiểu 100 ván, đổi màu cân bằng.
- [ ] Sau khi có Heuristic, đánh giá A/B trước cùng Heuristic Agent.
- [ ] So sánh Score, Win Rate, thời gian quyết định và các chỉ số chiến thuật.
- [ ] Tính khoảng tin cậy cho chênh lệch Score.

**5.4. Stress Test**

- [ ] Ruleset A vs Ruleset A.
- [ ] Ruleset B vs Ruleset B.
- [ ] Kiểm tra tính ổn định và các tình huống lặp lại.
- [ ] Kiểm tra các ván kéo dài hoặc không có tiến triển.

**5.5. Chế độ ngân sách**

- [ ] Chạy cấu hình mặc định.
- [ ] Chạy chế độ ngân sách tính toán được quy định rõ.
- [ ] Ghi trường hợp Agent vượt ngân sách.
- [ ] Không thay đổi ruleset trong cùng một lượt đánh giá.

### VI. Thu thập kết quả

**6.1. Game Log và Move Log**

- [ ] `games.csv`: kết quả từng ván.
- [ ] `moves.csv`: dữ liệu từng nước.
- [ ] `pair_results.csv`: tổng hợp từng cặp.
- [ ] `game_records/game_XXXX.json`: biên bản đầy đủ.
- [ ] Lưu cấu hình và phiên bản ruleset.

**6.2. Chỉ số thi đấu**

- [ ] Wins / Draws / Losses.
- [ ] Win Rate / Draw Rate / Loss Rate.
- [ ] Score = (Wins + 0,5 × Draws) / Games.
- [ ] Wilson/Bootstrap Confidence Interval.
- [ ] Thời gian trung bình một nước.
- [ ] Độ trễ p95.
- [ ] Số lượt trung bình một ván.

**6.3. Chỉ số đặc thù Rule-based**

- [ ] `rule_triggered`: quy tắc quyết định nước đi.
- [ ] `rule_candidates`: những hành động thỏa quy tắc.
- [ ] `rule_priority`: mức ưu tiên.
- [ ] `rule_conflicts`: các quy tắc cùng thỏa mãn.
- [ ] `fallback_count`: số lần phải chọn ngẫu nhiên.
- [ ] `check_opportunities`: số cơ hội chiếu phát hiện được.
- [ ] `check_moves`: số nước chiếu được thực hiện.
- [ ] `unsafe_check_moves`: số nước chiếu bị phân loại không an toàn theo tiêu chí công bố.
- [ ] `check_followed_by_loss`: số nước chiếu dẫn đến mất quân chiếu ngay lượt đối phương.
- [ ] `missed_winning_moves`: số nước thắng ngay bị bỏ lỡ.
- [ ] `missed_defensive_moves`: số lần không xử lý được đe dọa có thể phòng thủ.
- [ ] `high_value_piece_losses`: số quân giá trị cao bị mất.

**6.4. Dữ liệu Ablation**

- [ ] Score của Ruleset A và Ruleset B.
- [ ] Chênh lệch Score: `score_B - score_A`.
- [ ] Chênh lệch Win Rate.
- [ ] Chênh lệch thời gian quyết định.
- [ ] Số nước chiếu và kết quả sau các nước chiếu.
- [ ] Số lần chiếu khiến quân tấn công bị mất.
- [ ] Số lần có cơ hội chiếu nhưng Ruleset A lựa chọn nước khác.
- [ ] Lưu những trạng thái có quyết định khác nhau giữa A và B.

### VII. Trực quan hóa

**7.1. Kết quả thi đấu**

- [ ] Biểu đồ Win / Draw / Loss.
- [ ] Biểu đồ Score kèm Confidence Interval.
- [ ] So sánh hiệu năng khi chơi Đỏ và Xanh.

**7.2. Phân tích quy tắc**

- [ ] Biểu đồ tần suất kích hoạt từng quy tắc.
- [ ] Tỷ lệ fallback.
- [ ] Tỷ lệ xảy ra xung đột luật.
- [ ] Số nước chiếu theo từng cấu hình.
- [ ] Số nước chiếu an toàn và không an toàn.

**7.3. Ablation: Ruleset A vs Ruleset B**

- [ ] Biểu đồ so sánh Score.
- [ ] Biểu đồ so sánh Win Rate.
- [ ] Biểu đồ so sánh thời gian trung bình và p95.
- [ ] Biểu đồ số nước chiếu và số quân bị mất sau khi chiếu.
- [ ] Minh họa ít nhất một tình huống A và B lựa chọn khác nhau.

### VIII. Nhận xét và kết luận

- [ ] Rule-based có cải thiện kết quả so với Random không?
- [ ] Quy tắc nào kích hoạt nhiều nhất?
- [ ] Quy tắc nào hiếm khi xuất hiện?
- [ ] Bật Luật 3 có cải thiện Score không?
- [ ] Việc ưu tiên chiếu có làm tăng nguy cơ mất quân không?
- [ ] Có trường hợp nước chiếu khiến Agent bỏ lỡ phương án tốt hơn không?
- [ ] Ruleset A hay Ruleset B ổn định hơn khi đổi màu quân?
- [ ] Kết quả có nhất quán khi thay đổi seed và đối thủ không?
- [ ] Phân biệt hạn chế chiến lược, lỗi ruleset và lỗi Game Engine.
- [ ] Kết luận có giữ Luật 3 cho Rule-based Agent chính thức hay không, dựa trên dữ liệu.

**Điều kiện nghiệm thu:**

1. Cả hai ruleset hoạt động đúng thứ tự ưu tiên.
2. Có scenario tests cho từng quy tắc.
3. Có trace giải thích nước đi được lựa chọn.
4. Có kết quả đối đầu với Random.
5. Có Ablation Study bật/tắt Luật 3.
6. Có log và cấu hình để tái lập thực nghiệm.
7. Có phân tích định lượng và ít nhất một tình huống chiến thuật điển hình.

---

## 3. `07_test_heuristic_agent.ipynb`

**Mục tiêu:** Kiểm tra hàm đánh giá định lượng, tính đúng của điểm cho các nước hợp lệ, tác động của **trọng số** và chất lượng thi đấu so với Random/Rule-based.

### I–III. Import, cấu hình, khởi tạo
- [ ] Cell Markdown: I. IMPORT THƯ VIỆN → Cell Code: **Code**.
- [ ] Cell Markdown: II. CẤU HÌNH → Cell Code: **Code** (weights, normalization, seed, tie-breaking).
- [ ] Cell Markdown: III. KHỞI TẠO HEURISTIC AGENT → Cell Code: **Code**.
- [ ] Ghi rõ heuristic tính từ **góc nhìn phe đến lượt**, trạng thái hiện tại hay trạng thái sau action.

### IV. Kiểm thử chức năng
- [ ] `4.1. Component score`: tính riêng điểm vật chất, an toàn Tư lệnh, cơ hội tấn công, kiểm soát vị trí (chỉ những thành phần đã triển khai).
- [ ] `4.2. Weighting`: đối chiếu điểm tổng với các thành phần và trọng số; kiểm tra dấu và đơn vị.
- [ ] `4.3. Legal ranking`: chỉ chấm các action hợp lệ, chọn điểm cao nhất theo quy tắc.
- [ ] `4.4. Terminal priority`: thắng/hòa/thua kết thúc được xếp đúng; không để điểm vị trí lấn át thắng ngay nếu thiết kế coi thắng là ưu tiên tuyệt đối.
- [ ] `4.5. Side consistency`: lật góc nhìn Đỏ/Xanh và đảm bảo dấu điểm hợp lý theo định nghĩa.
- [ ] `4.6. Tie-breaking`: trường hợp bằng điểm nhất quán và có seed nếu ngẫu nhiên.
- [ ] `4.7. Không đột biến`: không thay đổi state đầu vào.
- [ ] `4.8. Numerical sanity`: không NaN/Inf; không overflow trong trạng thái bình thường.
- [ ] `4.9. Scenario tests`: đòn thắng ngay, đe dọa Tư lệnh, ăn quân, phòng không, hải quân và vận tải nếu có đưa vào hàm lượng giá.

### V. Chạy thực nghiệm
- [ ] Một ván `Heuristic vs Random` để debug.
- [ ] `Heuristic vs Random`: >=100 ván/cặp, chia đều hai màu.
- [ ] `Heuristic vs Rule-based`: >=100 ván/cặp, chia đều hai màu.
- [ ] `Heuristic vs Heuristic`: test độ ổn định (bổ sung).
- [ ] **Sensitivity (gợi ý):** thay đổi lần lượt một trọng số trong các mức đã định, giữ nguyên phần còn lại; không chọn kết quả test cuối để tối ưu weights.
- [ ] **Ablation (gợi ý):** bật/tắt một thành phần (ví dụ position control) trong hàm đánh giá; so sánh trên bộ seed/tình huống giống nhau.
- [ ] Hai chế độ default/controlled budget; lưu trọng số tương ứng từng ván.

### VI. Thu thập kết quả
- [ ] Mọi cột chuẩn của moves/games/pairs.
- [ ] `heuristic_components`, `heuristic_total`, `candidate_rank` nếu có.
- [ ] `weight_config_id` và đầy đủ bộ trọng số.
- [ ] `heuristic_ablation.csv`/`heuristic_sensitivity.csv`: cấu hình, số ván, Score, CI, latency.
- [ ] Danh sách các nước được chọn có giá trị cao nhưng dẫn tới kết quả xấu để phân tích.

### VII. Trực quan hóa
- [ ] W/D/L, Score + CI theo đối thủ.
- [ ] Phân phối giá trị heuristic / top action scores.
- [ ] So sánh Mean/p95 với Random và Rule-based.
- [ ] Biểu đồ độ nhạy theo từng trọng số.
- [ ] Biểu đồ ablation (bật/tắt thành phần) nếu thực hiện.
- [ ] Kết quả theo phe Đỏ/Xanh.

### VIII. Nhận xét
- [ ] Thành phần heuristic nào hữu ích, thành phần nào tạo ra lỗi chiến thuật?
- [ ] Trọng số có ổn định qua nhiều seed không?
- [ ] So sánh chi phí quyết định và chất lượng nước đi so với Rule-based.
- [ ] Nêu rõ các kết luận chỉ đúng trong số ván, thế cờ và ngân sách thử nghiệm.

**Điều kiện nghiệm thu:** Điểm heuristic được giải thích và kiểm chứng; có kết quả thi đấu đối kháng và ít nhất một khảo sát tham số/thành phần nếu chọn thực nghiệm này cho phần ablation toàn đồ án.

---

## BỔ SUNG W&B CHO `07_test_heuristic_agent.ipynb`

### I–III. Import, cấu hình, khởi tạo

- [ ] Import thư viện `wandb` tại Cell I – IMPORT THƯ VIỆN.
- [ ] Kiểm tra trạng thái cài đặt và khả năng kết nối W&B.
- [ ] Khởi tạo W&B project: `commander-chess-ai`.
- [ ] Thiết lập `experiment_group = heuristic-agent`.
- [ ] Hỗ trợ cấu hình `use_wandb = True/False`.
- [ ] Hỗ trợ chế độ `online`, `offline` hoặc `disabled`.
- [ ] Thiết lập `run_name` riêng cho mỗi cấu hình trọng số.
- [ ] Lưu seed, cấu hình trọng số, phiên bản ruleset/game engine và Git commit.
- [ ] Lưu các tham số `normalization`, `tie_breaking`, đối thủ và số ván đấu.
- [ ] Mỗi W&B run đại diện cho một cấu hình thực nghiệm xác định, không gộp kết quả của nhiều cấu hình khác nhau.

### V. Chạy thực nghiệm – Tích hợp W&B

**5.1. Benchmark Heuristic vs Random / Rule-based**

- [ ] Khởi tạo W&B run trước khi chạy benchmark.
- [ ] Ghi thông tin Agent, đối thủ và cấu hình thực nghiệm.
- [ ] Ghi số ván đã hoàn thành.
- [ ] Theo dõi Win Rate, Draw Rate, Loss Rate và Score.
- [ ] Ghi thời gian quyết định trung bình và p95.
- [ ] Ghi nhận số lần vượt ngân sách tính toán nếu có.
- [ ] Kết thúc W&B run sau khi hoàn thành thực nghiệm.

**5.2. Sensitivity Analysis – Khảo sát trọng số**

- [ ] Thiết lập nhiều bộ trọng số thử nghiệm.
- [ ] Thay đổi một trọng số tại một thời điểm, giữ nguyên các tham số còn lại.
- [ ] Nếu có normalization, ghi rõ tác động của nó đến các trọng số khác.
- [ ] Tạo W&B run riêng cho từng cấu hình.
- [ ] Nhóm các run bằng `group = heuristic-sensitivity`.
- [ ] Lưu đầy đủ `weight_config_id` và trọng số thực tế.
- [ ] Sử dụng cùng tập seed và cùng đối thủ để so sánh.
- [ ] Theo dõi Score, Win Rate, CI và thời gian quyết định.
- [ ] Xác định mức độ nhạy của Agent với từng trọng số.
- [ ] Không sử dụng kết quả benchmark cuối cùng để lựa chọn trọng số tối ưu.

**5.3. Ablation Study – Bật/tắt thành phần heuristic**

- [ ] Thiết lập cấu hình đầy đủ (Full Heuristic).
- [ ] Thiết lập cấu hình bỏ một thành phần, chẳng hạn Position Control.
- [ ] Giữ nguyên các thành phần và tham số còn lại.
- [ ] Tạo W&B run riêng cho từng cấu hình.
- [ ] Nhóm bằng `group = heuristic-ablation`.
- [ ] So sánh Win Rate, Score, CI, Mean Latency và p95.
- [ ] Ghi nhận những tình huống hai cấu hình lựa chọn nước khác nhau.
- [ ] Đánh giá đóng góp thực tế của thành phần bị loại bỏ.

### VI. Thu thập kết quả – W&B Metrics

**6.1. Match Metrics**

- [ ] `match/wins`
- [ ] `match/draws`
- [ ] `match/losses`
- [ ] `match/win_rate`
- [ ] `match/draw_rate`
- [ ] `match/loss_rate`
- [ ] `match/score`
- [ ] `match/score_ci_low`
- [ ] `match/score_ci_high`

**6.2. Performance Metrics**

- [ ] `performance/avg_decision_ms`
- [ ] `performance/p95_decision_ms`
- [ ] `performance/max_decision_ms`
- [ ] `performance/avg_game_length`
- [ ] `performance/total_experiment_sec`
- [ ] `performance/peak_ram_mb` nếu có đo

**6.3. Heuristic Metrics**

- [ ] `heuristic/avg_capture_score`
- [ ] `heuristic/avg_safety_score`
- [ ] `heuristic/avg_position_score`
- [ ] `heuristic/avg_attack_score`
- [ ] `heuristic/avg_total_score`
- [ ] `heuristic/weight_config_id` lưu trong cấu hình hoặc bảng tổng hợp.
- [ ] Các thành phần điểm chỉ ghi khi thực sự được triển khai.

**6.4. Ablation / Sensitivity Metrics**

- [ ] `analysis/score_difference`
- [ ] `analysis/win_rate_difference`
- [ ] `analysis/latency_difference_ms`
- [ ] `analysis/score_ci_low`
- [ ] `analysis/score_ci_high`
- [ ] Lưu tên thành phần bật/tắt trong W&B config.
- [ ] Không đồng nhất CI của từng cấu hình với CI của chênh lệch giữa hai cấu hình.

**6.5. Lưu dữ liệu gốc**

- [ ] Tiếp tục lưu `moves.csv`.
- [ ] Tiếp tục lưu `games.csv`.
- [ ] Tiếp tục lưu `pair_results.csv`.
- [ ] Lưu `heuristic_sensitivity.csv`.
- [ ] Lưu `heuristic_ablation.csv`.
- [ ] Lưu Game Record của từng ván.
- [ ] Ghi `wandb_run_id` vào metadata của thực nghiệm.
- [ ] Không sử dụng W&B làm nguồn lưu trữ duy nhất.

### VII. Trực quan hóa – W&B Dashboard

- [ ] Biểu đồ so sánh Score giữa các bộ trọng số.
- [ ] Biểu đồ Win Rate theo cấu hình.
- [ ] Biểu đồ Mean Latency và p95.
- [ ] Biểu đồ Score theo từng giá trị trọng số.
- [ ] Biểu đồ Ablation: Full Heuristic vs Removed Component.
- [ ] Bảng so sánh các W&B runs.
- [ ] Phân tích các cấu hình có Score cao nhưng chi phí xử lý lớn.
- [ ] Xuất bảng số liệu và hình phù hợp để đưa vào báo cáo LaTeX.
- [ ] Không sử dụng trực tiếp đường cong Score giữa các run có số ván khác nhau mà không làm rõ mẫu số và cách tính.

### VIII. Nhận xét – Phân tích kết quả W&B

- [ ] Cấu hình trọng số nào có Score tốt nhất trên tập dùng để lựa chọn cấu hình?
- [ ] Trọng số nào tác động mạnh nhất đến Score?
- [ ] Trọng số nào làm tăng thời gian quyết định?
- [ ] Có hiện tượng thay đổi trọng số nhưng hiệu năng không cải thiện không?
- [ ] Loại bỏ thành phần heuristic nào làm giảm hiệu năng rõ nhất?
- [ ] Có sự đánh đổi giữa chất lượng nước đi và chi phí tính toán không?
- [ ] Kết quả có ổn định giữa các seed và màu quân không?
- [ ] Cấu hình được chọn có duy trì hiệu quả trên tập đánh giá cuối cùng không?

### IX. QUẢN LÝ VÀ TỔNG HỢP THỰC NGHIỆM BẰNG W&B

**9.1. Tổ chức W&B Project**

- [ ] Project: `commander-chess-ai`.
- [ ] Group: `heuristic-benchmark`.
- [ ] Group: `heuristic-sensitivity`.
- [ ] Group: `heuristic-ablation`.
- [ ] Đặt tên run thể hiện rõ cấu hình và đối thủ.
- [ ] Sử dụng tags để phân biệt `benchmark`, `ablation`, `sensitivity`.

**9.2. Quản lý dữ liệu và phiên bản**

- [ ] Lưu cấu hình của từng run.
- [ ] Lưu seed và phiên bản mã nguồn.
- [ ] Gắn đường dẫn kết quả CSV/JSON.
- [ ] Nếu sử dụng W&B Artifacts, lưu dataset hoặc bảng kết quả tổng hợp có phiên bản.
- [ ] Có thể khôi phục thông tin cấu hình sau khi kết thúc run.
- [ ] Không ghi thông tin nhạy cảm hoặc API key vào W&B config/log.

**9.3. Đánh giá khả năng tái lập**

- [ ] Chạy lại một cấu hình đã lưu bằng cùng seed.
- [ ] Kiểm tra kết quả và sai khác đo lường.
- [ ] Xác nhận notebook vẫn chạy khi `use_wandb = False`.
- [ ] Đảm bảo dữ liệu cục bộ không mất khi W&B không kết nối.
- [ ] Kiểm tra run được kết thúc đúng cách.

**Điều kiện nghiệm thu W&B:**

1. Mỗi cấu hình Heuristic có thông tin nhận diện và tham số rõ ràng.
2. Có dashboard so sánh các cấu hình trọng số.
3. Có kết quả Sensitivity hoặc Ablation được ghi nhận.
4. Có dữ liệu thực nghiệm cục bộ để đối chiếu.
5. Có thể tái lập thực nghiệm mà không phụ thuộc hoàn toàn vào W&B.


## 4. Kế hoạch đối đầu giai đoạn đầu (3 Agent)

| Cặp đấu | Đỏ / Xanh (Agent đầu) | chạy |
|---|---:|---|---:|
| Random – Rule-based | 100 / 100 | 200 |
| Random – Heuristic | 100 / 100| 200 |
| Rule-based – Heuristic | 100 / 100 | 200 |
| **Tổng / chế độ** | Cân bằng | **600** |

Với **2 chế độ** và đủ 200 ván/cặp, tổng cộng **1.200 ván** (chưa tính smoke/stress, self-play hoặc sensitivity/ablation). Các ván `Random vs Random` chỉ dùng kiểm thử baseline riêng, không làm tăng số cặp khác nhau của round-robin ba Agent.

## 5. Bộ đầu ra cần có để viết Chương 4

- [ ] **Bảng 1:** Ma trận Score đối đầu (3×3), kèm số ván mỗi cặp.
- [ ] **Bảng 2:** W/D/L, Win Rate, Draw Rate, Loss Rate, Score và Wilson/Bootstrap CI.
- [ ] **Bảng 3:** Mean decision time, p95 latency theo từng Agent và đối thủ.
- [ ] **Bảng 4:** Cấu hình seed, phiên bản luật/engine, hardware, budget mode.
- [ ] **Hình 1:** Ma trận đối đầu/heatmap.
- [ ] **Hình 2:** Biểu đồ W/D/L và khoảng tin cậy cho Score.
- [ ] **Hình 3:** Biểu đồ latency trung bình và p95.
- [ ] **Hình 4:** Tần suất các rules được kích hoạt (Rule-based).
- [ ] **Hình 5:** Ảnh hưởng weights hoặc bật/tắt thành phần (Heuristic).
- [ ] **Hình 6:** So sánh kết quả khi đi Đỏ và Xanh.
- [ ] **Phân tích:** 2–3 ván tiêu biểu (ít nhất thắng, thua, sai lầm chiến thuật), có thể tái hiện từ log.
- [ ] **Kết luận:** Trả lời liệu Rule-based và Heuristic có cải thiện trước Random không; cái giá về latency; hạn chế và nguy cơ thiên lệch do seed/màu quân.

**Không áp dụng ở giai đoạn này:** training time và learning curve vì ba Agent này không được huấn luyện bằng gradient. `nodes_visited` và `simulations` của Random/Rule-based/Heuristic thường là **NA** trừ khi thực sự có tìm kiếm; không tự báo cáo các số liệu giả định.

## 6. File/folder đề xuất

```text
research/
├── common/
│   ├── config.py                 # Cấu hình chung, schema
│   ├── agent_factory.py          # Khởi tạo Agent
│   ├── match_runner.py           # Chạy 1 ván, replay
│   ├── tournament.py             # Round-robin, đổi màu
│   ├── metrics.py                # Win/Draw/Loss, Score, latency
│   ├── statistics.py             # Wilson / Bootstrap CI
│   ├── data_logger.py            # Ghi config/moves/games/pairs
│   ├── reproducibility.py       # RNG seed, phiên bản
│   └── visualization.py         # Biểu đồ
├── experiments/
│   ├── 05_test_random_agent.ipynb
│   ├── 06_test_rules_agent.ipynb
│   └── 07_test_heuristic_agent.ipynb
└── results/
    └── phase1_round_robin/
        ├── config.json
        ├── environment.json
        ├── moves.csv
        ├── games.csv
        ├── pair_results.csv
        ├── rule_frequency.csv
        ├── heuristic_sensitivity.csv
        ├── game_records/
        └── figures/
```

> **Nguyên tắc kiến trúc:** Engine xác định hành động hợp lệ và chuyển trạng thái; Agent quyết định chọn action; `research/common` chạy thực nghiệm, ghi log, tính chỉ số và vẽ biểu đồ. Không lặp lại luật Game Engine trong notebook.

## 7. Checklist hoàn thành toàn giai đoạn

- [ ] Random Agent pass legal-action, uniformity, seed và non-mutation tests.
- [ ] Rule-based Agent pass ưu tiên luật, xung đột, fallback và non-mutation tests.
- [ ] Heuristic Agent pass component scoring, ranking, terminal handling và non-mutation tests.
- [ ] Đã chạy ít nhất 100 ván cho từng cặp Agent trong Round-robin, đảo màu cân bằng, ghi rõ hai chế độ đánh giá.
- [ ] Có log move-level, game-level, pair-level với seed/config và đường dẫn replay.
- [ ] Có kết quả Score, W/D/L, latency mean/p95, khoảng tin cậy và phân tích đi trước.
- [ ] Có ít nhất một bảng sensitivity/ablation heuristic **nếu chọn làm một trong hai phân tích bắt buộc của toàn đồ án**.
- [ ] Có bảng/hình và nhận xét rút ra từ số liệu **đã thực sự chạy**, không điền số minh họa vào báo cáo như dữ liệu thật.
- [ ] Có thể chạy lại một experiment từ `config.json`, commit và seed.

---

**Phạm vi:** Tài liệu này chỉ bao gồm ba Agent đầu. Các yêu cầu của thầy về Minimax/Alpha-Beta, MCTS, NN/RL, AlphaGo/AlphaZero-inspired, thời gian huấn luyện và ít nhất hai ablations **vẫn phải được hoàn thành ở các giai đoạn tương ứng**; checklist này không thay thế yêu cầu tổng thể.

**Lưu ý:** log ván đấu được ghi lại theo quy tắc của biên bản nước đi. Trong biên bản nước đi phải nêu rõ agent nào cầm quân nào nhé. 
