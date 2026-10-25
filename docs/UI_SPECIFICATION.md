# UI SPECIFICATION — Commander Chess AI

> **Trạng thái:** Draft v0.1 — bản mẫu để chủ dự án chỉnh sửa.  
> **Phạm vi:** Frontend `apps/web/` (React + TypeScript + Vite).  
> **Nguồn yêu cầu:** `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/GAME_RULES.md`, `docs/API_CONTRACT.md`, `docs/MOVE_NOTATION.md` và các asset do chủ dự án cung cấp.  
> **Nguyên tắc:** Đây là đặc tả giao diện, **không** bổ sung hoặc thay đổi luật. Các mục `[ĐỀ XUẤT]` chưa được chủ dự án phê duyệt; các mục `[CẦN CHỐT]` không được AI Coding Agent tự quyết định.

## 1. Mục tiêu

Xây dựng ứng dụng web Cờ Tư Lệnh để (1) chơi Người–AI, (2) theo dõi AI–AI, (3) xem lại biên bản, (4) xem thống kê và nghiên cứu khi có dữ liệu thực. Giao diện trực quan, hiển thị đúng ảnh quân và bàn cờ SVG; có tiếng Việt và tiếng Anh.

### 1.1. Nguồn dữ liệu và ranh giới trách nhiệm

- **Game Engine** quyết định trạng thái, lượt đi, nước đi hợp lệ, ăn quân, vận tải, vùng phòng không, phong Anh hùng và kết thúc trận.
- **API** cung cấp dữ liệu cho frontend; frontend không tự suy diễn luật từ tọa độ hoặc SVG.
- **Frontend** chỉ hiển thị trạng thái, hỗ trợ người dùng chọn hành động và gửi yêu cầu. Mọi thao tác có tác động đến ván cờ phải được Engine xác nhận trước khi cập nhật trạng thái chính thức.
- **AI Agents** chọn hành động qua giao diện Engine; UI không chứa logic quyết định nước đi của AI.
- **Ký pháp biên bản** lấy từ `MOVE_NOTATION.md`; không lấy tên file ảnh làm ký pháp.
- Không tuyên bố tính năng hoặc Agent đã hoạt động nếu chưa có backend thực.

## 2. Cấu trúc trang và điều hướng

| Trang | Nội dung | Ưu tiên |
|---|---|---|
| Dashboard | Trạng thái hệ thống, danh sách Agent khả dụng, thống kê thật | P1 |
| Play | Bàn cờ, chơi Người–AI, trạng thái ván, biên bản | P0 |
| AI vs AI | Chọn hai Agent, quan sát ván đấu | P1 — [ĐỀ XUẤT] có thể là chế độ trong Play |
| Replays | Danh sách ván đã lưu, phát lại theo nước đi | P1 |
| Statistics | Thắng/hòa/thua, tỷ lệ, thời gian suy nghĩ, bộ lọc | P2 |
| Rules | Hướng dẫn chơi dựa trên luật đã xác minh | P1 |
| Research/Tournaments | Thiết lập/tham khảo thực nghiệm khi được triển khai | P2 |

**Điều hướng chung:** tên ứng dụng/logo bên trái; menu các trang; chọn ngôn ngữ **Tiếng Việt / English ở góc trên bên phải**. Tiếng Việt là mặc định, ghi nhớ lựa chọn sau tải lại. `[CẦN CHỐT]` tên hiển thị và phong cách header.

## 3. Asset quân cờ — ĐÃ CUNG CẤP

### 3.1. Vị trí lưu trữ đề xuất

```text
apps/web/public/assets/
├── pieces/
│   ├── TL_red.png    TL_blue.png
│   ├── C_red.png     C_blue.png
│   ├── K_red.png     K_blue.png
│   ├── D_red.png     D_blue.png
│   ├── H_red.png     H_blue.png
│   ├── L_red.png     L_blue.png
│   ├── T_red.png     T_blue.png
│   ├── B_red.png     B_blue.png
│   ├── S_red.png     S_blue.png
│   ├── F_red.png     F_blue.png
│   └── A_red.png     A_blue.png
└── board/
    └── commander-board.svg
```

**Quy tắc tên:** Giữ nguyên **chữ hoa** trong mã quân và chữ thường `red`/`blue` (quan trọng trên Linux). Không tự đổi `TL` thành `commander` hoặc đổi tên ảnh nếu chưa cập nhật ánh xạ.

### 3.2. Bảng ánh xạ ảnh

