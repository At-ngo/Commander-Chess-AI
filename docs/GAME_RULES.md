# GAME_RULES.md — Đặc tả luật Cờ Tư Lệnh

**Phiên bản:** 24/10/2026  
**Phạm vi chính:** Cờ Tư Lệnh cơ bản, chiến tranh tổng lực, hai phe Đỏ và Xanh.  
**Đối tượng:** Game Engine, AI Agent, backend, frontend và kiểm thử tự động.

> **NGUYÊN TẮC BẮT BUỘC:** Đây là tài liệu luật độc lập. Không cần truy cập tài liệu bên ngoài để đọc các quy tắc đã được mô tả. Game Engine là nguồn xác định tính hợp lệ của nước đi; giao diện không tự cài đặt luật riêng. Các mục `NEEDS_DECISION` phải được xác nhận trước khi lập trình tính năng tương ứng. Không tự suy diễn để lấp khoảng trống.

## 0. Trạng thái và thứ tự áp dụng luật

- `CONFIRMED`: quy tắc đã được chủ dự án xác nhận hoặc hai bản mô tả nhất quán.
- `PROJECT_DECISION`: quyết định riêng cho phiên bản nghiên cứu; được ưu tiên khi khác mô tả truyền thống.
- `NEEDS_DECISION`: có khác biệt, thiếu chi tiết hoặc chưa đủ thông tin để thực thi duy nhất.
- **Ưu tiên:** `PROJECT_DECISION` > quy tắc được mô tả rõ trong tài liệu này > quy tắc tổng quát.
- Nếu một hành động vi phạm nhiều luật, Game Engine trả về lỗi hợp lệ có mã, không âm thầm sửa hành động.
- Một *lượt* là quyền hành động của một phe; một *hành động* là một nước đi/ăn/triển khai của một quân trong tổ hợp. Một lượt có thể có 1–3 hành động nếu áp dụng luật cõng quân.

## 1. Mục tiêu, bàn cờ và tọa độ

- Hai phe **Đỏ** và **Xanh**; **Đỏ đi trước** (`PROJECT_DECISION`).
- Mỗi phe có 19 quân, tổng cộng 38 quân, thuộc 11 loại.
- Bàn cờ có **11 đường dọc** (hoành độ `x = 0..10`) và **12 đường ngang** (tung độ `y = 0..11`), tức **132 giao điểm**.
- Gốc `(0,0)` ở góc **dưới trái**, sát vùng biển. Để tránh nhầm: tài liệu dùng biểu diễn **`(y,x)`** khi ghi tọa độ truyền thống, ví dụ `(3,5)` nghĩa là `y=3, x=5`. Nếu API dùng `{x,y}`, phải chuyển đổi tường minh.
- Quân đặt trên **giao điểm**, không đặt ở tâm ô.
- **Biển:** hai dải sát mép trái, `x=0..2`, kéo dài theo `y=0..11`. Ranh giới `x=2` là bờ biển, **không đồng nghĩa mọi giao điểm x=2 đều là nước sâu**.
- **Sông:** dải ngang giữa hai chiến tuyến, từ `y=5` đến `y=6`; khi kiểm tra một bước vượt sông, phải xét **đoạn nối** giữa hai giao điểm ở hai bờ, không coi toàn bộ các giao điểm ở `y=5` hay `y=6` là quân đứng giữa nước.
- **Hai ngầm qua sông:** các hành lang theo `x≈5` và `x≈7` được đánh dấu trên bàn cờ; mọi quân được phép qua ngầm theo luật địa hình.
- **Nước sâu:** các đoạn sông khác ngoài ngầm; áp dụng luật vượt sông ở §4.
- **Bờ biển sát nước:** `x=2` (`PROJECT_DECISION`).

**CONFIRMED — BOARD_DATA:** Đã chuẩn hóa chính thức tại [GAME_RULES_PHAN_1_TOA_DO.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES_PHAN_1_TOA_DO.md) và cài đặt trong `packages/commander_game_engine/initial_setup.py`. Tọa độ đủ 38 quân chuẩn, Đỏ đi trước, hai đường ngầm tại `((5, 5), (6, 5))` và `((5, 7), (6, 7))`, Tàu chiến Xanh thứ hai tại `(8, 2)`.

### 1.1. Quy ước cho bộ sinh nước

- `ORTHOGONAL`: bốn hướng lên, xuống, trái, phải.
- `DIAGONAL`: bốn hướng chéo 45°.
- `ALL_8`: cả tám hướng.
- Một đoạn = khoảng cách giữa hai giao điểm kề nhau trên một hướng hợp lệ.
- Quân không được đi xuyên quân cản đường, **trừ** các ngoại lệ được nêu rõ (pháo khi ăn, máy bay, hải quân và tương tác bờ).
- Một nước ăn quân thường đưa quân tấn công tới tọa độ mục tiêu (**thế chỗ**), trừ luật **bắn tại chỗ / ném bom / 1 đổi 1**.

## 2. Quân cờ và điểm

| Loại | Mã | Số lượng mỗi phe | Điểm khi bị tiêu diệt |
|---|---|---:|---:|
| Tư lệnh | `COMMANDER` | 1 | 100 |
| Bộ binh | `INFANTRY` | 2 | 10 |
| Xe tăng | `TANK` | 2 | 20 |
| Dân quân | `MILITIA` | 1 | 10 |
| Công binh | `ENGINEER` | 2 | 10 |
| Pháo binh | `ARTILLERY` | 2 | 30 |
| Cao xạ | `ANTI_AIR` | 2 | 10 |
| Tên lửa phòng không | `MISSILE` | 1 | 20 |
| Máy bay / Không quân | `AIRCRAFT` | 2 | 40 |
| Hải quân / Tàu chiến | `NAVY` | 2 | 80 |
| Sở chỉ huy | `HEADQUARTERS` | 2 | 10 |

- Quân **Anh hùng** được cộng **10 điểm** vào giá trị của quân đó khi tính điểm bị tiêu diệt.
- Điểm Hải quân 80 = tên lửa hải đối hải 40 + pháo hạm 30 + cao xạ 10.
- Khi một phương tiện chở quân bị tiêu diệt, tính tổng điểm của phương tiện và **tất cả quân bên trong**, kể cả quân cõng lồng nhau; không đếm trùng.

## 3. Di chuyển và ăn quân theo loại

