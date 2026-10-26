# 1. Bàn cờ, hệ tọa độ và bố trí quân ban đầu

> Nội dung chuyển từ tài liệu **Quy định về tọa độ bàn cờ**. Các tọa độ bên dưới luôn theo thứ tự **(trục tung, trục hoành)**, tương ứng **(y, x)**. Đây là phần để chèn vào `GAME_RULES.md`, không phải một bộ luật độc lập.

## 1.1. Kích thước và hệ tọa độ

- Bàn cờ hình chữ nhật, gồm **11 đường dọc** và **12 đường ngang**, tạo thành **132 giao điểm**.
- **Trục tung (y):** các giá trị nguyên từ `0` đến `11`.
- **Trục hoành (x):** các giá trị nguyên từ `0` đến `10`.
- **Gốc tọa độ `(0, 0)`** nằm ở góc dưới cùng bên trái, phía vùng biển, theo góc nhìn của người chơi thứ nhất.
- Tọa độ được **đọc và ghi theo thứ tự `(y, x)`**. Ví dụ: `(3, 5)`, `(0, 7)`, `(11, 10)`.
- Phía Đỏ triển khai gần `y = 0`; phía Xanh triển khai gần `y = 11`.

**Quy tắc kiểm tra tọa độ hợp lệ:**

```python
def is_valid_coordinate(y: int, x: int) -> bool:
    return 0 <= y <= 11 and 0 <= x <= 10
```

## 1.2. Các vùng địa hình

### Biển

- Biển nằm về phía trái bàn cờ của người chơi thứ nhất (bên phải đối với người chơi thứ hai).
- Vùng biển kéo dài từ `(0, 0)` đến `(11, 2)`, tức dải giữa các đường `x = 0` và `x = 2`.
- Theo tài liệu, vùng biển rộng **2 ô** và dài **11 ô**; đây là mô tả diện tích giữa các đường lưới, **không đồng nghĩa** với việc chỉ có 2 cột giao điểm.

### Sông

- Sông nằm ngang ở giữa bàn cờ, ngăn hai chiến tuyến.
- Vùng sông kéo dài từ `(5, 2)` đến `(6, 10)`, tức dải giữa các đường `y = 5` và `y = 6`, từ `x = 2` đến `x = 10`.
- Theo tài liệu, sông rộng **1 ô** và dài **8 ô**.
- Phần nước sâu không cho các phương tiện qua theo quy định địa hình; điều kiện di chuyển cụ thể của từng loại quân tuân theo các phần luật tương ứng trong `GAME_RULES.md`.

### Hai đường ngầm

- **Ngầm 1:** nối `(5, 5)` với `(6, 5)`.
- **Ngầm 2:** nối `(5, 7)` với `(6, 7)`.
- Ngầm là đoạn nước nông có nền đá, cho phép các phương tiện qua lại theo luật.

> **Lưu ý khi lập trình:** Biển và sông là các **vùng nằm giữa đường lưới**. Không tự động coi toàn bộ giao điểm trên ranh giới là ô nước hoặc ô bị cấm. Game Engine cần áp dụng quy tắc đi qua địa hình khi xét đoạn di chuyển; các quy tắc chi tiết lấy từ các mục còn lại của `GAME_RULES.md`.

## 1.3. Bố trí quân ban đầu

Mỗi bên có **19 quân**, tổng cộng **38 quân** trên bàn cờ. Tọa độ giữ nguyên theo tài liệu gốc.

| Loại quân | Mã quân | Phe Đỏ — `(y, x)` | Phe Xanh — `(y, x)` |
|---|---|---|---|
| Tư lệnh | `TL` | `(0, 6)` | `(11, 6)` |
| Không quân / Máy bay | `K` | `(1, 4)`, `(1, 8)` | `(10, 4)`, `(10, 8)` |
| Sở chỉ huy | `S` | `(1, 5)`, `(1, 7)` | `(10, 5)`, `(10, 7)` |
| Tên lửa | `L` | `(2, 6)` | `(9, 6)` |
| Pháo binh | `A` | `(2, 3)`, `(2, 9)` | `(9, 3)`, `(9, 9)` |
| Cao xạ | `F` | `(3, 4)`, `(3, 8)` | `(8, 4)`, `(8, 8)` |
| Xe tăng | `T` | `(3, 5)`, `(3, 7)` | `(8, 5)`, `(8, 7)` |
| Bộ binh | `B` | `(4, 2)`, `(4, 10)` | `(7, 2)`, `(7, 10)` |
| Công binh | `C` | `(4, 3)`, `(4, 9)` | `(7, 3)`, `(7, 9)` |
| Dân quân | `D` | `(4, 6)` | `(7, 6)` |
| Tàu chiến | `H` | `(1, 1)`, `(3, 2)` | `(10, 1)`, `(6, 2)` |

