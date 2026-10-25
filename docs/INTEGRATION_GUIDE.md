# INTEGRATION_GUIDE.md — Hướng dẫn tích hợp hệ thống AI Cờ Tư Lệnh

**Trạng thái:** Tài liệu hướng dẫn tích hợp (living document)  
**Cập nhật:** 24/10/2026  
**Phạm vi:** `apps/web`, `apps/api`, `packages/game-engine`, `packages/agents`, `workers/tournament-runner`, `research`  
**Ngôn ngữ tài liệu:** Tiếng Việt; tên định danh, API và khóa cấu hình dùng tiếng Anh.

> **QUAN TRỌNG:** Đây là hướng dẫn phối hợp các thành phần, **không phải** đặc tả luật chơi, đặc tả UI hay hợp đồng API cuối cùng. `docs/GAME_RULES.md` là nguồn luật đã được chủ dự án chốt; `docs/API_CONTRACT.md` là nguồn hợp đồng HTTP; `docs/MOVE_NOTATION.md` là nguồn ký pháp và định dạng biên bản. Không tự thêm hoặc sửa luật khi tích hợp. Những schema, hàm và payload gắn nhãn **[ĐỀ XUẤT]** chỉ là ví dụ thiết kế, chưa khẳng định đã được triển khai.

## 1. Mục tiêu tích hợp

- Người chơi thao tác trên web, nước đi được API tiếp nhận và Game Engine kiểm tra trước khi áp dụng.
- Người chơi có thể đấu với Agent đã thực sự triển khai; Agent chọn hành động hợp lệ từ Engine.
- Chế độ AI vs AI và Tournament Runner dùng **cùng Game Engine và Agent Protocol**, không viết bản sao luật.
- Trạng thái, sự kiện và biên bản được lưu đủ để phát lại trận đấu và phục vụ đánh giá AI.
- Các thông tin về luật, nước đi, kết quả và thống kê thống nhất giữa API, UI, Engine và nghiên cứu.
- Lỗi tích hợp được báo rõ; không hiển thị mock, placeholder hoặc kết quả giả như chức năng hoàn thiện.

## 2. Tài liệu nguồn và thứ tự ưu tiên

| Tài liệu | Phạm vi chịu trách nhiệm |
|---|---|
| `AGENTS.md` | Ranh giới quyền sửa mã, quy tắc làm việc của AI Coding Agent |
| `docs/GAME_RULES.md` | Luật, trạng thái hợp lệ, hành động hợp lệ, kết thúc trận |
| `docs/MOVE_NOTATION.md` | Ký pháp quân/nước đi, biên bản, log và xuất/nhập biên bản |
| `docs/ARCHITECTURE.md` | Kiến trúc module, công nghệ và phụ thuộc |
| `docs/API_CONTRACT.md` | Endpoint, request/response, mã lỗi và tương thích |
| `packages/agents/agent_protocol.md` | Đầu vào/đầu ra và nghĩa vụ của Agent |
| `docs/DEVELOPMENT.md` | Môi trường, quy trình phát triển, cách chạy và kiểm thử |
| `docs/UI_SPECIFICATION.md` | Đặc tả giao diện **sẽ bổ sung sau**, không tự chốt thiết kế trong file này |
| `docs/DECISIONS.md` | Nhật ký quyết định kỹ thuật khi có thay đổi hoặc lựa chọn mới |

**Khi tài liệu mâu thuẫn:** Không chọn tùy ý. Đối với luật, dừng ở `GAME_RULES.md` và hỏi chủ dự án; đối với API, đối chiếu `API_CONTRACT.md` với mã nguồn và xác nhận trước khi thay đổi interface. Quy tắc luật đã chốt không bị thay thế bởi ví dụ trong tài liệu này.

## 3. Kiến trúc tích hợp

