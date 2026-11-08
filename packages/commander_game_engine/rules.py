# packages/commander_game_engine/rules.py
"""Bộ kiểm tra luật Cờ Tư Lệnh (không thay đổi GameState).

Phạm vi: hình học, tầm đi/tấn công, vật cản, địa hình, quan hệ vận chuyển,
điều kiện xác nhận triển khai, vùng phòng không và cấm Tư lệnh đối mặt.
Những tình huống chưa được tích hợp đầy đủ với Engine trả về UNSUPPORTED.
Engine chịu trách nhiệm áp dụng nước đi, thương vong, phong Anh hùng và đổi lượt.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

from .board import EdgeType, Position, Terrain
from .game_state import GameState, Piece, PieceType, Player
from .actions import ActionType, AtomicAction, TurnCommand, TurnCommandType


class RuleCode(Enum):
    """Mã trả về để engine và giao diện phân biệt từng nguyên nhân."""
    OK = "ok"                           # Hợp lệ
    INVALID_ACTION = "invalid_action"   # Thiếu dữ liệu/loại hành động sai
    INVALID_POSITION = "invalid_position"  # Tọa độ ngoài bàn
    GAME_OVER = "game_over"             # Trận đã kết thúc
    WRONG_PLAYER = "wrong_player"       # Sai phe đến lượt
    PIECE_NOT_FOUND = "piece_not_found" # Không tìm thấy quân
    INVALID_ORIGIN = "invalid_origin"   # Sai vị trí xuất phát
    INVALID_TARGET = "invalid_target"   # Sai mục tiêu
    OUT_OF_RANGE = "out_of_range"       # Sai hướng/tầm
    PATH_BLOCKED = "path_blocked"       # Vật cản trên đường
    TERRAIN_BLOCKED = "terrain_blocked" # Cấm đi theo địa hình
    INVALID_TRANSPORT = "invalid_transport" # Quan hệ/sức chứa chở quân sai
    INVALID_COMPOUND = "invalid_compound"   # Lượt ghép không thể hoàn tất
    COMMANDERS_FACING = "commanders_facing" # Hai Tư lệnh lộ mặt
    AIR_DEFENSE = "air_defense"         # Liên quan vùng phòng không
    UNSUPPORTED = "unsupported"         # Chưa đủ đặc tả/hiện thực


@dataclass(frozen=True)
class RuleResult:
    """Kết quả phép kiểm tra thuần, không tự áp dụng hành động."""
    valid: bool                  # True: hợp lệ
    code: RuleCode               # Mã lý do
    reason: str = ""             # Diễn giải


def accept() -> RuleResult:
    """Chấp nhận hành động."""
    return RuleResult(True, RuleCode.OK)


def reject(code: RuleCode, reason: str) -> RuleResult:
    """Từ chối hành động kèm lý do."""
    return RuleResult(False, code, reason)


ORTHOGONAL = frozenset({(1, 0), (-1, 0), (0, 1), (0, -1)})  # Bốn hướng ngang/dọc
DIAGONAL = frozenset({(1, 1), (1, -1), (-1, 1), (-1, -1)})  # Bốn hướng chéo

# Định nghĩa tầm cơ bản; một vài quân có tầm ăn khác tầm đi.
_BASE_MOVE: dict[PieceType, tuple[str, int]] = {
    PieceType.COMMANDER: ("orthogonal", 11),
    PieceType.INFANTRY: ("orthogonal", 1),
    PieceType.MILITIA: ("all", 1),
    PieceType.TANK: ("orthogonal", 2),
    PieceType.ARTILLERY: ("all", 3),
    PieceType.ANTI_AIRCRAFT: ("orthogonal", 1),
    PieceType.MISSILE: ("orthogonal", 2),
    PieceType.AIRCRAFT: ("all", 4),
    PieceType.NAVY: ("all", 4),
    PieceType.ENGINEER: ("orthogonal", 1),
    PieceType.HEADQUARTERS: ("none", 0),
}

# Các loại quân được chở trực tiếp (không phải luật về sức chứa).
_CARRIER_TYPES = {
    PieceType.TANK: frozenset({PieceType.INFANTRY, PieceType.MILITIA, PieceType.COMMANDER}),
    PieceType.AIRCRAFT: frozenset({PieceType.INFANTRY, PieceType.MILITIA, PieceType.COMMANDER, PieceType.TANK}),
    PieceType.NAVY: frozenset({PieceType.INFANTRY, PieceType.MILITIA, PieceType.COMMANDER, PieceType.TANK, PieceType.AIRCRAFT}),
    PieceType.ENGINEER: frozenset({PieceType.ARTILLERY, PieceType.ANTI_AIRCRAFT, PieceType.MISSILE}),
}
_CAPACITY = {PieceType.TANK: 2, PieceType.AIRCRAFT: 2, PieceType.NAVY: 2, PieceType.ENGINEER: 1}
_DEEP_RIVER_CROSSERS = frozenset({
    PieceType.COMMANDER, PieceType.INFANTRY, PieceType.MILITIA,
    PieceType.TANK, PieceType.ENGINEER,
})
_NAVY_TERRAINS = frozenset({Terrain.SEA, Terrain.COAST, Terrain.RIVER_BANK})


def _origin(state: GameState, piece: Piece) -> Position | None:
    """Tìm tọa độ vật lý của quân, kể cả quân được chở lồng nhau."""
    visited = set()
    cursor = piece
    while cursor.carried_by is not None:
        if cursor.id in visited:
            return None
        visited.add(cursor.id)
        cursor = state.pieces.get(cursor.carried_by)
        if cursor is None:
            return None
    return cursor.position


def movement_shape(piece: Piece, destination: Position, capture: bool = False,
                   *, origin: Position | None = None) -> RuleResult:
    """Kiểm tra hướng/tầm theo loại quân (chưa kiểm tra địa hình, vật cản).

    origin dùng khi quân đang được phương tiện chở, không sửa Piece.position.
    """
    start = origin if origin is not None else piece.position
    if start is None:
        return reject(RuleCode.INVALID_ORIGIN, "Quân được chở cần tọa độ tổ hợp.")
    dy, dx = destination[0] - start[0], destination[1] - start[1]
    ady, adx = abs(dy), abs(dx)
    if max(ady, adx) == 0:
        return reject(RuleCode.INVALID_ACTION, "Vị trí đích trùng vị trí đầu.")
    orth = (ady == 0) != (adx == 0)
    diagonal = ady == adx and ady > 0
    if not (orth or diagonal):
        return reject(RuleCode.OUT_OF_RANGE, "Chỉ được đi thẳng hoặc chéo 45 độ.")
    mode, reach = _BASE_MOVE[piece.piece_type]
    if piece.piece_type == PieceType.COMMANDER and capture:
        reach = 1
    if piece.piece_type == PieceType.MISSILE and diagonal:
        mode = "all"
        reach = 1
    if piece.piece_type == PieceType.NAVY and capture:
        reach = 4  # Chỉ dùng với mục tiêu Hải quân; mục tiêu khác xem validate_action.
    if piece.is_heroic:
        if piece.piece_type == PieceType.HEADQUARTERS:
            mode, reach = "all", 2
        else:
            mode, reach = "all", reach + 1
    if mode == "none" or (diagonal and mode != "all") or max(ady, adx) > reach:
        return reject(RuleCode.OUT_OF_RANGE, "Hướng hoặc khoảng cách không hợp lệ.")
    return accept()


def path_points(start: Position, end: Position) -> tuple[Position, ...]:
    """Trả về các giao điểm *nằm giữa* hai vị trí theo tuyến thẳng/chéo."""
    dy, dx = end[0] - start[0], end[1] - start[1]
    n = max(abs(dy), abs(dx))
    if n == 0 or not (dy == 0 or dx == 0 or abs(dy) == abs(dx)):
        raise ValueError("Đường đi phải nằm ngang, dọc hoặc chéo 45 độ.")
    sy, sx = (dy > 0) - (dy < 0), (dx > 0) - (dx < 0)
    return tuple((start[0] + i * sy, start[1] + i * sx) for i in range(1, n))


def _route(start: Position, end: Position) -> tuple[Position, ...]:
    """Toàn bộ đường đi, gồm điểm xuất phát và điểm đích."""
    return (start, *path_points(start, end), end)


def _terrain_ok(state: GameState, piece: Piece, start: Position,
                end: Position, capture: bool) -> RuleResult:
    """Kiểm tra đường qua sông và điểm dừng; không cập nhật bàn cờ."""
    board = state.board
    terrain = board.get_region(*end)
    if piece.piece_type == PieceType.NAVY:
        if terrain not in _NAVY_TERRAINS:
            return reject(RuleCode.TERRAIN_BLOCKED, "Hải quân không được lên đất liền.")
        if any(board.get_region(*p) not in _NAVY_TERRAINS for p in _route(start, end)):
            return reject(RuleCode.TERRAIN_BLOCKED, "Hải quân không thể đi xuyên đất liền.")
        for a, b in zip(_route(start, end), _route(start, end)[1:]):
            if a[0] != b[0] and a[1] != b[1]:
                if min(a[1], b[1]) >= 2:
                    if (a[0] >= 7 and b[0] <= 6) or (b[0] >= 7 and a[0] <= 6):
                        return reject(RuleCode.TERRAIN_BLOCKED, "Đường chéo Hải quân cắt qua đất liền.")
                    if (a[0] <= 4 and b[0] >= 5) or (b[0] <= 4 and a[0] >= 5):
                        return reject(RuleCode.TERRAIN_BLOCKED, "Đường chéo Hải quân cắt qua đất liền.")
    elif terrain == Terrain.SEA:
        return reject(RuleCode.TERRAIN_BLOCKED, "Quân trên bộ/không quân không được đứng trên biển.")
    if piece.piece_type == PieceType.AIRCRAFT:
        return accept()  # Vùng phòng không được kiểm tra riêng.
    route = _route(start, end)
    for a, b in zip(route, route[1:]):
        if {a[0], b[0]} != {5, 6} or min(a[1], b[1]) < 2:
            continue
        if a[1] != b[1]:
            # DEC-018: Tên lửa, pháo binh không thể đi qua sông sâu theo đường chéo sang ô trống.
            # Chỉ có thể qua ngầm theo đường thẳng ở x=5 và x=7, hoặc ăn quân thế chỗ (capture).
            if piece.piece_type == PieceType.NAVY:
                return reject(RuleCode.UNSUPPORTED, "Đường chéo tàu qua sông cần bản đồ luồng nước chi tiết.")
            if piece.piece_type in _DEEP_RIVER_CROSSERS:
                continue
            if capture:
                continue  # Ăn quân bên kia sông sâu trong phạm vi di chuyển/ăn quân, bắt buộc thế chỗ.
            return reject(RuleCode.TERRAIN_BLOCKED, "Tên lửa, pháo binh không thể đi qua sông sâu theo đường chéo.")
        edge = board.get_edge_type(a, b)
        if piece.piece_type == PieceType.NAVY:
            if edge == EdgeType.FORD:
                return reject(RuleCode.TERRAIN_BLOCKED, "Hải quân không được qua ngầm.")
        elif edge == EdgeType.DEEP_RIVER and piece.piece_type not in _DEEP_RIVER_CROSSERS:
            if not capture:
                return reject(RuleCode.TERRAIN_BLOCKED, "Quân nặng chỉ được qua nước sâu khi ăn thế chỗ bên kia sông.")
    return accept()


def _visible_occupancy(state: GameState, removed: set[str] | None = None,
                       moved: tuple[str, Position] | None = None) -> dict[Position, Piece]:
    """Tính vị trí quân độc lập dự kiến, không đụng tới dữ liệu gốc."""
    removed = removed or set()
    occupied: dict[Position, Piece] = {}
    for piece in state.pieces.values():
        if piece.id in removed or piece.carried_by is not None:
            continue
        pos = moved[1] if moved is not None and piece.id == moved[0] else piece.position
        if pos is not None:
            occupied[pos] = piece
    return occupied


def commanders_face(occupied: dict[Position, Piece]) -> bool:
    """K02: phát hiện hai Tư lệnh trực diện, không có quân/vật chắn.

    Mọi quân độc lập (kể cả tàu, Sở chỉ huy, Anh hùng) đều chắn đường.
    Tư lệnh được chở/trú ẩn cần xét trong state chuyên biệt khi tích hợp.
    """
    red = [pos for pos, p in occupied.items() if p.piece_type == PieceType.COMMANDER and p.owner == Player.RED]
    blue = [pos for pos, p in occupied.items() if p.piece_type == PieceType.COMMANDER and p.owner == Player.BLUE]
    if len(red) != 1 or len(blue) != 1:
        return False
    r, b = red[0], blue[0]
    if r[0] != b[0] and r[1] != b[1]:
        return False
    return all(pos not in occupied for pos in path_points(r, b))


def validate_commander_exposure(state: GameState, *, removed: set[str] | None = None,
                                moved: tuple[str, Position] | None = None) -> RuleResult:
    """K02: kiểm tra trạng thái dự kiến sau khi mất quân chắn hoặc di chuyển."""
    if commanders_face(_visible_occupancy(state, removed, moved)):
        return reject(RuleCode.COMMANDERS_FACING, "Hành động khiến hai Tư lệnh đối mặt trực tiếp.")
    return accept()


def _path_blocked(state: GameState, start: Position, end: Position,
                  *, ignore: set[str] | None = None) -> bool:
    """Kiểm tra quân chắn trên các giao điểm giữa đường đi."""
    ignore = ignore or set()
    return any((p := state.get_piece_at(pos)) is not None and p.id not in ignore
               for pos in path_points(start, end))


def validate_action(state: GameState, action: AtomicAction) -> RuleResult:
    """Kiểm tra nước đơn MOVE/CAPTURE/BOMBARD/BOMB; không cập nhật trạng thái.

    Chưa kết luận được kết quả chiến đấu do phòng không hoặc tác động lên nơi
    Tư lệnh trú trong Sở chỉ huy: trả UNSUPPORTED, không tự cho đi.
    """
    if getattr(state.game_status, "value", "ongoing") != "ongoing":
        return reject(RuleCode.GAME_OVER, "Trận đã kết thúc.")
    piece = state.pieces.get(action.piece_id)
    if piece is None:
        return reject(RuleCode.PIECE_NOT_FOUND, "Không tìm thấy quân.")
    if piece.owner != state.current_player:
        return reject(RuleCode.WRONG_PLAYER, "Chưa đến lượt của quân này.")
    if action.action_type not in (ActionType.MOVE, ActionType.CAPTURE, ActionType.BOMB, ActionType.BOMBARD):
        return reject(RuleCode.UNSUPPORTED, "BOARD/PICKUP cần bộ kiểm tra vận chuyển và lượt riêng.")
    if action.action_type == ActionType.BOMB and piece.piece_type != PieceType.AIRCRAFT:
        return reject(RuleCode.INVALID_ACTION, "Chỉ Máy bay được sử dụng BOMB.")
    if action.start is None or action.end is None or not state.board.is_valid_position(action.end):
        return reject(RuleCode.INVALID_POSITION, "Thiếu tọa độ hoặc đích nằm ngoài bàn.")
    start = _origin(state, piece)
    if start != action.start:
        return reject(RuleCode.INVALID_ORIGIN, "Sai vị trí xuất phát của quân/tổ hợp.")
    if piece.carried_by is not None:
        return reject(RuleCode.UNSUPPORTED, "Quân đang được chở cần xác thực lượt ghép trước.")
    target = state.get_piece_at(action.end)
    capture = action.action_type != ActionType.MOVE
    if capture:
        if target is None or target.owner == piece.owner:
            return reject(RuleCode.INVALID_TARGET, "Cần quân địch tại vị trí mục tiêu.")
        if action.target_piece_id is not None and target.id != action.target_piece_id:
            return reject(RuleCode.INVALID_TARGET, "ID mục tiêu không khớp.")
    elif target is not None:
        return reject(RuleCode.INVALID_TARGET, "MOVE cần đích trống.")

    shape = movement_shape(piece, action.end, capture=capture, origin=start)
    if not shape.valid:
        return shape
    n = max(abs(start[0] - action.end[0]), abs(start[1] - action.end[1]))
    navy_vs_land = piece.piece_type == PieceType.NAVY and capture and target.piece_type != PieceType.NAVY
    if navy_vs_land and n > 3 + int(piece.is_heroic):
        return reject(RuleCode.OUT_OF_RANGE, "Hải quân chỉ tấn công quân khác tàu trong tầm 3 đoạn.")

    through = piece.piece_type == PieceType.AIRCRAFT or (capture and piece.piece_type in (
        PieceType.ARTILLERY, PieceType.MISSILE))
    if piece.piece_type == PieceType.NAVY:
        # Q07: không thể đi/ăn xuyên tàu để ăn tàu sau; K01: có thể xuyên tàu
        # để ăn quân bộ trong tầm, kể cả thế chỗ tại bờ hợp lệ.
        middle = [state.get_piece_at(p) for p in path_points(start, action.end)]
        if capture and navy_vs_land:
            through = True
        elif any(p is not None and p.piece_type == PieceType.NAVY for p in middle):
            return reject(RuleCode.PATH_BLOCKED, "Hải quân không được đi/ăn xuyên Hải quân khác.")
        else:
            through = True  # Hải quân có thể vượt qua quân không phải tàu.
    if not through and _path_blocked(state, start, action.end):
        return reject(RuleCode.PATH_BLOCKED, "Có quân chắn trên đường.")

    # Mục tiêu ngoài biển: quân bộ bắn tại chỗ, không bao giờ thế chỗ.
    destination_terrain = state.board.get_region(*action.end)
    if capture and piece.piece_type != PieceType.NAVY and destination_terrain == Terrain.SEA:
        if action.action_type != ActionType.BOMBARD:
            return reject(RuleCode.INVALID_ACTION, "Tấn công tàu ngoài biển phải dùng BOMBARD, không thế chỗ.")
        if target.piece_type != PieceType.NAVY:
            return reject(RuleCode.INVALID_TARGET, "Mục tiêu biển không hợp lệ.")
        # Đường qua biển của quân bộ không phải đường di chuyển: không kiểm tra địa hình đích.
    elif piece.piece_type == PieceType.NAVY and capture:
        if target.piece_type == PieceType.NAVY:
            if action.action_type == ActionType.BOMBARD:
                return reject(RuleCode.UNSUPPORTED, "Chưa chốt bắn tại chỗ vào tàu trong tình huống này.")
        elif destination_terrain in (Terrain.LAND,):
            if action.action_type != ActionType.BOMBARD:
                return reject(RuleCode.INVALID_ACTION, "Hải quân bắn quân trong đất phải đứng tại chỗ.")
        elif action.action_type == ActionType.BOMBARD:
            pass  # Q08: được bắn xuyên và không thế chỗ.
    else:
        if action.action_type == ActionType.BOMB and piece.piece_type != PieceType.AIRCRAFT:
            return reject(RuleCode.INVALID_ACTION, "Chỉ Máy bay được thả bom.")
        if action.action_type == ActionType.BOMBARD and destination_terrain != Terrain.SEA:
            return reject(RuleCode.UNSUPPORTED, "Hình thức bắn tại chỗ của quân này chưa được quy định.")

    if not (capture and destination_terrain == Terrain.SEA and piece.piece_type != PieceType.NAVY):
        if not (capture and piece.piece_type == PieceType.NAVY and destination_terrain == Terrain.LAND):
            terrain = _terrain_ok(state, piece, start, action.end, capture)
            if not terrain.valid:
                return terrain

    if piece.piece_type == PieceType.AIRCRAFT:
        return reject(RuleCode.UNSUPPORTED, "Cần kết hợp kiểm tra đường bay, trạng thái đe dọa và hệ quả phòng không ở Engine.")
    if target is not None and target.piece_type == PieceType.HEADQUARTERS:
        return reject(RuleCode.UNSUPPORTED, "Phá Sở chỉ huy/quan hệ trú ẩn cần trạng thái chuyên biệt.")

    # Với đòn đánh tại chỗ, chỉ loại mục tiêu; với CAPTURE, đổi vị trí quân đánh.
    if capture:
        removed = {target.id}
        moved = (piece.id, action.end) if action.action_type == ActionType.CAPTURE else None
    else:
        removed, moved = set(), (piece.id, action.end)
    exposure = validate_commander_exposure(state, removed=removed, moved=moved)
    if not exposure.valid:
        return exposure
    return accept()


def validate_basic_action(state: GameState, action: AtomicAction) -> RuleResult:
    """Tên hàm tương thích phiên bản cũ (chuyển qua validate_action)."""
    return validate_action(state, action)


def transport_capacity(piece_type: PieceType) -> int:
    """Số quân tối đa (bao gồm quân được chở lồng nhau)."""
    return _CAPACITY.get(piece_type, 0)


def can_carry(carrier: Piece, passenger: Piece) -> RuleResult:
    """Kiểm tra loại quân được chở trực tiếp, chưa xét đường đi/sức chứa."""
    if carrier.id == passenger.id or carrier.owner != passenger.owner:
        return reject(RuleCode.INVALID_TRANSPORT, "Phương tiện và quân phải cùng phe, khác ID.")
    if passenger.piece_type not in _CARRIER_TYPES.get(carrier.piece_type, frozenset()):
        return reject(RuleCode.INVALID_TRANSPORT, "Phương tiện không chở được loại quân này.")
    return accept()


def validate_transport_plan(state: GameState, plan: dict[str, list[str]]) -> RuleResult:
    """Kiểm tra quan hệ vận chuyển đầy đủ, vòng lặp và sức chứa lồng nhau.

    plan được xem là sơ đồ dự kiến, không nhất thiết trùng cargo ở state hiện tại.
    """
    parent: dict[str, str] = {}
    for carrier_id, children in plan.items():
        carrier = state.pieces.get(carrier_id)
        if carrier is None:
            return reject(RuleCode.INVALID_TRANSPORT, f"Không có phương tiện {carrier_id}.")
        if len(children) != len(set(children)):
            return reject(RuleCode.INVALID_TRANSPORT, "Một quân bị liệt kê hai lần trong cargo.")
        for cid in children:
            child = state.pieces.get(cid)
            if child is None:
                return reject(RuleCode.INVALID_TRANSPORT, f"Không có quân {cid}.")
            check = can_carry(carrier, child)
            if not check.valid:
                return check
            if cid in parent:
                return reject(RuleCode.INVALID_TRANSPORT, "Một quân có nhiều phương tiện cha.")
            parent[cid] = carrier_id

    def descendants(pid: str, chain: frozenset[str]) -> set[str]:
        """Tìm quân con/cháu và phát hiện chu trình."""
        if pid in chain:
            raise ValueError("Chu trình chở quân")
        result: set[str] = set()
        for cid in plan.get(pid, []):
            result.add(cid)
            result.update(descendants(cid, chain | {pid}))
        return result

    try:
        for carrier_id in plan:
            if len(descendants(carrier_id, frozenset())) > transport_capacity(state.pieces[carrier_id].piece_type):
                return reject(RuleCode.INVALID_TRANSPORT, f"Phương tiện {carrier_id} vượt sức chứa.")
    except ValueError:
        return reject(RuleCode.INVALID_TRANSPORT, "Có chu trình vận chuyển.")
    return accept()


def validate_deployment_confirmation(state: GameState, remaining_at_origin: set[str],
                                     complete_transport_plan: dict[str, list[str]]) -> RuleResult:
    """Q19: Kiểm tra những quân còn tại gốc có thể tạo tổ hợp duy nhất.

    CONFIRM chỉ kết thúc phương án, không tự tách quân. Không kiểm tra lịch sử
    hay đường đi; engine cung cấp trạng thái/quan hệ sau các action.
    """
    if not remaining_at_origin:
        if complete_transport_plan:
            return reject(RuleCode.INVALID_COMPOUND, "Không còn quân ở gốc nhưng phương án chở vẫn chứa quân.")
        return accept()
    if any(pid not in state.pieces for pid in remaining_at_origin):
        return reject(RuleCode.INVALID_COMPOUND, "Thiếu quân trong tổ hợp còn lại.")
    check = validate_transport_plan(state, complete_transport_plan)
    if not check.valid:
        return check
    passengers = {c for children in complete_transport_plan.values() for c in children}
    if not passengers.issubset(remaining_at_origin) or any(k not in remaining_at_origin for k in complete_transport_plan):
        return reject(RuleCode.INVALID_COMPOUND, "Sơ đồ chở chứa quân ngoài tập đang xét.")
    independent = remaining_at_origin - passengers
    if len(independent) != 1:
        return reject(RuleCode.INVALID_COMPOUND, "Phải còn đúng một quân độc lập tại vị trí gốc.")
    return accept()


def validate_compound_budget(actions_used: int, additional_actions: int = 0) -> RuleResult:
    """Kiểm tra tối đa ba hành động *trên toàn tổ hợp*, không tính CONFIRM."""
    if actions_used < 0 or additional_actions < 0 or actions_used + additional_actions > 3:
        return reject(RuleCode.INVALID_COMPOUND, "Tổ hợp vượt giới hạn ba hành động.")
    return accept()


def validate_compound_feasibility(state: GameState, actions_used: int,
                                  has_legal_completion: bool) -> RuleResult:
    """Q20: từ chối lựa chọn gây bế tắc không thể xác nhận hợp lệ.

    has_legal_completion phải do bộ sinh/phân tích hành động hợp lệ tính từ
    trạng thái dự kiến. Không mặc định True và không làm thay việc tìm kiếm.
    """
    check = validate_compound_budget(actions_used)
    if not check.valid:
        return check
    if not has_legal_completion:
        return reject(RuleCode.INVALID_COMPOUND, "Không còn chuỗi hành động hợp lệ để hoàn tất triển khai.")
    return accept()


def anti_air_offsets(piece_type: PieceType, heroic: bool = False) -> frozenset[tuple[int, int]]:
    """Vùng phòng không theo (dy,dx), không gồm tọa độ trung tâm.

    Q16: Tên lửa Anh hùng có 12 điểm ngang/dọc + 8 chéo + 8 dạng mã = 28.
    Hàm chỉ tạo mặt nạ; xử lý thời điểm cháy thuộc engine.
    """
    orth_range = 0
    diagonal_range = 0
    if piece_type in (PieceType.ANTI_AIRCRAFT, PieceType.NAVY):
        orth_range, diagonal_range = (2, 1) if heroic else (1, 0)
    elif piece_type == PieceType.MISSILE:
        orth_range, diagonal_range = (3, 2) if heroic else (2, 1)
    else:
        return frozenset()
    out = set()
    for d in range(1, orth_range + 1):
        out.update({(d, 0), (-d, 0), (0, d), (0, -d)})
    for d in range(1, diagonal_range + 1):
        out.update({(d, d), (d, -d), (-d, d), (-d, -d)})
    if heroic and piece_type == PieceType.MISSILE:
        out.update({(sy * y, sx * x) for y, x in ((2, 1), (1, 2)) for sy in (-1, 1) for sx in (-1, 1)})
    return frozenset(out)


def defended_positions(state: GameState, defender: Player) -> frozenset[Position]:
    """Tập các giao điểm bị phòng không phe defender kiểm soát.

    Chỉ tổng hợp vùng theo vị trí; Engine theo dõi đe dọa trì hoãn và thời điểm kết thúc lượt.
    """
    positions = set()
    for piece in state.pieces.values():
        if piece.owner != defender or piece.carried_by is not None:
            continue
        if piece.position is None:
            continue
        for dy, dx in anti_air_offsets(piece.piece_type, piece.is_heroic):
            pos = (piece.position[0] + dy, piece.position[1] + dx)
            if state.board.is_valid_position(pos):
                positions.add(pos)
    return frozenset(positions)


class AirDefenseEffect(Enum):
    """Hệ quả phòng không để Engine áp dụng; không chỉnh sửa quân trong Rules."""
    NONE = "none"                    # Không có hệ quả phòng không
    EXCHANGE = "exchange"            # Máy bay và mục tiêu cùng bị diệt (1 đổi 1)
    AIRCRAFT_LOST = "aircraft_lost"  # Chỉ máy bay bị tiêu diệt
    DEFERRED = "deferred"            # Vẫn bị đe dọa, chưa bị tiêu diệt ngay


@dataclass(frozen=True)
class AirDefenseResult:
    """Mô tả hệ quả dự kiến, không phải thao tác cập nhật GameState."""
    effect: AirDefenseEffect              # Hệ quả phòng không
    reason: str = ""                      # Diễn giải lý do


def resolve_bomb_while_threatened(
    aircraft: Piece,
    target: Piece,
    *,
    is_deferred_threat: bool,
) -> AirDefenseResult:
    """Q10: máy bay đang chịu đe dọa trì hoãn thực hiện BOMB.

    Mục tiêu là Cao xạ/Tên lửa/Hải quân (quân tạo phòng không): 1 đổi 1.
    Mục tiêu khác: máy bay giữ nguyên trạng thái bị đe dọa, Engine
    phải kiểm tra việc tự cháy vào lần chuyển lượt đã chốt (Q12).
    Máy bay Anh hùng miễn nguy cơ phòng không theo luật Anh hùng.

    Hàm này không đánh giá tầm BOMB, đường bay, hay việc mục tiêu hợp lệ.
    """
    if aircraft.piece_type != PieceType.AIRCRAFT:
        raise ValueError("Chỉ Máy bay mới được thực hiện BOMB.")
    if aircraft.is_heroic or not is_deferred_threat:
        return AirDefenseResult(AirDefenseEffect.NONE, "Không có đe dọa trì hoãn áp dụng.")
    if target.piece_type in (PieceType.ANTI_AIRCRAFT, PieceType.MISSILE, PieceType.NAVY):
        return AirDefenseResult(AirDefenseEffect.EXCHANGE, "Q10: ném bom quân phòng không: 1 đổi 1.")
    return AirDefenseResult(AirDefenseEffect.DEFERRED, "Q10: ném bom quân khác; máy bay vẫn bị đe dọa.")


def aircraft_enters_active_defense(
    state: GameState,
    aircraft: Piece,
    path: tuple[Position, ...],
) -> AirDefenseResult:
    """Q11: máy bay triển khai từ tàu chịu vùng phòng không ngay lập tức.

    path là các giao điểm trên đường bay sau khi rời phương tiện,
    bao gồm cả điểm đến; tính toán đường bay thuộc module khác.
    Không tự cho phép triển khai và không thay đổi trạng thái.
    """
    if aircraft.piece_type != PieceType.AIRCRAFT:
        raise ValueError("Chỉ áp dụng cho Máy bay.")
    if aircraft.is_heroic:
        return AirDefenseResult(AirDefenseEffect.NONE, "Máy bay Anh hùng miễn phòng không.")
    enemy = Player.BLUE if aircraft.owner == Player.RED else Player.RED
    danger = defended_positions(state, enemy)
    if any(position in danger for position in path):
        return AirDefenseResult(AirDefenseEffect.AIRCRAFT_LOST, "Q11: đường triển khai bay qua vùng phòng không.")
    return AirDefenseResult(AirDefenseEffect.NONE, "Đường bay không cắt vùng phòng không.")


def deferred_aircraft_burns(
    state: GameState,
    aircraft_id: str,
    *,
    threat_pending: bool,
    opponent_turn_has_started: bool,
) -> bool:
    """Q10/Q12: kiểm tra máy bay còn ở vùng phòng không khi tới lượt đối phương.

    Engine cung cấp hai cờ thời điểm/trạng thái đe dọa (lưu trong GameState);
    Rules chỉ trả về True/False. Không tự loại quân, không đổi lượt.
    """
    aircraft = state.pieces.get(aircraft_id)
    if aircraft is None or aircraft.piece_type != PieceType.AIRCRAFT:
        return False
    if aircraft.is_heroic or not threat_pending or not opponent_turn_has_started:
        return False
    if aircraft.carried_by is not None or aircraft.position is None:
        return False
    enemy = Player.BLUE if aircraft.owner == Player.RED else Player.RED
    return aircraft.position in defended_positions(state, enemy)


def threatened_hero_candidates(state: GameState) -> frozenset[str]:
    """K03: liệt kê quân có *hình học tầm ăn* đến Tư lệnh địch.

    Bao gồm quân đang được chở, dùng vị trí phương tiện gốc. Không coi đây là
    bộ xác định phong hoàn chỉnh khi tương tác Sở chỉ huy/phòng không chưa có.
    """
    result = set()
    for piece in state.pieces.values():
        if piece.piece_type == PieceType.COMMANDER:
            continue
        start = _origin(state, piece)
        if start is None:
            continue
        for enemy in state.pieces.values():
            if enemy.piece_type != PieceType.COMMANDER or enemy.owner == piece.owner:
                continue
            dest = _origin(state, enemy)
            if dest is None:
                continue
            if movement_shape(piece, dest, capture=True, origin=start).valid:
                result.add(piece.id)
    return frozenset(result)