| Quân | Di chuyển thường (ô trống) | Tấn công / Ăn quân | Đối tượng có thể tấn công | Tương tác Sông / Biển |
|---|---|---|---|---|
| **⋆ Tư lệnh** (`COMMANDER`) | `ORTHOGONAL`, không giới hạn đoạn đến khi gặp vật cản (cấm vào ô nguy hiểm/đối mặt) | `ORTHOGONAL`, **1 đoạn** (thế chỗ `@` hoặc `_@_` tàu biển/SCH) | **Mọi quân địch (kể cả Máy bay)** và tàu ở bờ/biển gần. Tuyệt đối cấm đi vào ô khiến Tư lệnh bị uy hiếp. | Qua được sông sâu. Không ra biển sâu. Chỉ `HEADQUARTERS` thường che chở khỏi đối mặt khi đã vào trong; cấm lên phương tiện/SCH trên đường nhìn Tư lệnh địch và cấm phương tiện đang chở Tư lệnh dừng trên đường nhìn Tư lệnh địch. |
| **S Sở chỉ huy** (`HEADQUARTERS`) | Thường: Không di chuyển. Anh hùng: `ALL_8`, 1–2 đoạn | Thường: Không ăn. Anh hùng: `ALL_8`, 1–2 đoạn | Thường che chở Tư lệnh; chỉ phong Anh hùng khi chỉ còn 1 SCH duy nhất (+ Tư lệnh đã bước ra). | Cố định trên đất liền. |
| **B Bộ binh** (`INFANTRY`) | `ORTHOGONAL`, 1 đoạn | `ORTHOGONAL`, 1 đoạn (thế chỗ) | Mọi quân mặt đất, **Máy bay**, tàu ở sát bờ. | **Bơi qua sông sâu được**. Lên được xe tăng, tàu chiến. |
| **D Dân quân** (`MILITIA`) | `ALL_8` (8 hướng), 1 đoạn | `ALL_8`, 1 đoạn (thế chỗ) | Mọi quân mặt đất, **Máy bay**, tàu ở sát bờ. | Qua được sông sâu. Lên được xe tăng, tàu chiến. |
| **T Xe tăng** (`TANK`) | `ORTHOGONAL`, 1–2 đoạn (bị cản nếu đoạn 1 có quân) | `ORTHOGONAL`, 1–2 đoạn | Quân mặt đất, **Máy bay**; bắn tàu trên biển tại chỗ (`_@_`). | Không tự qua sông sâu (qua ngầm hoặc Công binh chở). Cõng tối đa 2 quân bộ. |
| **C Công binh** (`ENGINEER`) | `ORTHOGONAL`, 1 đoạn | `ORTHOGONAL`, 1 đoạn (thế chỗ) | Mọi quân mặt đất, **Máy bay**, tàu ven bờ. | Bơi qua sông sâu được. Đứng bờ sông cõng vũ khí nặng qua sông. |
| **A Pháo binh** (`ARTILLERY`) | `ALL_8`, 1–3 đoạn (bị cản khi đi/lên xe) | `ALL_8`, 1–3 đoạn (**BẮN XUYÊN BẤT KỲ SỐ LƯỢNG QUÂN CẢN**) | Mọi quân mặt đất (thế chỗ `@`), **Máy bay**; bắn tàu trên biển tại chỗ (`_@_`). | Không tự qua sông sâu vào ô trống (trừ ngầm `x=5,7` thẳng hoặc Công binh chở; được ăn vượt sông `@`). |
| **F Cao xạ** (`ANTI_AIR`) | `ORTHOGONAL`, 1 đoạn | `ORTHOGONAL`, 1 đoạn (thế chỗ) | **Máy bay**, mọi quân bộ và tàu ven bờ/biển gần. Tạo vành đai lửa 1 đoạn. | Không tự qua sông sâu vào ô trống (trừ ngầm `x=5,7` thẳng hoặc Công binh chở; được ăn vượt sông `@`). |
| **L Tên lửa** (`MISSILE`) | `ORTHOGONAL`, 1–2 đoạn; `DIAGONAL`, 1 đoạn (**KHÔNG xuyên vật cản khi đi/lên xe**) | `ORTHOGONAL`, 1–2 đoạn; `DIAGONAL`, 1 đoạn (**ĐƯỢC ĂN XUYÊN VẬT CẢN**) | **Máy bay, tàu chiến, mọi quân mặt đất** (ăn thế chỗ `@` trên đất/bờ, bắn tại chỗ `_@_` tàu biển `x<=1` hoặc SCH che Tư lệnh). Tạo vành đai lửa. | Không tự qua sông sâu vào ô trống (trừ ngầm `x=5,7` thẳng hoặc Công binh chở). **Không dừng trên biển trống (`x<=1`)**. |
| **K Máy bay** (`AIRCRAFT`) | `ALL_8`, 1–4 đoạn (**BAY XUYÊN MỌI QUÂN TA VÀ ĐỊCH**) | `ALL_8`, 1–4 đoạn | • Đánh Máy bay: **Thế chỗ** (`@`).<br>• Đánh đất/biển: **Ném bom tại chỗ** (`_@_`) hoặc **Oanh tạc thế chỗ** (`@`). | **Không dừng trên biển trống (`x<=1`)**, được bay qua biển để lên Tàu chiến cùng phe. Bị bắn hạ bởi vành đai lửa phòng không. |
| **H Hải quân** (`NAVY`) | `ALL_8`, 1–4 đoạn trên sông/biển (**được vượt qua quân ta không phải Hải quân ở bờ biển/bờ sông**) | 3 hệ vũ khí: diệt hạm 4 đoạn, pháo hạm đất liền 3 đoạn (qua vật cản), cao xạ hạm 1 đoạn (AH: +1) | Tàu chiến địch, **mọi quân trên đất liền/bờ** (pháo hạm), **máy bay**. | Hoạt động trên **Biển (`x=0..2`)** và **Sông (`y=5..6`)**. Không qua ngầm. Bị chặn di chuyển bởi đất liền sâu & tàu chiến khác. |

