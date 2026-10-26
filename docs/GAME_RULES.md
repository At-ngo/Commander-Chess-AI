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

**NEEDS_DECISION — BOARD_DATA:** Cần chuẩn hóa tọa độ chính xác của *các đoạn nối ngầm*, *điểm có thể đặt tàu ở bờ sông/bờ biển*, và *vị trí xuất phát đủ 38 quân* thành dữ liệu máy đọc được. Hình minh họa chưa đủ để khẳng định tất cả các điểm đặt quân. **Không tự sinh bàn khởi đầu chuẩn từ dữ liệu suy đoán.**

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
| Sở chỉ huy | `HEADQUARTERS` | 2 | 100 |

- Quân **Anh hùng** được cộng **10 điểm** vào giá trị của quân đó khi tính điểm bị tiêu diệt.
- Điểm Hải quân 80 = tên lửa hải đối hải 40 + pháo hạm 30 + cao xạ 10.
- Khi một phương tiện chở quân bị tiêu diệt, tính tổng điểm của phương tiện và **tất cả quân bên trong**, kể cả quân cõng lồng nhau; không đếm trùng.

## 3. Di chuyển và ăn quân theo loại

| Quân | Di chuyển thường | Ăn quân thường | Đặc biệt |
|---|---|---|---|
| Tư lệnh | `ORTHOGONAL`, không giới hạn đến khi gặp vật cản | `ORTHOGONAL`, 1 đoạn | Có thể vào Sở chỉ huy; cấm đối mặt trực tiếp với Tư lệnh địch |
| Bộ binh | `ORTHOGONAL`, 1 đoạn | như di chuyển | Có thể qua sông sâu |
| Công binh | `ORTHOGONAL`, 1 đoạn | như di chuyển | Hỗ trợ chở vũ khí nặng qua sông |
| Cao xạ | `ORTHOGONAL`, 1 đoạn | như di chuyển | Tạo vùng phòng không thụ động |
| Dân quân | `ALL_8`, 1 đoạn | như di chuyển | Có đường chéo ngay từ đầu |
| Xe tăng | `ORTHOGONAL`, 1–2 đoạn | như di chuyển | Có thể bắn tàu trên biển mà không thế chỗ |
| Tên lửa | `ORTHOGONAL`, 1–2 đoạn; `DIAGONAL`, 1 đoạn | như di chuyển | Tạo vùng phòng không |
| Pháo binh | `ALL_8`, 1–3 đoạn | `ALL_8`, 1–3 đoạn | Khi ăn có thể bắn xuyên vật cản; bắn tàu ngoài biển không thế chỗ |
| Máy bay | `ALL_8`, 1–4 đoạn | `ALL_8`, 1–4 đoạn | Bay/ăn xuyên quân; có ném bom tại chỗ; bị phòng không |
| Hải quân | `ALL_8`, 1–4 đoạn theo địa hình tàu | Nhiều chế độ, xem §5 | Có pháo hạm, tên lửa hải đối hải, cao xạ |
| Sở chỉ huy | Không | Không | Công trình cố định, có thể che Tư lệnh |

### 3.1. Chặn đường và tầm bắn

- Xe tăng, Tư lệnh và các quân đi thẳng nhiều đoạn bị chặn bởi quân nằm giữa, trừ ngoại lệ địa hình/đơn vị đã nêu.
- **Pháo binh:** được **bắn xuyên quân khi ăn**, nhưng **không được đi xuyên quân khi chỉ di chuyển** (`PROJECT_DECISION`). Khi ăn quân trên đất, phải thế chỗ; bắn tàu ở biển có thể đứng nguyên.
- **Máy bay:** được **bay xuyên và ăn xuyên quân** trong tầm 4 đoạn, nhưng vẫn phải xét toàn bộ quỹ đạo bay đối với phòng không.
- Pháo được bắn qua bất kỳ số quân cản dù là 1 quân cản sau lưng quân đó có quân thì pháo vẫn có thể ăn, dù là 2 quân cản sau lưng 2 quân đó thì pháo vẫn ăn được miễn trong tầm ăn quân của pháo.

## 4. Sông, biển, bờ và Sở chỉ huy

### 4.1. Vượt sông

