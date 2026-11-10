# packages/commander_game_engine/move_generator.py
"""Sinh các hành động hợp lệ Cờ Tư Lệnh từ GameState hiện tại.

Nguyên tắc:
- KHÔNG thay đổi GameState.
- Chỉ trả về hành động đã qua kiểm tra hình học/địa hình/vật cản/vận chuyển (`validate_structural_action`)
  VÀ kiểm tra an toàn Tư lệnh sau mô phỏng (`preview_action_safety`).
- Hỗ trợ đầy đủ cả tổ hợp cõng quân (BOARD, PICKUP, triển khai từ phương tiện,
  rời đi bỏ lại cargo `carry_cargo=False`, và `TurnCommand(END_TURN)` trong lượt ghép).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .actions import ActionType, AtomicAction, TurnCommand, TurnCommandType
from .board import Position
from .game_state import GameState, Piece, PieceType
from . import engine, rules


@dataclass(frozen=True)
class GenerationIssue:
    """Ghi lại một đề xuất bị rules từ chối vì chưa được hỗ trợ."""

    action: AtomicAction               # Hành động được thử
    code: rules.RuleCode               # Mã lỗi từ rules.py
    reason: str                        # Mô tả từ rules.py


@dataclass
class GenerationResult:
    """Kết quả sinh hành động và các trường hợp chưa hỗ trợ."""

    actions: list[AtomicAction | TurnCommand] = field(default_factory=list)
    unsupported: list[GenerationIssue] = field(default_factory=list)


def _physical_origin(state: GameState, piece: Piece) -> Position | None:
    """Tìm tọa độ gốc (kể cả quân chở lồng nhau)."""
    return rules._origin(state, piece)


_ORTH_DIRS: tuple[tuple[int, int], ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))
_ALL_DIRS: tuple[tuple[int, int], ...] = (
    (-1, 0), (1, 0), (0, -1), (0, 1),
    (-1, -1), (-1, 1), (1, -1), (1, 1),
)


def _candidates_for_piece(state: GameState, piece: Piece):
    """Sinh ứng viên hợp lý dọc theo tia từ tọa độ thực tế; xác thực cuối cùng thuộc rules + engine safety."""
    start = _physical_origin(state, piece)
    if start is None or not state.board.is_valid_position(start):
        return

    base_mode, base_reach = rules._BASE_MOVE[piece.piece_type]
    if piece.piece_type == PieceType.HEADQUARTERS:
        if not piece.is_heroic:
            return
        dirs = _ALL_DIRS
        max_reach = 2
    elif piece.piece_type == PieceType.COMMANDER:
        dirs = _ALL_DIRS if piece.is_heroic else _ORTH_DIRS
        max_reach = max(state.board.ROWS, state.board.COLS) - 1
    else:
        allow_diag = (
            piece.is_heroic
            or base_mode == "all"
            or piece.piece_type == PieceType.MISSILE
        )
        dirs = _ALL_DIRS if allow_diag else _ORTH_DIRS
        max_reach = base_reach + (1 if piece.piece_type == PieceType.NAVY else 0) + (1 if piece.is_heroic else 0)

    can_split_solo = (
        piece.carried_by is None
        and piece.piece_type != PieceType.HEADQUARTERS
        and bool(piece.cargo)
        and rules.can_carrier_leave_cargo_behind(state, piece)
    )

    sy, sx = start
    rows, cols = state.board.ROWS, state.board.COLS
    for dy, dx in dirs:
        for step in range(1, max_reach + 1):
            y = sy + dy * step
            x = sx + dx * step
            if not (0 <= y < rows and 0 <= x < cols):
                break
            end: Position = (y, x)
            target = state.get_piece_at(end)
            if target is None:
                if rules.movement_shape(piece, end, capture=False, origin=start).valid:
                    yield AtomicAction(
                        action_type=ActionType.MOVE,
                        piece_id=piece.id,
                        start=start,
                        end=end,
                        carry_cargo=True,
                    )
                    if can_split_solo:
                        yield AtomicAction(
                            action_type=ActionType.MOVE,
                            piece_id=piece.id,
                            start=start,
                            end=end,
                            carry_cargo=False,
                        )
            elif target.owner != piece.owner:
                if rules.movement_shape(piece, end, capture=True, origin=start).valid:
                    yield AtomicAction(
                        action_type=ActionType.CAPTURE,
                        piece_id=piece.id,
                        start=start,
                        end=end,
                        target_piece_id=target.id,
                        carry_cargo=True,
                    )
                    if can_split_solo:
                        yield AtomicAction(
                            action_type=ActionType.CAPTURE,
                            piece_id=piece.id,
                            start=start,
                            end=end,
                            target_piece_id=target.id,
                            carry_cargo=False,
                        )
                    stand_mode = ActionType.BOMB if piece.piece_type == PieceType.AIRCRAFT else ActionType.BOMBARD
                    yield AtomicAction(
                        action_type=stand_mode,
                        piece_id=piece.id,
                        start=start,
                        end=end,
                        target_piece_id=target.id,
                    )
            else:
                # Quân đồng minh ở đích: lên xe (BOARD) hoặc đón quân (PICKUP)
                if rules.movement_shape(piece, end, capture=False, origin=start).valid:
                    if rules.can_board(state, piece, target).valid:
                        yield AtomicAction(
                            action_type=ActionType.BOARD,
                            piece_id=piece.id,
                            start=start,
                            end=end,
                            target_piece_id=target.id,
                            carrier_id=target.id,
                        )
                    if (
                        piece.carried_by is None
                        and target.carried_by is None
                        and rules.can_board(state, target, piece).valid
                    ):
                        yield AtomicAction(
                            action_type=ActionType.PICKUP,
                            piece_id=piece.id,
                            start=start,
                            end=end,
                            target_piece_id=target.id,
                            passenger_id=target.id,
                        )


def _piece_eligible_in_turn(state: GameState, piece: Piece) -> bool:
    """Lọc nhanh quân có thể hành động trong lượt / lượt ghép / ngoại lệ Sở chỉ huy duy nhất."""
    if getattr(state.game_status, "value", "ongoing") != "ongoing":
        return False
    if piece.owner != state.current_player:
        return False
    trap_cmd_id = rules.delayed_solitary_hq_commander_id(state, state.current_player)
    if trap_cmd_id is not None and piece.id != trap_cmd_id:
        return False
    if state.compound_turn is not None:
        ct = state.compound_turn
        if ct.actions_used >= 3 or piece.id in ct.acted_piece_ids:
            return False
        root_at_origin = state.get_piece_at(ct.origin)
        if root_at_origin is None or root_at_origin.owner != state.current_player:
            return False
        eligible_ids = {root_at_origin.id, *rules.all_carried_ids(state, root_at_origin.id)}
        if piece.id not in eligible_ids:
            return False
    return True


def generate_piece_actions(
    state: GameState,
    piece_id: str,
    *,
    include_unsupported: bool = False,
) -> list[AtomicAction] | GenerationResult:
    """Sinh toàn bộ hành động hợp lệ (đã lọc an toàn Tư lệnh) của một quân cờ."""
    piece = state.pieces.get(piece_id)
    if piece is None:
        raise ValueError(f"Không tìm thấy quân: {piece_id}")
    result = GenerationResult()
    if not _piece_eligible_in_turn(state, piece):
        return result if include_unsupported else result.actions

    for action in _candidates_for_piece(state, piece):
        verdict = rules.validate_structural_action(state, action)
        if verdict.valid:
            safety = engine.preview_action_safety(state, action)
            if safety.valid:
                result.actions.append(action)
        elif include_unsupported and verdict.code is rules.RuleCode.UNSUPPORTED:
            result.unsupported.append(
                GenerationIssue(action, verdict.code, verdict.reason)
            )
    return result if include_unsupported else result.actions


def generate_legal_actions(
    state: GameState,
    *,
    include_unsupported: bool = False,
) -> list[AtomicAction | TurnCommand] | GenerationResult:
    """Sinh tất cả hành động hợp lệ cho phe đến lượt (bao gồm tổ hợp và END_TURN)."""
    summary = GenerationResult()
    if getattr(state.game_status, "value", "ongoing") != "ongoing" or getattr(state, "_engine_terminal", False):
        return summary if include_unsupported else summary.actions

    for piece in state.pieces.values():
        if not _piece_eligible_in_turn(state, piece):
            continue
        generated = generate_piece_actions(
            state, piece.id, include_unsupported=include_unsupported
        )
        if include_unsupported:
            summary.actions.extend(generated.actions)
            summary.unsupported.extend(generated.unsupported)
        else:
            summary.actions.extend(generated)

    if state.compound_turn is not None:
        summary.actions.append(TurnCommand(TurnCommandType.END_TURN))

    return summary if include_unsupported else summary.actions


def has_legal_action(state: GameState) -> bool:
    """Kiểm tra nhanh xem phe đến lượt còn ít nhất 1 nước đi hợp lệ hay không."""
    if getattr(state.game_status, "value", "ongoing") != "ongoing" or getattr(state, "_engine_terminal", False):
        return False
    if state.compound_turn is not None:
        return True
    for piece in state.pieces.values():
        if not _piece_eligible_in_turn(state, piece):
            continue
        for action in _candidates_for_piece(state, piece):
            if rules.validate_structural_action(state, action).valid:
                if engine.preview_action_safety(state, action).valid:
                    return True
    return False


__all__ = [
    "GenerationIssue",
    "GenerationResult",
    "generate_piece_actions",
    "generate_legal_actions",
    "has_legal_action",
]