### 3.1. Chặn đường, tầm bắn và mục tiêu hợp lệ
- **Tất cả các loại quân chiến đấu đều có thể tấn công/ăn Máy bay (`AIRCRAFT`)** nằm trong tầm ăn quân hợp lệ của quân đó (ngoại trừ Sở chỉ huy thường bất động).
- Xe tăng, Tư lệnh và các quân đi nhiều đoạn (trừ các ngoại lệ dưới đây) bị chặn bởi quân nằm giữa khi di chuyển và khi ăn.
- **Tên lửa (`MISSILE`):** **Được phép ăn xuyên vật cản** (`CAPTURE_REPLACE` trên đất/bờ, `CAPTURE_STAND` ngoài biển/SCH) trong tầm 1–2 đoạn thẳng hoặc 1 đoạn chéo (Anh hùng: 1–3 thẳng, 1–2 chéo), nhưng **TUYỆT ĐỐI KHÔNG được di chuyển (`MOVE`) hay lên phương tiện (`BOARD`/`PICKUP`) xuyên qua vật cản**.
- **Tàu chiến (`NAVY`) di chuyển & bắn vào đất liền:**
  - Di chuyển tối đa 4 đoạn (Anh hùng 5 đoạn) trên mặt nước (`x<=2` hoặc `y=5,6`, trừ 2 ngầm đá). Bị chặn ngay bởi đất liền sâu (`!isWater`), các đường chéo cắt góc đất liền (ví dụ giữa `(2, 7)` và `(3, 6)` ở Bắc sông, hoặc giữa `(2, 4)` và `(3, 5)` ở Nam sông), và bị chặn bởi tàu chiến khác (`NAVY`).
  - **Ngoại lệ bờ biển/bờ sông:** Khi di chuyển trên bờ biển (`x=2`) hoặc bờ sông (`y=5,6`), tàu chiến **được phép đi xuyên qua (vượt qua) quân đồng minh KHÔNG phải Hải quân** đang đứng trên mép bờ để tới các ô nước/bờ phía sau hoặc dừng tại ô trống sau đó; tàu vẫn dừng trước tàu chiến khác (`NAVY`) và không vượt qua quân địch (chỉ ăn `@` tại ô quân địch ở bờ).
  - **Pháo hạm bắn đất liền:** Tàu chiến được phép dùng Pháo hạm bắn quân địch sâu trong đất liền (`LAND`, bờ sông, ngầm đá) theo cả hướng thẳng và chéo trong tầm **3 đoạn** (Anh hùng **4 đoạn**), kể cả vượt qua vật cản hoặc tàu chiến khác: nếu đích ở mép bờ thông thoáng (không phải SCH che Tư lệnh) thì ăn thế chỗ (`CAPTURE_REPLACE` `@`), nếu đích nằm sâu trong đất liền, ngầm đá, bị chắn tàu, hoặc là SCH che Tư lệnh thì bắn tại chỗ (`CAPTURE_STAND` `_@_`).
- **Pháo binh (`ARTILLERY`):** Được **bắn xuyên bất kỳ số lượng quân cản nào** trong tầm 1–3 đoạn theo 8 hướng khi ăn thế chỗ (`@`) hoặc bắn tàu biển tại chỗ (`_@_`), nhưng **không được đi xuyên quân** khi chỉ di chuyển (`MOVE` / `BOARD`).
- **Thả bom / Bắn tại chỗ (`CAPTURE_STAND` - `_@_`):** Áp dụng cho: (1) Máy bay ném bom tại chỗ đối với quân đất/nước ngoài vùng phòng không; (2) Quân bộ, Xe tăng, Pháo binh, Tên lửa bắn Tàu chiến địch ngoài biển sâu (`x<=1`); (3) Hải quân bắn Pháo hạm vào đất liền sâu hoặc qua vật cản; (4) Mọi quân tấn công Sở chỉ huy đang che chở Tư lệnh.
- **Tên lửa và Máy bay trên biển:** Tên lửa và Máy bay không thể di chuyển/dừng chân trên các ô biển trống (`x<=1`). Máy bay được quyền bay qua biển để đáp lên Tàu chiến cùng phe (`BOARD`) nếu tàu chiến nằm trên đường bay.
- **Máy bay (`AIRCRAFT`):** Được **bay xuyên và ăn xuyên quân ta lẫn quân địch** trong tầm 4 đoạn (Anh hùng 5 đoạn), nhưng toàn bộ quỹ đạo bay chịu sự khống chế của vành đai lửa phòng không đối phương (trừ Máy bay Anh hùng).
## 4. Sông, biển, bờ và Sở chỉ huy

### 4.1. Vượt sông
1. Qua **ngầm** (`(5, 5) - (6, 5)` và `(5, 7) - (6, 7)`): tất cả quân có thể vượt qua theo **đường thẳng** tại cột `x = 5` và `x = 7` (`from_x == to_x && (from_x == 5 || from_x == 7)`).
2. Qua **nước sâu**: Tư lệnh, Bộ binh, Dân quân, Công binh có thể tự vượt sông.
3. Xe tăng, Cao xạ, Pháo binh, Tên lửa **không được tự di chuyển vào ô trống qua nước sâu**:
   - **Cấm đi chéo qua sông sâu:** Tên lửa, Pháo binh, Cao xạ tuyệt đối **không thể đi qua sông sâu theo đường chéo** sang ô trống (kể cả đường chéo có xuất phát hoặc kết thúc tại cột sông ngầm x=5 hay x=7).
   - Chỉ có thể đi qua sông ngầm theo **đường thẳng** ở cột `x = 5` và `x = 7`.
4. **Ngoại lệ vượt sông sâu khi ăn quân (DEC-018):** Các loại vũ khí nặng (Tên lửa, Pháo binh, Cao xạ) **được phép vượt sông sâu bằng nước ăn quân thế chỗ (`CAPTURE_REPLACE`)** bên kia sông sâu trong phạm vi di chuyển/ăn quân hợp lệ của mình (cả đường thẳng và đường chéo). Không được áp dụng ngoại lệ này cho nước di chuyển vào ô trống.
5. **Hỗ trợ vượt sông bằng Công binh:** Quân nặng muốn sang bờ bên kia mà không có quân địch để ăn thế chỗ thì phải nhờ Công binh đứng ở bờ sông (`y = 5` hoặc `y = 6`) cõng qua (`BOARD` / `DEPLOY`).

### 4.2. Biển, bờ biển và bờ sông
- Quân bộ **không được di chuyển ra biển sâu (`x=0..1`)**. Khi tấn công tàu ở vị trí trên biển, quân bộ ăn tại chỗ (`_@_`), giữ nguyên vị trí trên đất liền. Quân bộ trên bờ (`x=2`) được phép lên Tàu chiến đồng minh đang ở biển sâu (`x<=1`) nếu đủ sức chứa.
- Hải quân hoạt động trên biển (`x=0..2`) và vùng nước sông (`y=5..6`); không đi vào đường ngầm và không tiến sâu vào đất liền.
- Hải quân không đi xuyên qua tàu chiến khác (`NAVY`, kể cả cùng phe hay đối phương), nhưng **được phép vượt qua quân ta không phải Hải quân đang đứng ở bờ biển (`x=2`) hoặc bờ sông (`y=5,6`)**.