1. Qua **ngầm**: tất cả quân có thể vượt theo nước đi hợp lệ của chính mình.
2. Qua **nước sâu**: Tư lệnh, Bộ binh, Dân quân, Xe tăng, Công binh có thể qua.
3. Cao xạ, Pháo binh, Tên lửa **không được tự di chuyển qua nước sâu**; có thể được Công binh hỗ trợ chở qua (xem §8).
4. Ba loại quân nặng trên **được phép vượt nước sâu bằng nước ăn quân hợp lệ ở bờ đối diện**; không được lợi dụng ngoại lệ này cho nước đi trống.
5. Máy bay bay qua sông theo quy tắc bay và phòng không; không đứng ở vùng biển như quân thủy.

Công binh đứng sát bờ sông nghĩa là đứng tại trục tung y = 5 bên đỏ hoặc đứng tại trục tung y = 6 đối với bên xanh, các quân nặng có tầm đi tới công binh sẽ có thể lên công binh để công binh chở, ngang, dọc hoặc chéo đều được.

### 4.2. Biển, bờ biển và bờ sông

- Quân bộ **không được di chuyển ra biển**. Khi đánh tàu ở vị trí trên biển, quân bộ có thể **ăn tại chỗ**, không phải thế chỗ xuống nước.
- Nếu tàu địch nằm trên bờ biển hoặc bờ sông ở vị trí hợp lệ để quân bộ đứng, nước ăn phải **thế chỗ**.
- Hải quân được hoạt động trên biển, dọc bờ biển/bờ sông và vùng nước sông sâu hợp lệ; **không đi vào ngầm** và không đi sâu trong đất liền.
- Hải quân **không đi xuyên Hải quân** (đồng minh hoặc địch); có thể đi qua quân bộ ở bờ theo mô tả về các lớp hoạt động khác nhau.
- Quân bộ và Hải quân ở cùng tuyến bờ có thể vượt qua nhau theo điều kiện địa hình, không xem mặc định là hai quân chắn đường nhau.
- Tư lệnh đứng sát bờ không được coi là an toàn khỏi quy tắc đối mặt chỉ vì có Hải quân trên cùng tuyến.


### 4.3. Sở chỉ huy

- Mỗi phe có 2 Sở chỉ huy; không di chuyển, không ăn quân trong trạng thái thường.
- Tư lệnh có thể trú trong Sở chỉ huy; không được coi việc trú ẩn là miễn nhiễm hoàn toàn.
- **PROJECT_DECISION:** Khi đối phương tấn công Sở chỉ huy đang che Tư lệnh, **Sở chỉ huy bị phá trước; Tư lệnh còn sống và lộ ra**.
- Tư lệnh vẫn phải tuân thủ luật không đối mặt trực tiếp với Tư lệnh địch.
- Nếu Sở chỉ huy là quân cuối cùng bảo vệ Tư lệnh, nó có thể trở thành **Sở chỉ huy Anh hùng** và di chuyển/ăn như Bộ binh Anh hùng; lúc này Tư lệnh **không thể tiếp tục trú trong đó**.
- Khi quân tấn công Sở chỉ huy có Tư lệnh bên trong: thì không được phép tấn công thế chỗ, chỉ được tấn công ăn tại chỗ sở chỉ huy để tư lệnh lộ ra.

## 5. Hải quân và ba hệ vũ khí

| Hệ vũ khí | Mục tiêu | Tầm/hướng | Thế chỗ |
|---|---|---|---|
| Tên lửa hải đối hải | Chỉ Hải quân địch | `ALL_8`, tối đa 4 đoạn | Có nếu đường hợp lệ; nếu vướng đất liền có thể bắn tại chỗ |
| Pháo hạm | Quân khác trên đất/bờ | `ALL_8`, tối đa 3 đoạn | Đích sâu trong đất: bắn tại chỗ; đích dọc bờ hợp lệ: thế chỗ |
| Cao xạ hạm | Máy bay địch | Phòng không 1 đoạn ngang/dọc | Tác dụng phòng thủ, xem §6 |

- Tàu không đi qua tàu khác.
- Quy tắc người chơi mô tả: tàu chỉ tấn công Hải quân địch **ở phía trước**, không tấn công tàu địch **ở phía sau**; tàu vẫn có thể bắn quân bộ phía sau tàu địch nếu đường/tầm pháo hạm cho phép.

## 6. Vành đai lửa và Máy bay

### 6.1. Vùng phòng không thường

| Đơn vị | Vùng phòng không |
|---|---|
| Cao xạ | Ngang/dọc 1 đoạn |
| Tên lửa phòng không | Ngang/dọc 1–2 đoạn **và** chéo 1 đoạn |
| Hải quân | Ngang/dọc 1 đoạn |