**Quan trọng:** Tọa độ Tàu chiến Xanh thứ hai là **`(6, 2)`**, đúng theo tài liệu; không tự ý đối xứng thành `(8, 2)`.

## 1.4. Dữ liệu khởi tạo tham khảo cho Game Engine

Đoạn Python dưới đây là **biểu diễn dữ liệu**, không phải thuật toán sinh nước đi. Mỗi cặp tọa độ đều theo `(y, x)`.

```python
BOARD_CONFIG = {
    "vertical_lines": 11,
    "horizontal_lines": 12,
    "intersection_count": 132,
    "coordinate_order": "y_x",
    "y_range": [0, 11],
    "x_range": [0, 10],
    "sea_bounds": {"y_min": 0, "y_max": 11, "x_min": 0, "x_max": 2},
    "river_bounds": {"y_min": 5, "y_max": 6, "x_min": 2, "x_max": 10},
    "fords": [((5, 5), (6, 5)), ((5, 7), (6, 7))],
}

INITIAL_POSITIONS = {
    "red": {
        "COMMANDER": [(0, 6)],
        "AIRCRAFT": [(1, 4), (1, 8)],
        "HEADQUARTERS": [(1, 5), (1, 7)],
        "MISSILE": [(2, 6)],
        "ARTILLERY": [(2, 3), (2, 9)],
        "ANTI_AIRCRAFT": [(3, 4), (3, 8)],
        "TANK": [(3, 5), (3, 7)],
        "INFANTRY": [(4, 2), (4, 10)],
        "ENGINEER": [(4, 3), (4, 9)],
        "MILITIA": [(4, 6)],
        "NAVY": [(1, 1), (3, 2)],
    },
    "blue": {
        "COMMANDER": [(11, 6)],
        "AIRCRAFT": [(10, 4), (10, 8)],
        "HEADQUARTERS": [(10, 5), (10, 7)],
        "MISSILE": [(9, 6)],
        "ARTILLERY": [(9, 3), (9, 9)],
        "ANTI_AIRCRAFT": [(8, 4), (8, 8)],
        "TANK": [(8, 5), (8, 7)],
        "INFANTRY": [(7, 2), (7, 10)],
        "ENGINEER": [(7, 3), (7, 9)],
        "MILITIA": [(7, 6)],
        "NAVY": [(10, 1), (8, 2)],
    },
}
```

### 1.5. Kiểm tra dữ liệu khởi tạo

Khi khởi tạo ván đấu, Game Engine cần xác minh:

1. Có đúng **19 quân Đỏ** và **19 quân Xanh**.
2. Mọi tọa độ đều nằm trong phạm vi `0 <= y <= 11`, `0 <= x <= 10`.
3. Không có hai quân độc lập cùng chiếm một giao điểm ban đầu.
4. Các vị trí ban đầu khớp chính xác với bảng tại mục 1.3.
5. Phe Đỏ được đi trước theo `GAME_RULES.md`.

### 1.6. Ánh xạ sang bàn cờ SVG

SVG bàn cờ sử dụng `viewBox="0 0 1024 949"`, có đường lưới từ `x_svg = 63` đến `943` và từ `y_svg = 61` đến `880`.

**Theo hướng SVG hiện tại (hàng `y = 0` ở phía trên),** giao điểm `(y, x)` được ánh xạ:

```typescript
function toSvgPoint(y: number, x: number) {
  return {
    x: 63 + x * 88,
    y: 61 + y * (819 / 11),
  };
}
```

**Lưu ý hướng hiển thị:** Tài liệu quy định `(0, 0)` ở **góc dưới bên trái**, trong khi SVG mặc định tăng tọa độ `y` **từ trên xuống**. Để giữ đúng góc nhìn của tài liệu khi hiển thị, cần đảo trục dọc:

```typescript
function toSvgPointBottomOrigin(y: number, x: number) {
  return {
    x: 63 + x * 88,
    y: 880 - y * (819 / 11),
  };
}
```

Chọn **một** quy ước hiển thị thống nhất trong `UI_SPECIFICATION.md`; tuyệt đối không đảo tọa độ trong dữ liệu Game Engine chỉ để phù hợp với SVG.