### 4.3. Sở chỉ huy và Quy tắc Phong Anh hùng Trễ (`DELAYED_SOLITARY_HQ`)
- Mỗi phe có 2 Sở chỉ huy; công trình cố định, không di chuyển, không ăn quân trong trạng thái thường.
- Tư lệnh có thể trú ẩn trong Sở chỉ huy thường; Sở chỉ huy che chở hoàn toàn cho Tư lệnh khỏi bị chiếu bởi hỏa lực đối phương (đối phương phải đánh phá Sở chỉ huy tại chỗ `CAPTURE_STAND`, Sở chỉ huy bị phá hủy, Tư lệnh sống sót lộ diện tại vị trí đó).
- **Điều kiện 2 SCH vs 1 SCH duy nhất (DEC-015 & DEC-020):**
  - Nếu phe vẫn còn **2 Sở chỉ huy** và Tư lệnh (dù không còn quân chiến đấu khác): **cả 2 Sở chỉ huy tuyệt đối KHÔNG được phong Anh hùng**, giữ nguyên trạng thái bất động và cho phép Tư lệnh ẩn nấp.
  - Khi toàn bộ quân tác chiến (không tính Tư lệnh & SCH) đã bị tiêu diệt và chỉ còn **đúng 1 Sở chỉ huy duy nhất cùng Tư lệnh**:
    - Nếu Tư lệnh **KHÔNG** đang núp bên trong Sở chỉ huy duy nhất đó → Sở chỉ huy **lập tức được phong Anh hùng** (Bộ binh Anh hùng: 8 hướng 1–2 đoạn, không còn cho Tư lệnh ẩn nấp).
    - Nếu Tư lệnh **ĐANG NỨP bên trong** Sở chỉ huy duy nhất đó (ví dụ quân chiến đấu cuối cùng bên ngoài vừa bị ăn) → Sở chỉ huy **CHƯA được phong Anh hùng ngay**. Tới lượt của người chơi đó, người chơi **CHỈ có nước đi duy nhất là di chuyển Tư lệnh rời khỏi Sở chỉ huy** (không được phép ở lại hoặc quay lại núp vào Sở chỉ huy); **ngay khi Tư lệnh bước ra khỏi Sở chỉ huy thì Sở chỉ huy duy nhất đó được phong Anh hùng ngay lập tức**.

## 5. Hải quân và ba hệ vũ khí

| Hệ vũ khí | Mục tiêu | Tầm / Hướng | Hình thức ăn quân |
|---|---|---|---|
| **Tên lửa hải đối hải** | Chỉ Tàu chiến địch | `ALL_8`, tối đa 4 đoạn | Thế chỗ nếu đường biển thông suốt; bắn tại chỗ nếu bị ngăn cách bởi mũi đất |
| **Pháo hạm** | Quân bộ / bờ sông / bờ biển / đất liền | `ALL_8`, tối đa 3 đoạn (AH: 4 đoạn), **bắn qua vật cản** | Đích ở mép bờ thông suốt (không phải SCH che Tư lệnh): thế chỗ (`@`); đích sâu trong đất liền, ngầm đá, bị cản tàu hoặc SCH che Tư lệnh: bắn tại chỗ (`_@_`) |
| **Cao xạ hạm** | Máy bay địch | Phòng không 1 đoạn ngang/dọc (AH: 2 thẳng, 1 chéo) | Tạo vành đai lửa bảo vệ tàu và các ô kề cạnh |

- Tàu chiến chỉ tấn công tàu chiến địch ở phía trước dọc theo tia ngắm, không xuyên qua tàu địch ở trước để bắn tàu địch phía sau; tuy nhiên tàu vẫn bắn Pháo hạm qua tàu địch/vật cản để tiêu diệt quân bộ trên đất liền trong tầm 3 đoạn (Anh hùng 4 đoạn).
- Quân phòng không (`ANTI_AIR`, `MISSILE`, `NAVY`) chỉ phát sinh vành đai lửa khi đang đứng trực tiếp trên bàn cờ (`carried_by_id == null`), không phát sinh vành đai lửa khi đang bị quân khác cõng bên trong.
- Tàu chiến có thể cõng tối đa 1 máy bay hoặc 1 xe tăng hoặc 2 bộ binh/dân quân trên hải trình.

## 6. Vành đai lửa Phòng không và Máy bay

### 6.1. Phạm vi Vành đai lửa Phòng không
Vành đai lửa là **vùng cấm bay thụ động tự động kích hoạt** của lực lượng phòng không:
- **Cao xạ (`ANTI_AIR`):** Bảo vệ bán kính **1 đoạn ngang/dọc** (4 giao điểm kề cạnh).
- **Tên lửa (`MISSILE`):** Bảo vệ bán kính **1–2 đoạn ngang/dọc và 1 đoạn chéo** (vành đai hỏa lực diện rộng).
- **Tàu chiến (`NAVY` - Cao xạ hạm):** Bảo vệ bán kính **1 đoạn ngang/dọc** xung quanh tàu.

### 6.2. Cơ chế tương tác với Máy bay (`AIRCRAFT`)
1. **Bay qua vùng cấm bay (`AIR_SHOT_DOWN`):** Máy bay thường bay **vào hoặc xuyên qua** bất kỳ ô nào thuộc vành đai lửa của địch sẽ bị hỏa lực phòng không bắn hạ ngay lập tức, kể cả khi điểm đến cuối cùng nằm ngoài vùng cấm bay.
2. **Tấn công trong vùng phòng không — Quy tắc 1 đổi 1 (`AIR_EXCHANGE`):** Nếu máy bay tấn công một quân địch nằm bên trong vành đai lửa của đối phương, máy bay tiêu diệt được mục tiêu nhưng **bản thân máy bay cũng bị bắn rơi cùng lúc (1 đổi 1)**.
3. **Chồng lấn nhiều vùng phòng không:** Nếu mục tiêu nằm trong giao điểm bảo vệ của nhiều quân phòng không, chỉ máy bay tấn công và mục tiêu bị tiêu diệt; các quân phòng không còn lại vẫn an toàn và tiếp tục duy trì vành đai bảo vệ.
4. **Phòng không áp sát máy bay (`AA_DEFERRED_THREAT`):** Nếu quân phòng không di chuyển tới vị trí làm máy bay địch lọt vào vùng cấm, máy bay **không bị bắn hạ ngay ở lượt đó**. Đến lượt kế tiếp của phe sở hữu máy bay, nếu máy bay không bay thoát khỏi vùng nguy hiểm thì sẽ bị tiêu diệt.
5. **Hiển thị trực quan trên giao diện Web:** Khi người chơi click chọn quân Máy bay, toàn bộ giao điểm thuộc vành đai lửa phòng không của đối phương sẽ được hiển thị bằng hiệu ứng radar cảnh báo nguy hiểm (`🔥`) trên bàn cờ.
6. **Ngoại lệ Máy bay Anh hùng:** Máy bay Anh hùng là **máy bay tàng hình**, hoàn toàn miễn nhiễm với vành đai lửa (bay qua không bị bắn rơi, tấn công trong vùng cấm không chịu quy tắc 1 đổi 1).

### 6.3. Hai hình thức tấn công của Máy bay
- **Oanh tạc thế chỗ (`CAPTURE_REPLACE` - `@`):** Máy bay tiêu diệt mục tiêu và bay đến chiếm lĩnh tọa độ mục tiêu. Khi không chiến tiêu diệt Máy bay địch, **bắt buộc phải thế chỗ**.
- **Ném bom tại chỗ (`CAPTURE_STAND` - `_@_`):** Máy bay tiêu diệt mục tiêu mặt đất/mặt nước hợp lệ ngoài vùng phòng không nhưng **giữ nguyên vị trí ban đầu**. Không được ném bom tại chỗ để trốn tránh quy tắc 1 đổi 1 nếu mục tiêu nằm trong vùng phòng không.