| Quân | Mã asset | Đỏ | Xanh |
|---|---|---|---|
| Tư lệnh | `TL` | `TL_red.png` | `TL_blue.png` |
| Công binh | `C` | `C_red.png` | `C_blue.png` |
| Không quân / Máy bay | `K` | `K_red.png` | `K_blue.png` |
| Dân quân | `D` | `D_red.png` | `D_blue.png` |
| Tàu chiến / Hải quân | `H` | `H_red.png` | `H_blue.png` |
| Tên lửa | `L` | `L_red.png` | `L_blue.png` |
| Xe tăng | `T` | `T_red.png` | `T_blue.png` |
| Bộ binh | `B` | `B_red.png` | `B_blue.png` |
| Sở chỉ huy | `S` | `S_red.png` | `S_blue.png` |
| Cao xạ | `F` | `F_red.png` | `F_blue.png` |
| Pháo binh | `A` | `A_red.png` | `A_blue.png` |

**Đường dẫn:** `/assets/pieces/${code}_${side}.png` với `side ∈ {red, blue}`. Dùng map từ **piece type nội bộ** sang `code`, không lấy ký pháp biên bản làm ID trong Engine. Tư lệnh có ký hiệu biên bản `⋆` (LaTeX `\star`) nhưng **ảnh là `TL_red.png` / `TL_blue.png`**.

Ví dụ minh họa (TypeScript, chưa khẳng định enum API hiện tại):

```ts
const ASSET_CODE = {
  COMMANDER: 'TL', ENGINEER: 'C', AIRCRAFT: 'K', MILITIA: 'D',
  NAVY: 'H', MISSILE: 'L', TANK: 'T', INFANTRY: 'B',
  HEADQUARTERS: 'S', ANTI_AIR: 'F', ARTILLERY: 'A',
} as const;

type PieceType = keyof typeof ASSET_CODE;
type Side = 'red' | 'blue';

export function pieceImage(type: PieceType, side: Side): string {
  return `/assets/pieces/${ASSET_CODE[type]}_${side}.png`;
}
```

> `[CẦN XÁC NHẬN]` Tên enum của API/Engine. Đoạn code chỉ minh họa việc ánh xạ, không phải hợp đồng API đã chốt.

### 3.3. Cách hiển thị ảnh

- Giữ nguyên tỷ lệ ảnh (`object-fit: contain`); không bóp méo hoặc cắt mất quân.
- Tâm ảnh trùng với **giao điểm** của bàn cờ, không mặc định đặt giữa ô như cờ vua.
- Hiển thị quân chồng/vận tải theo trạng thái do Engine trả về. `[CẦN CHỐT]` kiểu hiển thị quân được chở (badge số lượng, chồng ảnh, popover).
- Nếu asset lỗi: hiển thị placeholder và ghi lỗi; không thay bằng ảnh của quân khác.
- Mỗi ảnh có nhãn hỗ trợ tiếp cận: tên quân, phe, tọa độ; quân phong Anh hùng có chỉ báo riêng `[ĐỀ XUẤT]`.

## 4. Bàn cờ SVG — ĐÃ CUNG CẤP

### 4.1. Asset nền và hình học

Chủ dự án cung cấp SVG nền với các thuộc tính và hình học sau:

- `viewBox="0 0 1024 949"`, `preserveAspectRatio="none"`.
- Khung gỗ, nền giấy màu sáng, vùng biển xanh ở bên trái, sông xanh ngang giữa bàn cờ, hai đoạn đánh dấu vị trí vượt sông.
- **11 cột giao điểm** tại `x = 63 + 88*c`, với `c = 0..10` (x cuối 943).
- **12 hàng giao điểm** tại `y = 61 + (819/11)*r`, với `r = 0..11` (y cuối 880).
- Vùng biển SVG: `x=63..239`; dải sông: `y≈433.273..507.727`, `x=239..943`.
- Hai vị trí đánh dấu qua sông ở gần `x=503` và `x=679`.

**Yêu cầu quan trọng:** Sử dụng **chính SVG người dùng cung cấp**, không dựng lại bằng lưới ô vuông, không đổi màu hoặc tỷ lệ tùy ý. Nên lưu nguyên SVG vào `apps/web/public/assets/board/commander-board.svg`; đoạn SVG đã gửi trong hội thoại là nguồn asset, không phải ví dụ để AI Coding Agent tự vẽ lại.

### 4.2. Định vị quân lên giao điểm

Gợi ý lớp hiển thị:

