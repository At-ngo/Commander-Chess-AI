# MOVE_NOTATION.md — Ký pháp nước đi và biên bản Cờ Tư Lệnh

**Phiên bản:** 1.1  
**Phạm vi:** Chế độ chiến tranh tổng lực trong đồ án AI Cờ Tư Lệnh.  
**Vai trò:** Quy định cách **hiển thị**, **ghi biên bản**, **lưu log**, **phát lại trận đấu** và **xuất/nhập biên bản**.  
**Tài liệu liên quan:** `GAME_RULES.md` là nguồn xác định luật và nước đi hợp lệ. Tài liệu này không tự thay đổi luật.

> **Quy ước quan trọng:** Các mục ghi **[KÝ PHÁP GỐC]** phản ánh tài liệu ghi biên bản được cung cấp. Các mục ghi **[QUY ƯỚC DỰ ÁN]** là định dạng bổ sung để phần mềm xử lý ổn định, tương tự mục đích của PGN trong cờ vua. Không trình bày quy ước bổ sung như thể đó là luật ghi biên bản truyền thống.

## 1. Bảng ký hiệu quân — [KÝ PHÁP GỐC]

| Quân | Ký hiệu | Mã nội bộ khuyến nghị |
|---|:---:|---|
| Tên lửa | `L` | `MISSILE` |
| Sở chỉ huy | `S` | `HEADQUARTERS` |
| Xe tăng | `T` | `TANK` |
| Máy bay | `K` | `AIRCRAFT` |
| Tư lệnh | `⋆` (`\star` trong LaTeX) | `COMMANDER` |
| Bộ binh | `B` | `INFANTRY` |
| Tàu chiến / Hải quân | `H` | `NAVY` |
| Cao xạ | `F` | `ANTI_AIR` |
| Công binh | `C` | `ENGINEER` |
| Dân quân | `D` | `MILITIA` |
| Pháo binh | `A` | `ARTILLERY` |

**Đã xác nhận bởi chủ dự án:** Ký hiệu **Tư lệnh là `⋆`** (Unicode `U+22C6`, biểu diễn LaTeX `\star`). Khi xuất biên bản văn bản thuần, dùng ký tự `⋆`; trong log máy dùng mã `COMMANDER` và `piece_id`, với `notation_symbol: "⋆"`. Ví dụ: `⋆ [4 ; 3] _ [5 ; 3]`. Không thay thế bằng `TL`. Giao diện bàn cờ sử dụng ảnh quân cờ, không phụ thuộc ký tự biên bản.

**Lưu ý:** Ký hiệu `H` là **Hải quân**, không phải ký hiệu cố định của phong Anh hùng. Ký hiệu `S` là Sở chỉ huy.

## 2. Tọa độ — [KÝ PHÁP GỐC]

- Bàn cờ có tọa độ truyền thống **`[tung độ ; hoành độ]`**, tức **`[y ; x]`**.
- Tung độ `y = 0..11`, hoành độ `x = 0..10`; gốc `[0 ; 0]`, góc đối diện `[11 ; 10]`.
- Khi hiển thị, giữ đúng thứ tự này: `[4 ; 3]` nghĩa là `y=4, x=3`, **không phải** `x=4, y=3`.
- **[QUY ƯỚC DỰ ÁN]** API có thể dùng `{ "x": 3, "y": 4 }`, nhưng serializer phải đổi đúng thứ tự khi xuất biên bản. Trong ví dụ JSON của tài liệu này, dùng `{ "y": 4, "x": 3 }` để dễ đối chiếu.

## 3. Ký hiệu nước đi — [KÝ PHÁP GỐC]

| Ký hiệu | Ý nghĩa | Ghi chú |
|---|---|---|
| `_` | Di chuyển | Dấu gạch dưới giữa tọa độ nguồn và đích |
| `@` | Ăn quân và thế chỗ | Quân tấn công đến vị trí quân bị ăn |
| `_@_` | Ăn quân nhưng đứng tại chỗ | Tài liệu gốc diễn tả là `@` có gạch chân; bản thuần văn bản chuẩn hóa thành `_@_` |
| `@”` | Máy bay bị bắn hạ do vùng phòng không | Dấu ngoặc kép cong `”` theo tài liệu |
| `><` | Một đổi một | Chỉ áp dụng cho Máy bay trong tài liệu |
| `>` | Chiếu Tư lệnh | Có thể kèm ký hiệu phong Anh hùng |
| `^` | Chiếu hết / hoàn thành mục tiêu trận | Trong đồ án tổng lực, dùng cho kết thúc liên quan Tư lệnh |
| `!!` | Bị thua | Chú thích kết quả |
| `=` | Hòa | Chú thích kết quả |
| `+` | Nước hay | Nhận xét, không phải dấu chiếu |
| `++` | Nước quá hay | Nhận xét |
| `-` | Nước dở | Nhận xét |
| `--` | Nước quá dở | Nhận xét |
| `?` | Nước nghi ngờ | Nhận xét |
| `$` | Sai luật | Không được ghi như nước hợp lệ đã thực hiện |