## 7. Tư lệnh, Quy tắc Cấm đối mặt và Phong Anh hùng

### 7.1. Quy tắc Tối thượng: Cấm Tư lệnh Đối mặt nhau (Lộ mặt Tướng)
- **Định nghĩa:** Hai Tư lệnh của hai phe **không bao giờ được cùng nằm trên một đường thẳng (cùng hàng ngang hoặc cùng cột dọc)** mà ở giữa **không có bất kỳ quân cờ đang đứng trực tiếp trên bàn cờ nào che chắn** (bất kể quân phe mình hay phe địch).
- **Quy tắc Đối mặt Khi Cõng / Trú Ẩn Tư lệnh (`DEC-021`):**
  1. **Sở chỉ huy thường (`!is_hero`):** Chỉ Sở chỉ huy thường mới che chở Tư lệnh khỏi thế đối mặt và khỏi bị chiếu *khi Tư lệnh đã trú ẩn bên trong*; tuy nhiên Tư lệnh **không được lên (`BOARD`) Sở chỉ huy đang nằm trên đường nhìn thẳng không vật cản của Tư lệnh địch** (Q9).
  2. **Phương tiện cơ động (`TANK`, `AIRCRAFT`, `NAVY`, kể cả cõng lồng nhau):**
     - Tư lệnh **tuyệt đối không được lên (`BOARD`) phương tiện đang nằm trên đường nhìn thẳng (không có vật cản) của Tư lệnh đối phương** (kể cả trường hợp trước đó chính Tư lệnh hoặc phương tiện làm vật chắn).
     - Khi phương tiện đang cõng Tư lệnh (hoặc thực hiện `PICKUP` đón Tư lệnh), phương tiện đó **tuyệt đối không được dừng/đứng trên vị trí nằm trong tầm nhìn thẳng không vật cản của Tư lệnh đối phương** (tính đối mặt tại vị trí phương tiện gốc). Phương tiện chỉ được phép đi/bay cắt ngang qua đường nhìn đó nếu không dừng lại trên tuyến đối mặt, hoặc phải đi một mình tách cargo (`carry_cargo = False`).
     - Quân đứng giữa (phương tiện đang chở Tư lệnh) và Tư lệnh đối phương cũng bị ghim (`Pin`), không được rời khỏi đường thẳng chắn.
- **Các nước đi bất hợp lệ do vi phạm quy tắc đối mặt:**
  1. **Nước đi tự sát:** Tư lệnh không được tự di chuyển, lên phương tiện/Sở chỉ huy vào đường thẳng trống đối mặt Tư lệnh địch.
  2. **Phương tiện chở Tư lệnh lộ mặt:** Xe tăng, Máy bay, Tàu chiến đang chở Tư lệnh không được dừng lại (hoặc đón Tư lệnh) trên đường thẳng trống đối mặt Tư lệnh địch.
  3. **Quân cản bị ghim (`Pin`):** Nếu trên hàng/cột giữa hai Tư lệnh (kể cả khi Tư lệnh đang ngồi trong phương tiện cơ động) chỉ có **duy nhất 1 quân cản**, thì quân cản đó **tuyệt đối không được di chuyển rời khỏi đường thẳng đó**.
  4. **Ăn quân làm lộ mặt:** Không được ăn quân cản duy nhất nếu nước ăn đó làm trống đường đối mặt.

### 7.1.1. Quy tắc An Toàn Tuyệt Đối Cho Tư Lệnh (King Safety — DEC-019 & DEC-020)
- **Cấm tuyệt đối mọi nước đi để lộ Tư lệnh cho đối phương ăn:** Mọi nước đi khiến Tư lệnh phe mình rơi vào trạng thái bị đe dọa/chiếu ở trạng thái ngay sau nước đi đều **bị cấm hoàn toàn và loại bỏ khỏi `legal_actions`**. Không bao giờ fallback về nước đi để Tư lệnh bị ăn. Bao gồm:
  1. Tư lệnh tự đi hoặc ăn thế chỗ vào ô bị quân địch tấn công.
  2. Quân chắn bị ghim rời khỏi đường chiếu của quân địch (kể cả qua Pháo/Tên lửa/Pháo hạm bắn xuyên).
  3. Tư lệnh đang ngồi trên `TANK`/`AIRCRAFT`/`NAVY`/SCH Anh hùng bị quân địch đe dọa tại ô gốc của phương tiện (chỉ khi ở trong Sở chỉ huy **thường** `!is_hero` mới được che khỏi chiếu vì địch phải bắn `CAPTURE_STAND` phá Sở chỉ huy trước).
  4. **Đe dọa triển khai từ phương tiện địch:** Mối đe dọa được tính cả với **quân địch đang ngồi trên phương tiện vận tải của đối phương** nếu quân đó có nước triển khai trực tiếp ra ngoài (`CAPTURE_REPLACE` lên đất liền/bờ/ngầm) ăn đúng ô của Tư lệnh phe mình.
  5. **Tự sát phòng không khi cõng Tư lệnh:** Máy bay thường đang chở Tư lệnh tuyệt đối không được thực hiện hành động đi qua hoặc tấn công vào vành đai lửa phòng không làm máy bay bị bắn rơi kéo theo cái chết của Tư lệnh.
- **Hóa giải chiếu:** Khi Tư lệnh đang bị chiếu, người chơi chỉ được đi các nước hóa giải hoàn toàn thế chiếu (chạy Tư lệnh/phương tiện chở Tư lệnh tới ô an toàn, đưa quân khác vào chắn đường, ăn quân đang chiếu, hoặc đưa Tư lệnh vào Sở chỉ huy thường an toàn).

### 7.2. Phong Anh hùng và Huy hiệu Sao Vàng
- **Điều kiện phong Anh hùng:**
  1. Một quân cờ thực hiện **nước đi chiếu Tư lệnh đối phương** sẽ được tự động phong Anh hùng.
  2. Quân chiến đấu cuối cùng bảo vệ Tư lệnh (khi còn đúng 1 quân không phải Tư lệnh và Sở chỉ huy) được tự động phong Anh hùng.
  3. Khi còn **0 quân chiến đấu** và chỉ còn **đúng 1 Sở chỉ huy duy nhất cùng Tư lệnh** (nếu còn 2 Sở chỉ huy thì **không phong**): Sở chỉ huy duy nhất này được phong Bộ binh Anh hùng — **trừ trường hợp Tư lệnh đang núp bên trong Sở chỉ huy đó**, khi đó áp dụng **phong trễ (`DELAYED_SOLITARY_HQ`)**: người chơi chỉ được đi nước đưa Tư lệnh rời khỏi Sở chỉ huy, và ngay khi Tư lệnh bước ra ngoài thì Sở chỉ huy duy nhất lập tức được phong Anh hùng.