1. Lớp nền: SVG bàn cờ.
2. Lớp chỉ báo: chọn quân, nước đi hợp lệ, đích tấn công, nước vừa đi, vùng ảnh hưởng khi bật chế độ xem.
3. Lớp quân: ảnh PNG của hai phe.
4. Lớp tương tác: vùng bấm quanh giao điểm, menu hành động và tooltip.

Với **tọa độ chỉ số SVG** `(row, col)` theo thứ tự từ **trên xuống / trái sang phải**, tâm quân trong viewBox là:

```ts
const svgX = 63 + col * 88;
const svgY = 61 + row * (819 / 11);
```

> **Không đồng nhất `(row, col)` này với tọa độ biên bản `[trục tung ; trục hoành]` cho đến khi chốt phép biến đổi theo hướng nhìn.** Nếu Engine lưu hệ tọa độ khác hoặc đảo chiều theo phe, cần một hàm chuyển đổi duy nhất và kiểm thử đủ bốn góc.

**Lưu ý kỹ thuật:** SVG nền dùng `preserveAspectRatio="none"`, do đó ảnh nền có thể bị kéo giãn nếu khung chứa sai tỷ lệ. `[ĐỀ XUẤT]` Giữ khung bàn cờ tỷ lệ `1024 / 949` để các giao điểm và ảnh quân khớp nhau; lớp quân phải sử dụng cùng hệ quy chiếu, không căn theo kích thước ảnh tùy tiện.

### 4.3. Tương tác bàn cờ

| Sự kiện | Hành vi dự kiến |
|---|---|
| Chọn quân phe đang đi | Viền sáng quân được chọn; hiển thị nước đi hợp lệ do API/Engine cung cấp |
| Chọn giao điểm hợp lệ | Gửi yêu cầu hành động, chờ xác nhận, cập nhật trạng thái chính thức |
| Chọn giao điểm không hợp lệ | Không đổi trạng thái; thông báo ngắn gọn |
| Chọn quân khác cùng phe | Chuyển lựa chọn |
| Đến lượt AI | Khóa thao tác của người chơi; hiển thị AI đang suy nghĩ |
| Tấn công có nhiều phương án | Hiện hộp chọn phương án **do Engine cho phép** (ví dụ ném bom tại chỗ/thế chỗ) |
| Vận tải / triển khai | Chọn đúng loại hành động và mục tiêu theo danh sách Engine trả về; không tự tính nước đi |
| Quân bị tiêu diệt / phong Anh hùng | Hiệu ứng ngắn, không làm thay đổi dữ liệu trạng thái |
| Hoàn thành ván | Khóa nước đi, hiện kết quả từ API và nút xem lại |

`[ĐỀ XUẤT]` Màu đánh dấu: chọn quân vàng; di chuyển xanh; tấn công đỏ; nước vừa đi viền trung tính. `[CẦN CHỐT]` bảng màu và animation.

## 5. Trang Play — bố cục mẫu

```text
┌──────────────────────────────────────────────────────────────────────┐
│ Commander Chess AI             Play  Replays  Statistics  VI / EN    │
├─────────────────────────────────────────┬────────────────────────────┤
│                                         │  Trận đấu                  │
│                                         │  Đỏ: Người / Agent         │
│           BÀN CỜ SVG                   │  Xanh: Agent              │
│        + ẢNH QUÂN CỜ PNG                │  Lượt: Đỏ                  │
│                                         │  Thời gian / Điểm          │
│                                         │                            │
│                                         │  LỊCH SỬ NƯỚC ĐI          │
│                                         │  1. ...                    │
│                                         │  2. ...                    │
├─────────────────────────────────────────┴────────────────────────────┤
│  Ván mới   Chọn Agent   [Tùy chọn hiển thị]                          │
└──────────────────────────────────────────────────────────────────────┘
```

**Đây chỉ là wireframe**, không phải thiết kế màu sắc/kích thước đã chốt. Trên màn hình nhỏ `[ĐỀ XUẤT]` đặt bảng điều khiển dưới bàn cờ và cho phép cuộn biên bản.

### 5.1. Trước trận

- Chọn chế độ: Người vs AI / AI vs AI nếu đã có tính năng.
- Chọn phe người chơi và Agent có sẵn; Agent chưa sẵn sàng phải được đánh dấu hoặc vô hiệu hóa.
- Bắt đầu trận chỉ khi API xác nhận thành công.
- Có cho người chơi chọn phe Xanh hoặc Đỏ, có cho xoay bàn cờ khi xem chứ khi đang chơi(đang trong trận) thì không.

### 5.2. Trong trận

