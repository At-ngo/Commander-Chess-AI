# API Contract — Commander Chess AI

**Phiên bản:** 1.0 (Standardized)  
**Trạng thái:** Hoàn chỉnh (Authoritative Specification)  
**Base path:** `/api/v1`  
**Tài liệu liên quan:** [GAME_RULES.md](file:///d:/Commander-Chess-AI/docs/GAME_RULES.md), [MOVE_NOTATION.md](file:///d:/Commander-Chess-AI/docs/MOVE_NOTATION.md), [UI_SPECIFICATION.md](file:///d:/Commander-Chess-AI/docs/UI_SPECIFICATION.md)

---

## 1. Nguyên tắc chung

1. **Server-Authoritative:** Mọi biến đổi trạng thái, kiểm tra nước đi hợp lệ và tính điểm đều do **Game Engine** trên Backend quyết định. Client (Frontend / Tournament Runner) không bao giờ tự ý sửa trạng thái.
2. **RESTful & JSON:** Mọi request và response đều định dạng JSON UTF-8 chuẩn.
3. **Mã HTTP chuẩn:**
   - `200 OK`: Yêu cầu thành công.
   - `201 Created`: Tạo tài nguyên mới thành công (Game session).
   - `400 Bad Request`: Payload sai định dạng, thiếu trường bắt buộc.
   - `404 Not Found`: Không tìm thấy `game_id`, `replay_id` hoặc `agent_id`.
   - `409 Conflict`: Hành động không hợp lệ với trạng thái hiện tại (nước đi trái luật, sai lượt, trạng thái cõng quân không thỏa mãn).
   - `422 Unprocessable Entity`: Dữ liệu không qua được xác thực Pydantic (tọa độ ngoài phạm vi 0..10, 0..11).
   - `500 Internal Server Error`: Lỗi máy chủ hoặc crash từ phía Agent.
4. **Error Handling chuẩn hóa:** Mọi phản hồi lỗi đều có cấu trúc cố định với mã máy (`error.code`), thông điệp người đọc (`error.message`) và chi tiết gỡ lỗi (`error.details`).
5. **Đồng bộ tọa độ:** 
   - Trong JSON API: Tọa độ dùng đối tượng Cartesian `{ "x": int, "y": int }` với `0 <= x <= 10`, `0 <= y <= 11`.
   - Trong Notation / UI: Hiển thị theo truyền thống `[y ; x]` (tung độ trước, hoành độ sau).

---

## 2. Hệ thống Enum & Data Models dùng chung

### 2.1. Enums cốt lõi

```typescript
// Phe chơi
type Side = "RED" | "BLUE";

// 11 loại quân cờ
type PieceType = 
  | "COMMANDER"     // Tư lệnh (⋆, TL)
  | "INFANTRY"      // Bộ binh (B)
  | "TANK"          // Xe tăng (T)
  | "MILITIA"       // Dân quân (D)
  | "ENGINEER"      // Công binh (C)
  | "ARTILLERY"     // Pháo binh (A)
  | "ANTI_AIR"      // Cao xạ (F)
  | "MISSILE"       // Tên lửa (L)
  | "AIRCRAFT"      // Không quân / Máy bay (K)
  | "NAVY"          // Tàu chiến / Hải quân (H)
  | "HEADQUARTERS"; // Sở chỉ huy (S)

// Hành động người chơi / Agent gửi lên
type ActionType = 
  | "MOVE"              // Di chuyển không ăn quân (_)
  | "CAPTURE_REPLACE"   // Ăn quân và thế chỗ (@)
  | "CAPTURE_STAND"     // Ăn/bắn tại chỗ: máy bay ném bom, pháo bắn tàu, phá Sở chỉ huy (_@_)
  | "BOARD"             // Quân lên phương tiện cõng
  | "DEPLOY"            // Quân triển khai rời phương tiện cõng
  | "STACK_MOVE"        // Phương tiện mang theo quân được chở di chuyển
  | "END_TURN";         // Chủ động kết thúc sớm lượt tổ hợp

// Biến cố do Engine phát ra sau khi thực hiện hành động
type EventType = 
  | "PIECE_MOVED"       // Quân di chuyển
  | "PIECE_CAPTURED"    // Quân bị tiêu diệt
  | "AIR_SHOT_DOWN"     // Máy bay bị bắn hạ bởi vùng phòng không (@”)
  | "AIR_EXCHANGE"      // Máy bay 1 đổi 1 trong vùng phòng không (><)
  | "HERO_PROMOTION"    // Quân được phong Anh hùng (tự động)
  | "HQ_DESTROYED"      // Sở chỉ huy bị phá hủy, Tư lệnh lộ diện
  | "GAME_OVER";        // Trận đấu kết thúc (^ hoặc !!)

// Chế độ chơi
type GameMode = "HUMAN_VS_AI" | "AI_VS_AI" | "HUMAN_VS_HUMAN";

// Trạng thái trận đấu
type GameStatus = "NOT_STARTED" | "IN_PROGRESS" | "GAME_OVER";

// Giai đoạn trong lượt (Turn Phase)
type TurnPhase = 
  | "NORMAL"            // Lượt thông thường (1 hành động duy nhất)
  | "STACK_ACTIVE";     // Đang trong chuỗi hành động của tổ hợp cõng quân (tối đa 3 hành động)

// Lý do kết thúc trận
type TerminationReason = 
  | "COMMANDER_CAPTURED"// Tư lệnh bị tiêu diệt (+50 điểm)
  | "TIMEOUT"           // Hết thời gian 30 phút (so điểm số)
  | "RESIGNATION"       // Một bên đầu hàng
  | "MUTUAL_DRAW"       // Hai bên đồng thuận hòa
  | "MAX_MOVES_EXCEEDED"// Quá số nước quy định của thực nghiệm
  | "RULE_VIOLATION";   // Phạm luật (Agent trả nước đi không hợp lệ)
```

### 2.2. Data Models chi tiết

#### `Position`
```json
{
  "x": 6,
  "y": 0
}
```

#### `PieceState`
```json
{
  "piece_id": "red_commander_1",
  "side": "RED",
  "type": "COMMANDER",
  "position": { "x": 6, "y": 0 },
  "is_alive": true,
  "is_hero": false,
  "carrying_piece_ids": [],
  "carried_by_id": null
}
```

#### `LegalAction`
```json
{
  "action_id": "act_m_001",
  "action_type": "MOVE",
  "piece_id": "red_infantry_1",
  "from_pos": { "x": 2, "y": 4 },
  "to_pos": { "x": 2, "y": 5 },
  "target_piece_id": null,
  "notation": "B [4 ; 2] _ [5 ; 2]",
  "description": "Bộ binh đi thẳng 1 đoạn qua sông sâu"
}
```

#### `GameEvent`
```json
{
  "event_id": "evt_012",
  "event_type": "PIECE_CAPTURED",
  "actor_id": "red_aircraft_1",
  "target_id": "blue_militia_1",
  "notation": "K [1 ; 4] _@_ D [4 ; 6]",
  "score_delta": { "RED": 10, "BLUE": 0 },
  "details": {
    "is_bomb_stand": true,
    "hero_promoted": []
  }
}
```

---

## 3. Danh mục Endpoints

### 3.1. Hệ thống & Giám sát

#### `GET /health`
Kiểm tra trạng thái sẵn sàng của dịch vụ API và Game Engine.

- **Response:** `200 OK`
```json
{
  "status": "ok",
  "version": "1.0.0",
  "engine_status": "ready",
  "active_games": 3
}
```

---

### 3.2. Quản lý AI Agents

#### `GET /api/v1/agents`
Liệt kê danh sách các Agent có sẵn trong hệ thống (đã cài đặt và kiểm thử, không trả về placeholder).

- **Response:** `200 OK`
```json
{
  "agents": [
    {
      "agent_id": "random_agent",
      "name": "Random Agent",
      "version": "1.0.0",
      "description": "Tác tử chọn ngẫu nhiên trong danh sách nước đi hợp lệ",
      "capabilities": ["HUMAN_VS_AI", "AI_VS_AI"],
      "config_schema": {
        "seed": { "type": "integer", "default": 42 }
      }
    },
    {
      "agent_id": "heuristic_agent",
      "name": "Heuristic Agent",
      "version": "1.0.0",
      "description": "Tác tử đánh giá theo bảng điểm quân cờ và an toàn Tư lệnh",
      "capabilities": ["HUMAN_VS_AI", "AI_VS_AI"],
      "config_schema": {
        "thinking_time_ms": { "type": "integer", "default": 500 }
      }
    }
  ]
}
```

---

### 3.3. Quản lý Phiên chơi (Game Sessions)

#### `POST /api/v1/games`
Khởi tạo một ván cờ mới (Người vs AI, AI vs AI, hoặc Người vs Người).

- **Request:**
```json
{
  "mode": "HUMAN_VS_AI",
  "player_side": "RED",
  "red_agent_id": null,
  "blue_agent_id": "heuristic_agent",
  "time_limit_seconds": 1800,
  "agent_config": {
    "seed": 12345,
    "max_depth": 3
  }
}
```

- **Response:** `201 Created`
```json
{
  "game_id": "game-20261025-a1b2c3",
  "mode": "HUMAN_VS_AI",
  "status": "IN_PROGRESS",
  "side_to_move": "RED",
  "turn_index": 1,
  "action_index": 1,
  "turn_phase": "NORMAL",
  "state_version": 1,
  "scores": { "RED": 0, "BLUE": 0 },
  "remaining_time_ms": { "RED": 1800000, "BLUE": 1800000 },
  "pieces": [
    {
      "piece_id": "red_commander_1",
      "side": "RED",
      "type": "COMMANDER",
      "position": { "x": 6, "y": 0 },
      "is_alive": true,
      "is_hero": false,
      "carrying_piece_ids": [],
      "carried_by_id": null
    }
  ],
  "legal_actions": [
    {
      "action_id": "act_001",
      "action_type": "MOVE",
      "piece_id": "red_infantry_1",
      "from_pos": { "x": 2, "y": 4 },
      "to_pos": { "x": 2, "y": 5 },
      "target_piece_id": null,
      "notation": "B [4 ; 2] _ [5 ; 2]",
      "description": "Bộ binh tiến 1 đoạn"
    }
  ],
  "can_end_turn": false
}
```

---

#### `GET /api/v1/games/{game_id}`
Lấy trạng thái hiện tại của ván đấu cùng danh sách toàn bộ các nước đi hợp lệ cho phe đến lượt.

- **Response:** `200 OK` (Cấu trúc tương tự `POST /api/v1/games`)
- **Error:** `404 Not Found` nếu `game_id` không tồn tại.

---

#### `POST /api/v1/games/{game_id}/actions`
Gửi một hành động (nước đi, ăn quân, lên xe, tách quân, cõng quân).

- **Request:**
```json
{
  "state_version": 1,
  "action_type": "CAPTURE_STAND",
  "piece_id": "red_aircraft_1",
  "from_pos": { "x": 4, "y": 1 },
  "to_pos": { "x": 6, "y": 4 },
  "target_piece_id": "blue_militia_1"
}
```

- **Response:** `200 OK`
```json
{
  "game_id": "game-20261025-a1b2c3",
  "status": "IN_PROGRESS",
  "state_version": 2,
  "side_to_move": "RED",
  "turn_index": 1,
  "action_index": 2,
  "turn_phase": "STACK_ACTIVE",
  "active_stack_id": "red_tank_1",
  "remaining_stack_actions": 2,
  "can_end_turn": true,
  "applied_action": {
    "action_type": "CAPTURE_STAND",
    "piece_id": "red_aircraft_1",
    "notation": "K [1 ; 4] _@_ D [4 ; 6]"
  },
  "events": [
    {
      "event_type": "PIECE_CAPTURED",
      "actor_id": "red_aircraft_1",
      "target_id": "blue_militia_1",
      "notation": "K [1 ; 4] _@_ D [4 ; 6]",
      "score_delta": { "RED": 10, "BLUE": 0 }
    }
  ],
  "scores": { "RED": 10, "BLUE": 0 },
  "pieces": [ /* danh sách toàn bộ 38 quân cờ cập nhật */ ],
  "legal_actions": [ /* các hành động tiếp theo của tổ hợp hoặc END_TURN */ ],
  "is_game_over": false,
  "result": null
}
```
- **Error:** `409 Conflict` nếu nước đi trái luật cờ hoặc sai lượt.

---

#### `POST /api/v1/games/{game_id}/end-turn`
Chủ động kết thúc lượt tổ hợp cõng quân khi chưa dùng hết 3 hành động tối đa.

- **Request:**
```json
{
  "state_version": 2
}
```

- **Response:** `200 OK`
Chuyển `side_to_move` sang phe kế tiếp, đặt lại `turn_phase: "NORMAL"`, trả `legal_actions` cho phe mới.

---

#### `POST /api/v1/games/{game_id}/ai-step`
Kích hoạt lượt đi của AI. Dùng trong chế độ `AI_VS_AI` hoặc khi người chơi hoàn tất lượt của mình ở `HUMAN_VS_AI`.

- **Request:**
```json
{
  "time_budget_ms": 1000
}
```

- **Response:** `200 OK`
Trả về kết quả hành động mà AI đã chọn, bao gồm metadata suy nghĩ:
```json
{
  "action_taken": {
    "action_type": "MOVE",
    "piece_id": "blue_tank_1",
    "from_pos": { "x": 5, "y": 8 },
    "to_pos": { "x": 5, "y": 6 },
    "notation": "T [8 ; 5] _ [6 ; 5]"
  },
  "ai_diagnostics": {
    "agent_id": "heuristic_agent",
    "thinking_time_ms": 420,
    "nodes_searched": 1450,
    "evaluation_score": 15.5
  },
  "game_state": { /* GameState mới */ }
}
```

---

#### `POST /api/v1/games/{game_id}/undo`
Hoàn tác nước đi (chỉ khả dụng trong chế độ Người vs AI để học hỏi hoặc thử nghiệm).

- **Request:** `{}`
- **Response:** `200 OK`
Trả lại trạng thái bàn cờ trước nước đi gần nhất của Người chơi (thu hồi cả nước đi của AI nếu AI đã đi đáp trả).
- **Error:** `409 Conflict` nếu là đầu trận đấu hoặc chế độ không cho phép hoàn tác.

---

#### `POST /api/v1/games/{game_id}/resign`
Người chơi hoặc Agent chấp nhận đầu hàng.

- **Request:**
```json
{
  "side": "RED"
}
```

- **Response:** `200 OK`
```json
{
  "status": "GAME_OVER",
  "result": {
    "winner": "BLUE",
    "reason": "RESIGNATION",
    "final_scores": { "RED": 10, "BLUE": 20 }
  }
}
```

---

#### `POST /api/v1/games/{game_id}/draw`
Người chơi đề nghị hoặc chấp thuận kết thúc hòa.

- **Request:**
```json
{
  "side": "RED",
  "action": "OFFER" // hoặc "ACCEPT"
}
```

- **Response:** `200 OK`
Cập nhật trạng thái hòa trận đấu nếu cả hai bên đồng thuận.

---

### 3.4. Replays & Xuất bản biên bản

#### `GET /api/v1/replays`
Lấy danh sách các ván đấu đã được lưu trong hệ thống, hỗ trợ phân trang và bộ lọc.

- **Query Parameters:**
  - `page`: Trang hiện tại (mặc định 1)
  - `page_size`: Số bản ghi mỗi trang (mặc định 20, tối đa 100)
  - `agent_id`: Lọc theo tác tử tham gia
  - `winner`: `RED` | `BLUE` | `DRAW`

- **Response:** `200 OK`
```json
{
  "total": 45,
  "page": 1,
  "page_size": 20,
  "replays": [
    {
      "replay_id": "rep_20261025_001",
      "played_at": "2026-10-25T20:30:00Z",
      "mode": "AI_VS_AI",
      "red_player": "RandomAgent v1.0",
      "blue_player": "HeuristicAgent v1.0",
      "winner": "BLUE",
      "reason": "COMMANDER_CAPTURED",
      "total_turns": 42,
      "final_scores": { "RED": 40, "BLUE": 170 }
    }
  ]
}
```

---

#### `GET /api/v1/replays/{replay_id}`
Lấy dữ liệu đầy đủ của một trận đấu để phục vụ trình Replay Viewer trên web.

- **Response:** `200 OK`
```json
{
  "replay_id": "rep_20261025_001",
  "metadata": {
    "rules_version": "2026-10-25",
    "engine_version": "1.0.0",
    "notation_version": "COTULENH-NOTATION v1",
    "red_player": "RandomAgent",
    "blue_player": "HeuristicAgent",
    "winner": "BLUE",
    "seed": 42
  },
  "initial_positions": { /* Bố trí 38 quân khởi đầu */ },
  "action_history": [
    {
      "turn_id": 1,
      "action_index": 1,
      "side": "RED",
      "action_type": "MOVE",
      "notation": "H [1 ; 1] _ [5 ; 1]",
      "state_snapshot_hash": "hash_abc123"
    }
  ]
}
```

---

#### `GET /api/v1/replays/{replay_id}/export`
Xuất biên bản trận đấu theo định dạng văn bản dễ đọc hoặc JSON thuần.

- **Query Parameter:** `format=ctn` (mặc định) hoặc `format=json`.
- **Response (`format=ctn`):** `200 OK`, `Content-Type: text/plain; charset=utf-8`
```text
[Format "COTULENH-NOTATION"]
[Version "1"]
[Event "AI Evaluation SGU 2026"]
[Date "2026-10-25"]
[Red "RandomAgent"]
[Blue "HeuristicAgent"]
[Result "BLUE_WIN"]

1. Đỏ:   H [1 ; 1] _ [5 ; 1]
   Xanh: K [10 ; 8] _ [8 ; 6]
2. Đỏ:   B [4 ; 2] _ [5 ; 2]
   Xanh: K [8 ; 6] _@_ D [4 ; 6]
```

---

### 3.5. Báo cáo & Thống kê nghiên cứu (Statistics)

#### `GET /api/v1/statistics/summary`
Tổng hợp thống kê toàn diện từ dữ liệu ván đấu thực nghiệm đã lưu.

- **Response:** `200 OK`
```json
{
  "total_games": 120,
  "red_wins": 55,
  "blue_wins": 53,
  "draws": 12,
  "average_moves_per_game": 38.4,
  "average_duration_seconds": 412.5,
  "termination_breakdown": {
    "COMMANDER_CAPTURED": 98,
    "TIMEOUT": 14,
    "RESIGNATION": 8
  }
}
```

---

#### `GET /api/v1/statistics/matchups`
Thống kê đối đầu trực tiếp giữa các cặp Agent để phục vụ viết báo cáo học thuật.

- **Response:** `200 OK`
```json
{
  "matchups": [
    {
      "red_agent": "RandomAgent",
      "blue_agent": "HeuristicAgent",
      "total_matches": 50,
      "red_wins": 4,
      "blue_wins": 44,
      "draws": 2,
      "red_point_ratio": 0.10,
      "avg_thinking_time_ms": {
        "RandomAgent": 2,
        "HeuristicAgent": 350
      }
    }
  ]
}
```

---

## 4. Mô hình xử lý lỗi (Error Model & Error Codes)

### Cấu trúc phản hồi lỗi chuẩn:
```json
{
  "error": {
    "code": "ILLEGAL_MOVE_PATH_BLOCKED",
    "message": "Đường di chuyển bị cản trở bởi quân cờ khác trên bàn cờ.",
    "details": {
      "piece_id": "red_tank_1",
      "blocked_at": { "x": 5, "y": 4 }
    }
  }
}
```

### Bảng danh mục mã lỗi chuẩn hóa (`error.code`):

| Mã lỗi (`code`) | HTTP Status | Ý nghĩa |
|---|:---:|---|
| `GAME_NOT_FOUND` | 404 | Không tìm thấy phiên chơi với ID đã cung cấp. |
| `REPLAY_NOT_FOUND` | 404 | Không tìm thấy bản ghi replay. |
| `AGENT_NOT_FOUND` | 404 | Agent yêu cầu chưa được đăng ký trong hệ thống. |
| `STALE_STATE_VERSION` | 409 | `state_version` gửi lên không khớp (xung đột thao tác song song). |
| `NOT_PLAYER_TURN` | 409 | Phe gửi hành động không phải phe đang đến lượt. |
| `GAME_ALREADY_FINISHED` | 409 | Trận đấu đã kết thúc, không thể thực hiện thêm hành động. |
| `ILLEGAL_ACTION` | 409 | Nước đi không nằm trong danh mục `legal_actions` của Engine. |
| `ILLEGAL_PATH_BLOCKED` | 409 | Đường di chuyển bị cản (áp dụng cho xe tăng, bộ binh...). |
| `COMMANDER_FACING_VIOLATION` | 409 | Nước đi làm hai Tư lệnh đối mặt trực tiếp không có vật chắn. |
| `INVALID_STACK_ACTION` | 409 | Hành động không thuộc tổ hợp cõng quân đang kích hoạt. |
| `STACK_ACTION_LIMIT_EXCEEDED`| 409 | Đã đạt tối đa 3 hành động trong một lượt tổ hợp. |
| `TRANSPORT_CAPACITY_EXCEEDED`| 409 | Vượt quá sức chứa phương tiện cõng (tính cả quân cõng lồng nhau).|
| `CANNOT_UNDO` | 409 | Không thể hoàn tác (không có lịch sử hoặc không hỗ trợ ở chế độ này). |
| `AGENT_TIMEOUT` | 504 | Tác tử AI vượt quá thời gian suy nghĩ cho phép. |
| `AGENT_INTERNAL_ERROR` | 500 | Tác tử AI phát sinh ngoại lệ nội bộ hoặc crash. |

---

## 5. Quy định bảo đảm toàn vẹn dữ liệu (Data Integrity)

1. **Không tạo số liệu ảo:** Không bao giờ trả về số trận thắng hoặc chỉ số giả lập nếu cơ sở dữ liệu chưa có ván đấu thật tương ứng.
2. **Kiểm tra tính tái lập (Reproducibility):** Đối với các trận đấu của Agent có yếu tố ngẫu nhiên, hệ thống bắt buộc lưu trữ tham số `seed`. Khi chạy lại với cùng `seed` và cấu hình, chuỗi nước đi phải đồng nhất 100%.
3. **Phân biệt trận lỗi:** Trận đấu gặp lỗi crash của Agent hoặc timeout không bao giờ được tính là một trận thắng bình thường, mà phải ghi nhận trạng thái lỗi để phục vụ thống kê độ tin cậy của thuật toán.