```text
                 ┌──────────────────────────┐
                 │ apps/web                 │
                 │ React + TypeScript + Vite│
                 │ Ảnh quân cờ, i18n, UI    │
                 └────────────┬─────────────┘
                              │ HTTP / JSON
                              ▼
                 ┌──────────────────────────┐
                 │ apps/api                 │
                 │ Python + FastAPI         │
                 │ Phiên chơi, kiểm tra, DB │
                 └───────┬──────────┬───────┘
                         │          │
              Engine API │          │ Agent Protocol
                         ▼          ▼
             ┌────────────────┐ ┌────────────────┐
             │ packages/      │ │ packages/      │
             │ game-engine    │◄│ agents         │
             │ Luật, trạng    │ │ Chọn hành động │
             │ thái, kết quả  │ │ từ legal list  │
             └───────┬────────┘ └────────┬───────┘
                     │                   │
                     └─────────┬─────────┘
                               ▼
                  workers/tournament-runner
                               │
                               ▼
                 research / persisted matches
```

Sơ đồ thể hiện **phụ thuộc logic**, không bắt buộc mỗi hộp là một tiến trình hoặc dịch vụ riêng. Theo `ARCHITECTURE.md`, ưu tiên **modular monolith**, không tự thêm microservice.

### 3.1. Trách nhiệm và quyền sở hữu

| Thành phần | Chịu trách nhiệm | Không được làm |
|---|---|---|
| `apps/web` | Hiển thị ảnh bàn/quân, chọn nước đi, lịch sử, trạng thái chờ/lỗi, ngôn ngữ Việt/Anh | Tự sinh luật hoặc tự công nhận nước đi hợp lệ |
| `apps/api` | Xác thực request, quản lý phiên, điều phối Engine/Agent, trả trạng thái, lưu ván | Tin trạng thái hay legal actions do client gửi |
| `packages/game-engine` | Trạng thái chuẩn, sinh hành động hợp lệ, áp dụng hành động, kết quả, tuần tự hóa | Phụ thuộc UI hoặc nhân bản logic cho frontend |
| `packages/agents` | Chọn một hành động trong danh sách Engine cấp, trả metadata nếu có | Tự sửa trạng thái chuẩn hoặc trả hành động ngoài danh sách |
| `workers/tournament-runner` | Điều phối các trận tự động, seed, giới hạn tài nguyên, kết quả thực nghiệm | Tự định nghĩa luật riêng, tính trận lỗi là thắng |
| `research` | Huấn luyện, đánh giá, lưu cấu hình và kết quả | Công bố số liệu không có log/chạy thực tế |

**Phân quyền dự án:** AI Coding Agent phụ trách `apps/web`, `apps/api`, tích hợp và kiểm thử FE/API; chủ dự án phụ trách `packages/game-engine`, `packages/agents`, nghiên cứu, huấn luyện/đánh giá và xác minh luật. AI Coding Agent **không chỉnh sửa Engine/Agent khi chưa được chấp thuận**. Nếu interface thiếu hoặc thay đổi, mở yêu cầu xác nhận trước, không lặng lẽ đổi hoặc viết bản luật thứ hai.

## 4. Hợp đồng dữ liệu tại ranh giới module

### 4.1. Nguyên tắc chung

1. Chỉ Game Engine quyết định trạng thái và hành động hợp lệ.
2. API gửi xuống web **snapshot đã xác thực** và danh sách hành động hợp lệ cho phe tới lượt.
3. Mỗi quân cần định danh ổn định (`piece_id`) nếu log, vận tải hoặc replay yêu cầu phân biệt hai quân cùng loại.
4. Phân biệt **hành động nguyên tử** với **lượt**: một lượt có thể có nhiều hành động theo luật cõng quân; không mặc định `1 request = 1 lượt`.
5. Sử dụng một quy ước tọa độ chuẩn trong mã; ở biên bản, `MOVE_NOTATION.md` ghi `[y ; x]`. Nếu API dùng `{x, y}`, serializer phải chuyển đổi tường minh.
6. Mọi payload lưu hoặc trao đổi để phát lại cần có phiên bản schema và phiên bản luật/Engine phù hợp.
7. Phân biệt `game_id`, `turn_index`, `action_index` và `event_index`; không suy diễn rằng mỗi sự kiện đều là một nước đi.
8. Các enum và tên trường cuối cùng phải được chốt trong `API_CONTRACT.md` và mã nguồn.

### 4.2. Cấu trúc trạng thái — [ĐỀ XUẤT]

Đây là **minh họa cấu trúc**, không phải response đã chốt hoặc bàn cờ khởi đầu thực tế:

```json
{
  "schema_version": "1.0",
  "game_id": "example-game",
  "rules_version": "game-rules-version",
  "engine_version": "engine-version",
  "side_to_move": "RED",
  "status": "IN_PROGRESS",
  "turn_index": 0,
  "action_index": 0,
  "pieces": [
    {
      "piece_id": "red-commander-1",
      "side": "RED",
      "type": "COMMANDER",
      "position": { "x": 3, "y": 4 }
    }
  ],
  "legal_actions": []
}
```

**Lưu ý:** `pieces` ở ví dụ chỉ có một quân để mô tả schema; không phải trạng thái bàn cờ hợp lệ. `legal_actions: []` cũng không chứng minh bên Đỏ hết nước. Các trường về địa hình, vận tải, phong Anh hùng, đồng hồ, điểm, quyền hành động còn lại trong lượt và trạng thái phòng không phải được Engine xác định và bổ sung vào schema thật khi cần. Không dùng payload này làm fixture khởi tạo trận đấu.

### 4.3. Hành động — [ĐỀ XUẤT]

```json
{
  "action_id": "example-action-id",
  "type": "MOVE",
  "piece_id": "red-commander-1",
  "from": { "x": 3, "y": 4 },
  "to": { "x": 3, "y": 5 }
}
```

Đây là **ví dụ về dạng dữ liệu**, không phải cam kết tên enum `MOVE`. Các loại hành động đặc biệt (ăn thế chỗ, đánh tại chỗ, 1 đổi 1, lên phương tiện, triển khai quân, chuỗi hành động trong một lượt) phải được biểu diễn bằng schema có thể phân biệt rõ **loại hành động và hậu quả**, thống nhất với Engine. **Không** cố ép mọi hành động thành một cặp `from/to` đơn giản.

### 4.4. Ký pháp và dữ liệu nội bộ

- Engine/API lưu `piece_type: COMMANDER` (hoặc enum tương đương đã chốt), **không** dùng glyph để xử lý luật.
- Frontend hiển thị quân bằng ảnh PNG/SVG theo `type` và `side`; không cần render ký tự lên quân cờ.
- Serializer tạo ký pháp Tư lệnh bằng `⋆` tương ứng `\star` trong LaTeX; **đối chiếu và thống nhất một mã Unicode duy nhất trong `MOVE_NOTATION.md` trước khi triển khai parser**. Không trộn `★` và `⋆` tùy tiện.
- Biên bản hiển thị là **dữ liệu dẫn xuất** từ sự kiện có cấu trúc; không dùng chuỗi biên bản làm nguồn trạng thái duy nhất.
- Nếu parser hỗ trợ nhiều biến thể ký hiệu đầu vào, chuẩn hóa về ký hiệu canonical trước khi kiểm tra.

## 5. Luồng tích hợp người chơi vs AI

1. **Khởi tạo:** Web gọi `POST /api/v1/games` với cấu hình đã được API hỗ trợ.
2. **API tạo phiên:** Engine khởi tạo trạng thái theo `GAME_RULES.md`; API trả `game_id`, `state`, `legal_actions`, `status` theo `API_CONTRACT.md`.
3. **Web render:** Đọc `state`, ánh xạ `side/type` sang ảnh quân cờ, đánh dấu phe đến lượt. Không suy luận luật từ vị trí ảnh.
4. **Người chơi chọn:** Web chỉ cho phép chọn hành động được API/Engine công bố; nếu cần chọn loại hành động (ví dụ hình thức tấn công), phải hiển thị lựa chọn rõ ràng.
5. **Gửi hành động:** Web gọi `POST /api/v1/games/{game_id}/actions` với `action`; API kiểm tra session, phiên bản/trạng thái và hợp lệ qua Engine.
6. **Engine xử lý:** Áp dụng đúng hành động; nếu lượt có chuỗi hành động, trả trạng thái tiếp theo và quyền hành động còn lại, **không tự chuyển phe sớm**.
7. **Ghi log:** Lưu sự kiện có cấu trúc, số thứ tự, thay đổi trạng thái và ký pháp dẫn xuất theo `MOVE_NOTATION.md`.
8. **AI tới lượt:** API đưa snapshot + legal actions cho Agent, nhận hành động, xác thực lại bằng Engine rồi áp dụng.
9. **Đồng bộ:** API trả snapshot mới; web hiển thị kết quả và lịch sử.
10. **Kết thúc:** Engine xác định kết quả; API lưu đúng kết quả, thời gian, phiên bản và trạng thái hoàn tất.