- Hiển thị tên/loại hai bên, lượt hiện tại, đồng hồ và điểm số theo dữ liệu Engine/API.
- Lịch sử nước đi dùng định dạng `MOVE_NOTATION.md`, có phân biệt **Đỏ** và **Xanh**.
- Tương tác đặc biệt (ăn tại chỗ, một đổi một, chở quân, phong Anh hùng...) phải thể hiện từ sự kiện Engine; không giả lập bằng animation.
- `[ĐỀ XUẤT]` Cho phép mở chi tiết quân đang chọn và danh sách hành động hợp lệ.
- Có nút hoàn tác/đầu hàng/hòa; không hiển thị nếu chưa có luật và API hỗ trợ.

### 5.3. Sau trận

- Hiển thị thắng/thua/hòa, lý do kết thúc, điểm và thời gian thực tế nếu có.
- Nút `Ván mới`; nút `Xem lại` nếu có dữ liệu replay; nút `Lưu`/`Xuất biên bản` nếu backend hỗ trợ.
- Không tự lưu mọi trận vào dữ liệu nghiên cứu nếu chưa được chọn.

## 6. Chế độ AI vs AI — bản mẫu

- Hai ô chọn Agent (Đỏ / Xanh), chỉ liệt kê Agent thực sự khả dụng.
- Nút `Bắt đầu`, `Tạm dừng`, `Tiếp tục`, `Dừng` chỉ bật khi backend hỗ trợ tương ứng.
- Chọn tốc độ phát hình ảnh; tốc độ **hiển thị** không làm thay đổi kết quả Engine.
- Thể hiện lượt đang tính, thời gian suy nghĩ và biên bản theo dữ liệu thật.
- Nếu Agent timeout/lỗi: hiển thị trạng thái thực tế, không tự gán thắng cho đối phương khi chưa có kết quả Engine/tournament.

## 7. Trang Replays

- Danh sách ván **đã lưu** với thời gian, Agent, kết quả, phiên bản luật/Engine nếu có.
- Khi mở một ván: dựng lại trạng thái từ snapshot + chuỗi sự kiện hoặc cơ chế replay do backend cung cấp.
- Điều khiển: về đầu, lùi một nước, tiến một nước, tới cuối; tự phát/tạm dừng.
- Đồng bộ danh sách biên bản và bàn cờ tại mỗi bước.
- Chỉ dùng log có cấu trúc làm nguồn replay; ký pháp `⋆`, `@`, `_@_`, `><` là **định dạng hiển thị/xuất**, không phải nguồn duy nhất để tái tạo sự kiện phức tạp.

## 8. Dashboard, Statistics, Rules, Research

- **Dashboard:** chỉ số tổng quan, danh sách Agent và trạng thái hệ thống; có trạng thái rỗng khi chưa có dữ liệu.
- **Statistics:** thắng/hòa/thua, tỷ lệ, thời gian suy nghĩ, bộ lọc theo Agent và cấu hình; chỉ vẽ biểu đồ từ dữ liệu đo thật.
- **Rules:** trình bày luật từ `GAME_RULES.md`, hình minh họa nếu có; không tự viết luật mới.
- **Research/Tournaments:** chỉ hiển thị tính năng đã triển khai, phân biệt bản thử nghiệm và kết quả chính thức.

## 9. i18n, responsive và accessibility

- Ngôn ngữ: `vi` mặc định, `en` tùy chọn; chuyển ngay không reload, lưu lựa chọn.
- Dịch cả thông báo lỗi, trạng thái chờ, bảng thống kê, hộp thoại, tên menu; không dịch ID/enum kỹ thuật.
- Bàn cờ phải co theo màn hình nhưng giữ hình học giao điểm chính xác.
- Ảnh quân có văn bản thay thế; trạng thái chọn không chỉ dựa vào màu.

## 10. Trạng thái hệ thống và xử lý lỗi

| Trạng thái | Hiển thị |
|---|---|
| Loading | Skeleton/spinner có nhãn |
| API offline | Thông báo mất kết nối, nút thử lại |
| Agent chưa triển khai | Nhãn `Chưa khả dụng`, không cho chọn |
| Nước đi bị từ chối | Giữ bàn cờ ở trạng thái đã xác nhận, hiện lý do |
| Request chậm | Hiển thị đang xử lý, tránh gửi lặp |
| Thiếu ảnh quân | Placeholder có nhãn, ghi log lỗi asset |
| Không có replay/thống kê | Empty state, không dùng dữ liệu giả |
| Ván kết thúc | Hiển thị kết quả thực tế và khóa thao tác |

## 11. Tích hợp và các ràng buộc cho AI Coding Agent