**Phong Anh hùng:** Tài liệu thể hiện bằng **ký hiệu quân được in đậm** (ví dụ **K**, **B**, **H**). Việc gõ chuỗi chữ `H K B` liền nhau trong bản trích văn bản không có nghĩa đây là ba quân đồng thời được phong. **[QUY ƯỚC DỰ ÁN]** Trong tệp `.md`, dùng `**K**`; trong log có trường `hero_promoted: true`. Trong tệp văn bản thuần không hỗ trợ in đậm, dùng hậu tố `{hero}` và ghi rõ đây là cách mã hóa kỹ thuật, không phải ký pháp gốc.

## 4. Cú pháp và ví dụ — [KÝ PHÁP GỐC]

Các ví dụ dưới đây minh họa **cú pháp**, không khẳng định đây là nước đi hợp lệ trong một thế cờ cụ thể.

### 4.1. Di chuyển không ăn quân

**Mẫu:** `<QUÂN> [y ; x] _ [y ; x]`

```text
K [4 ; 3] _ [7 ; 6]
```

Máy bay đi từ `[4 ; 3]` đến `[7 ; 6]`.

### 4.2. Ăn quân và thế chỗ

**Mẫu:** `<QUÂN> [nguồn] @ <QUÂN_ĐỊCH> [đích]`

```text
A [4 ; 3] @ D [7 ; 6]
```

Pháo binh ăn Dân quân và chiếm vị trí của Dân quân.

### 4.3. Ăn quân nhưng không thế chỗ

**Mẫu:** `<QUÂN> [nguồn] _@_ <QUÂN_ĐỊCH> [đích]`

```text
K [4 ; 3] _@_ D [7 ; 6]
```

Máy bay ném bom Dân quân nhưng giữ nguyên vị trí.

### 4.4. Máy bay bị bắn hạ khi bay vào vùng phòng không

**Mẫu:** `K [nguồn] @” [đích_dự_kiến]`

```text
K [4 ; 3] @” [7 ; 6]
```

Máy bay bị loại trong quá trình bay; tọa độ sau `@”` là **đích dự kiến**, không được hiểu là vị trí máy bay còn sống.

### 4.5. Máy bay bị bắn hạ khi tấn công

**Mẫu:** `K [nguồn] @” <QUÂN_ĐỊCH> [đích]`

```text
K [4 ; 3] @” D [7 ; 6]
```

Máy bay bị bắn hạ trong đợt tấn công Dân quân. **Không được chỉ dựa vào `@”` để kết luận Dân quân đã bị tiêu diệt**; kết quả cụ thể phải lấy từ sự kiện Engine.

### 4.6. Máy bay một đổi một

**Mẫu:** `K [nguồn] >< <QUÂN_ĐỊCH> [đích]`

```text
K [4 ; 3] >< F [7 ; 6]
```

Máy bay và Cao xạ cùng bị loại.

### 4.7. Chiếu Tư lệnh và phong Anh hùng

```text
K [4 ; 3] _ [7 ; 6] > **K**
K [4 ; 3] @ D [7 ; 6] > **K**
```

Ký hiệu **K** in đậm biểu diễn quân Máy bay được phong Anh hùng. Trong Markdown, phần in đậm là cách trình bày của tài liệu, không nhất thiết là chuỗi ký tự xuất ra trong biên bản văn bản thuần.

### 4.8. Chiếu hết Tư lệnh

```text
K [4 ; 3] _ [7 ; 6] ^ **K**
K [4 ; 3] @ D [7 ; 6] ^ **K**
```

`^` biểu thị tình huống chiếu hết theo ký pháp gốc. **[QUY ƯỚC DỰ ÁN]** Engine vẫn phải quyết định kết thúc trận bằng điều kiện của `GAME_RULES.md`; không kết thúc chỉ vì bản ghi có ký hiệu `^`.

### 4.9. Kết thúc các trận chiến thuật

```text
K [4 ; 3] @ K [7 ; 6] ^
```

Ví dụ minh họa kết thúc trận Không chiến. **Không thuộc phạm vi triển khai chính** của đồ án tổng lực.