**Chưa chốt:** Cách kích hoạt lượt AI (trả ngay trong cùng request, polling hoặc background job) phải được chọn dựa trên độ trễ thật. Không tự thêm endpoint hay WebSocket vào hợp đồng hiện tại. Với Agent chạy lâu, không giữ UI ở trạng thái giả như đã xong; cần trạng thái đang tính toán, timeout và cơ chế đồng bộ có kiểm soát.

## 6. Luồng AI vs AI và Tournament Runner

1. Tạo cấu hình trận: Agent Đỏ, Agent Xanh, phiên bản, tham số, seed, ngân sách tính toán và phiên bản Engine.
2. Engine tạo trạng thái ban đầu; Đỏ đi trước theo luật đã chốt.
3. Trong mỗi lượt, lấy danh sách `legal_actions` từ Engine; Agent tới lượt chọn hành động theo Agent Protocol.
4. Runner kiểm tra đầu ra Agent thuộc danh sách hợp lệ; Engine áp dụng và phát sinh events.
5. Nếu luật cho phép nhiều hành động trong lượt, runner tiếp tục theo **quyền hành động thực tế do Engine trả**, không tự đổi phe sau hành động đầu.
6. Ghi metadata (Agent, version, seed, config), trạng thái, action, thời gian suy nghĩ và lỗi.
7. Dừng khi Engine xác định kết thúc hoặc khi chính sách giới hạn thực nghiệm kích hoạt; **giới hạn số lượt thử nghiệm không phải luật kết thúc trận**.
8. Phân biệt rõ `WIN`, `LOSS`, `DRAW`, `INCOMPLETE`, `ERROR` hoặc các trạng thái tương đương được chốt; không tự tính `ERROR` thành chiến thắng.
9. Xuất replay và số liệu từ trận đã chạy thật; hỗ trợ chạy lại với cùng cấu hình/seed khi tác tử và môi trường cho phép.

**Kiểm tra tính tái lập:** Cùng seed chỉ đủ tái lập nếu mọi nguồn ngẫu nhiên, phiên bản mã, thứ tự duyệt và cấu hình liên quan đều được kiểm soát. Agent học sâu trên phần cứng khác có thể cần ghi nhận sai khác do tính toán không tất định.

## 7. Log, biên bản và phát lại

### 7.1. Hai lớp dữ liệu

- **Structured event log (nguồn sự thật cho replay):** ID phiên, thứ tự lượt/hành động/sự kiện, trạng thái trước/sau hoặc delta xác định, actor, action, các quân bị ảnh hưởng, metadata và phiên bản.
- **Human-readable notation (để đọc/xuất):** Sinh từ event log theo `MOVE_NOTATION.md`, phân cột phe Đỏ và phe Xanh, có ký hiệu di chuyển/ăn/chiếu/v.v.

Một hành động có thể sinh nhiều sự kiện (ví dụ quân bị tiêu diệt do phòng không, phong Anh hùng, cập nhật điểm). Không giả định một ký hiệu duy nhất luôn đủ để phục dựng toàn bộ hậu quả.

### 7.2. Các trường cần có khi lưu — [ĐỀ XUẤT]

```json
{
  "schema_version": "1.0",
  "game_id": "example-game",
  "event_index": 12,
  "turn_index": 5,
  "action_index": 1,
  "actor_side": "RED",
  "action": { "type": "MOVE", "piece_id": "piece-123" },
  "notation": "⋆ [4 ; 3] _ [5 ; 3]",
  "engine_version": "engine-version",
  "rules_version": "rules-version"
}
```

**Chỉ là ví dụ cấu trúc.** Để replay chính xác cần lưu **payload action đầy đủ** và trạng thái ban đầu/ảnh chụp hoặc cơ chế phục dựng được kiểm thử; JSON rút gọn ở trên **không đủ** để phát lại độc lập.

### 7.3. Quy trình replay