1. Không sửa `packages/game-engine/` và `packages/agents/` khi chưa được chủ dự án duyệt.
2. Không sao chép luật sang frontend để tự sinh nước đi hợp lệ.
3. Không thay đổi API contract âm thầm; nếu thiếu field hoặc action, đề xuất cập nhật `API_CONTRACT.md` và xin duyệt.
4. Có thể dùng mock data để dựng UI nhưng phải gắn nhãn mock, không tuyên bố đã tích hợp thực tế.
5. Giữ nguyên tên asset PNG và SVG của chủ dự án.
6. Dữ liệu bàn cờ, lịch sử nước đi và đồng hồ phải đồng bộ theo phiên bản/trạng thái trận từ API.
7. Nếu dữ liệu không đủ cho UI (ví dụ quân chở lồng nhau, action variants), yêu cầu bổ sung contract thay vì đoán.
8. Khi thay đổi UI liên quan đến ký pháp, tham chiếu `MOVE_NOTATION.md`.

## 12. Checklist nghiệm thu giao diện

- [ ] Đọc đúng 22 file ảnh quân (11 loại × 2 phe), không lỗi đường dẫn/chữ hoa.
- [ ] Dùng đúng SVG nền được cung cấp; giữ 11 × 12 **giao điểm** và lớp quân khớp khi resize.
- [ ] Hiển thị đúng trạng thái trận từ API, đúng phe và tọa độ.
- [ ] Người chơi chỉ gửi hành động Engine cho phép; xử lý lỗi không đổi trạng thái.
- [ ] Các lựa chọn hành động đặc biệt không bị giản lược thành một nước đi thông thường.
- [ ] Biên bản hiển thị đúng ký pháp; Tư lệnh dùng `⋆`, ảnh dùng `TL_<side>.png`.
- [ ] Chuyển Tiếng Việt / English không reload và lưu lựa chọn.
- [ ] AI chưa triển khai không xuất hiện như AI đã sẵn sàng.
- [ ] Không có thống kê hoặc kết quả giả.
- [ ] Replay đồng bộ ảnh quân và log ở mọi bước.
- [ ] Giao diện sử dụng được trên desktop và mobile.
- [ ] Có trạng thái loading, empty, error và game-over.

## 13. Những điểm chủ dự án sẽ chỉnh sửa sau

| Mục | Trạng thái |
|---|---|
| Phong cách màu sắc, font, logo, header | Phong cách như một trò chơi cờ đối kháng khác nhưng có sự nổi bật về chiến tranh hiện đại pha lẫn với màu cờ Việt Nam |
| Bố cục cuối cùng desktop/mobile | desktop, mobile sẽ là bản mở rộng |
| Kích thước ảnh quân tại giao điểm | cân đối và chiếm 1/3 đường thẳng của 4 đường từ giao điểm |
| Cách hiển thị quân được chở, vận tải lồng nhau | quân chở sẽ vẫn hiển thị kích thước bình thường, còn quân được chở sẽ có kích thước nhỏ ở dưới góc phải của quân cờ chở cỡ 1/10 quân cờ chở, nếu chở 2 quân thì 2 quân ở góc trái không chồng vào nhau chỉ nằm kế nhau trên quân cờ chở |
| Có xoay bàn theo phe người chơi hay không | Có xoay bàn cờ theo phe người chơi, nhưng người chơi khi đang chơi không được xoay bàn cờ, chỉ khi xem lại replay hoặc xem các AI đấu với AI thì mới được xoay bàn cờ |
| Có hiển thị vùng phòng không / vùng di chuyển hay không | Có hiển thị vùng phòng không là vòng tròn nối các giao điểm mà quân đó có phạm vi phòng không, có hiển thị đường di chuyển của quân |
| Có animation, âm thanh, chế độ xem nâng cao hay không | Không cần animation quá phức tạp chỉ animation của quân di chuyển đến nơi nào đó, âm thanh không cần, không cần chế độ xem nâng cao |
| Giao diện riêng AI vs AI hay chung trang Play | Giao diện riêng AI vs AI |
| Nút hoàn tác, đầu hàng, đề nghị hòa | Có nút hoàn tác, đầu hàng, đề nghị hòa |
| Mapping enum và action schema chính xác từ API | `[CẦN ĐỐI CHIẾU API_CONTRACT.md]` |

---

**Quy tắc cập nhật:**  `UI_SPECIFICATION.md` không có quyền ghi đè `GAME_RULES.md`, `MOVE_NOTATION.md` hoặc `API_CONTRACT.md`.
