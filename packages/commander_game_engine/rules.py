# packages/commander_game_engine/rules.py
"""Bộ kiểm tra luật Cờ Tư Lệnh (không thay đổi GameState).

Phạm vi: hình học, tầm đi/tấn công, vật cản, địa hình, quan hệ vận chuyển,
lượt ghép tổ hợp, vùng phòng không, cấm Tư lệnh đối mặt và an toàn Tư lệnh.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .board import EdgeType, Position, Terrain
from .game_state import GameState, Piece, PieceType, Player
from .actions import ActionType, AtomicAction


class RuleCode(Enum):
    """Mã trả về để engine và giao diện phân biệt từng nguyên nhân."""
    OK = "ok"                              # Hợp lệ
    INVALID_ACTION = "invalid_action"      # Thiếu dữ liệu/loại hành động sai
    INVALID_POSITION = "invalid_position"  # Tọa độ ngoài bàn
    GAME_OVER = "game_over"                # Trận đã kết thúc
    WRONG_PLAYER = "wrong_player"          # Sai phe đến lượt
    PIECE_NOT_FOUND = "piece_not_found"    # Không tìm thấy quân
    INVALID_ORIGIN = "invalid_origin"      # Sai vị trí xuất phát
    INVALID_TARGET = "invalid_target"      # Sai mục tiêu
    OUT_OF_RANGE = "out_of_range"          # Sai hướng/tầm
    PATH_BLOCKED = "path_blocked"          # Vật cản trên đường
    TERRAIN_BLOCKED = "terrain_blocked"    # Cấm đi theo địa hình
    INVALID_TRANSPORT = "invalid_transport"# Quan hệ/sức chứa chở quân sai
    INVALID_COMPOUND = "invalid_compound"  # Lượt ghép không thể hoàn tất
    COMMANDERS_FACING = "commanders_facing"# Hai Tư lệnh lộ mặt
    COMMANDER_IN_CHECK = "commander_in_check"  # Tư lệnh vẫn bị chiếu/ăn sau nước đi
    AIR_DEFENSE = "air_defense"            # Liên quan vùng phòng không
    UNSUPPORTED = "unsupported"            # Chưa đủ đặc tả/hiện thực


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

# Các loại quân được chở trực tiếp (chưa tính HQ/sức chứa).
_CARRIER_TYPES = {
    PieceType.TANK: frozenset({PieceType.INFANTRY, PieceType.MILITIA, PieceType.COMMANDER}),
    PieceType.AIRCRAFT: frozenset({PieceType.INFANTRY, PieceType.MILITIA, PieceType.COMMANDER, PieceType.TANK}),
    PieceType.NAVY: frozenset({PieceType.INFANTRY, PieceType.MILITIA, PieceType.COMMANDER, PieceType.TANK, PieceType.AIRCRAFT}),
    PieceType.ENGINEER: frozenset({PieceType.ARTILLERY, PieceType.ANTI_AIRCRAFT, PieceType.MISSILE}),
    PieceType.HEADQUARTERS: frozenset({PieceType.COMMANDER}),
}
_CAPACITY = {
    PieceType.TANK: 2,
    PieceType.AIRCRAFT: 2,
    PieceType.NAVY: 2,
    PieceType.ENGINEER: 1,
    PieceType.HEADQUARTERS: 1,
}
_DEEP_RIVER_CROSSERS = frozenset({
    PieceType.COMMANDER, PieceType.INFANTRY, PieceType.MILITIA,
    PieceType.TANK, PieceType.ENGINEER, PieceType.HEADQUARTERS,
})
_NAVY_TERRAINS = frozenset({Terrain.SEA, Terrain.COAST, Terrain.RIVER_BANK})


def is_sea_square(pos: Position) -> bool:
    """Giao điểm biển sâu (x < 2)."""
    return pos[1] < 2


def is_ford_square(pos: Position) -> bool:
    """Hai đoạn ngầm qua sông (x=5 hoặc x=7, y=5 hoặc y=6)."""
    return pos[0] in (5, 6) and pos[1] in (5, 7)


def is_shore_square(pos: Position) -> bool:
    """Bờ biển (x=2) hoặc bờ sông (y=5,6 trừ ngầm đá)."""
    return pos[1] == 2 or (pos[0] in (5, 6) and 2 <= pos[1] <= 10 and not is_ford_square(pos))


def can_navy_occupy_square(pos: Position) -> bool:
    """Hải quân chỉ đi trên biển (x<=1), bờ biển (x=2) và dải sông (y=5,6 trừ ngầm)."""
    if is_ford_square(pos):
        return False
    return pos[1] <= 2 or pos[0] in (5, 6)


def is_navy_land_diagonal(a: Position, b: Position) -> bool:
    """Đường chéo cắt qua vùng đất liền giữa bờ biển và bờ sông."""
    if a[0] == b[0] or a[1] == b[1]:
        return False
    if min(a[1], b[1]) >= 2:
        if (a[0] >= 7 and b[0] <= 6) or (b[0] >= 7 and a[0] <= 6):
            return True
        if (a[0] <= 4 and b[0] >= 5) or (b[0] <= 4 and a[0] >= 5):
            return True
    return False


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


def _root_piece(state: GameState, piece: Piece) -> Piece | None:
    """Tìm quân gốc đang đứng trực tiếp trên bàn (kể cả khi piece không bị chở)."""
    visited = set()
    cursor = piece
    while cursor.carried_by is not None:
        if cursor.id in visited:
            return None
        visited.add(cursor.id)
        cursor = state.pieces.get(cursor.carried_by)
        if cursor is None:
            return None
    return cursor


def all_carried_ids(state: GameState, carrier_id: str) -> list[str]:
    """Lấy danh sách ID toàn bộ quân đang được cõng trực tiếp/gián tiếp."""
    collected: list[str] = []
    queue = [carrier_id]
    seen = {carrier_id}
    while queue:
        cid = queue.pop(0)
        carrier = state.pieces.get(cid)
        if carrier is None:
            continue
        for child_id in carrier.cargo:
            if child_id not in seen and child_id in state.pieces:
                seen.add(child_id)
                collected.append(child_id)
                queue.append(child_id)
    return collected


def movement_shape(piece: Piece, destination: Position, capture: bool = False,
                   *, origin: Position | None = None) -> RuleResult:
    """Kiểm tra hướng/tầm theo loại quân (chưa kiểm tra địa hình, vật cản)."""
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
        reach = 4  # Mục tiêu Hải quân tầm 4; mục tiêu khác tầm 3 (xem validate_structural_action).
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


def _navy_phase1_clear(
    state: GameState,
    navy: Piece,
    start: Position,
    end: Position,
    *,
    allow_enemy_target_at_end: bool,
) -> RuleResult:
    """Kiểm tra pha 1 Hải quân (di chuyển / đón / đánh tàu hoặc đổ bộ bờ biển-sông).

    - Không qua đất liền, ngầm đá (FORD) hoặc đường chéo đất liền.
    - Không đi/bắn xuyên Hải quân khác hoặc quân địch cản bờ.
    - ĐƯỢC PHÉP vượt qua quân đồng minh KHÔNG phải Hải quân đứng ở bờ biển / bờ sông.
    """
    route = _route(start, end)
    board = state.board
    for a, b in zip(route, route[1:]):
        if is_navy_land_diagonal(a, b):
            return reject(RuleCode.TERRAIN_BLOCKED, "Đường chéo Hải quân cắt qua đất liền.")
    for pos in route[1:]:
        if is_ford_square(pos) or board.get_region(*pos) not in _NAVY_TERRAINS:
            return reject(RuleCode.TERRAIN_BLOCKED, "Hải quân không thể đi qua đất liền hoặc ngầm đá.")
    for mid in path_points(start, end):
        occ = state.get_piece_at(mid)
        if occ is None:
            continue
        if occ.piece_type == PieceType.NAVY:
            return reject(RuleCode.PATH_BLOCKED, "Hải quân không được đi xuyên Hải quân khác.")
        if occ.owner != navy.owner:
            return reject(RuleCode.PATH_BLOCKED, "Quân địch trên bờ cản đường tiến Hải quân.")
    if not allow_enemy_target_at_end:
        occ_end = state.get_piece_at(end)
        if occ_end is not None and occ_end.owner != navy.owner:
            return reject(RuleCode.INVALID_TARGET, "Ô đích có quân địch.")
    return accept()


def _terrain_ok(
    state: GameState,
    piece: Piece,
    start: Position,
    end: Position,
    capture: bool,
    *,
    allow_sea_boarding: bool = False,
) -> RuleResult:
    """Kiểm tra đường qua sông và điểm dừng; không cập nhật bàn cờ."""
    board = state.board
    terrain = board.get_region(*end)
    if piece.piece_type == PieceType.NAVY:
        return _navy_phase1_clear(state, piece, start, end, allow_enemy_target_at_end=capture)
    if terrain == Terrain.SEA and not allow_sea_boarding:
        return reject(RuleCode.TERRAIN_BLOCKED, "Quân trên bộ/không quân không được đứng trên biển.")
    if piece.piece_type == PieceType.AIRCRAFT:
        return accept()  # Không quân bay vượt địa hình sông; vùng phòng không xử lý ở Engine.
    route = _route(start, end)
    for a, b in zip(route, route[1:]):
        if {a[0], b[0]} != {5, 6} or min(a[1], b[1]) < 2:
            continue
        if a[1] != b[1]:
            if piece.piece_type in _DEEP_RIVER_CROSSERS:
                continue
            if capture:
                continue  # DEC-018: Tên lửa, Pháo binh được ăn quân thế chỗ qua sông sâu.
            return reject(RuleCode.TERRAIN_BLOCKED, "Quân nặng không thể tự đi qua sông sâu theo đường chéo.")
        edge = board.get_edge_type(a, b)
        if edge == EdgeType.DEEP_RIVER and piece.piece_type not in _DEEP_RIVER_CROSSERS:
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

    Mọi quân độc lập (kể cả Xe tăng, Máy bay, Tàu chiến, Sở chỉ huy, Anh hùng) đều chắn đường.
    Tư lệnh đang được chở/trú ẩn (`carried_by is not None`) không nằm trong `occupied`
    nên không bị đối mặt trực tiếp với Tư lệnh đối phương.
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


def is_hq_sheltering_commander(state: GameState, target: Piece) -> bool:
    """Kiểm tra Sở chỉ huy có đang che chở Tư lệnh bên trong không."""
    if target.piece_type != PieceType.HEADQUARTERS:
        return False
    return any(
        p.piece_type == PieceType.COMMANDER and p.carried_by == target.id
        for p in state.pieces.values()
    )


def is_hq_facing_enemy_commander(state: GameState, hq: Piece, enemy_cmd: Piece | None) -> bool:
    """Kiểm tra Sở chỉ huy có đang đối mặt trực tiếp với Tư lệnh địch (chưa được chở) hay không."""
    if enemy_cmd is None or enemy_cmd.carried_by is not None or enemy_cmd.position is None:
        return False
    hq_pos = _origin(state, hq)
    if hq_pos is None:
        return False
    epos = enemy_cmd.position
    if hq_pos[0] != epos[0] and hq_pos[1] != epos[1]:
        return False
    return all(
        (occ := state.get_piece_at(pt)) is None or occ.id in (hq.id, enemy_cmd.id)
        for pt in path_points(hq_pos, epos)
    )


def delayed_solitary_hq_commander_id(state: GameState, player: Player) -> str | None:
    """Quy tắc phong Anh hùng trễ cho Sở chỉ huy duy nhất:

    Khi phe chỉ còn Tư lệnh + đúng 1 Sở chỉ huy (chưa Anh hùng) mà Tư lệnh đang trú
    bên trong Sở chỉ huy đó, Sở chỉ huy CHƯA được phong Anh hùng; người chơi chỉ
    có nước đi rời Tư lệnh ra khỏi Sở chỉ huy (sau khi rời sẽ phong Anh hùng ngay).
    """
    owned = [p for p in state.pieces.values() if p.owner == player]
    non_cmd_non_hq = [
        p for p in owned if p.piece_type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS)
    ]
    hq_pieces = [p for p in owned if p.piece_type == PieceType.HEADQUARTERS]
    cmd = next((p for p in owned if p.piece_type == PieceType.COMMANDER), None)
    if (
        cmd is not None
        and len(non_cmd_non_hq) == 0
        and len(hq_pieces) == 1
        and not hq_pieces[0].is_heroic
        and cmd.carried_by == hq_pieces[0].id
    ):
        return cmd.id
    return None


def can_carrier_leave_cargo_behind(state: GameState, carrier: Piece) -> bool:
    """Kiểm tra phương tiện có thể rời vị trí để lại quân cõng tại gốc hay không."""
    direct = [state.pieces[cid] for cid in carrier.cargo if cid in state.pieces]
    if not direct:
        return True
    origin = _origin(state, carrier)
    if origin is None or is_sea_square(origin):
        return False
    if len(direct) == 1:
        return True
    if len(direct) == 2:
        p1, p2 = direct[0], direct[1]
        def _can_nest(inner: Piece, outer: Piece) -> bool:
            if not can_carry(outer, inner).valid:
                return False
            if outer.piece_type == PieceType.ENGINEER and origin[0] not in (5, 6):
                return False
            used = 1 + len(all_carried_ids(state, inner.id))
            return used <= transport_capacity(outer.piece_type)
        return _can_nest(p2, p1) or _can_nest(p1, p2)
    return False


def _piece_threatens_square(state: GameState, attacker: Piece, target_pos: Position, occ_map: dict[Position, Piece]) -> bool:
    """Kiểm tra một quân địch (kể cả đang ngồi trên phương tiện) có ăn được vào target_pos không."""
    if attacker.piece_type == PieceType.HEADQUARTERS and not attacker.is_heroic:
        return False
    start = _origin(state, attacker)
    if start is None or start == target_pos:
        return False

    # Quân đang ngồi trên phương tiện địch muốn triển khai ăn trực tiếp:
    # bắt buộc phải là đòn thế chỗ hợp lệ (không đứng tại chỗ trên biển).
    if attacker.carried_by is not None and is_sea_square(target_pos) and attacker.piece_type != PieceType.NAVY:
        return False

    dy, dx = target_pos[0] - start[0], target_pos[1] - start[1]
    ady, adx = abs(dy), abs(dx)
    is_orth = (ady == 0) != (adx == 0)
    is_diag = ady == adx and ady > 0
    if not (is_orth or is_diag):
        return False

    dist = max(ady, adx)
    mid = path_points(start, target_pos)
    blocked = any(pt in occ_map for pt in mid)

    ptype = attacker.piece_type
    hero = attacker.is_heroic

    if ptype == PieceType.COMMANDER:
        if hero:
            return dist <= 2 and not blocked
        return is_orth and dist == 1

    if ptype in (PieceType.INFANTRY, PieceType.ENGINEER, PieceType.ANTI_AIRCRAFT):
        dirs_ok = True if hero else is_orth
        max_r = 2 if hero else 1
        return dirs_ok and dist <= max_r and not blocked

    if ptype == PieceType.MILITIA:
        return dist <= (2 if hero else 1) and not blocked

    if ptype == PieceType.TANK:
        dirs_ok = True if hero else is_orth
        max_r = 3 if hero else 2
        return dirs_ok and dist <= max_r and not blocked

    if ptype == PieceType.MISSILE:
        # Tên lửa được phép ăn xuyên vật cản (cả ngang/dọc và chéo)
        max_r = (3 if hero else 2) if is_orth else (2 if hero else 1)
        return dist <= max_r

    if ptype == PieceType.ARTILLERY:
        return dist <= (4 if hero else 3)

    if ptype == PieceType.AIRCRAFT:
        return dist <= (5 if hero else 4)

    if ptype == PieceType.NAVY:
        if not can_navy_occupy_square(start):
            return False
        target_occ = occ_map.get(target_pos)
        if target_occ is not None and target_occ.piece_type == PieceType.NAVY:
            if dist > (5 if hero else 4):
                return False
            return _navy_phase1_clear(state, attacker, start, target_pos, allow_enemy_target_at_end=True).valid
        # Pháo hạm bắn đất liền / không quân / ô trống (tầm 3, Anh hùng 4), xuyên đất liền/tàu
        return dist <= (4 if hero else 3)

    if ptype == PieceType.HEADQUARTERS:
        return hero and dist <= 2 and not blocked

    return False


def is_square_attacked_by_enemy(state: GameState, target_pos: Position, enemy_player: Player) -> bool:
    """Kiểm tra giao điểm target_pos có bị bất kỳ quân nào của enemy_player tấn công/chiếu hay không.

    Bao gồm cả quân địch đang ngồi trên phương tiện triển khai ăn trực tiếp!
    """
    occ_map: dict[Position, Piece] = {
        p.position: p
        for p in state.pieces.values()
        if p.carried_by is None and p.position is not None
    }
    for piece in state.pieces.values():
        if piece.owner != enemy_player:
            continue
        if _piece_threatens_square(state, piece, target_pos, occ_map):
            return True
    return False


def is_commander_in_check(state: GameState, player: Player) -> bool:
    """Kiểm tra Tư lệnh của phe player có đang bị chiếu hay không."""
    cmd = next(
        (p for p in state.pieces.values() if p.owner == player and p.piece_type == PieceType.COMMANDER),
        None,
    )
    if cmd is None:
        return False
    enemy = Player.BLUE if player == Player.RED else Player.RED
    if cmd.carried_by is not None:
        carrier = state.pieces.get(cmd.carried_by)
        if carrier is None:
            return False
        if carrier.piece_type == PieceType.HEADQUARTERS and not carrier.is_heroic:
            return False  # Sở chỉ huy thường che chở hoàn toàn khỏi bị chiếu trực tiếp
        cpos = _origin(state, carrier)
        if cpos is None:
            return False
        return is_square_attacked_by_enemy(state, cpos, enemy)
    if cmd.position is None:
        return False
    return is_square_attacked_by_enemy(state, cmd.position, enemy)


def can_board(state: GameState, passenger: Piece, carrier: Piece) -> RuleResult:
    """Kiểm tra passenger có thể lên carrier theo quan hệ, vị trí (Công binh) và sức chứa."""
    if carrier.id == passenger.id or carrier.owner != passenger.owner:
        return reject(RuleCode.INVALID_TRANSPORT, "Phương tiện và quân phải cùng phe, khác ID.")
    if carrier.carried_by is not None:
        return reject(RuleCode.INVALID_TRANSPORT, "Không thể trực tiếp lên phương tiện đang nằm trong phương tiện khác.")
    if carrier.piece_type == PieceType.HEADQUARTERS:
        if carrier.is_heroic:
            return reject(RuleCode.INVALID_TRANSPORT, "Sở chỉ huy Anh hùng không còn tiếp nhận Tư lệnh.")
        if passenger.piece_type != PieceType.COMMANDER or len(carrier.cargo) >= 1:
            return reject(RuleCode.INVALID_TRANSPORT, "Sở chỉ huy chỉ tiếp nhận tối đa 1 Tư lệnh.")
        return accept()
    if passenger.piece_type not in _CARRIER_TYPES.get(carrier.piece_type, frozenset()):
        return reject(RuleCode.INVALID_TRANSPORT, "Phương tiện không chở được loại quân này.")
    if carrier.piece_type == PieceType.ENGINEER:
        cpos = _origin(state, carrier)
        if cpos is None or cpos[0] not in (5, 6):
            return reject(RuleCode.INVALID_TRANSPORT, "Công binh chỉ chở vũ khí nặng tại bờ sông.")
    used = len(all_carried_ids(state, carrier.id))
    added = 1 + len(all_carried_ids(state, passenger.id))
    if used + added > transport_capacity(carrier.piece_type):
        return reject(RuleCode.INVALID_TRANSPORT, "Phương tiện vượt quá sức chứa tối đa.")
    return accept()


def validate_structural_action(state: GameState, action: AtomicAction) -> RuleResult:
    """Kiểm tra luật hình học, địa hình, vật cản, vận chuyển, tổ hợp và đối mặt Tư lệnh."""
    if getattr(state.game_status, "value", "ongoing") != "ongoing":
        return reject(RuleCode.GAME_OVER, "Trận đã kết thúc.")
    piece = state.pieces.get(action.piece_id)
    if piece is None:
        return reject(RuleCode.PIECE_NOT_FOUND, "Không tìm thấy quân.")
    if piece.owner != state.current_player:
        return reject(RuleCode.WRONG_PLAYER, "Chưa đến lượt của quân này.")

    # Quy tắc phong Anh hùng trễ cho Sở chỉ huy duy nhất
    trap_cmd_id = delayed_solitary_hq_commander_id(state, piece.owner)
    if trap_cmd_id is not None:
        if piece.id != trap_cmd_id:
            return reject(RuleCode.INVALID_ACTION, "Tư lệnh phải rời Sở chỉ huy duy nhất trước.")
        if action.action_type not in (ActionType.MOVE, ActionType.CAPTURE, ActionType.BOMBARD):
            return reject(RuleCode.INVALID_ACTION, "Tư lệnh phải rời khỏi Sở chỉ huy duy nhất.")

    # Kiểm tra lượt tổ hợp đang diễn ra
    if state.compound_turn is not None:
        ct = state.compound_turn
        if ct.actions_used >= 3:
            return reject(RuleCode.INVALID_COMPOUND, "Tổ hợp đã đạt tối đa 3 hành động.")
        if piece.id in ct.acted_piece_ids:
            return reject(RuleCode.INVALID_COMPOUND, "Quân này đã hành động trong lượt tổ hợp.")
        root_at_origin = state.get_piece_at(ct.origin)
        if root_at_origin is None or root_at_origin.owner != piece.owner:
            return reject(RuleCode.INVALID_COMPOUND, "Không còn tổ hợp tại gốc.")
        eligible_ids = {root_at_origin.id, *all_carried_ids(state, root_at_origin.id)}
        if piece.id not in eligible_ids:
            return reject(RuleCode.INVALID_COMPOUND, "Quân không thuộc tổ hợp đang triển khai.")

    if action.action_type not in (
        ActionType.MOVE, ActionType.CAPTURE, ActionType.BOMB, ActionType.BOMBARD, ActionType.BOARD, ActionType.PICKUP
    ):
        return reject(RuleCode.INVALID_ACTION, "Loại hành động không hợp lệ.")
    if action.action_type == ActionType.BOMB and piece.piece_type != PieceType.AIRCRAFT:
        return reject(RuleCode.INVALID_ACTION, "Chỉ Máy bay được sử dụng BOMB.")
    if action.action_type == ActionType.BOMBARD and piece.piece_type == PieceType.AIRCRAFT:
        return reject(RuleCode.INVALID_ACTION, "Máy bay bắn tại chỗ phải sử dụng BOMB.")
    if action.start is None or action.end is None or not state.board.is_valid_position(action.end):
        return reject(RuleCode.INVALID_POSITION, "Thiếu tọa độ hoặc đích nằm ngoài bàn.")

    start = _origin(state, piece)
    if start is None or start != action.start:
        return reject(RuleCode.INVALID_ORIGIN, "Sai vị trí xuất phát của quân/tổ hợp.")

    # Ràng buộc của hành động rời bỏ cargo (carry_cargo=False)
    if not action.carry_cargo:
        if action.action_type not in (ActionType.MOVE, ActionType.CAPTURE):
            return reject(RuleCode.INVALID_ACTION, "Chỉ MOVE hoặc CAPTURE mới dùng carry_cargo=False.")
        if not piece.cargo:
            return reject(RuleCode.INVALID_ACTION, "Quân không cõng quân nào để tách lẻ.")
        if not can_carrier_leave_cargo_behind(state, piece):
            return reject(RuleCode.INVALID_TRANSPORT, "Không thể bỏ lại toàn bộ quân đang cõng tại vị trí xuất phát.")

    # Ràng buộc cho quân đang được cõng triển khai ra ngoài
    if piece.carried_by is not None:
        if action.action_type in (ActionType.BOMB, ActionType.BOMBARD, ActionType.PICKUP):
            return reject(RuleCode.INVALID_TRANSPORT, "Quân đang được chở bắt buộc phải rời khỏi phương tiện (không đứng tại chỗ hoặc đón thêm).")

    target = state.get_piece_at(action.end)
    capture = action.action_type in (ActionType.CAPTURE, ActionType.BOMB, ActionType.BOMBARD)

    if action.action_type == ActionType.BOARD:
        if target is None or target.owner != piece.owner:
            return reject(RuleCode.INVALID_TARGET, "Cần phương tiện đồng minh tại đích để lên xe/tàu.")
        if action.target_piece_id is not None and target.id != action.target_piece_id:
            return reject(RuleCode.INVALID_TARGET, "ID mục tiêu không khớp.")
        if action.carrier_id is not None and target.id != action.carrier_id:
            return reject(RuleCode.INVALID_TARGET, "ID phương tiện không khớp.")
        if trap_cmd_id is not None and target.piece_type == PieceType.HEADQUARTERS:
            return reject(RuleCode.INVALID_ACTION, "Tư lệnh phải rời Sở chỉ huy duy nhất.")
        board_chk = can_board(state, piece, target)
        if not board_chk.valid:
            return board_chk
        if piece.piece_type == PieceType.COMMANDER and target.piece_type == PieceType.HEADQUARTERS:
            enemy = Player.BLUE if piece.owner == Player.RED else Player.RED
            enemy_cmd = next((p for p in state.pieces.values() if p.owner == enemy and p.piece_type == PieceType.COMMANDER), None)
            if is_hq_facing_enemy_commander(state, target, enemy_cmd):
                return reject(RuleCode.COMMANDERS_FACING, "Không thể trú vào Sở chỉ huy đang đối mặt Tư lệnh địch.")

    elif action.action_type == ActionType.PICKUP:
        if piece.carried_by is not None:
            return reject(RuleCode.INVALID_TRANSPORT, "Quân đang được chở không thể chủ động đi đón quân khác.")
        if target is None or target.owner != piece.owner or target.carried_by is not None:
            return reject(RuleCode.INVALID_TARGET, "Cần quân đồng minh độc lập tại đích để đón.")
        if action.target_piece_id is not None and target.id != action.target_piece_id:
            return reject(RuleCode.INVALID_TARGET, "ID mục tiêu không khớp.")
        if action.passenger_id is not None and target.id != action.passenger_id:
            return reject(RuleCode.INVALID_TARGET, "ID quân được đón không khớp.")
        pickup_chk = can_board(state, target, piece)
        if not pickup_chk.valid:
            return pickup_chk

    elif capture:
        if target is None or target.owner == piece.owner:
            return reject(RuleCode.INVALID_TARGET, "Cần quân địch tại vị trí mục tiêu.")
        if action.target_piece_id is not None and target.id != action.target_piece_id:
            return reject(RuleCode.INVALID_TARGET, "ID mục tiêu không khớp.")
    else:  # MOVE
        if target is not None:
            return reject(RuleCode.INVALID_TARGET, "MOVE cần đích trống.")

    # Kiểm tra hình học di chuyển / tấn công
    shape = movement_shape(piece, action.end, capture=capture, origin=start)
    if not shape.valid:
        return shape

    n = max(abs(start[0] - action.end[0]), abs(start[1] - action.end[1]))
    navy_vs_land = piece.piece_type == PieceType.NAVY and capture and target.piece_type != PieceType.NAVY
    if navy_vs_land and n > 3 + int(piece.is_heroic):
        return reject(RuleCode.OUT_OF_RANGE, "Hải quân chỉ tấn công quân khác tàu trong tầm 3 đoạn (Anh hùng: 4).")

    # Vật cản trên đường đi:
    # - Máy bay bay qua mọi vật cản (cùng phe lẫn địch).
    # - Tên lửa và Pháo binh ăn xuyên vật cản khi tấn công, nhưng KHÔNG đi/BOARD xuyên vật cản.
    # - Hải quân pha 1 vượt quân đồng minh KHÔNG phải tàu; pha 2 pháo hạm bắn đất liền xuyên mọi vật cản.
    destination_terrain = state.board.get_region(*action.end)

    if piece.piece_type == PieceType.NAVY:
        if capture and navy_vs_land:
            phase1_ok = _navy_phase1_clear(state, piece, start, action.end, allow_enemy_target_at_end=True)
            sheltered_hq = is_hq_sheltering_commander(state, target)
            is_open_shore = phase1_ok.valid and is_shore_square(action.end) and not sheltered_hq
            if is_open_shore:
                if action.action_type != ActionType.CAPTURE:
                    return reject(RuleCode.INVALID_ACTION, "Hải quân đánh quân trên bờ thoáng phải thế chỗ.")
            else:
                if action.action_type != ActionType.BOMBARD:
                    return reject(RuleCode.INVALID_ACTION, "Hải quân bắn vào đất liền sâu hoặc qua vật cản phải dùng BOMBARD.")
        else:
            # MOVE, PICKUP, hoặc đánh Hải quân địch: phải thông pha 1
            if capture and target.piece_type == PieceType.NAVY and action.action_type != ActionType.CAPTURE:
                return reject(RuleCode.INVALID_ACTION, "Hải chiến đánh tàu địch phải thế chỗ (CAPTURE).")
            phase1_ok = _navy_phase1_clear(
                state,
                piece,
                start,
                action.end,
                allow_enemy_target_at_end=(capture and target.piece_type == PieceType.NAVY),
            )
            if not phase1_ok.valid:
                return phase1_ok
    else:
        through = (
            piece.piece_type == PieceType.AIRCRAFT
            or (capture and piece.piece_type in (PieceType.ARTILLERY, PieceType.MISSILE))
        )
        if not through and _path_blocked(state, start, action.end):
            return reject(RuleCode.PATH_BLOCKED, "Có quân chắn trên đường.")

    # Kiểm tra phương thức tấn công tại chỗ (BOMB / BOMBARD) vs thế chỗ (CAPTURE)
    if capture and piece.piece_type != PieceType.NAVY:
        sheltered_hq = is_hq_sheltering_commander(state, target)
        if destination_terrain == Terrain.SEA or sheltered_hq:
            expected_stand = ActionType.BOMB if piece.piece_type == PieceType.AIRCRAFT else ActionType.BOMBARD
            if action.action_type != expected_stand:
                return reject(RuleCode.INVALID_ACTION, "Đánh mục tiêu biển hoặc Sở chỉ huy che chở Tư lệnh phải đứng tại chỗ.")
        elif piece.piece_type == PieceType.AIRCRAFT:
            if target.piece_type == PieceType.AIRCRAFT and action.action_type != ActionType.CAPTURE:
                return reject(RuleCode.INVALID_ACTION, "Không chiến Máy bay vs Máy bay phải thế chỗ.")
        else:
            if action.action_type != ActionType.CAPTURE:
                return reject(RuleCode.INVALID_ACTION, "Quân bộ ăn quân trên bộ phải dùng CAPTURE thế chỗ.")

    # Kiểm tra địa hình điểm đến và vượt sông sâu
    allow_sea_boarding = action.action_type == ActionType.BOARD and target.piece_type == PieceType.NAVY
    skip_terrain_for_stand_fire = (
        capture
        and (
            (piece.piece_type != PieceType.NAVY and destination_terrain == Terrain.SEA)
            or (piece.piece_type == PieceType.NAVY and navy_vs_land)
        )
    )
    if not skip_terrain_for_stand_fire:
        terrain_chk = _terrain_ok(
            state, piece, start, action.end, capture, allow_sea_boarding=allow_sea_boarding
        )
        if not terrain_chk.valid:
            return terrain_chk

    # Kiểm tra Tư lệnh đối mặt dọc tuyến di chuyển của Tư lệnh
    if piece.piece_type == PieceType.COMMANDER and action.action_type in (ActionType.MOVE, ActionType.CAPTURE, ActionType.BOARD):
        removed = {target.id} if capture and target is not None else set()
        for step_pos in (*path_points(start, action.end), action.end):
            moved = None if action.action_type == ActionType.BOARD and step_pos == action.end else (piece.id, step_pos)
            rem = removed | ({piece.id} if action.action_type == ActionType.BOARD and step_pos == action.end else set())
            if step_pos != action.end:
                rem = set()
                moved = (piece.id, step_pos)
            exp = validate_commander_exposure(state, removed=rem, moved=moved)
            if not exp.valid:
                return exp

    # Kiểm tra Tư lệnh đối mặt sau nước đi
    if action.action_type == ActionType.BOARD:
        exp = validate_commander_exposure(state, removed={piece.id})
    elif action.action_type == ActionType.PICKUP:
        exp = validate_commander_exposure(state, removed={target.id}, moved=(piece.id, action.end))
    elif action.action_type == ActionType.MOVE:
        if (not action.carry_cargo or piece.piece_type == PieceType.HEADQUARTERS) and piece.cargo:
            # Quân cõng / Tư lệnh ở lại vị trí start nên vị trí start vẫn có quân chắn
            exp = validate_commander_exposure(state, moved=None)
        else:
            exp = validate_commander_exposure(state, moved=(piece.id, action.end))
    elif action.action_type == ActionType.CAPTURE:
        removed_ids = {target.id} if not is_hq_sheltering_commander(state, target) else set()
        if (not action.carry_cargo or piece.piece_type == PieceType.HEADQUARTERS) and piece.cargo:
            exp = validate_commander_exposure(state, removed=removed_ids, moved=None)
        else:
            exp = validate_commander_exposure(state, removed=removed_ids, moved=(piece.id, action.end))
    else:  # BOMB / BOMBARD
        removed_ids = {target.id} if not is_hq_sheltering_commander(state, target) else set()
        exp = validate_commander_exposure(state, removed=removed_ids, moved=None)
    if not exp.valid:
        return exp

    return accept()


def validate_action(state: GameState, action: AtomicAction) -> RuleResult:
    """Kiểm tra đầy đủ tính hợp lệ của một AtomicAction (gồm cả an toàn Tư lệnh)."""
    verdict = validate_structural_action(state, action)
    if not verdict.valid:
        return verdict
    from .engine import preview_action_safety
    return preview_action_safety(state, action)


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
    if carrier.piece_type == PieceType.HEADQUARTERS and carrier.is_heroic:
        return reject(RuleCode.INVALID_TRANSPORT, "Sở chỉ huy Anh hùng không chở Tư lệnh.")
    if passenger.piece_type not in _CARRIER_TYPES.get(carrier.piece_type, frozenset()):
        return reject(RuleCode.INVALID_TRANSPORT, "Phương tiện không chở được loại quân này.")
    return accept()


def validate_transport_plan(state: GameState, plan: dict[str, list[str]]) -> RuleResult:
    """Kiểm tra quan hệ vận chuyển đầy đủ, vòng lặp và sức chứa lồng nhau."""
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
    """Q19: Kiểm tra những quân còn tại gốc có thể tạo tổ hợp duy nhất."""
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
    """Q20: từ chối lựa chọn gây bế tắc không thể xác nhận hợp lệ."""
    check = validate_compound_budget(actions_used)
    if not check.valid:
        return check
    if not has_legal_completion:
        return reject(RuleCode.INVALID_COMPOUND, "Không còn chuỗi hành động hợp lệ để hoàn tất triển khai.")
    return accept()


def anti_air_offsets(piece_type: PieceType, heroic: bool = False) -> frozenset[tuple[int, int]]:
    """Vùng phòng không theo (dy,dx), không gồm tọa độ trung tâm."""
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
    """Tập các giao điểm bị phòng không phe defender kiểm soát."""
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


def aa_danger_positions(state: GameState, defender: Player) -> frozenset[Position]:
    """Toàn bộ giao điểm vùng phòng không lẫn tọa độ đứng của đơn vị phòng không phe defender."""
    danger = set(defended_positions(state, defender))
    for piece in state.pieces.values():
        if piece.owner != defender or piece.carried_by is not None or piece.position is None:
            continue
        if piece.piece_type in (PieceType.ANTI_AIRCRAFT, PieceType.MISSILE, PieceType.NAVY):
            danger.add(piece.position)
    return frozenset(danger)


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
    """Q10: máy bay đang chịu đe dọa trì hoãn thực hiện BOMB."""
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
    """Q11: máy bay triển khai từ tàu chịu vùng phòng không ngay lập tức."""
    if aircraft.piece_type != PieceType.AIRCRAFT:
        raise ValueError("Chỉ áp dụng cho Máy bay.")
    if aircraft.is_heroic:
        return AirDefenseResult(AirDefenseEffect.NONE, "Máy bay Anh hùng miễn phòng không.")
    enemy = Player.BLUE if aircraft.owner == Player.RED else Player.RED
    danger = aa_danger_positions(state, enemy)
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
    """Q10/Q12: kiểm tra máy bay còn ở vùng phòng không khi tới lượt đối phương."""
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
    """K03: liệt kê quân có khả năng tấn công trực tiếp Tư lệnh địch."""
    result = set()
    occ_map: dict[Position, Piece] = {
        p.position: p
        for p in state.pieces.values()
        if p.carried_by is None and p.position is not None
    }
    for piece in state.pieces.values():
        if piece.piece_type == PieceType.COMMANDER:
            continue
        enemy = Player.BLUE if piece.owner == Player.RED else Player.RED
        enemy_cmd = next(
            (p for p in state.pieces.values() if p.owner == enemy and p.piece_type == PieceType.COMMANDER),
            None,
        )
        if enemy_cmd is None:
            continue
        dest = _origin(state, enemy_cmd)
        if dest is None:
            continue
        if _piece_threatens_square(state, piece, dest, occ_map):
            result.add(piece.id)
    return frozenset(result)
