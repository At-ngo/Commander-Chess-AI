# Nhật ký quyết định kiến trúc & luật chơi (Architecture & Rules Decisions)

Tài liệu này lưu lại toàn bộ các quyết định kỹ thuật, quy ước dữ liệu và luật chơi đã được xác nhận bởi Project Owner trong quá trình phát triển dự án **Commander-Chess-AI**.

---

## Danh mục quyết định

### DEC-001: Ký hiệu Tư lệnh trong biên bản
- **Ngày quyết định:** 24/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:** Ký hiệu Tư lệnh trong ký pháp văn bản và biên bản là **`⋆`** (Unicode `U+22C6`, tương ứng `\star` trong LaTeX). Không dùng `TL` hay `★` trong biên bản ký pháp chuẩn.
- **Tài liệu tham chiếu:** [MOVE_NOTATION.md](file:///d:/Commander-Chess-AI/docs/MOVE_NOTATION.md#L26-L27)

---

### DEC-002: Quy ước hệ tọa độ giữa các tầng hệ thống
- **Ngày quyết định:** 25/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  - Bàn cờ gồm 11 đường dọc (`x = 0..10`) và 12 đường ngang (`y = 0..11`), tổng cộng 132 giao điểm. Gốc `(0, 0)` ở góc dưới bên trái phía vùng biển của phe Đỏ.
  - **Trong luật chơi & biên bản hiển thị:** Tọa độ ghi theo thứ tự `(tung độ, hoành độ)`, tức `(y, x)` hoặc `[y ; x]` (ví dụ `[4 ; 2]`).
  - **Trong API JSON:** Tọa độ dùng Cartesian object chuẩn `{ "x": int, "y": int }`. Serializer có trách nhiệm chuyển đổi sang chuỗi `[y ; x]`.
  - **Trong SVG Bàn cờ:** SVG có viewBox `1024x949` với trục `y` tăng từ trên xuống. Để hiển thị đúng gốc `(0, 0)` ở dưới đáy, frontend sử dụng hàm ánh xạ đảo trục tung: `svg_y = 880 - y * (819 / 11)`.
- **Tài liệu tham chiếu:** [GAME_RULES_PHAN_1_TOA_DO.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES_PHAN_1_TOA_DO.md)

---

### DEC-003: Chuẩn hóa bộ định danh ActionType & EventType
- **Ngày quyết định:** 25/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  - **ActionType (Người/AI chủ động gửi):**
    - `MOVE`: Di chuyển không ăn quân (`_`)
    - `CAPTURE_REPLACE`: Ăn quân và thế chỗ (`@`)
    - `CAPTURE_STAND`: Ăn/bắn tại chỗ không thế chỗ (`_@_`), dùng chung cho Máy bay ném bom, Pháo/Xe tăng bắn tàu, Hải quân bắn đất, và đánh phá Sở chỉ huy đang che Tư lệnh.
    - `BOARD`: Lên phương tiện cõng quân.
    - `DEPLOY`: Triển khai tách quân rời phương tiện.
    - `STACK_MOVE`: Phương tiện mang theo quân di chuyển.
    - `END_TURN`: Chủ động kết thúc sớm lượt của tổ hợp.
  - **EventType (Biến cố Engine tự động sinh ra):**
    - `PIECE_MOVED`: Quân di chuyển.
    - `PIECE_CAPTURED`: Quân bị tiêu diệt.
    - `AIR_SHOT_DOWN`: Máy bay bị bắn hạ bởi vùng phòng không (`@”`).
    - `AIR_EXCHANGE`: Máy bay 1 đổi 1 trong vùng phòng không (`><`).
    - `HERO_PROMOTION`: Phong Anh hùng tự động (ký hiệu in đậm).
    - `HQ_DESTROYED`: Sở chỉ huy bị phá hủy, Tư lệnh lộ diện.
    - `GAME_OVER`: Kết thúc trận đấu (`^` hoặc `!!`).
  - **GameStatus:** `NOT_STARTED`, `IN_PROGRESS`, `GAME_OVER`.
- **Tài liệu tham chiếu:** [API_CONTRACT.md](file:///d:/Commander-Chess-AI/docs/API_CONTRACT.md)

---

### DEC-004: Tầm bắn và vật cản của Pháo binh
- **Ngày quyết định:** 25/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:** Pháo binh được phép bắn qua **bất kỳ số lượng quân cản nào** trên đường bắn (1 quân hay 2 quân cản phía trước đều ăn được), miễn là mục tiêu nằm trong tầm ăn quân hợp lệ từ 1 đến 3 đoạn theo 8 hướng. Khi chỉ di chuyển không ăn, Pháo không được đi xuyên quân.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md#L83)

---

### DEC-005: Tấn công Sở chỉ huy đang che Tư lệnh
- **Ngày quyết định:** 25/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:** Khi quân đối phương tấn công Sở chỉ huy đang có Tư lệnh trú ẩn bên trong: **không được phép tấn công thế chỗ**, bắt buộc phải thực hiện **tấn công ăn tại chỗ (`CAPTURE_STAND`)** để phá hủy Sở chỉ huy, làm lộ diện Tư lệnh tại vị trí đó mà không làm di dời Tư lệnh.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md#L110)

---

### DEC-006: Vị trí và cơ chế Công binh hỗ trợ vượt sông
- **Ngày quyết định:** 25/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:** Công binh đứng sát bờ sông tức là tại hàng `y = 5` (đối với bên Đỏ) hoặc hàng `y = 6` (đối với bên Xanh). Các quân nặng (Pháo, Cao xạ, Tên lửa) có tầm đi tới vị trí Công binh sẽ lên Công binh (`BOARD`) theo hướng ngang, dọc hoặc chéo để được chở qua sông.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md#L95)

---

### DEC-007: Vị trí xuất phát chuẩn của 38 quân cờ (BOARD_DATA)
- **Ngày quyết định:** 25/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:** Xác nhận toàn bộ 38 vị trí quân lúc khởi đầu ván đấu theo tài liệu chuẩn. Trong đó, Tàu chiến Xanh thứ hai đóng tại `(8, 2)` (trục tung y=8, trục hoành x=2, tương ứng tọa độ `{x: 2, y: 8}`), đối xứng với Tàu chiến Đỏ thứ hai tại `(3, 2)`. Đỏ đi trước. Hai đường ngầm tại `((5, 5), (6, 5))` và `((5, 7), (6, 7))`.
- **Tài liệu tham chiếu:** [GAME_RULES_PHAN_1_TOA_DO.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES_PHAN_1_TOA_DO.md)

---

### DEC-008: Tài nguyên Bàn cờ SVG
- **Ngày quyết định:** 25/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:** Sử dụng file `apps/web/public/assets/board/board.svg` (viewBox `0 0 1024 949`) do chủ dự án cung cấp làm hình nền bàn cờ chính thức của giao diện web.

---

### DEC-009: Quy tắc Cấm Tư lệnh Đối mặt nhau (Lộ mặt Tướng)
- **Ngày quyết định:** 26/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  - Hai Tư lệnh không bao giờ được cùng nằm trên một đường thẳng (cùng hàng ngang hoặc cùng cột dọc) mà ở giữa không có bất kỳ quân cờ nào che chắn.
  - Mọi nước đi dẫn đến thế đối mặt trực tiếp (Tư lệnh tự đi vào đường trống, quân cản duy nhất di chuyển rời đi, hoặc ăn quân cản duy nhất) đều là **nước đi bất hợp lệ ngay lập tức**.
  - Kiểm tra toàn bộ hành trình bước đi của Tư lệnh: nếu chạm đường nhìn thẳng của Tư lệnh đối phương, hành trình bị chặn ngay lập tức.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md#L155)

---

### DEC-010: Vành đai lửa Phòng không & Radar hiển thị khi chọn Máy bay
- **Ngày quyết định:** 26/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  - Vành đai lửa phòng không được tạo bởi: Cao xạ (bán kính 1 đoạn ngang/dọc), Tên lửa (1–2 đoạn ngang/dọc và 1 đoạn chéo), Tàu chiến (1 đoạn ngang/dọc).
  - Máy bay bay qua vùng phòng không bị bắn hạ (`AIR_SHOT_DOWN`); tấn công mục tiêu trong vùng phòng không xử lý 1 đổi 1 (`AIR_EXCHANGE`). Máy bay Anh hùng được miễn nhiễm.
  - Trên bàn cờ web: Khi người chơi click chọn quân Máy bay (`AIRCRAFT`), hệ thống tự động tính toán và hiển thị vùng vành đai lửa phòng không của đối phương dưới dạng radar cảnh báo nguy hiểm trực quan.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md#L125)

---

### DEC-011: Huy hiệu Sao Vàng Quân Anh hùng & Chuẩn hóa Cõng quân
- **Ngày quyết định:** 26/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  - Khi quân cờ được phong Anh hùng, sẽ có thêm một **ngôi sao vàng nhỏ (`★`) nằm ở góc trên của quân cờ** trên bàn cờ.
  - Xe tăng chở tối đa 2 quân bộ; Tàu chiến chở tối đa 1 máy bay / 1 xe tăng / 2 quân bộ; Công binh đứng ở bờ sông chở 1 vũ khí nặng vượt sông. Phương tiện bị tiêu diệt thì toàn bộ quân bên trong bị tiêu diệt theo.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md#L180)

---

### DEC-012: Chi tiết hóa Quy tắc Hải quân, Phòng không Anh hùng và Sở chỉ huy (Từ Q5 - Q9)
- **Ngày quyết định:** 28/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  1. **Hải quân tấn công phía trước (Q5):** Tàu chiến chỉ tấn công tàu chiến địch ở phía trước dọc theo đường ngắm; tàu chiến địch đầu tiên cản trở việc tấn công các tàu chiến địch phía sau nó trên cùng tia bắn. Tuy nhiên, nếu phía sau tàu địch là quân đất liền thì tàu chiến vẫn có thể bắn quân đất liền đó trong tầm 3 đoạn.
  2. **Vành đai lửa Tên lửa Anh hùng (Q6):** Ngoài phạm vi ngang dọc 3 đoạn và chéo 2 đoạn, bổ sung thêm đúng 8 điểm dạng kỵ mã: `(|dy|=2, |dx|=1)` và `(|dy|=1, |dx|=2)` (tổng cộng 28 điểm phòng không).
  3. **Tư lệnh trong phương tiện (Q7):** Phương tiện chở Tư lệnh được phép cắt ngang đường nhìn thẳng (vượt mặt), nhưng Engine nghiêm cấm nước đi dừng lại ở vị trí đối mặt trực tiếp với Tư lệnh đối phương (chặn không sinh action tự sát).
  4. **Hải quân đánh bờ biển/bờ sông (Q8):** Mục tiêu ở bờ biển (`x=2`) hoặc bờ sông (`y=5,6` trừ sông ngầm) bắt buộc Tàu chiến phải ăn thế chỗ (`CAPTURE_REPLACE`). Mục tiêu ở đất liền sâu bắt buộc bắn tại chỗ (`CAPTURE_STAND`).
  5. **Tư lệnh và Sở chỉ huy (Q9):**
     - Tư lệnh kề cận Sở chỉ huy được vào trú ẩn (`BOARD`), tiêu tốn 1 lượt, với điều kiện Sở chỉ huy không nằm trên đường nhìn thẳng của Tư lệnh địch.
     - Khi Sở chỉ huy bị địch tấn công: Sở chỉ huy bị phá hủy, Tư lệnh sống sót và lộ diện tại ô đó; quân địch bắt buộc đánh tại chỗ (`CAPTURE_STAND`).
     - Khi một bên chỉ còn lại Tư lệnh và Sở chỉ huy: Sở chỉ huy tự động được phong thành Bộ binh Anh hùng, có thể di chuyển/tấn công 8 hướng 1–2 đoạn, và Tư lệnh không thể ẩn nấp vào HQ nữa.
     - Quân cuối cùng còn bảo vệ Tư lệnh (không tính HQ) tự động được phong Anh hùng.
- **Tài liệu tham chiếu:** [RESOLVED_QUESTIONS.md](file:///d:/Commander-Chess-AI/docs/RESOLVED_QUESTIONS.md#L36-L75)


---

### DEC-013: Tích hợp Động cơ Thực thi, Gói Tác tử AI Level 1 & Đồng bộ Hệ thống
- **Ngày quyết định:** 07/11/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  1. **Tích hợp Động cơ Thực thi Authoritative Engine Adapter:**
     - Xây dựng lớp `AuthoritativeEngineAdapter` trong `apps/api/src/services/engine_adapter.py` kết nối trực tiếp với gói tác quyền `packages/commander_game_engine` của Sinh viên.
     - Tự động ủy quyền sinh nước đi hợp lệ (`legal_actions`) và thực thi bước chuyển trạng thái (`apply_action`) sang `packages/commander_game_engine`, bảo đảm nguyên tắc Single Source of Truth theo đúng [AGENTS.md](file:///d:/Commander-Chess-AI/AGENTS.md).
     - Giữ cơ chế fallback an toàn về `MockEngineAdapter` đối với các hành động cõng quân nâng cao (`BOARD`/`DEPLOY`) hoặc khi trạng thái chưa tương thích.
  2. **Gói Tác tử AI Level 1 (`packages/agents/`):**
     - Xây dựng lớp cơ sở `BaseAgent` đo lường thời gian suy nghĩ và kiểm tra tính hợp lệ của hành động được trả về theo đúng hợp đồng `packages/agents/agent_protocol.md`.
     - Triển khai tác tử `RandomAgent` (Level 1) lựa chọn ngẫu nhiên đồng đều các nước đi hợp lệ từ engine thật, kiểm soát seed tái lập (`seed`).
     - Tích hợp trực tiếp `RandomAgent` vào endpoint `POST /api/v1/games/{id}/ai-step` của backend FastAPI.
  3. **Đồng bộ Thang điểm Giá trị Quân cờ:**
     - Chuẩn hóa điểm số: **Xe tăng = 20 điểm** (thay vì 10 điểm), **Tư lệnh = 100 điểm** (+50 điểm thưởng khi bắt được Tư lệnh kết thúc trận đấu).
     - Đồng bộ nhất quán trên toàn bộ 3 tầng: `packages/commander_game_engine`, `apps/api` (`engine_adapter.py`), và `apps/web` (`mockGameService.ts`).
  4. **Bộ Kiểm thử Luật & Fuzzing Độc lập:**
     - 15 kịch bản kiểm thử cô lập `tests/test_rule_scenarios.py` (tầm cản xe tăng, tầm ăn Tư lệnh, pháo bắn xuyên vật cản, ghim đối mặt tướng, sông ngầm vs nước sâu, pháo bờ biển bắn hải quân, tự động phong Anh hùng).
     - Kiểm thử bất biến `tests/test_invariant_fuzzing.py` đảm bảo không trùng ô, không đối mặt tướng và tính đúng đắn 2 chiều của `legal_actions` vs `apply_action`.
- **Tài liệu tham chiếu:** [AGENTS.md](file:///d:/Commander-Chess-AI/AGENTS.md), [agent_protocol.md](file:///d:/Commander-Chess-AI/packages/agents/agent_protocol.md), [API_CONTRACT.md](file:///d:/Commander-Chess-AI/docs/API_CONTRACT.md)

---

### DEC-014: Chuẩn hóa 5 Quy tắc Tác chiến Chi tiết & Giao diện Tổ hợp Cõng quân
- **Ngày quyết định:** 07/11/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  1. **Tàu chiến di chuyển bị chặn bởi đất liền (Point 1):**
     - Tàu chiến di chuyển tối đa 4 đoạn (Anh hùng 5 đoạn) trên mặt nước (biển, bờ biển, bờ sông).
     - Nếu bất kỳ giao điểm trung gian nào trên tia di chuyển là đất liền sâu (`!isWater`), tàu chiến bị chặn ngay lập tức, không được phép đi xuyên qua đất liền để tới vùng nước phía sau (Ví dụ: Tàu tại `(x=2, y=3)` đi chéo bị đất liền `(x=3, y=4)` chặn, không được tới `(x=4, y=5)`).
     - **Đường chéo góc bờ biển - bờ sông thuộc đất liền:** Đoạn chéo giữa Bờ biển (x=2) và Bờ sông (x=3) chạy cắt qua vùng đất liền của 2 phe (giữa (y=7, x=2) và (y=6, x=3) thuộc đất liền bên Xanh; giữa (y=4, x=2) và (y=5, x=3) thuộc đất liền bên Đỏ). Do đó, Tàu chiến tại (7, 2) không thể đi chéo đến (6, 3) hoặc (5, 4); Tàu chiến tại (4, 2) không thể đi chéo đến (5, 3) hoặc (6, 4) vì vướng đất liền.
  2. **Tư lệnh trong Sở chỉ huy & Giao diện chọn quân tổ hợp cõng quân (Point 2):**
     - **Ở Sở chỉ huy:** Sở chỉ huy là căn cứ cố định bất động (không di chuyển). Khi có Tư lệnh trú ẩn bên trong, người chơi click vào ô Sở chỉ huy sẽ tự động chọn Tư lệnh để triển khai di chuyển ra ngoài.
     - **Ở tổ hợp cõng nhau (Xe tăng, Tàu chiến, Công binh):** Hiển thị thanh Dock chọn quân (`compoundDock`) trên bàn cờ và trong bảng chi tiết `PieceDetail`, cho phép người chơi chọn điều khiển Phương tiện (di chuyển cả tổ hợp) hoặc chọn từng Quân đang được cõng (để triển khai ra ngoài). Sau đó cung cấp nút "Xác nhận tổ hợp" (`CONFIRM_DEPLOYMENT`). Khi quân cõng triển khai ra ngoài, phương tiện tự động cập nhật gỡ quân khỏi `carrying_piece_ids`.
  3. **Máy bay và Vành đai lửa Phòng không (Point 3):**
     - **Di chuyển thuần túy (`MOVE`):** Máy bay thường bay vào vùng phòng không đối phương bị tiêu diệt ngay lập tức (`is_alive = False`), đối phương được thưởng 40 điểm bắn rơi máy bay.
     - **Tấn công (`CAPTURE_STAND` hoặc `CAPTURE_REPLACE`):** Khi tấn công mục tiêu nằm trong vùng phòng không, áp dụng cơ chế **1 đổi 1 (`AIR_EXCHANGE`)** — mục tiêu bị tiêu diệt và máy bay cũng bị tiêu diệt cùng lúc. Cả hai bên đều nhận điểm tương ứng.
  4. **Giới hạn Mặt biển đối với Tên lửa và Máy bay (Point 4):**
     - Tên lửa là phương tiện mặt đất, tuyệt đối không thể di chuyển lên các ô biển trống (`x <= 1`).
     - Máy bay không thể dừng/đáp trên các ô biển trống (`x <= 1`). Tuy nhiên, máy bay được quyền bay qua biển để đáp lên Tàu chiến cùng phe (`BOARD`) nếu tàu chiến nằm trên đường bay.
  5. **Quy định Thả bom / Pháo kích vs Ăn thế chỗ (Point 5):**
     - **Pháo binh trên đất liền:** Chỉ được ăn thế chỗ (`CAPTURE_REPLACE`), không được thả bom tại chỗ (`CAPTURE_STAND`) như máy bay.
     - **Thả bom / Bắn tại chỗ (`CAPTURE_STAND`):** Trên đất liền chỉ DUY NHẤT Máy bay được thả bom tại chỗ. Quân mặt đất (Xe tăng, Pháo binh, Tên lửa) CHỈ được bắn tại chỗ khi mục tiêu là Tàu chiến địch ngoài biển sâu nơi quân bộ không thể thế chỗ.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md), [mockGameService.ts](file:///d:/Commander-Chess-AI/apps/web/src/services/mockGameService.ts), [engine_adapter.py](file:///d:/Commander-Chess-AI/apps/api/src/services/engine_adapter.py)

---

### DEC-015: Quy tắc Phong Anh hùng khi Chiếu Tư lệnh & Năng lực Quân Anh hùng (RULE-HERO-001..004)
- **Ngày quyết định:** 07/11/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  1. **Phong Anh hùng khi Chiếu Tư lệnh (Rule 1):**
     - Khi một quân bất kỳ tạo thế chiếu hợp lệ lên Tư lệnh đối phương (Tư lệnh không đang ẩn nấp trong Sở chỉ huy), quân cờ đó được phong **Anh hùng** (`is_hero = True`).
     - Quân được phong hiển thị huy hiệu ngôi sao vàng (`★`) trên nền tối ở góc trên bên phải quân cờ trên bàn cờ SVG.
     - **Tăng cường năng lực (Buff):**
       - Quân chưa có đường chéo (Bộ binh, Công binh, Cao xạ, Xe tăng): được buff thêm 4 hướng chéo (tổng 8 hướng) và tăng tầm đánh lên 1 đoạn (Bộ binh, Công binh, Cao xạ: 8 hướng tầm 1–2; Xe tăng: 8 hướng tầm 1–3).
       - Quân đã có sẵn đường chéo (Dân quân, Tên lửa, Pháo binh, Máy bay, Hải quân): được tăng tầm thêm 1 đoạn (Dân quân: tầm 1–2; Tên lửa: thẳng 1–3, chéo 1–2; Pháo binh: tầm 1–4; Máy bay: tầm 1–5; Hải quân: tầm 1–5, pháo hạm bắn đất liền tầm 1–4).
  2. **Máy bay Tàng hình Anh hùng (Rule 2):**
     - Máy bay Anh hùng miễn nhiễm hoàn toàn với vành đai lửa phòng không (Cao xạ, Tên lửa, Hải quân).
     - Không bị bắn hạ khi bay qua hoặc hạ cánh trong vùng phòng không, và không bị cơ chế 1 đổi 1 (`AIR_EXCHANGE`) khi tiêu diệt các đơn vị phòng không.
  3. **Quân bảo vệ cuối cùng (Rule 3):**
     - Quân chiến đấu cuối cùng bảo vệ Tư lệnh (không tính Sở chỉ huy) tự động được phong Anh hùng, kể cả khi chưa có cơ hội trực tiếp chiếu Tư lệnh đối phương.
   4. **Sở chỉ huy cuối cùng & Điều kiện 1 HQ vs 2 HQ (Rule 4 & Cập nhật):**
      - **CHỈ KHI** một phe chỉ còn lại **DUY NHẤT 1 Sở chỉ huy và Tư lệnh** (toàn bộ quân tác chiến khác đã bị tiêu diệt), Sở chỉ huy duy nhất này mới được phong thành Bộ binh Anh hùng (di chuyển và tấn công 8 hướng tầm 1–2 đoạn). Lúc này Tư lệnh không thể ẩn núp vào Sở chỉ huy nữa (`can_board = False`).
      - **NẾU CÒN 2 SỞ CHỈ HUY VÀ TƯ LỆNH**, cả 2 Sở chỉ huy **TUYỆT ĐỐI KHÔNG** được phong Anh hùng (vẫn giữ nguyên là công trình cố định không di chuyển, không có sao vàng `is_hero = False`, và Tư lệnh vẫn có thể trú ẩn vào 1 trong 2 Sở chỉ huy bình thường).
  5. **Ký pháp biên bản:**
     - Nước đi chiếu và được phong Anh hùng tự động xuất biên bản theo định dạng: `[Nước đi] > **[Ký hiệu quân]**` (ví dụ: `T [5 ; 4] _ [7 ; 4] > **T**` hoặc `K [4 ; 3] _ [7 ; 6] > **K**`).
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md), [MOVE_NOTATION.md](file:///d:/Commander-Chess-AI/docs/MOVE_NOTATION.md), [mockGameService.ts](file:///d:/Commander-Chess-AI/apps/web/src/services/mockGameService.ts), [engine_adapter.py](file:///d:/Commander-Chess-AI/apps/api/src/services/engine_adapter.py)


---

### DEC-016: Phương tiện Chủ động Di chuyển đến Đón Cõng Quân (RULE-PICKUP-001)
- **Ngày quyết định:** 08/11/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  1. **Hai chiều trong quy tắc cõng quân:**
     - Ngoài hình thức quân được cõng chủ động di chuyển lên phương tiện (`BOARD`), cho phép **phương tiện chủ động di chuyển đến vị trí của quân được cõng để đón cõng quân đó lên**.
     - Phương tiện (Xe tăng, Máy bay, Tàu chiến, Công binh bên bờ sông) di chuyển theo tầm và đường đi hợp lệ đến ô của quân đồng minh hợp lệ (thỏa mãn quy tắc sức chứa và loại quân có thể chở `can_board_carrier`).
  2. **Trạng thái sau khi đón cõng:**
     - Phương tiện di chuyển đến tọa độ đích (nơi quân đồng minh đang đứng).
     - Quân đồng minh được đón chuyển sang trạng thái cõng (`carried_by_id = carrier.id`), phương tiện cập nhật danh sách chở (`carrying_piece_ids`).
     - Toàn bộ quân đã có sẵn trên phương tiện (nếu có) cũng di chuyển theo phương tiện đến tọa độ mới.
  3. **Tính lượt:**
     - Hành động đón cõng quân tiêu tốn đúng **1 lượt tác chiến**, kết thúc lượt tương tự như hành động quân lên phương tiện thông thường.
  4. **Ký pháp biên bản:**
     - Biên bản ghi nhận theo cú pháp: `[Ký hiệu phương tiện] [Từ tọa độ] ^ [Ký hiệu quân được đón] [Đến tọa độ]` (ví dụ: `T [5 ; 5] ^ B [5 ; 7]` hoặc `X [4 ; 6] ^ D [4 ; 5]`).
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md), [mockGameService.ts](file:///d:/Commander-Chess-AI/apps/web/src/services/mockGameService.ts), [engine_adapter.py](file:///d:/Commander-Chess-AI/apps/api/src/services/engine_adapter.py)

---

### DEC-017: Hệ Thống 5 Loại Quân Chở/Che Chở & Mở Rộng Boarding Tại Bờ Biển, Bờ Sông (RULE-CARRIER-MATRIX-001)
- **Ngày quyết định:** 08/11/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  1. **Danh sách đầy đủ 5 loại quân chở / che chở:**
     - **Xe tăng (`TANK`):** Chở Bộ binh, Dân quân, Tư lệnh (tối đa 2 quân).
     - **Không quân (`AIRCRAFT`):** Chở Bộ binh, Dân quân, Tư lệnh, Xe tăng (tối đa 2 quân).
     - **Hải quân (`NAVY`):** Chở Bộ binh, Dân quân, Tư lệnh, Xe tăng, Máy bay (tối đa 2 quân).
     - **Công binh (`ENGINEER`):** Chở Cao xạ, Pháo binh, Tên lửa khi đứng ở bờ sông (`y=5` hoặc `y=6`, tối đa 1 vũ khí nặng để chở qua sông sâu).
     - **Sở chỉ huy (`HEADQUARTERS`):** Che chở cho Tư lệnh (tối đa 1 Tư lệnh). Khi Sở chỉ huy bị diệt thì Tư lệnh sống sót và lộ diện tại đó. Khi chỉ còn 1 Sở chỉ huy và Tư lệnh thì Sở chỉ huy được phong thành Bộ binh Anh hùng và không còn che chở Tư lệnh nữa.
  2. **Cho phép quân tại bờ biển (x=2) lên Tàu chiến ngoài biển (x<=1):**
     - Đã tinh chỉnh điều kiện `canOccupySquare`: khi ô đích là biển (`x<=1`), các quân trên bộ được phép nhắm đến ô đó nếu ô có tàu chiến đồng minh có thể cõng quân (`can_board_carrier`) hoặc tàu địch để bắn tại chỗ (`CAPTURE_STAND`).
  3. **Đồng bộ hóa bờ sông cho Công binh cả hai phe:**
     - Công binh tại cả hàng `y=5` và hàng `y=6` đều được tính là đứng ở bờ sông để đón/cõng vũ khí hạng nặng vượt sông.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md), [mockGameService.ts](file:///d:/Commander-Chess-AI/apps/web/src/services/mockGameService.ts), [engine_adapter.py](file:///d:/Commander-Chess-AI/apps/api/src/services/engine_adapter.py)

---

### DEC-018: Quy Tắc Vượt Sông Ngầm Thẳng & Vượt Sông Sâu Khi Ăn Quân Cho Tên Lửa, Pháo Binh (RULE-RIVER-002)
- **Ngày quyết định:** 08/11/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  1. **Cấm đi chéo qua sông sâu sang ô trống:**
     - Tên lửa, Pháo binh, Cao xạ **tuyệt đối không thể di chuyển qua sông sâu theo đường chéo** vào ô trống (kể cả khi tọa độ xuất phát hoặc đích rơi vào cột x=5 hoặc x=7).
  2. **Chỉ qua sông ngầm theo đường thẳng:**
     - Các vũ khí nặng chỉ được phép tự vượt sông vào ô trống khi đi **theo đường thẳng** dọc theo cột ngầm đá `x = 5` và `x = 7` (`from_x == to_x && (from_x == 5 || from_x == 7)`).
  3. **Hai cách duy nhất để vượt qua sông sâu:**
     - **Cách 1: Nhờ Công binh chở qua:** Lên Công binh (`BOARD`) tại bờ sông (`y=5` hoặc `y=6`) để Công binh chở sang bờ đối diện rồi triển khai.
     - **Cách 2: Ăn quân địch thế chỗ (`CAPTURE_REPLACE`):** Được phép vượt sông sâu khi thực hiện nước tấn công ăn quân thế chỗ vào vị trí quân địch bên kia sông sâu trong phạm vi di chuyển/ăn quân hợp lệ của mình (cả đường thẳng và đường chéo).
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md#L88), [mockGameService.ts](file:///d:/Commander-Chess-AI/apps/web/src/services/mockGameService.ts#L106), [engine_adapter.py](file:///d:/Commander-Chess-AI/apps/api/src/services/engine_adapter.py#L121), [rules.py](file:///d:/Commander-Chess-AI/packages/commander_game_engine/rules.py#L180)

---

### DEC-019: Quy Tắc An Toàn Cho Tư Lệnh (Cấm Tự Sát & Ghim Quân) & Thắng Trận Bằng Chiếu Hết (CHECKMATE)
- **Ngày quyết định:** 08/11/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:**
  1. **Cấm nước đi khiến Tư lệnh bị đối phương ăn (King-safety / Suicidal moves):**
     - Tư lệnh tuyệt đối không được di chuyển vào bất kỳ ô cờ nào đang nằm trong tầm tấn công/chiếu của quân địch.
     - Các nước đi của Tư lệnh dẫn vào ô bị đối phương ăn bị loại bỏ hoàn toàn khỏi danh sách nước đi hợp lệ (`legal_actions`).
  2. **Quy tắc ghim quân và giải chiếu (Pinning & Resolving Check):**
     - Mọi nước đi của các quân khác khiến Tư lệnh phe mình rơi vào thế bị chiếu (ví dụ: quân chắn đường di chuyển làm lộ Tư lệnh) đều là bất hợp lệ và bị loại bỏ.
     - Khi Tư lệnh đang bị chiếu, người chơi bắt buộc phải thực hiện nước đi giải chiếu (di chuyển Tư lệnh tới ô an toàn, đưa quân ra chắn đường tấn công, ăn quân đang chiếu, hoặc đưa Tư lệnh ẩn nấp vào Sở chỉ huy).
  3. **Thắng trận khi Chiếu hết Tư lệnh đối phương (Checkmate Victory):**
     - Khi Tư lệnh của một bên đang bị chiếu (`is_in_check == True`) và toàn bộ các quân còn lại của bên đó không còn bất kỳ nước đi hợp lệ nào (`len(legal_actions) == 0`):
       Ván đấu ngay lập tức kết thúc với chiến thắng thuộc về bên đang chiếu hết (`status = GAME_OVER`, `winner = checking_side`, `reason = 'CHECKMATE'`).
     - Bên thắng do chiếu hết được thưởng thêm **+50 điểm** tương đương điểm thưởng khi bắt được Tư lệnh đối phương.
     - Biên bản nước đi được gắn thêm ký hiệu `#` ở cuối (chuẩn ký pháp cờ quốc tế cho Chiếu hết, ví dụ: `T [9 ; 9] _ [11 ; 9] > **T** #`).
     - Hiển thị thông báo chiến thắng Chiếu hết trong `GameOverModal` và giao diện đa ngữ (Tiếng Việt: "Chiếu hết Tư lệnh đối phương (+50 điểm)", Tiếng Anh: "Checkmate: Opposing Commander has no escape (+50 pts)").
   4. **Chiến lược chọn nước đi an toàn & giải chiếu cho Tác tử AI (AI King-Safety & Check Resolution Policy):**
      - **Khi KHÔNG bị chiếu:** AI ưu tiên 100% các quân tác chiến (Xe tăng, Bộ binh, Dân quân, Pháo binh, Cao xạ, Tên lửa, Máy bay, Hải quân, Công binh) hoặc đưa Tư lệnh trú ẩn an toàn vào Sở chỉ huy/phương tiện. Tuyệt đối không chọn nước đi của Tư lệnh lang thang ra ngoài bàn cờ cho đối phương ăn. Chỉ khi toàn bộ quân khác hết nước đi (chỉ còn Tư lệnh có thể di chuyển), Tư lệnh mới được đi và chỉ được chọn ô đến an toàn tuyệt đối mà đối phương không thể ăn được.
      - **Khi ĐANG BỊ CHIẾU:** AI bắt buộc chọn các nước đi hóa giải thế chiếu:
        a) Dùng quân khác chặn đường chiếu (nếu quân địch chiếu từ xa dọc theo đường thẳng/chéo).
        b) Dùng quân khác hoặc chính Tư lệnh ăn quân địch đang chiếu.
        c) Chạy Tư lệnh sang ô an toàn không bị đối phương ăn.
        d) Đưa Tư lệnh trú ẩn vào Sở chỉ huy.
      - **Triển khai đồng bộ:** Hàm select_smart_ai_action tại apps/api/src/services/engine_adapter.py được cấp cho endpoint POST /api/v1/games/{id}/ai-step, và hàm selectSmartAiAction tại apps/web/src/services/mockGameService.ts được áp dụng cho offline fallback trong App.tsx.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md#L149), [mockGameService.ts](file:///d:/Commander-Chess-AI/apps/web/src/services/mockGameService.ts), [engine_adapter.py](file:///d:/Commander-Chess-AI/apps/api/src/services/engine_adapter.py), [App.tsx](file:///d:/Commander-Chess-AI/apps/web/src/App.tsx)

---

### DEC-020: Chuẩn hóa Phương án A — An toàn Tư lệnh Tuyệt đối, Hòa Cờ Bí, Sửa Luật Tác chiến & Phong Trễ Sở chỉ huy
- **Ngày quyết định:** 10/11/2026
- **Trạng thái:** CONFIRMED
- **Quyết định (do Project Owner chốt toàn bộ):**
  1. **Phạm vi triển khai — Phương án A (Full-stack):** Đồng bộ đầy đủ trên cả `packages/commander_game_engine`, `packages/agents`, `apps/api`, `apps/web`, `docs/` và `tests/`.
  2. **An toàn Tư lệnh tuyệt đối, Chiếu hết thắng & Hòa cờ bí:**
     - Mọi nước đi khiến Tư lệnh phe mình rơi vào trạng thái bị đe dọa đều bị cấm tuyệt đối và loại bỏ khỏi `legal_actions` (tuyệt đối không fallback sang nước tự sát). Bao gồm cả trường hợp Tư lệnh bị đe dọa bởi **quân địch đang ngồi trên phương tiện của đối phương triển khai trực tiếp ra ăn** (`CAPTURE_REPLACE` lên đất liền/bờ/ngầm) hay Tư lệnh ngồi trong Máy bay thường bị bắn hạ tại vành đai lửa phòng không.
     - Thắng trận thông thường bằng **Chiếu hết (`CHECKMATE`, +50 điểm)**. Khi đến lượt một bên chỉ còn **0 nước đi hợp lệ** nhưng Tư lệnh **KHÔNG bị chiếu**, ván đấu kết thúc **HÒA (`winner = "DRAW"`, `reason = "STALEMATE"`)**, không cộng thưởng +50 điểm.
  3. **Chỉnh sửa các quy tắc quân cờ theo xác nhận của Chủ dự án:**
     - **Tên lửa (`MISSILE`):** Được phép **ăn xuyên vật cản** (`CAPTURE_REPLACE` trên đất/bờ, `CAPTURE_STAND` trên biển `x<=1` hoặc Sở chỉ huy che Tư lệnh), nhưng **KHÔNG được di chuyển (`MOVE`) hay đón/lên xe (`BOARD`/`PICKUP`) xuyên vật cản**.
     - **Hải quân (`NAVY`):** Được phép **bắn Pháo hạm vào đất liền qua vật cản** trong tầm 3 đoạn (Anh hùng: 4 đoạn); và được phép **vượt qua quân đồng minh không phải Hải quân đang đứng ở bờ biển (`x=2`) hoặc bờ sông (`y=5,6`)** khi di chuyển.
     - **Tấn công Máy bay (`AIRCRAFT`):** **Tất cả các loại quân chiến đấu đều có thể tấn công/ăn Máy bay** trong tầm ăn quân hợp lệ của quân đó (kể cả Tư lệnh, Bộ binh, Dân quân, Xe tăng, Công binh, Pháo binh).
     - **Tư lệnh trên phương tiện chắn đối mặt (cập nhật tại DEC-021):** Trước đây tạm coi mọi phương tiện chở Tư lệnh đều chắn đối mặt; theo cập nhật mới tại `DEC-021`, chỉ Sở chỉ huy thường `!is_hero` che chắn sau khi vào trong, còn phương tiện cơ động chở Tư lệnh vẫn không được đứng/lên xe trên đường nhìn Tư lệnh địch.
  4. **Phong Anh hùng trễ Sở chỉ huy duy nhất:**
     - Khi còn 2 Sở chỉ huy + Tư lệnh: không phong.
     - Khi chỉ còn 1 Sở chỉ huy duy nhất + Tư lệnh (+ 0 quân chiến đấu khác): nếu Tư lệnh đang ở ngoài Sở chỉ huy thì Sở chỉ huy phong Anh hùng ngay lập tức; nếu Tư lệnh **đang núp bên trong Sở chỉ huy đó**, Sở chỉ huy **CHƯA phong Anh hùng ngay**, tới lượt người chơi đó chỉ có lựa chọn đưa Tư lệnh **bước ra khỏi Sở chỉ huy** (không được quay lại núp vào Sở chỉ huy), và ngay khi Tư lệnh bước ra thì Sở chỉ huy duy nhất được phong Anh hùng lập tức.
  5. **Động bộ `RandomAgent` & Nước đi Tổ hợp:**
     - Danh sách nước đi hợp lệ được tái tính động sau mỗi trạng thái bàn cờ (kể cả trong lượt `STACK_ACTIVE`). `RandomAgent` và `select_smart_ai_action` / `selectSmartAiAction` thu thập đầy đủ các lựa chọn hợp lệ từ quân được cõng, phương tiện (`carry_cargo = True/False`), nước tiếp theo trong `STACK_ACTIVE` và `END_TURN`.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md), [API_CONTRACT.md](file:///d:/Commander-Chess-AI/docs/API_CONTRACT.md), [rules.py](file:///d:/Commander-Chess-AI/packages/commander_game_engine/rules.py), [engine.py](file:///d:/Commander-Chess-AI/packages/commander_game_engine/engine.py), [random_agent.py](file:///d:/Commander-Chess-AI/packages/agents/random_agent.py), [engine_adapter.py](file:///d:/Commander-Chess-AI/apps/api/src/services/engine_adapter.py), [mockGameService.ts](file:///d:/Commander-Chess-AI/apps/web/src/services/mockGameService.ts)

---

### DEC-021: Cấm Tư lệnh lên phương tiện và cấm phương tiện chở Tư lệnh đứng trên đường nhìn Tư lệnh đối phương
- **Ngày quyết định:** 11/11/2026
- **Trạng thái:** CONFIRMED
- **Quyết định (do Project Owner chốt):**
  1. Nếu một phương tiện có thể cõng Tư lệnh (`TANK`, `AIRCRAFT`, `NAVY`, hoặc `HEADQUARTERS` thường) đang nằm trên đường nhìn thẳng không vật cản của Tư lệnh đối phương, Tư lệnh **không được lên (`BOARD`) phương tiện đó** (kể cả khi chính Tư lệnh đang làm vật cản trước đó).
  2. Khi Tư lệnh đang ngồi trong phương tiện vận tải cơ động (`TANK`, `AIRCRAFT`, `NAVY` — trực tiếp hoặc lồng nhau), vị trí đối mặt được tính theo **vị trí phương tiện gốc**; phương tiện đang chở Tư lệnh **không được dừng/đứng trên đường nhìn thẳng không vật cản của Tư lệnh đối phương** (kể cả khi `PICKUP` đón Tư lệnh), cũng như quân chắn giữa không được rời hàng/cột gây lộ mặt. Phương tiện vẫn được đi/bay vượt qua tuyến nhìn đó nếu điểm dừng cuối nằm ngoài tầm nhìn đối mặt, hoặc đi một mình tách cargo (`carry_cargo = False`).
  3. Sở chỉ huy thường (`HEADQUARTERS`, `!is_hero`) tiếp tục che chở Tư lệnh khỏi bị chiếu và khỏi đối mặt sau khi Tư lệnh đã ở bên trong an toàn (`Q9`), nhưng vẫn cấm Tư lệnh bước vào Sở chỉ huy đang bị Tư lệnh địch nhìn thẳng không vật cản.
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md#L149), [rules.py](file:///d:/Commander-Chess-AI/packages/commander_game_engine/rules.py), [engine.py](file:///d:/Commander-Chess-AI/packages/commander_game_engine/engine.py), [engine_adapter.py](file:///d:/Commander-Chess-AI/apps/api/src/services/engine_adapter.py), [mockGameService.ts](file:///d:/Commander-Chess-AI/apps/web/src/services/mockGameService.ts)

---

### DEC-022: Hiệu chỉnh điểm Sở chỉ huy (`HEADQUARTERS`) từ 100 về 10 điểm
- **Ngày quyết định:** 12/11/2026
- **Trạng thái:** CONFIRMED
- **Quyết định (do Project Owner xác nhận):**
  - Sửa lỗi gõ dư một chữ số `0` ở điểm Sở chỉ huy (`HEADQUARTERS`): điều chỉnh giá trị từ `100` xuống **`10` điểm** (cộng thêm `+10` nếu là Sở chỉ huy Anh hùng = `20` điểm), giữ nguyên Tư lệnh (`COMMANDER`) = `100` điểm (+`50` thưởng kết thúc ván).
  - Đồng bộ giá trị `HEADQUARTERS = 10` trên toàn bộ hệ thống: `packages/commander_game_engine/engine.py` (`PIECE_POINTS`), `apps/api/src/services/engine_adapter.py` (`PIECE_SCORES`), `apps/web/src/services/mockGameService.ts` (`PIECE_SCORES`), khớp với bảng vật chất CCHEF tại `packages/agents/evaluation/material_table.py` (`HEADQUARTERS = 10.0`).
- **Tài liệu tham chiếu:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md#L56), [engine.py](file:///d:/Commander-Chess-AI/packages/commander_game_engine/engine.py#L28), [engine_adapter.py](file:///d:/Commander-Chess-AI/apps/api/src/services/engine_adapter.py#L52), [mockGameService.ts](file:///d:/Commander-Chess-AI/apps/web/src/services/mockGameService.ts#L21), [material_table.py](file:///d:/Commander-Chess-AI/packages/agents/evaluation/material_table.py#L11)