- Vùng phòng không là **năng lực phòng thủ**, không phải một nước đi tấn công chủ động.
- Máy bay thường bay **vào hoặc xuyên qua** vùng phòng không của địch sẽ bị tiêu diệt, **kể cả khi điểm kết thúc nằm ngoài vùng** (`PROJECT_DECISION`).
- Nếu Máy bay tấn công một quân địch nằm trong vùng phòng không của địch, **Máy bay và mục tiêu cùng bị tiêu diệt (1 đổi 1)**.
- Nếu có nhiều vùng phòng không chồng nhau, **chỉ Máy bay tấn công và mục tiêu bị tiêu diệt**; các quân phòng không còn lại vẫn sống và giữ vùng bảo vệ (`PROJECT_DECISION`).
- Máy bay được Hải quân chở **không bị vùng phòng không tác động khi còn ở trên tàu**.
- Máy bay không được kết thúc nước di chuyển ở biển.

### 6.2. Hai hình thức tấn công của Máy bay

1. **Ăn thế chỗ:** Máy bay đến tọa độ mục tiêu sau khi tiêu diệt quân địch.
2. **Ném bom tại chỗ:** Máy bay tiêu diệt mục tiêu hợp lệ nhưng **giữ nguyên tọa độ ban đầu**.

**PROJECT_DECISION:**
- Máy bay có thể lựa chọn **ném bom tại chỗ hoặc ăn thế chỗ** khi tấn công mục tiêu đất hợp lệ **ngoài vùng phòng không**.
- Khi ăn **Máy bay địch**, bắt buộc **thế chỗ**.
- Không được dùng ném bom tại chỗ để tránh tổn thất nếu mục tiêu nằm trong vùng phòng không: vẫn xử lý **1 đổi 1**.
- Đường bay khi tấn công vẫn phải xét phòng không; không được chỉ kiểm tra ô đích.

### 6.3. Phòng không di chuyển tới gần Máy bay

Quy tắc người chơi bổ sung:
- Nếu Cao xạ/Tên lửa/Hải quân **di chuyển** tới vị trí khiến Máy bay địch nằm trong vùng phòng không, Máy bay **không bị tiêu diệt ngay ở lượt phòng không vừa đi**.
- Nếu đến lượt kế tiếp của Máy bay mà nó **không bay khỏi vùng nguy hiểm**, nó bị tiêu diệt; phe phòng không không phải dùng một nước ăn riêng.

### 6.4. Máy bay Anh hùng

- Máy bay Anh hùng là **máy bay tàng hình**: được bay qua vùng phòng không mà không bị bắn hạ, được tấn công Cao xạ/Tên lửa/Hải quân mà không chịu quy tắc 1 đổi 1 do phòng không.
- Các quy tắc di chuyển, phạm vi, địa hình và ăn quân khác vẫn áp dụng, trừ ngoại lệ Anh hùng đã nêu.

## 7. Tư lệnh, đối mặt và phong Anh hùng

### 7.1. Tư lệnh

- Đi dọc/ngang không giới hạn số đoạn nếu đường không bị chặn; ăn quân dọc/ngang **1 đoạn**.
- Không đi chéo trong trạng thái thường.
- **PROJECT_DECISION:** Hành động khiến hai Tư lệnh **đối mặt trực tiếp trên cùng hàng/cột, không có vật chắn hợp lệ** là **bất hợp lệ ngay**; không đợi đối phương thực hiện nước ăn.
- Khi Tư lệnh được chở bởi phương tiện, có ngoại lệ liên quan tới đi qua tuyến đối mặt, nhưng **không được để lộ Tư lệnh đối mặt trực tiếp sau khi triển khai**.

### 7.2. Phong Anh hùng