## 5. Cách ghi biên bản hai phe — [KÝ PHÁP GỐC]

```text
Bên Đỏ:  H [1 ; 1] _ [5 ; 1]
Bên Xanh: K [10 ; 8] _ [8 ; 6]
```

- Ghi rõ **Đỏ** và **Xanh**.
- Một dòng nước đi có thể được đặt theo lượt và theo phe.
- Trong hệ thống, Đỏ đi trước theo `GAME_RULES.md`.
- Những ví dụ ở trên chỉ là ví dụ ký pháp, không phải một ván cờ đã được kiểm tra hợp lệ.

## 6. Định dạng biên bản trận đấu có thể xuất/nhập — [QUY ƯỚC DỰ ÁN]

### 6.1. Mục tiêu

Tạo một định dạng **tương tự PGN về chức năng**, nhưng **không gọi là PGN chuẩn của cờ vua**. Tên đề xuất: **COTULENH-NOTATION v1** (`.ctn` hoặc `.txt`); có thể xuất `.md` để đọc dễ dàng. Định dạng này lưu thông tin trận, thứ tự lượt, ký pháp nước đi và kết quả.

### 6.2. Header trận

```text
[Format "COTULENH-NOTATION"]
[Version "1"]
[Event "AI Evaluation"]
[Date "2026-10-24"]
[Red "RandomAgent"]
[Blue "HeuristicAgent"]
[Mode "TOTAL_FORCE"]
[TimeControl "30m"]
[Result "*"]
```

Các trường là **metadata kỹ thuật**, không phải ký pháp truyền thống. `Result` có thể là `RED_WIN`, `BLUE_WIN`, `DRAW` hoặc `*` (chưa kết thúc). Không dùng `1-0` / `0-1` nếu không công bố rõ cách ánh xạ phe.

### 6.3. Danh sách lượt

```text
1. Đỏ:  H [1 ; 1] _ [5 ; 1]
   Xanh: K [10 ; 8] _ [8 ; 6]
```

- Số `1.` là **vòng** gồm tối đa một lượt Đỏ và một lượt Xanh.
- Một lượt tổ hợp có thể gồm **nhiều hành động**, phải ghi cùng `turn_id` và các `action_index` khác nhau; không tách thành nhiều lượt giả.
- Không dùng ví dụ ở trên làm dữ liệu kiểm thử nước đi hợp lệ khi chưa có trạng thái bàn tương ứng.

### 6.4. Ký pháp mở rộng cho tổ hợp quân

Tài liệu ký pháp người dùng **không định nghĩa đầy đủ** cách viết lên xe, triển khai, cõng lồng nhau hoặc kết thúc lượt sớm. Để không phát minh ký pháp gốc, dự án ghi các hành động đó trong **event log JSON** (§7). Khi xuất biên bản đọc được, hiển thị một dòng chú giải đặt trong `{...}` bên cạnh nước đi gốc:

```text
3. Đỏ:  B [5 ; 5] _ [6 ; 5] {action=DEPLOY; stack=stack-12; index=1}
         D [5 ; 5] _ [6 ; 6] {action=DEPLOY; stack=stack-12; index=2}
         T [5 ; 5] _ [7 ; 5] {action=STACK_MOVE; stack=stack-12; index=3}
```

Đây là **minh họa định dạng**, không phải xác nhận các điểm đích là nước hợp lệ trong một thế cờ thực tế. Dấu `{...}` là **metadata dự án**, không phải luật ký pháp Cờ Tư Lệnh.

## 7. Event log chuẩn để Game Engine và AI dùng — [QUY ƯỚC DỰ ÁN]

**Nguyên tắc:** Lưu sự kiện cấu trúc trước, **sinh chuỗi ký pháp từ sự kiện**. Không dùng regex phân tích chuỗi ký pháp làm nguồn dữ liệu duy nhất để khôi phục ván.

### 7.1. Mẫu bản ghi

```json
{
  "schema_version": "1.0",
  "game_id": "game-001",
  "turn_id": 8,
  "action_index": 1,
  "side": "RED",
  "actor": {
    "piece_id": "red-aircraft-1",
    "piece_type": "AIRCRAFT",
    "notation_symbol": "K"
  },
  "action_type": "CAPTURE_STAND",
  "from": { "y": 4, "x": 3 },
  "to": { "y": 7, "x": 6 },
  "position_after": { "y": 4, "x": 3 },
  "targets": [
    { "piece_id": "blue-militia-1", "piece_type": "MILITIA", "removed": true }
  ],
  "removed_piece_ids": ["blue-militia-1"],
  "hero_promoted_piece_ids": [],
  "score_delta": { "RED": 10, "BLUE": 0 },
  "stack_id": null,
  "notation": "K [4 ; 3] _@_ D [7 ; 6]",
  "state_hash_before": null,
  "state_hash_after": null
}
```