1. Tải metadata + trạng thái khởi tạo + chuỗi action/event có thứ tự.
2. Kiểm tra `schema_version`, `rules_version`, `engine_version` và khả năng tương thích.
3. Dùng Engine phiên bản phù hợp áp dụng tuần tự các hành động, hoặc dùng snapshot đáng tin cậy để xem lại theo chính sách hệ thống.
4. Sau mỗi bước, đối chiếu trạng thái, lượt, điểm và kết quả với dữ liệu đã lưu.
5. Nếu thiếu action, sai thứ tự hoặc khác luật, trả lỗi replay; **không** tự bỏ qua event để làm cho ván chạy tiếp.
6. Giao diện cho phép đi tới/lùi dựa trên snapshot hoặc trạng thái tái dựng, không tự mô phỏng luật.

## 8. Hợp đồng HTTP đang có trong repository

`docs/API_CONTRACT.md` đang ở trạng thái **Draft** và liệt kê:

| Phương thức | Endpoint | Mục đích |
|---|---|---|
| GET | `/health` | Kiểm tra tình trạng API |
| GET | `/api/v1/agents` | Danh sách Agent khả dụng |
| POST | `/api/v1/games` | Tạo phiên chơi |
| GET | `/api/v1/games/{game_id}` | Lấy trạng thái phiên |
| POST | `/api/v1/games/{game_id}/actions` | Gửi hành động người chơi |
| GET | `/api/v1/replays` | Danh sách replay |
| GET | `/api/v1/replays/{replay_id}` | Chi tiết replay |
| GET | `/api/v1/statistics/summary` | Thống kê tổng hợp |
| GET | `/api/v1/statistics/matchups` | Thống kê theo cặp Agent |

**Không coi bảng trên là danh sách endpoint đã chạy được.** Khi thay đổi endpoint, schema, mã lỗi hoặc quy tắc trả dữ liệu, cập nhật `API_CONTRACT.md` trước hoặc cùng PR tích hợp. Endpoint AI vs AI, streaming tiến độ, quản lý tournament hay export notation **chưa được chốt** trong hợp đồng này; nếu cần, đề xuất và duyệt riêng.

### 8.1. Xử lý lỗi

Theo API Contract, lỗi cần có `error.code`, `error.message` và `error.details` (tùy chọn); dùng HTTP 400 cho request sai cấu trúc, 404 khi không tìm thấy tài nguyên và 409 cho chuyển trạng thái không hợp lệ. Mã lỗi cụ thể chỉ được dùng khi đã thống nhất trong hợp đồng.

- **Invalid action:** Không thay đổi trạng thái; trả lỗi có thể hiểu được; web tải lại trạng thái chuẩn nếu cần.
- **Stale state / concurrent actions:** Không ghi đè lượt đi khác; đề xuất bổ sung `state_version` hoặc cơ chế optimistic concurrency khi chốt API.
- **Agent timeout / crash:** Lưu lỗi và trạng thái trận phù hợp; không tự suy diễn bên thắng.
- **DB failure:** Không xác nhận đã lưu replay nếu thao tác lưu thất bại.
- **Network failure:** Web không tự áp dụng nước đi khi chưa có phản hồi xác thực; hỗ trợ retry an toàn theo chính sách được chốt.

## 9. Cách chạy và kiểm tra kết nối

> Repository ban đầu chưa chốt lệnh chạy và dependency cụ thể. **Không bịa lệnh `npm run ...`, `uvicorn ...` hoặc Docker Compose là đã hoạt động.** Lấy lệnh thật từ `apps/web/README.md`, `apps/api/README.md`, file cấu hình và `docs/DEVELOPMENT.md` sau khi cài đặt.

**Thứ tự kiểm tra khuyến nghị:**

1. Kiểm tra nhánh Git và thay đổi chưa commit; đọc `AGENTS.md`.
2. Cài dependencies theo manifest thực tế của web và API; cập nhật `.env.example` nếu có biến môi trường mới.
3. Chạy unit test Engine; xác nhận khởi tạo, legal actions, apply, kết thúc trận và serialization.
4. Chạy test Agent Protocol; xác nhận Agent chỉ chọn action hợp lệ và không sửa state.
5. Khởi chạy API; kiểm tra `GET /health` **nếu endpoint đã được triển khai**.
6. Kiểm tra API tạo phiên, lấy trạng thái, gửi action hợp lệ và action không hợp lệ.
7. Khởi chạy web; kiểm tra ánh xạ ảnh quân cờ, trạng thái lượt và xử lý lỗi.
8. Chạy một ván thực tế người vs AI; kiểm tra lượt nhiều hành động nếu có.
9. Lưu replay; phát lại và so sánh trạng thái cuối với trận gốc.
10. Chạy trận AI vs AI ngắn, kiểm tra log, seed, metadata và kết quả thực tế.