- Một quân **chiếu Tư lệnh địch** có thể được phong Anh hùng; **PROJECT_DECISION:** phong **tự động** khi đủ điều kiện.
- **PROJECT_DECISION:** Khi phe chỉ còn **đúng một quân khác ngoài Tư lệnh** trên toàn bàn (tính cả Sở chỉ huy), quân đó **tự động phong Anh hùng**.
- Danh hiệu tồn tại **đến khi quân bị tiêu diệt**.
- Quân Anh hùng được tăng **1 đoạn** tầm di chuyển và ăn; quân chưa có đường chéo sẽ được thêm đường chéo, quân đã có thì vẫn tăng tầm.
- Ví dụ: Bộ binh Anh hùng đi/ăn `ALL_8` tối đa 2 đoạn; Xe tăng Anh hùng đi/ăn `ALL_8` tối đa 3 đoạn.
- Sở chỉ huy Anh hùng đi/ăn như **Bộ binh Anh hùng** (8 hướng, tối đa 2 đoạn), không còn là công trình trú ẩn cố định.
- Máy bay Anh hùng bỏ qua nguy cơ phòng không theo §6.4.

### 7.3. Phòng không Anh hùng

- Cao xạ/Hải quân Anh hùng: vùng cấm bay ngang/dọc **2 đoạn**, chéo **1 đoạn**.
- Tên lửa Anh hùng: vùng cấm bay ngang/dọc **3 đoạn**, chéo **2 đoạn**, và có **những điểm bổ sung** được mô tả bằng hình dạng đặc biệt.

## 8. Hành quân thần tốc — Cõng quân, tổ hợp và triển khai

### 8.1. Phương tiện và sức chứa

| Phương tiện | Quân được chở trực tiếp | Sức chứa tối đa |
|---|---|---:|
| Xe tăng | Bộ binh, Dân quân, Tư lệnh | 2 |
| Máy bay | Bộ binh, Dân quân, Tư lệnh, Xe tăng | 2 |
| Hải quân | Bộ binh, Dân quân, Tư lệnh, Xe tăng, Máy bay | 2 |
| Công binh | Pháo binh, Cao xạ, Tên lửa | 1 |

- **PROJECT_DECISION — Q09-E:** Cho phép **cõng lồng nhau**; sức chứa của phương tiện cha tính **tổng số quân con cháu**, không chỉ đếm phương tiện con trực tiếp.
- Ví dụ: Hải quân chở Máy bay đang chở 1 Bộ binh = **2 quân** được Hải quân vận chuyển, hợp lệ. Hải quân chở Máy bay đang chở 2 Bộ binh = **3 quân**, không hợp lệ.
- Không có chu trình chở quân; mỗi quân chỉ có tối đa một phương tiện cha.

### 8.2. Lên phương tiện

- **PROJECT_DECISION — Q09-A1:** Lên phương tiện **tốn một lượt**; phương tiện chỉ được di chuyển trong lượt sau.
- **PROJECT_DECISION — Q09-F3:** Có thể để quân đi tới phương tiện hoặc phương tiện tới đón quân, miễn đường đi, địa hình và sức chứa hợp lệ.
- Khi Công binh đón quân nặng, áp dụng giới hạn 1 quân.

### 8.3. Triển khai và hành động tổ hợp

**PROJECT_DECISION — Q09-B, C, G:**
1. Quân được chở **không có thao tác “xuống xe tại chỗ” riêng**. Khi triển khai, nó thực hiện ngay **một nước di chuyển hoặc ăn quân hợp lệ của chính nó**, xuất phát từ tọa độ của tổ hợp.
2. Một tổ hợp có thể thực hiện **tối đa 3 hành động** trong **cùng một lượt**, với các quân khác nhau của tổ hợp.
3. Người chơi **tự chọn thứ tự** hành động và có thể **kết thúc lượt sớm**.
4. Mọi quân triển khai phải xuất phát từ **cùng vị trí tổ hợp ban đầu**. Không được di chuyển phương tiện rồi mới cho quân đang chở tách ra ở vị trí mới trong cùng lượt.
5. Khi một quân/phương tiện **rời vị trí tổ hợp và mang theo quân khác**, các quân còn ở trên phương tiện đó **đi theo**, không được tiếp tục hành động độc lập trong lượt này.
6. Không được chọn quân **ngoài tổ hợp** khi lượt hành động tổ hợp chưa kết thúc.
7. Không được bỏ lại hai quân mà bản thân chúng **không có khả năng tự tạo tổ hợp chở hợp lệ**; trạng thái sau từng hành động phải thỏa quy tắc chở.