Các giá trị trong JSON là **ví dụ minh họa**. `to` là tọa độ mục tiêu; `position_after` là vị trí thực tế sau hành động. Hai trường này có thể khác nhau khi ném bom tại chỗ hoặc bị phòng không bắn hạ.

### 7.2. Các loại hành động (`action_type`) và biến cố (`event_type`)

Theo [API_CONTRACT.md](file:///d:/Commander-Chess-AI/docs/API_CONTRACT.md) và [DECISIONS.md](file:///d:/Commander-Chess-AI/docs/DECISIONS.md), hệ thống phân định rõ:

**1. Hành động do người chơi / Agent chủ động gửi (`action_type`):**

| `action_type` | Mô tả | Ký hiệu hiển thị |
|---|---|:---:|
| `MOVE` | Di chuyển không ăn | `_` |
| `CAPTURE_REPLACE` | Ăn và thế chỗ | `@` |
| `CAPTURE_STAND` | Ăn tại chỗ (ném bom, pháo bắn tàu, phá Sở chỉ huy) | `_@_` |
| `BOARD` | Quân lên phương tiện cõng | Chú giải metadata |
| `DEPLOY` | Quân triển khai tách khỏi phương tiện | Ký pháp đi/ăn + metadata |
| `STACK_MOVE` | Phương tiện mang theo quân di chuyển | Ký pháp đi/ăn + metadata |
| `END_TURN` | Chủ động kết thúc lượt tổ hợp sớm | Chú giải metadata |

**2. Biến cố do Engine tự động phát sinh (`event_type`):**

| `event_type` | Mô tả | Ký hiệu hiển thị |
|---|---|:---:|
| `AIR_SHOT_DOWN` | Máy bay bị phòng không bắn hạ | `@”` |
| `AIR_EXCHANGE` | Máy bay 1 đổi 1 trong vùng phòng không | `><` |
| `HERO_PROMOTION` | Phong Anh hùng tự động | Ký hiệu quân in đậm (ví dụ **K**) |
| `HQ_DESTROYED` | Sở chỉ huy bị phá hủy, Tư lệnh lộ diện | Chú giải metadata |
| `GAME_OVER` | Kết thúc ván đấu | `^` (thắng) hoặc `!!` (thua) |

**Quan trọng:** Các sự kiện tự động (phong Anh hùng, phòng không, kết thúc ván) được ghi là **events / effects** của một hành động chính, thay vì chiếm thêm một lượt. Cần giữ thứ tự nhân quả.

### 7.3. Các trường bắt buộc khi lưu ván hoàn chỉnh

- **Trận:** `game_id`, `rules_version`, `notation_version`, `mode`, `red_player`, `blue_player`, `initial_state`, `result`, `termination_reason`.
- **Lượt:** `turn_id`, `side`, `started_at`, `ended_at`, `actions`.
- **Hành động:** `action_index`, `piece_id`, `action_type`, `from`, `to`, `position_after`, `targets`, `removed_piece_ids`, `notation`, `effects`.
- **Tổ hợp:** `stack_id`, cấu trúc chở quân trước/sau hành động, danh sách quân đã hành động, thời điểm kết thúc lượt.
- **Kiểm chứng:** `state_hash_before`, `state_hash_after` (khuyến nghị), `score_before`, `score_after`.

Nếu không lưu `initial_state` và các thay đổi tổ hợp/phong Anh hùng, biên bản ký pháp ngắn **không đủ** để phát lại chính xác mọi ván.

## 8. Quy tắc serializer và parser — [QUY ƯỚC DỰ ÁN]

1. **Engine xác nhận nước hợp lệ trước**, sau đó phát sự kiện và sinh ký pháp. Không cho phép văn bản tự làm thay đổi trạng thái Engine.
2. Chuẩn hiển thị: `<KÝ_HIỆU> [y ; x] <TOÁN_TỬ> ...`, dùng đúng thứ tự tung–hoành.
3. Parser chỉ nhận các mẫu đã hỗ trợ. Ký hiệu Tư lệnh là `⋆`; nếu hành động tổ hợp không thể biểu diễn duy nhất, trả về `UNSUPPORTED_NOTATION` hoặc dùng event log JSON, **không đoán**.
4. `@”` không tự xác nhận quân mục tiêu có bị tiêu diệt hay không; phải đọc `removed_piece_ids`.
5. `^`, `>`, phong Anh hùng, điểm số và kết quả phải được **tính từ trạng thái Engine**. Khi nhập tệp, nếu ghi chú mâu thuẫn Engine, đánh dấu `NOTATION_STATE_MISMATCH`.
6. Dấu `+`, `++`, `-`, `--`, `?` là **chú giải đánh giá**, không thay đổi tính hợp lệ hay điểm số.
7. Nước sai luật `$` chỉ được ghi vào **attempt log** (nếu muốn theo dõi người chơi thử sai), không thêm vào lịch sử nước hợp lệ.
8. Phải hỗ trợ Unicode `@”` và cách trình bày in đậm; có thể cung cấp chế độ ASCII cho nội bộ nhưng không thay ký pháp gốc trong bản xuất người đọc.
9. **Replay:** nạp trạng thái đầu, thực hiện tuần tự các action/effect, kiểm tra hash và kết quả cuối; không dựa duy nhất vào chuỗi biên bản.
10. **Export:** có thể xuất `notation_text` để đọc và `events.json` để phát lại. **Import:** ưu tiên JSON có cấu trúc; nhập văn bản chỉ hỗ trợ khi đủ thông tin và có thể xác thực.

## 9. Kiểm thử chấp nhận

| Mã | Trường hợp | Kết quả kỳ vọng |
|---|---|---|
| `NOT-01` | `K [4 ; 3] _ [7 ; 6]` | Parse được quân, nguồn, đích, loại `MOVE` |
| `NOT-02` | `A [4 ; 3] @ D [7 ; 6]` | `CAPTURE_REPLACE`, mục tiêu `D` |
| `NOT-03` | `K [4 ; 3] _@_ D [7 ; 6]` | `CAPTURE_STAND`, vị trí sau vẫn là nguồn |
| `NOT-04` | `K [4 ; 3] @” [7 ; 6]` | `AIR_SHOT_DOWN`, không giả định Máy bay sống ở đích |
| `NOT-05` | `K [4 ; 3] >< F [7 ; 6]` | `AIR_EXCHANGE`, hai quân bị loại theo Engine |
| `NOT-06` | Chuỗi `> **K**` | Hiển thị chiếu và phong Anh hùng; lưu trạng thái riêng |
| `NOT-07` | Nước có `^` nhưng Engine chưa kết thúc | Báo mismatch, không ép kết thúc |
| `NOT-08` | Biên bản có `+`, `++`, `?` | Lưu đánh giá, không thay đổi nước |
| `NOT-09` | Nước tổ hợp 3 hành động | Cùng `turn_id`, `action_index` tăng dần |
| `NOT-10` | Máy bay bị phòng không sau nước của đối phương | Ghi effect đúng thời điểm, không tạo lượt giả |
| `NOT-11` | Nạp và phát lại `events.json` | Trạng thái và điểm cuối khớp bản gốc |
| `NOT-12` | Tọa độ `[4 ; 3]` | Đúng `y=4, x=3` |
| `NOT-13` | `⋆ [4 ; 3] _ [5 ; 3]` | Parser nhận `⋆` là `COMMANDER`; giữ đúng thứ tự tọa độ |

## 10. Các điểm cần xác nhận trước khi khóa ký pháp v1

1. **Ký hiệu Tư lệnh đã chốt:** `⋆` (`\star` trong LaTeX).
2. **Cách hiển thị phong Anh hùng trong văn bản thuần**: ký hiệu in đậm là nguyên tắc gốc; `{hero}` chỉ là đề xuất kỹ thuật.
3. **Cách biểu diễn đầy đủ một lượt cõng quân**: tài liệu ghi biên bản chưa có cú pháp chuẩn cho lên phương tiện, tách quân, cõng lồng nhau và kết thúc lượt sớm.
4. **Cách ghi việc Sở chỉ huy bị phá nhưng Tư lệnh sống**: cần thống nhất với quy tắc trạng thái trong `GAME_RULES.md`.
5. **Ký pháp chính thức cho Máy bay bị tiêu diệt do vùng phòng không di chuyển đến**: chưa có mẫu riêng trong tài liệu.

---

**Kết luận:** `GAME_RULES.md` quy định **đi được hay không và kết quả nước đi**; `MOVE_NOTATION.md` quy định **nước đi được mô tả và ghi lại như thế nào**. Trong đồ án, **event log JSON là dữ liệu gốc để replay**, còn **biên bản ký pháp là biểu diễn dễ đọc** cho người chơi, giảng viên và nghiên cứu AI.
