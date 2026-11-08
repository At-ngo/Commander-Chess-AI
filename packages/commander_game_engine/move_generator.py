# packages/commander_game_engine/move_generator.py
"""Sinh các đề xuất hành động Cờ Tư Lệnh từ GameState hiện tại.

Nguyên tắc:
- KHÔNG thay đổi GameState; KHÔNG tự quyết định luật.
- Luật hình học và hành động được xác thực bởi rules.py.
- Chỉ trả về nước đi đã được rules.validate_action() chấp nhận.
- Trường hợp luật chưa hỗ trợ sẽ được báo trong diagnostics (không coi là hợp lệ).

Giới hạn hiện tại:
- rules.validate_action chưa duyệt BOARD/PICKUP, máy bay và quân đang được chở.
- Chuỗi lượt ghép cần state trung gian do engine tạo và xác minh khả năng hoàn tất.
- Không giả tạo nước đi của các trường hợp chưa được rules hỗ trợ.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .actions import ActionType, AtomicAction
from .board import Position
from .game_state import GameState, Piece, Player
from . import rules


# BOMBARD/BOMB/CAPTURE chỉ là đề xuất kiểu hành động; rules kiểm tra ý nghĩa.
_ATTACK_MODES: tuple[ActionType, ...] = (
    ActionType.CAPTURE, ActionType.BOMB, ActionType.BOMBARD
)


@dataclass(frozen=True)
class GenerationIssue:
    """Ghi lại một đề xuất bị rules từ chối vì chưa được hỗ trợ."""

    action: AtomicAction               # Hành động được thử
    code: rules.RuleCode               # Mã lỗi từ rules.py
    reason: str                        # Mô tả từ rules.py


@dataclass
class GenerationResult:
    """Kết quả sinh hành động và các trường hợp chưa hỗ trợ."""

    actions: list[AtomicAction] = field(default_factory=list)
    unsupported: list[GenerationIssue] = field(default_factory=list)


def _physical_origin(state: GameState, piece: Piece) -> Position | None:
    """Tìm tọa độ gốc (kể cả quân chở lồng nhau), chỉ để sinh đề xuất."""
    seen: set[str] = set()
    current = piece
    while current.carried_by is not None:
        if current.id in seen:
            return None
        seen.add(current.id)
        parent = state.pieces.get(current.carried_by)
        if parent is None:
            return None
        current = parent
    return current.position


def _candidates_for_piece(state: GameState, piece: Piece):
    """Sinh ứng viên từ tọa độ trên bàn; KHÔNG tự kết luận hợp lệ.

    Dùng rules.movement_shape() để lọc hình học trước, giúp tránh tạo
    ứng viên vô nghĩa, nhưng việc duyệt cuối cùng là rules.validate_action().
    """
    start = _physical_origin(state, piece)
    if start is None or not state.board.is_valid_position(start):
        return
    for y in range(state.board.ROWS):
        for x in range(state.board.COLS):
            end: Position = (y, x)
            if end == start:
                continue
            target = state.get_piece_at(end)
            if target is None:
                # Chỉ sinh MOVE đến vị trí trống.
                if rules.movement_shape(piece, end, capture=False, origin=start).valid:
                    yield AtomicAction(
                        action_type=ActionType.MOVE,
                        piece_id=piece.id,
                        start=start,
                        end=end,
                    )
            elif target.owner != piece.owner:
                # Kiểm tra phạm vi từng hình thức tấn công tại rules.py.
                if rules.movement_shape(piece, end, capture=True, origin=start).valid:
                    for mode in _ATTACK_MODES:
                        yield AtomicAction(
                            action_type=mode,
                            piece_id=piece.id,
                            start=start,
                            end=end,
                            target_piece_id=target.id,
                        )
            else:
                # Quân đồng minh ở đích: BOARD/PICKUP hiện do rules khác xử lý;
                # không tự coi là MOVE hợp lệ và không tự tạo quan hệ chở.
                continue


def generate_piece_actions(
    state: GameState,
    piece_id: str,
    *,
    include_unsupported: bool = False,
) -> list[AtomicAction] | GenerationResult:
    """Sinh hành động hợp lệ của một quân theo phiên bản rules hiện có.

    Với quân đang được chở, rules hiện trả UNSUPPORTED; không tự triển khai.
    Khi include_unsupported=True, trả thêm danh sách các đề xuất chưa được
    rules hỗ trợ để phân tích trong notebook, không phải nước đi hợp lệ.
    """
    piece = state.pieces.get(piece_id)
    if piece is None:
        raise ValueError(f"Không tìm thấy quân: {piece_id}")
    result = GenerationResult()
    if piece.owner != state.current_player:
        return result if include_unsupported else result.actions

    for action in _candidates_for_piece(state, piece):
        verdict = rules.validate_action(state, action)
        if verdict.valid:
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
) -> list[AtomicAction] | GenerationResult:
    """Sinh tất cả hành động đơn đã được rules chấp thuận cho phe đến lượt.

    Không bao gồm lệnh CONFIRM_DEPLOYMENT/END_TURN hoặc chuỗi CompoundAction:
    những lựa chọn đó phụ thuộc trạng thái lượt ghép, mô phỏng engine và
    bài toán tìm một phương án triển khai hoàn tất (Q20).
    """
    summary = GenerationResult()
    for piece in state.pieces.values():
        if piece.owner != state.current_player:
            continue
        generated = generate_piece_actions(
            state, piece.id, include_unsupported=include_unsupported
        )
        if include_unsupported:
            summary.actions.extend(generated.actions)
            summary.unsupported.extend(generated.unsupported)
        else:
            summary.actions.extend(generated)
    return summary if include_unsupported else summary.actions


def has_legal_action(state: GameState) -> bool:
    """Có ít nhất một hành động đơn được rules cho phép hay không."""
    return bool(generate_legal_actions(state))


__all__ = [
    "GenerationIssue",
    "GenerationResult",
    "generate_piece_actions",
    "generate_legal_actions",
    "has_legal_action",
]
