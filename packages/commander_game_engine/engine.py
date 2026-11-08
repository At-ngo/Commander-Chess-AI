# packages/commander_game_engine/engine.py
"""Bộ chuyển trạng thái (transition engine) cho Cờ Tư Lệnh.

Nguyên tắc kiến trúc
-------------------
* ``rules.py`` quyết định nước đi có hợp lệ hay không.
* ``engine.py`` tạo BẢN SAO GameState rồi mới áp dụng hành động.
* Không sửa ``GameState`` do người gọi truyền vào.
* Không tự cho phép hành động mà Rules từ chối hoặc chưa hỗ trợ.

Phiên bản nền tảng này thực thi MOVE, CAPTURE, BOMBARD khi Rules đã duyệt.
Các ca phòng không, tổ hợp, BOARD/PICKUP, trú ẩn trong Sở chỉ huy
và lượt ghép 1–3 hành động cần thêm mô hình trạng thái / bộ giải riêng.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .actions import ActionType, AtomicAction, TurnCommand, TurnCommandType
from .game_state import GameState, PieceType, Player
from . import rules


# Điểm quân theo đặc tả. Chưa gán điểm cho HEADQUARTERS vì luật chưa chốt.
PIECE_POINTS: dict[PieceType, int] = {
    PieceType.COMMANDER: 100,
    PieceType.INFANTRY: 10,
    PieceType.MILITIA: 10,
    PieceType.TANK: 20,
    PieceType.ARTILLERY: 30,
    PieceType.ANTI_AIRCRAFT: 10,
    PieceType.MISSILE: 20,
    PieceType.AIRCRAFT: 40,
    PieceType.NAVY: 80,
    PieceType.ENGINEER: 10,
}


class EngineEventType(Enum):
    """Các sự kiện giúp frontend và notebook giải thích diễn biến ván."""
    MOVED = "moved"                  # Quân thay đổi tọa độ
    CAPTURED = "captured"            # Quân đối phương bị tiêu diệt
    CARGO_LOST = "cargo_lost"        # Quân chở bị tiêu diệt theo phương tiện
    POINTS_AWARDED = "points_awarded"# Ghi điểm từ quân bị tiêu diệt
    HERO_PROMOTED = "hero_promoted"  # Phong Anh hùng khi thỏa điều kiện đã rõ
    TURN_CHANGED = "turn_changed"    # Đổi phe đến lượt
    GAME_WON = "game_won"            # Kết thúc ván do Tư lệnh bị diệt


@dataclass(frozen=True)
class EngineEvent:
    """Một sự kiện sau khi engine áp dụng thành công hành động."""
    event_type: EngineEventType             # Loại sự kiện
    piece_id: str | None = None             # ID quân liên quan
    detail: str = ""                        # Diễn giải tiếng Việt
    points: int = 0                        # Điểm cộng bởi sự kiện này


@dataclass
class EngineResult:
    """Kết quả áp dụng hành động (luôn chứa trạng thái độc lập).

    Khi accepted=False, state là bản sao KHÔNG thay đổi của đầu vào.
    Khi accepted=True, state là trạng thái mới sau hành động.
    """
    accepted: bool                         # Hành động được chấp nhận?
    state: GameState                       # Bản sao trạng thái sau xử lý
    verdict: rules.RuleResult              # Kết quả kiểm tra luật
    events: list[EngineEvent] = field(default_factory=list)
    winner: Player | None = None           # Phe thắng nếu Tư lệnh bị tiêu diệt
    terminal: bool = False                 # Đã kết thúc do Tư lệnh bị tiêu diệt?


def _opponent(player: Player) -> Player:
    """Xác định phe còn lại."""
    return Player.BLUE if player == Player.RED else Player.RED


def _fail(state: GameState, code: rules.RuleCode, reason: str) -> EngineResult:
    """Tạo kết quả từ chối, không cho phép thay đổi trạng thái nguồn."""
    return EngineResult(False, deepcopy(state), rules.reject(code, reason))


def _children(state: GameState, parent_id: str) -> set[str]:
    """Lấy toàn bộ quân con/cháu đang được chở, có phát hiện chu trình."""
    collected: set[str] = set()
    visiting: set[str] = set()

    def walk(pid: str) -> None:
        if pid in visiting:
            raise ValueError("Phát hiện chu trình chở quân trong GameState.")
        visiting.add(pid)
        p = state.pieces[pid]
        # Đối chiếu cả cargo và carried_by: không xử lý trạng thái lệch nhau.
        direct_from_parent = {q.id for q in state.pieces.values() if q.carried_by == pid}
        direct_from_cargo = set(p.cargo)
        if len(p.cargo) != len(direct_from_cargo) or direct_from_parent != direct_from_cargo:
            raise ValueError(f"Quan hệ cargo/carried_by không nhất quán tại {pid}.")
        for child_id in p.cargo:
            if child_id not in state.pieces:
                raise ValueError(f"Không tìm thấy quân được chở: {child_id}.")
            if child_id in collected or child_id == parent_id:
                raise ValueError("Phát hiện quân xuất hiện lặp trong tổ hợp vận chuyển.")
            collected.add(child_id)
            walk(child_id)
        visiting.remove(pid)

    walk(parent_id)
    return collected


def _casualties(state: GameState, target_id: str) -> tuple[str, ...]:
    """Tính danh sách quân bị loại: phương tiện cùng toàn bộ quân con cháu."""
    return (target_id, *sorted(_children(state, target_id)))


def _award_points(state: GameState, winner: Player, points: int) -> None:
    """Cộng điểm nếu GameState có thuộc tính scores theo dạng dict.

    Không tự tạo trường scores khi dữ liệu thực tế chưa có. Event vẫn ghi điểm.
    """
    scores = getattr(state, "scores", None)
    if isinstance(scores, dict):
        # Không trộn key Player và key string trong cùng dict.
        key: Any = winner if winner in scores or not scores else winner.value
        if key not in scores and scores and all(isinstance(k, str) for k in scores):
            key = winner.value
        scores[key] = scores.get(key, 0) + points


def _mark_ended(state: GameState, winner: Player) -> None:
    """Đánh dấu kết thúc khi enum GameStatus có giá trị được hỗ trợ.

    Đối với enum chưa có trạng thái thắng/thua, EngineResult.terminal/winner
    vẫn mô tả kết quả; phải mở rộng GameState trước khi tích hợp AI.
    """
    status = getattr(state, "game_status", None)
    enum_cls = type(status)
    if issubclass(enum_cls, Enum):
        for name in ("RED_WINS", "BLUE_WINS", "RED_WIN", "BLUE_WIN", "FINISHED", "GAME_OVER"):
            if name.startswith("RED") and winner != Player.RED:
                continue
            if name.startswith("BLUE") and winner != Player.BLUE:
                continue
            if name in enum_cls.__members__:
                state.game_status = enum_cls[name]
                break


def _promote_last_survivor(state: GameState, events: list[EngineEvent]) -> None:
    """Q10 Anh hùng: quân bảo vệ cuối cùng (ngoại trừ Sở chỉ huy) được phong Anh hùng.
    Khi chỉ còn đúng 1 Sở chỉ huy và Tư lệnh, Sở chỉ huy cũng được phong thành Bộ binh Anh hùng.
    Nếu còn 2 Sở chỉ huy thì không phong (DEC-015).
    """
    for player in (Player.RED, Player.BLUE):
        alive = [p for p in state.pieces.values() if p.owner == player]
        non_cmd_non_hq = [p for p in alive if p.piece_type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS)]
        hq_pieces = [p for p in alive if p.piece_type == PieceType.HEADQUARTERS]
        if len(non_cmd_non_hq) == 1 and not non_cmd_non_hq[0].is_heroic:
            hero = non_cmd_non_hq[0]
            hero.is_heroic = True
            events.append(EngineEvent(EngineEventType.HERO_PROMOTED, hero.id,
                                      "Tự phong Anh hùng cho quân bảo vệ cuối cùng (ngoại trừ Sở chỉ huy)."))
        elif len(non_cmd_non_hq) == 0 and len(hq_pieces) == 1 and not hq_pieces[0].is_heroic:
            hero = hq_pieces[0]
            hero.is_heroic = True
            events.append(EngineEvent(EngineEventType.HERO_PROMOTED, hero.id,
                                      "Tự phong Sở chỉ huy duy nhất thành Bộ binh Anh hùng khi chỉ còn 1 Sở chỉ huy và Tư lệnh."))


def apply_action(state: GameState, action: AtomicAction) -> EngineResult:
    """Kiểm tra và áp dụng một hành động đơn, tạo GameState mới.

    Chỉ thực thi MOVE, CAPTURE, BOMBARD khi rules.validate_action duyệt.
    Không tự giải các trường hợp chưa được Rules hỗ trợ.
    """
    # Ngăn nhập hành động đơn vào giữa lượt ghép chưa được Engine hỗ trợ.
    if getattr(state, "_engine_terminal", False):
        return _fail(state, rules.RuleCode.GAME_OVER, "Ván đã kết thúc do Tư lệnh bị tiêu diệt.")
    if getattr(state, "compound_turn", None) is not None:
        return _fail(state, rules.RuleCode.UNSUPPORTED,
                     "Engine chưa tích hợp chuyển trạng thái cho lượt ghép đang diễn ra.")
    if action.action_type not in (ActionType.MOVE, ActionType.CAPTURE, ActionType.BOMBARD):
        return _fail(state, rules.RuleCode.UNSUPPORTED,
                     "Engine hiện chỉ thực thi MOVE, CAPTURE, BOMBARD; "
                     "BOMB/BOARD/PICKUP cần xử lý trạng thái đặc biệt.")

    verdict = rules.validate_action(state, action)
    if not verdict.valid:
        return EngineResult(False, deepcopy(state), verdict)

    actor = state.pieces[action.piece_id]
    target = state.get_piece_at(action.end) if action.action_type != ActionType.MOVE else None
    to_remove: tuple[str, ...] = ()
    if target is not None:
        try:
            to_remove = _casualties(state, target.id)
        except ValueError as exc:
            return _fail(state, rules.RuleCode.INVALID_TRANSPORT, str(exc))
        if any(state.pieces[pid].piece_type == PieceType.HEADQUARTERS for pid in to_remove):
            return _fail(state, rules.RuleCode.UNSUPPORTED,
                         "Điểm Sở chỉ huy và quan hệ trú ẩn chưa được xác định đầy đủ.")

    next_state = deepcopy(state)
    events: list[EngineEvent] = []
    player = next_state.current_player

    if to_remove:
        # Loại quân theo ID, không dựa vào tọa độ của quân được chở.
        total = 0
        for pid in to_remove:
            victim = next_state.pieces[pid]
            total += PIECE_POINTS[victim.piece_type] + (10 if victim.is_heroic else 0)
            kind = EngineEventType.CAPTURED if pid == target.id else EngineEventType.CARGO_LOST
            events.append(EngineEvent(kind, pid,
                                      "Bị ăn quân." if pid == target.id else "Bị loại theo phương tiện."))
        for pid in to_remove:
            del next_state.pieces[pid]
        # Điểm thưởng cho việc diệt Tư lệnh được tính riêng.
        commander_killed = any(state.pieces[pid].piece_type == PieceType.COMMANDER
                               for pid in to_remove)
        if commander_killed:
            total += 50
        _award_points(next_state, player, total)
        events.append(EngineEvent(EngineEventType.POINTS_AWARDED, detail="Cộng điểm tiêu diệt.", points=total))
    else:
        commander_killed = False

    # MOVE và CAPTURE thế chỗ. BOMBARD bắn tại chỗ, giữ nguyên tọa độ.
    if action.action_type in (ActionType.MOVE, ActionType.CAPTURE):
        next_state.pieces[action.piece_id].position = action.end
        events.append(EngineEvent(EngineEventType.MOVED, action.piece_id,
                                  f"Tới tọa độ {action.end}."))

    if commander_killed:
        next_state._engine_terminal = True  # Chặn các bước Engine tiếp theo, kể cả khi GameStatus chưa đủ trạng thái.
        next_state._engine_winner = player
        _mark_ended(next_state, player)
        events.append(EngineEvent(EngineEventType.GAME_WON, detail=f"Phe {player.value} tiêu diệt Tư lệnh."))
        return EngineResult(True, next_state, verdict, events, winner=player, terminal=True)

    _promote_last_survivor(next_state, events)
    next_state.current_player = _opponent(player)
    if hasattr(next_state, "turn_number"):
        next_state.turn_number += 1
    if hasattr(next_state, "action_count"):
        next_state.action_count += 1
    events.append(EngineEvent(EngineEventType.TURN_CHANGED, detail=f"Đến lượt {_opponent(player).value}."))
    return EngineResult(True, next_state, verdict, events)


def apply_turn_command(state: GameState, command: TurnCommand) -> EngineResult:
    """Điều khiển lượt ghép; chưa thực thi khi thiếu trạng thái triển khai.

    Không dùng END_TURN để bỏ qua kiểm tra Q20 hoặc tự xác nhận tổ hợp.
    """
    if command.command_type not in (TurnCommandType.CONFIRM_DEPLOYMENT, TurnCommandType.END_TURN):
        return _fail(state, rules.RuleCode.INVALID_ACTION, "Lệnh điều khiển lượt không hợp lệ.")
    return _fail(state, rules.RuleCode.UNSUPPORTED,
                 "Cần trạng thái lượt ghép, phương án chở còn lại và kiểm tra Q20 trước khi thực thi lệnh.")


def preview_action(state: GameState, action: AtomicAction) -> EngineResult:
    """Mô phỏng một hành động mà không thay đổi trạng thái gốc (alias)."""
    return apply_action(state, action)


__all__ = [
    "PIECE_POINTS", "EngineEventType", "EngineEvent", "EngineResult",
    "apply_action", "apply_turn_command", "preview_action",
]
