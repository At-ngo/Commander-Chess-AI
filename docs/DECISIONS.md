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
- **Quyết định:** Xác nhận toàn bộ 38 vị trí quân lúc khởi đầu ván đấu theo tài liệu chuẩn. Trong đó, Tàu chiến Xanh thứ hai đóng tại `(6, 2)` (bất đối xứng so với phe Đỏ), Đỏ đi trước. Hai đường ngầm tại `((5, 5), (6, 5))` và `((5, 7), (6, 7))`.
- **Tài liệu tham chiếu:** [GAME_RULES_PHAN_1_TOA_DO.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES_PHAN_1_TOA_DO.md)

---

### DEC-008: Tài nguyên Bàn cờ SVG
- **Ngày quyết định:** 25/10/2026
- **Trạng thái:** CONFIRMED
- **Quyết định:** Sử dụng file `apps/web/public/assets/board/board.svg` (viewBox `0 0 1024 949`) do chủ dự án cung cấp làm hình nền bàn cờ chính thức của giao diện web.