- **Dấu hiệu nhận biết trên bàn cờ:** Quân được phong Anh hùng sẽ có thêm **ngôi sao vàng nhỏ (`★`) nằm ở góc trên của quân cờ**, sáng rõ và nổi bật.
- **Quyền năng của quân Anh hùng:**
  - Tăng thêm **1 đoạn** tầm di chuyển và tầm ăn quân.
  - Quân chưa có đường chéo (như Bộ binh, Xe tăng) sẽ được bổ sung thêm khả năng đi và ăn 4 hướng chéo.
    - *Bộ binh Anh hùng:* Đi và ăn 8 hướng, tối đa 2 đoạn.
    - *Xe tăng Anh hùng:* Đi và ăn 8 hướng, tối đa 3 đoạn.
  - *Máy bay Anh hùng:* Trở thành máy bay tàng hình, bỏ qua toàn bộ vành đai lửa phòng không đối phương.
  - *Cao xạ / Hải quân Anh hùng:* Vành đai phòng không mở rộng lên 2 đoạn ngang/dọc và 1 đoạn chéo.
  - *Tên lửa Anh hùng:* Vành đai phòng không mở rộng lên 3 đoạn ngang/dọc và 2 đoạn chéo.
  - *Sở chỉ huy Anh hùng:* Di chuyển và ăn quân như Bộ binh Anh hùng (8 hướng, tối đa 2 đoạn), không còn là công trình trú ẩn cố định.

## 8. Hành quân thần tốc — Cõng quân, tổ hợp và triển khai

### 8.1. Phương tiện và sức chứa tối đa

| Phương tiện vận tải / Che chở | Quân được chở trực tiếp | Sức chứa tối đa |
|---|---|---:|
| **Xe tăng (`TANK`)** | Bộ binh, Dân quân, Tư lệnh | **2 quân bộ** |
| **Không quân (`AIRCRAFT`)** | Bộ binh, Dân quân, Tư lệnh, Xe tăng | **2 quân** (tối đa 1 xe tăng hoặc 2 quân bộ) |
| **Tàu chiến (`NAVY`)** | Bộ binh, Dân quân, Tư lệnh, Xe tăng, Máy bay | **2 quân** (tối đa 1 máy bay / 1 xe tăng / 2 quân bộ) |
| **Công binh (`ENGINEER`)** | Pháo binh, Cao xạ, Tên lửa (khi ở bờ sông `y=5` hoặc `y=6`) | **1 vũ khí nặng** (chở qua sông sâu) |
| **Sở chỉ huy (`HEADQUARTERS`)** | Tư lệnh (trú ẩn, che chở hỏa lực) | **1 Tư lệnh** (không nhận quân khi thành Anh hùng) |

- **Cõng lồng nhau:** Được phép cõng lồng nhau (ví dụ Máy bay chở Xe tăng đang chở 1 Bộ binh; Tàu chiến chở Xe tăng đang chở Dân quân), nhưng tổng số quân con cháu bên trong không được vượt quá sức chứa quy đổi của phương tiện gốc.
- Xe tăng không chở được pháo, không chở được xe tăng khác hay máy bay.
- Sở chỉ huy là công trình cố định che chở Tư lệnh; khi bị tiêu diệt thì Sở chỉ huy mất nhưng Tư lệnh sống sót và lộ diện tại đó. Khi chỉ còn 1 Sở chỉ huy và Tư lệnh thì Sở chỉ huy được phong Bộ binh Anh hùng và không còn cho Tư lệnh ẩn nấp nữa.

### 8.2. Quy trình Lên phương tiện & Đón cõng quân (`BOARD` & `PICKUP`)
- **Hai hình thức cõng quân (DEC-016):**
  1. **Quân chủ động lên phương tiện:** Quân được chở di chuyển vào tọa độ của phương tiện cùng phe.
  2. **Phương tiện chủ động đến đón cõng quân:** Phương tiện di chuyển theo tầm đi hợp lệ đến vị trí của quân được cõng để đón quân đó lên ngay tại tọa độ đích.
- Cả hai hình thức đều tiêu tốn **1 lượt tác chiến** tương tự nhau, kết thúc lượt và chuyển lượt sang đối phương. Phương tiện và quân được chở sẽ bắt đầu các hoạt động tác chiến / tổ hợp từ các lượt tiếp theo.
- Quân đang được chở được hiển thị huy hiệu số lượng trên phương tiện (`+1`, `+2`), danh sách quân chở và bảng điều khiển tổ hợp khi click chọn.

### 8.3. Hành quân & Triển khai tách quân (`DEPLOY`)
- Khi phương tiện di chuyển, tất cả quân đang ngồi bên trong di chuyển cùng phương tiện theo tọa độ mới.
- Quân trên phương tiện **không có thao tác xuống xe đứng yên tại chỗ**. Khi triển khai, quân đó thực hiện một **nước đi hoặc nước ăn quân hợp lệ** xuất phát từ vị trí của phương tiện.
- Một tổ hợp phương tiện - quân chở có thể thực hiện chuỗi hành động phối hợp trong lượt triển khai. Người chơi có quyền chủ động bấm kết thúc lượt (`END_TURN`).

### 8.4. Phương tiện bị tiêu diệt
- Nếu Xe tăng hoặc Tàu chiến bị đối phương tiêu diệt, **toàn bộ quân đang ngồi bên trong (kể cả cõng lồng nhau) đều bị tiêu diệt ngay lập tức**.
- Điểm thưởng cho bên tấn công bằng tổng giá trị điểm của phương tiện cộng với điểm của tất cả các quân bên trong.
- Nếu trong phương tiện có Tư lệnh, trận đấu lập tức kết thúc với thất bại thuộc về phe có Tư lệnh bị tiêu diệt.

## 9. Điểm số, thời gian và kết thúc ván

### 9.1. Chế độ chính: Tổng lực

- Giới hạn **30 phút**.
- **Kết thúc ván đấu (DEC-019 & DEC-020):**
  1. **Chiếu hết Tư lệnh đối phương (`CHECKMATE` — Hình thức thắng chính):** Ván kết thúc ngay lập tức khi bên đến lượt có Tư lệnh đang bị chiếu (`is_in_check == True`) và có **0 nước đi hợp lệ** (`len(legal_actions) == 0`). Bên chiếu hết thắng ngay và được **thưởng +50 điểm** (biên bản gắn dấu `#`).
  2. **Hòa cờ bí (`STALEMATE`):** Khi bên đến lượt còn **0 nước đi hợp lệ** (`len(legal_actions) == 0`) nhưng Tư lệnh **KHÔNG bị chiếu** (`is_in_check == False`), ván đấu kết thúc **HÒA (`winner = "DRAW"`, `reason = "STALEMATE"`)**, không bên nào nhận thưởng +50 điểm.
  3. **Bắt / Tiêu diệt Tư lệnh (`COMMANDER_CAPTURED` — nhánh phòng vệ):** Vì mọi nước đi để lộ Tư lệnh cho đối phương ăn đều bị cấm tuyệt đối, điều kiện thắng thông thường là **Chiếu hết**; `COMMANDER_CAPTURED` chỉ giữ làm kiểm tra phòng vệ cho trạng thái bàn cờ tổng hợp.