**Ví dụ — Xe tăng ở `(5,5)` chở Bộ binh và Dân quân:**
- Phương án 1: Xe tăng di chuyển trước, mang cả hai quân → kết thúc lượt.
- Phương án 2: Bộ binh triển khai; Xe tăng di chuyển mang Dân quân → kết thúc lượt.
- Phương án 3: Bộ binh triển khai; Dân quân triển khai; Xe tăng di chuyển → kết thúc lượt.
- Phương án 4: Chỉ triển khai Dân quân, Xe tăng vẫn chở Bộ binh ở chỗ cũ → kết thúc lượt.
- **Không hợp lệ:** Xe tăng đi từ `(5,5)` tới `(7,5)` rồi Bộ binh mới tách từ `(7,5)` trong cùng lượt.


### 8.4. Phương tiện bị tiêu diệt

- **PROJECT_DECISION — Q09-D1:** Phương tiện bị tiêu diệt → **toàn bộ quân đang được chở, kể cả lồng nhau, bị tiêu diệt**.
- Điểm cộng cho bên tấn công bằng tổng giá trị từng quân bị loại; cộng thưởng Anh hùng cho quân đủ điều kiện.
- Nếu trong tổ hợp có Tư lệnh, kiểm tra kết thúc ván ngay khi Tư lệnh bị loại.

## 9. Điểm số, thời gian và kết thúc ván

### 9.1. Chế độ chính: Tổng lực

- Giới hạn **30 phút**.
- Ván kết thúc ngay khi một bên **tiêu diệt Tư lệnh đối phương**.
- Bên tiêu diệt Tư lệnh được thưởng thêm **50 điểm**.
- Nếu hết 30 phút mà không Tư lệnh nào bị tiêu diệt, so **tổng điểm quân đã ăn/tiêu diệt**; bên cao hơn thắng.
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
- `END-01`: Diệt Tư lệnh → kết thúc, cộng 50.
- `END-02`: Hết giờ, điểm cao hơn thắng; bằng điểm hòa.

## 13. Các quyết định còn cần khóa trước khi tuyên bố engine hoàn chỉnh

| Mã | Câu hỏi chưa chốt | Ảnh hưởng |
|---|---|---|
| `BOARD_DATA` | Chính xác vị trí 38 quân, các ngầm và tọa độ bờ/sông | Khởi tạo ván, địa hình |
| `HQ_SCORE` | Sở chỉ huy có bao nhiêu điểm? | Tính điểm |
| `HQ_CAPTURE` | Vị trí Tư lệnh sau khi Sở chỉ huy che nó bị phá | Trạng thái hợp lệ |
| `AA_TIMING` | Máy bay bị vùng phòng không mới bao phủ sẽ bị loại chính xác lúc nào? | Trình tự lượt |
| `HERO_MISSILE_MASK` | Tập điểm phòng không bổ sung của Tên lửa Anh hùng | Sinh vùng nguy hiểm |
| `NAVY_FRONT` | Cách xác định “trước/sau” của Hải quân | Nước ăn tàu |
| `COAST_OCCUPANCY` | Hải quân và quân bộ ở cùng tọa độ bờ biểu diễn thế nào? | Dữ liệu bàn cờ |
| `ENGINEER_BRIDGE` | Cơ chế Công binh đưa quân nặng qua sông | Sinh nước đi |
| `CLOCK_MODEL` | Đồng hồ chung hay riêng từng phe? | Kết thúc ván |
| `STACK_ACTION_COUNT` | Tổ hợp cõng lồng nhau >3 quân giới hạn 3 hành động toàn lượt? | Luật tổ hợp |

**Không biến các câu hỏi này thành “luật mặc định” chỉ để code chạy.** Các phần độc lập có thể được triển khai và kiểm thử trước.

---

## 14. Hợp đồng giữa Game Engine và AI

- Engine cung cấp `get_legal_actions(state)` và `apply_action(state, action)`; Agent **không tự suy diễn nước hợp lệ** từ UI.
- Nếu đang trong lượt tổ hợp, `get_legal_actions` trả về hành động hợp lệ tiếp theo **và** lựa chọn `END_TURN` khi được phép.
- `state` phải lưu: phe đến lượt, quân còn sống, vị trí, trạng thái Anh hùng, cây chở quân, tổ hợp đang hoạt động, các quân đã hành động, các mối đe dọa phòng không trì hoãn, điểm, đồng hồ và kết quả ván.
- `apply_action` phải là hàm xác định và có thể kiểm thử bằng trạng thái trước/sau.
- Các giới hạn tìm kiếm AI (độ sâu, thời gian suy nghĩ, số lượt mô phỏng, seed) là **cấu hình nghiên cứu**, không phải luật chơi.

**Kết thúc đặc tả.**