**Cấu hình cần thống nhất:** địa chỉ API từ web, CORS, đường dẫn asset ảnh, thư mục dữ liệu lưu, môi trường phát triển/kiểm thử, phiên bản Python/Node và giới hạn tài nguyên Agent. Không hardcode secret hoặc URL máy cá nhân vào source.

## 10. Kiểm thử tích hợp bắt buộc

| ID | Kịch bản | Điều kiện đạt |
|---|---|---|
| INT-01 | Web tạo trận | API trả ID, state và status nhất quán |
| INT-02 | Render quân | `side/type` ánh xạ đúng ảnh; không đổi luật |
| INT-03 | Gửi nước đi hợp lệ | Engine chấp nhận, API trả trạng thái mới đúng |
| INT-04 | Gửi nước đi sai | Bị từ chối; state không đổi |
| INT-05 | Tọa độ | `{x,y}` và `[y ; x]` chuyển đổi chính xác |
| INT-06 | Nước đi đặc biệt | Capture tại chỗ/thế chỗ, phòng không và 1 đổi 1 đúng Engine |
| INT-07 | Vận tải / nhiều hành động | Không chuyển lượt trước khi Engine kết thúc lượt |
| INT-08 | Agent hợp lệ | Action trả về thuộc legal actions |
| INT-09 | Agent lỗi/timeout | Trạng thái lỗi rõ ràng; không tạo thắng giả |
| INT-10 | Biên bản | Serializer sinh đúng ký pháp `MOVE_NOTATION.md` |
| INT-11 | Replay | Phục dựng cùng trạng thái và kết quả, đúng thứ tự |
| INT-12 | Đồng bộ web/API | Không hiển thị trạng thái cũ như đã xác nhận |
| INT-13 | AI vs AI | Hai Agent dùng chung Engine; metadata/seed được lưu |
| INT-14 | Thống kê | Chỉ tính dữ liệu ván thực tế; phân biệt hòa/lỗi/chưa xong |
| INT-15 | i18n | Chuyển Việt/Anh cập nhật đầy đủ văn bản giao diện |
| INT-16 | Thay đổi luật/phiên bản | Replay cũ được xử lý tương thích hoặc báo không tương thích |

**Quy tắc báo cáo:** Chỉ đánh dấu PASS khi đã chạy kiểm thử; nếu chưa triển khai, ghi `NOT_IMPLEMENTED`; nếu chưa chạy, ghi `NOT_RUN`; nếu thất bại, ghi `FAIL` cùng bằng chứng và lệnh thực thi. Bảng trên là **test plan**, không phải báo cáo PASS.

## 11. Quy trình phối hợp giữa chủ dự án và AI Coding Agent

### 11.1. Khi giao nhiệm vụ frontend/backend

Cung cấp tối thiểu:

- Mục tiêu và hành vi mong đợi.
- File được phép sửa, file không được sửa.
- Endpoint/schema hiện hành hoặc mock được chấp thuận.
- Ví dụ trạng thái và legal actions do chủ dự án cung cấp nếu Engine chưa sẵn sàng.
- Acceptance Criteria và test cần chạy.

AI Coding Agent phải:

1. Đọc `AGENTS.md`, các tài liệu liên quan và kiểm tra mã hiện có.
2. Nêu file dự kiến thay đổi và giả định còn thiếu.
3. Dùng **mock API có đánh dấu rõ** nếu Engine chưa có; không chép luật vào frontend.
4. Không thay đổi interface Engine/Agent hoặc sửa mã thuộc quyền chủ dự án khi chưa duyệt.
5. Không khẳng định tích hợp thành công chỉ vì mock hoạt động.
6. Chạy kiểm thử thực tế, báo kết quả và cập nhật tài liệu nếu hợp đồng thay đổi.