- Nếu hết 30 phút mà không Tư lệnh nào bị chiếu hết hoặc hòa cờ bí, so **tổng điểm quân đã ăn/tiêu diệt**; bên cao hơn thắng.
- **PROJECT_DECISION:** Hai bên bằng điểm khi hết giờ → **hòa**.

### 9.2. Các chế độ tham khảo (không thuộc MVP chính)

- **Chiến thuật 15 phút:** Hải chiến (diệt 2 tàu), Không chiến (diệt 2 máy bay), Lục chiến (diệt 2 xe tăng + 2 Bộ binh + 2 Pháo binh), Đột kích (diệt Tư lệnh); mục tiêu chiến thuật được thưởng 50 điểm, có quy tắc so điểm.
- **Hải chiến/Không chiến 9 quân:** dùng bộ quân rút gọn, 15 phút.
- **Chơi rút gọn:** bỏ bớt 2 Công binh mỗi phe.
- **Bố trí nâng cao:** mỗi bên có thời gian sắp xếp quân trước khi bắt đầu.
- Các chế độ này **không tự động bật** trong Game Engine của đồ án.

## 10. Ký pháp nước đi và ghi log

- `MOVE`: quân di chuyển, ghi loại quân, nguồn, đích.
- `CAPTURE_REPLACE`: ăn và thế chỗ.
- `CAPTURE_STAND`: bắn/ăn tại chỗ.
- `AIR_BOMB`: Máy bay ném bom tại chỗ.
- `AIR_EXCHANGE`: Máy bay và mục tiêu cùng bị loại vì phòng không.
- `BOARD`: lên phương tiện.
- `DEPLOY`: tách quân được chở bằng nước đi/ăn hợp lệ.
- `STACK_ACTION`: một hành động trong chuỗi tổ hợp.
- `END_TURN`: chủ động kết thúc lượt tổ hợp.
- `HERO_PROMOTE`: phong Anh hùng tự động.
- `AA_DEFERRED_THREAT`: Máy bay bị đe dọa do vùng phòng không di chuyển tới.
- `GAME_OVER`: kết thúc trận, lý do và điểm.

Mỗi bản ghi tối thiểu cần: `turn_index`, `action_index`, `side`, `piece_id`, `action_type`, `from`, `to`, `captures`, `stack_before`, `stack_after`, `hero_changes`, `score_delta`, `game_status`.

## 11. Kiểm tra tính hợp lệ và thứ tự xử lý đề xuất

> Thứ tự dưới đây là **quy ước kỹ thuật đề xuất** để triển khai nhất quán, không phải một nước đi bổ sung vào luật.

1. Xác thực phe đến lượt, quân còn sống, trạng thái ván.
2. Nếu đang ở lượt tổ hợp, chỉ chấp nhận quân trong tổ hợp đang hoạt động.
3. Kiểm tra loại hành động, hướng, khoảng cách và đích.
4. Kiểm tra vật cản, địa hình, lớp biển/bờ/sông và quy tắc chở.
5. Kiểm tra Tư lệnh đối mặt trực tiếp; từ chối hành động bất hợp lệ.
6. Áp dụng ăn/thế chỗ/bắn tại chỗ, ngoại lệ Máy bay và phòng không.
7. Áp dụng loại bỏ tổ hợp bị tiêu diệt và cập nhật điểm.
8. Kiểm tra điều kiện phong Anh hùng và vùng phòng không mới.
9. Kiểm tra kết thúc ván; nếu chưa kết thúc, quyết định lượt tổ hợp còn tiếp tục hay chuyển phe.
10. Ghi log sự kiện có thể tái hiện.

**Lưu ý:** Với `AA_DEFERRED_THREAT` phải dùng trạng thái sự kiện có thời điểm, không dùng bước 6 để bắn hạ Máy bay ngay khi phòng không mới di chuyển tới.

## 12. Bộ kiểm thử bắt buộc

- `BOARD-01`: 132 giao điểm, đúng trục, đúng biển/sông/ngầm.
- `SETUP-01`: đúng 19 quân/phe, 11 loại, vị trí chuẩn khi đã chốt dữ liệu.
- `MOVE-01`: Bộ binh 4 hướng, Dân quân 8 hướng.
- `MOVE-02`: Xe tăng 1–2 đoạn, Tư lệnh đi xa nhưng chỉ ăn 1 đoạn.
- `MOVE-03`: Pháo bắn xuyên vật cản nhưng không đi xuyên.
- `RIVER-01`: Quân nặng không tự đi qua sông sâu nhưng có thể ăn qua sông.
- `COAST-01`: Quân bộ bắn tàu ngoài biển không xuống biển.
- `NAVY-01`: Tàu không đi xuyên tàu; phân biệt pháo hạm/tên lửa hải đối hải.
- `AIR-01`: Máy bay bay xuyên quân; bay xuyên vùng phòng không thì bị bắn hạ.
- `AIR-02`: Ném bom tại chỗ ngoài vùng; ăn Máy bay phải thế chỗ.
- `AIR-03`: Mục tiêu trong nhiều vùng phòng không → 1 đổi 1, các quân bảo vệ khác sống.
- `AIR-04`: Vùng phòng không vừa di chuyển tới → không bắn hạ ngay.
- `COMMANDER-01`: Cấm tạo thế đối mặt trực tiếp.
- `HQ-01`: Phá Sở chỉ huy trước, Tư lệnh sống.
- `HERO-01`: Tự phong khi chiếu Tư lệnh hoặc còn một quân khác.
- `HERO-02`: Máy bay Anh hùng bỏ qua phòng không; phòng không Anh hùng tăng tầm.
- `CARRY-01`: Xe tăng tối đa 2, Công binh tối đa 1.
- `CARRY-02`: Cõng lồng nhau tính cả hậu duệ; không vượt sức chứa.
- `CARRY-03`: Lên phương tiện tốn lượt, lượt sau mới di chuyển.
- `CARRY-04`: Triển khai bằng nước đi/ăn, không có “xuống tại chỗ”.
- `CARRY-05`: Tối đa 3 hành động, cùng vị trí gốc; được kết thúc sớm.
- `CARRY-06`: Phương tiện rời đi mang quân còn lại → không triển khai tiếp.
- `CARRY-07`: Phương tiện bị tiêu diệt → toàn bộ quân được chở bị loại, cộng điểm tổng.
- `END-01`: Chiếu hết Tư lệnh (`CHECKMATE`) → thắng ngay, cộng 50 điểm; Hòa cờ bí (`STALEMATE`, 0 nước hợp lệ & không bị chiếu) → hòa, 0 điểm thưởng.
- `END-02`: Hết giờ, điểm cao hơn thắng; bằng điểm hòa.
- `SAFETY-01`: Cấm tuyệt đối nước đi để lộ Tư lệnh cho quân thường hoặc quân địch ngồi trên phương tiện triển khai ăn được; không fallback nước đi tự sát.
- `DELAYED-HQ-01`: Còn 2 SCH không phong; còn 1 SCH + Tư lệnh đang núp thì buộc Tư lệnh bước ra mới phong Anh hùng.

## 13. Bảng tổng hợp trạng thái các quyết định quy tắc (Rules Decisions Status)

| Mã | Quy tắc | Trạng thái | Nội dung đã chốt & Tài liệu tham chiếu |
|---|---|:---:|---|
| `BOARD_DATA` | Vị trí 38 quân, ngầm và bờ | **CONFIRMED** | Chuẩn 38 quân, Đỏ đi trước, ngầm tại x=5,7, Tàu 2 Xanh tại `(8, 2)` (DEC-007, `initial_setup.py`) |
| `HQ_SCORE` | Điểm Sở chỉ huy | **CONFIRMED** | 10 điểm (DEC-022; sửa nhầm số 0 từ 100đ, khớp CCHEF) |
| `HQ_CAPTURE` | Tư lệnh trú trong Sở chỉ huy bị đánh | **CONFIRMED** | Tấn công `CAPTURE_STAND`, Sở chỉ huy bị phá hủy, Tư lệnh sống sót lộ diện (DEC-005, Q9) |
| `AA_TIMING` | Thời điểm vùng phòng không kích hoạt | **CONFIRMED** | Đe dọa trì hoãn (`AA_DEFERRED_THREAT`), không bắn hạ ngay khi phòng không vừa áp sát |
| `HERO_MISSILE_MASK` | Vùng phòng không Tên lửa Anh hùng | **CONFIRMED** | 28 điểm gồm 8 điểm dạng kỵ mã (DEC-006, Q6) |
| `NAVY_FRONT` | Hướng tấn công trước/sau của Hải quân | **CONFIRMED** | Tàu địch phía trước cản tàu địch phía sau; pháo hạm vẫn bắn đất liền qua vật cản trong 3–4 đoạn (Q5, DEC-020) |
| `NAVY_PASS_SHORE` | Tàu chiến vượt quân ta trên bờ | **CONFIRMED** | Tàu chiến được vượt qua quân đồng minh không phải Hải quân đứng trên bờ biển/bờ sông (DEC-020) |
| `MISSILE_PIERCE` | Tên lửa ăn xuyên vật cản | **CONFIRMED** | Tên lửa ăn xuyên vật cản (không đi xuyên vật cản) (DEC-020) |
| `ALL_VS_AIRCRAFT` | Mọi quân chiến đấu tấn công Máy bay | **CONFIRMED** | Toàn bộ quân chiến đấu đều tấn công được Máy bay trong tầm hợp lệ (DEC-020) |
| `CARRIED_CMD_FACE` | Tư lệnh trên phương tiện chắn đối mặt | **CONFIRMED** | Tư lệnh ngồi trên `TANK`/`AIRCRAFT`/`NAVY`/`HEADQUARTERS` đều chắn đối mặt giữa 2 Tư lệnh (DEC-020) |
| `KING_SAFETY_AND_DRAW` | Cấm tự sát tuyệt đối, Chiếu hết & Hòa cờ bí | **CONFIRMED** | Thắng bằng `CHECKMATE` (+50đ); 0 nước đi & không chiếu xử `STALEMATE` (Hòa); tính cả đe dọa triển khai từ phương tiện địch (DEC-019, DEC-020) |
| `DELAYED_SOLITARY_HQ` | Phong Anh hùng trễ Sở chỉ huy duy nhất | **CONFIRMED** | Khi Tư lệnh đang núp trong SCH duy nhất thì CHƯA phong, bắt buộc Tư lệnh bước ra trước rồi mới phong Anh hùng (DEC-020) |
| `COAST_OCCUPANCY` | Thế chỗ vs Bắn tại chỗ ở bờ | **CONFIRMED** | Ăn quân ở bờ bắt buộc thế chỗ (`CAPTURE_REPLACE`); bắn đất sâu bắt buộc tại chỗ (`CAPTURE_STAND`) (DEC-008, Q8) |
| `ENGINEER_BRIDGE` | Công binh hỗ trợ vượt sông | **CONFIRMED** | Công binh đứng tại hàng y=5 (Đỏ) hoặc y=6 (Xanh), quân nặng lên Công binh để chở qua sông (DEC-006) |
| `CLOCK_MODEL` | Mô hình đồng hồ thi đấu | **CONFIRMED** | 30 phút cho thực nghiệm AI vs AI, không đếm ngược áp lực cho Người vs AI (Q2) |
| `STACK_ACTION_COUNT` | Giới hạn hành động tổ hợp | **CONFIRMED** | Tối đa 3 hành động trong toàn lượt tổ hợp triển khai (Q20, `rules.py`) |

Toàn bộ các quy tắc trên đã được phản ánh đồng bộ vào `packages/commander_game_engine`, `packages/agents`, `apps/api`, `apps/web` và được xác minh qua các bộ kiểm thử tự động.

---

## 14. Hợp đồng giữa Game Engine và AI

- Engine cung cấp `get_legal_actions(state)` và `apply_action(state, action)`; Agent **không tự suy diễn nước hợp lệ** từ UI.
- **Cập nhật động sau mỗi trạng thái bàn cờ:** Sau mỗi bước thay đổi trạng thái (bao gồm từng bước trong tổ hợp `STACK_ACTIVE`), Engine tái tính toán danh sách nước đi hợp lệ an toàn tuyệt đối cho Tư lệnh (loại bỏ hoàn toàn nước đi khiến Tư lệnh bị ăn, kể cả bởi quân triển khai từ phương tiện địch) và cung cấp đầy đủ lựa chọn tổ hợp cõng quân (`BOARD`/`PICKUP`, quân được cõng triển khai, `carry_cargo=True/False` khi phương tiện mang/tách quân, các nước tiếp theo trong `STACK_ACTIVE`, và `END_TURN` khi được phép) để `RandomAgent` và mọi Agent khác có thể chọn ngẫu nhiên chuẩn xác.
- `state` phải lưu: phe đến lượt, quân còn sống, vị trí, trạng thái Anh hùng, cây chở quân, tổ hợp đang hoạt động, các quân đã hành động, các mối đe dọa phòng không trì hoãn, điểm, đồng hồ và kết quả ván.
- `apply_action` phải là hàm xác định và có thể kiểm thử bằng trạng thái trước/sau.
- Các giới hạn tìm kiếm AI (độ sâu, thời gian suy nghĩ, số lượt mô phỏng, seed) là **cấu hình nghiên cứu**, không phải luật chơi.

**Kết thúc đặc tả.**