### 11.2. Khi Game Engine/Agent sẵn sàng

- Chủ dự án cung cấp interface thật, fixture tối thiểu, version và cách chạy test.
- AI Coding Agent thay adapter/mock bằng kết nối thật; giữ nguyên nguyên tắc Engine là nguồn luật duy nhất.
- Hai phía thống nhất lỗi, timeout, serialization và vòng đời lượt.
- Thực hiện smoke test toàn luồng trước khi bỏ mock.

### 11.3. Quy trình đề xuất thay đổi interface

```text
Phát hiện thiếu/khác interface
    ↓
Ghi vấn đề: yêu cầu, ví dụ input/output, ảnh hưởng
    ↓
Chủ dự án xem xét và chấp thuận/điều chỉnh
    ↓
Cập nhật API_CONTRACT.md / agent_protocol.md nếu liên quan
    ↓
Triển khai tại module thuộc quyền sở hữu
    ↓
Chạy unit + integration tests
    ↓
Cập nhật INTEGRATION_GUIDE.md và PR/commit
```

## 12. Checklist bàn giao tích hợp

- [ ] Đã đọc `AGENTS.md`, `GAME_RULES.md`, `MOVE_NOTATION.md` và API Contract.
- [ ] Các interface đã được xác nhận; không còn mock bị trình bày là thật.
- [ ] Engine là nơi duy nhất kiểm tra và áp dụng luật.
- [ ] Tọa độ, loại quân, phe, lượt và hành động đặc biệt được chuyển đổi nhất quán.
- [ ] Web dùng ảnh quân cờ; mọi lựa chọn nước đi được xác thực ở server.
- [ ] Có cơ chế xử lý lượt nhiều hành động, lỗi, timeout và trạng thái chờ.
- [ ] Có structured log đủ phục vụ replay; biên bản sinh từ log.
- [ ] API và tài liệu phản ánh đúng hành vi hiện có.
- [ ] Test đã thực sự chạy, có lệnh và kết quả được ghi lại.
- [ ] Không thay đổi mã Engine/Agent ngoài phạm vi được chủ dự án duyệt.
- [ ] Không công bố Agent, số liệu, replay hoặc tính năng chưa hoàn thiện là đã xong.

## 13. Tình trạng các vấn đề tích hợp

Các mục dưới đây đã được chuẩn hóa và ghi nhận chính thức:

1. **Schema thực tế (`GameState`, `Action`, `Event`, `LegalAction`):** Đã hoàn tất và chốt tại [API_CONTRACT.md](file:///d:/Commander-Chess-AI/docs/API_CONTRACT.md).
2. **Cách biểu diễn chuỗi hành động trong một lượt cõng quân:** Sử dụng mô hình `TurnPhase: NORMAL | STACK_ACTIVE`, mỗi hành động gửi qua `POST /actions`, hỗ trợ kết thúc sớm qua `POST /games/{id}/end-turn` hoặc action `END_TURN`.
3. **Quy ước ký hiệu sao Tư lệnh:** Đã chốt dùng `⋆` (Unicode `U+22C6`, `\star` trong LaTeX), ghi nhận tại [DECISIONS.md:DEC-001](file:///d:/Commander-Chess-AI/docs/DECISIONS.md).
4. **Vị trí xuất phát và địa hình:** Đã chốt toàn bộ 38 vị trí quân và 2 ngầm tại [GAME_RULES_PHAN_1_TOA_DO.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES_PHAN_1_TOA_DO.md).

**Các vấn đề kỹ thuật còn cần thiết lập khi bắt đầu code:**
- Cơ chế lưu trữ bảng SQLite (`games`, `replays`, `events`) cho `apps/api`.
- Cấu hình tiến trình nền khi chạy giải đấu tự động dài hạn trong `workers/tournament-runner`.

---

**Nguyên tắc cuối:** Tích hợp tốt là các module trao đổi dữ liệu theo cùng một hợp đồng, **không phải** mỗi module tự hiểu và triển khai lại luật Cờ Tư Lệnh. Mọi thay đổi luật được xử lý tại `GAME_RULES.md` và Game Engine; mọi thay đổi giao tiếp được kiểm soát qua hợp đồng và kiểm thử tích hợp.
