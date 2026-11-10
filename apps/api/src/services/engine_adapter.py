"""
Commander Chess AI — Engine Adapter Interface & Authoritative Implementation

NOTE (AGENTS.md Rule 3 & 6):
- Authoritative game rules and state transitions belong to `packages/commander_game_engine`.
- `AuthoritativeEngineAdapter` integrates directly with `packages/commander_game_engine`.
- `MockEngineAdapter` serves as a strict rule-parity helper/fallback for legacy API
  explicit compound flags (`is_compound_action=True` on standalone moves) while keeping
  identical rules enforcement across all helpers.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Set, Any
import time

from ..models.enums import (
    Side,
    PieceType,
    ActionType,
    EventType,
    GameMode,
    GameStatus,
    TurnPhase,
    TerminationReason,
)
from ..models.common import Position
from ..models.game import (
    PieceState,
    LegalAction,
    GameEvent,
    GameState,
    GameResultDTO,
    ActionRequest,
)

PIECE_NOTATION_SYMBOL: Dict[PieceType, str] = {
    PieceType.COMMANDER: "⋆",
    PieceType.MISSILE: "L",
    PieceType.HEADQUARTERS: "S",
    PieceType.TANK: "T",
    PieceType.AIRCRAFT: "K",
    PieceType.INFANTRY: "B",
    PieceType.NAVY: "H",
    PieceType.ANTI_AIR: "F",
    PieceType.ENGINEER: "C",
    PieceType.MILITIA: "D",
    PieceType.ARTILLERY: "A",
}

PIECE_SCORES: Dict[PieceType, int] = {
    PieceType.COMMANDER: 100,
    PieceType.HEADQUARTERS: 100,
    PieceType.AIRCRAFT: 40,
    PieceType.NAVY: 80,
    PieceType.MISSILE: 20,
    PieceType.TANK: 20,
    PieceType.ARTILLERY: 30,
    PieceType.ANTI_AIR: 10,
    PieceType.ENGINEER: 10,
    PieceType.INFANTRY: 10,
    PieceType.MILITIA: 10,
}

ORTHOGONAL = [(0, 1), (0, -1), (-1, 0), (1, 0)]
DIAGONAL = [(1, 1), (1, -1), (-1, 1), (-1, -1)]
ALL_8 = ORTHOGONAL + DIAGONAL

# 8 knight offsets for Heroic Missile Air Defense Zone (Q6)
KNIGHT_OFFSETS = [
    (-1, -2), (1, -2), (-1, 2), (1, 2),
    (-2, -1), (2, -1), (-2, 1), (2, 1),
]


def is_inside_board(x: int, y: int) -> bool:
    return 0 <= x <= 10 and 0 <= y <= 11


def is_sea_square(x: int) -> bool:
    return x <= 1


def is_ford_square(x: int, y: int) -> bool:
    return (x == 5 or x == 7) and (y == 5 or y == 6)


def is_shore_square(x: int, y: int) -> bool:
    return x == 2 or ((y == 5 or y == 6) and 2 <= x <= 10 and not is_ford_square(x, y))


def is_river_square(x: int, y: int) -> bool:
    return (y == 5 or y == 6) and 2 <= x <= 10


def is_crossing_river(from_y: int, to_y: int) -> bool:
    return (from_y <= 5 and to_y >= 6) or (from_y >= 6 and to_y <= 5)


def can_navy_occupy_square(nx: int, ny: int) -> bool:
    if is_ford_square(nx, ny):
        return False
    return nx <= 2 or ny == 5 or ny == 6


def is_navy_land_diagonal(x1: int, y1: int, x2: int, y2: int) -> bool:
    """Kiểm tra đường chéo Hải quân có cắt qua vùng đất liền giữa bờ biển và bờ sông hay không."""
    if x1 == x2 or y1 == y2:
        return False
    if min(x1, x2) >= 2 and ((y1 >= 7 and y2 <= 6) or (y2 >= 7 and y1 <= 6)):
        return True
    if min(x1, x2) >= 2 and ((y1 <= 4 and y2 >= 5) or (y2 <= 4 and y1 >= 5)):
        return True
    return False


def can_piece_cross_river_to_empty(
    piece_type: PieceType,
    from_x: int,
    from_y: int,
    to_x: int,
    to_y: int,
) -> bool:
    """Kiểm tra xem quân có được tự vượt sông sâu sang ô trống không (RULE-RIVER-001 & DEC-018)."""
    if not is_crossing_river(from_y, to_y):
        return True
    if from_x == to_x and from_x in (5, 7):
        return True
    if piece_type in (PieceType.ANTI_AIR, PieceType.ARTILLERY, PieceType.MISSILE):
        return False
    return True


def get_all_carried_piece_ids(carrier_id: str, pieces: List[PieceState]) -> List[str]:
    """Lấy danh sách ID toàn bộ quân đang được cõng trực tiếp/gián tiếp."""
    collected: List[str] = []
    queue = [carrier_id]
    seen = {carrier_id}
    while queue:
        cid = queue.pop(0)
        for other in pieces:
            if other.is_alive and other.carried_by_id == cid and other.piece_id not in seen:
                seen.add(other.piece_id)
                collected.append(other.piece_id)
                queue.append(other.piece_id)
    return collected


def get_root_carrier(piece: PieceState, pieces: List[PieceState]) -> PieceState:
    """Tìm quân gốc đang đứng trực tiếp trên bàn cờ."""
    by_id = {p.piece_id: p for p in pieces if p.is_alive}
    cursor = piece
    seen = {piece.piece_id}
    while cursor.carried_by_id is not None:
        parent = by_id.get(cursor.carried_by_id)
        if not parent or parent.piece_id in seen:
            break
        seen.add(parent.piece_id)
        cursor = parent
    return cursor


def can_board_carrier(passenger: PieceState, carrier: PieceState) -> bool:
    if carrier.side != passenger.side or not carrier.is_alive or not passenger.is_alive:
        return False
    if carrier.carried_by_id is not None:
        return False
    if passenger.piece_id == carrier.piece_id:
        return False
    current_passengers = len(carrier.carrying_piece_ids)

    if carrier.type == PieceType.TANK:
        return current_passengers < 2 and passenger.type in (
            PieceType.INFANTRY,
            PieceType.MILITIA,
            PieceType.COMMANDER,
        )

    if carrier.type == PieceType.AIRCRAFT:
        return current_passengers < 2 and passenger.type in (
            PieceType.INFANTRY,
            PieceType.MILITIA,
            PieceType.COMMANDER,
            PieceType.TANK,
        )

    if carrier.type == PieceType.NAVY:
        return current_passengers < 2 and passenger.type in (
            PieceType.INFANTRY,
            PieceType.MILITIA,
            PieceType.COMMANDER,
            PieceType.TANK,
            PieceType.AIRCRAFT,
        )

    if carrier.type == PieceType.ENGINEER:
        is_at_river_bank = carrier.position.y in (5, 6)
        return is_at_river_bank and current_passengers < 1 and passenger.type in (
            PieceType.ARTILLERY,
            PieceType.ANTI_AIR,
            PieceType.MISSILE,
        )

    if carrier.type == PieceType.HEADQUARTERS:
        if carrier.is_hero:
            return False
        return current_passengers < 1 and passenger.type == PieceType.COMMANDER

    return False


def _can_nest_pair(inner: PieceState, outer: PieceState, pieces: List[PieceState], origin_y: int) -> bool:
    """Kiểm tra khi phương tiện gốc tách lẻ bỏ lại 2 quân cõng trực tiếp thì 1 quân có cõng được quân kia không."""
    outer_free = outer.model_copy(update={"carried_by_id": None, "carrying_piece_ids": []})
    inner_free = inner.model_copy(update={"carried_by_id": None})
    if not can_board_carrier(inner_free, outer_free):
        return False
    if outer.type == PieceType.ENGINEER and origin_y not in (5, 6):
        return False
    total_nested = 1 + len(get_all_carried_piece_ids(inner.piece_id, pieces))
    max_cap = 1 if outer.type in (PieceType.ENGINEER, PieceType.HEADQUARTERS) else 2
    return total_nested <= max_cap


def can_carrier_leave_cargo_behind(carrier: PieceState, pieces: List[PieceState]) -> bool:
    """Kiểm tra phương tiện có thể di chuyển bỏ lại toàn bộ quân đang cõng ở vị trí xuất phát hay không."""
    direct = [p for p in pieces if p.is_alive and p.carried_by_id == carrier.piece_id]
    if not direct:
        return True
    root = get_root_carrier(carrier, pieces)
    if is_sea_square(root.position.x):
        return False
    if len(direct) == 1:
        return True
    if len(direct) == 2:
        p1, p2 = direct[0], direct[1]
        return (
            _can_nest_pair(p2, p1, pieces, root.position.y)
            or _can_nest_pair(p1, p2, pieces, root.position.y)
        )
    return False


def delayed_solitary_hq_commander_id(pieces: List[PieceState], side: Side) -> Optional[str]:
    """Quy tắc phong Anh hùng trễ cho Sở chỉ huy duy nhất:
    Khi một phe chỉ còn Tư lệnh + 1 Sở chỉ huy (chưa Anh hùng) và Tư lệnh đang trú bên trong
    Sở chỉ huy đó, Sở chỉ huy CHƯA được phong Anh hùng; người chơi chỉ được đi nước đưa
    Tư lệnh rời Sở chỉ huy đó (sau khi rời sẽ phong Anh hùng ngay lập tức).
    """
    alive = [p for p in pieces if p.is_alive and p.side == side]
    non_cmd_non_hq = [p for p in alive if p.type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS)]
    hq_pieces = [p for p in alive if p.type == PieceType.HEADQUARTERS]
    cmd = next((p for p in alive if p.type == PieceType.COMMANDER), None)
    if (
        cmd is not None
        and len(non_cmd_non_hq) == 0
        and len(hq_pieces) == 1
        and not hq_pieces[0].is_hero
        and cmd.carried_by_id == hq_pieces[0].piece_id
    ):
        return cmd.piece_id
    return None


def get_air_defense_zones(target_side: Side, pieces: List[PieceState]) -> Set[Tuple[int, int]]:
    zones: Set[Tuple[int, int]] = set()
    aa_units = [
        p for p in pieces
        if p.is_alive and p.carried_by_id is None and p.side == target_side
        and p.type in (PieceType.ANTI_AIR, PieceType.MISSILE, PieceType.NAVY)
    ]

    for unit in aa_units:
        x, y = unit.position.x, unit.position.y

        if unit.type in (PieceType.ANTI_AIR, PieceType.NAVY):
            max_straight = 2 if unit.is_hero else 1
            for dx, dy in ORTHOGONAL:
                for r in range(1, max_straight + 1):
                    nx, ny = x + dx * r, y + dy * r
                    if is_inside_board(nx, ny):
                        zones.add((nx, ny))
            if unit.is_hero:
                for dx, dy in DIAGONAL:
                    nx, ny = x + dx, y + dy
                    if is_inside_board(nx, ny):
                        zones.add((nx, ny))

        elif unit.type == PieceType.MISSILE:
            straight_range = 3 if unit.is_hero else 2
            diag_range = 2 if unit.is_hero else 1
            for dx, dy in ORTHOGONAL:
                for r in range(1, straight_range + 1):
                    nx, ny = x + dx * r, y + dy * r
                    if is_inside_board(nx, ny):
                        zones.add((nx, ny))
            for dx, dy in DIAGONAL:
                for r in range(1, diag_range + 1):
                    nx, ny = x + dx * r, y + dy * r
                    if is_inside_board(nx, ny):
                        zones.add((nx, ny))
            if unit.is_hero:
                for dx, dy in KNIGHT_OFFSETS:
                    nx, ny = x + dx, y + dy
                    if is_inside_board(nx, ny):
                        zones.add((nx, ny))

    return zones


def is_aircraft_flight_affected_by_aa(
    from_pos: Position,
    to_pos: Position,
    enemy_aa_zones: Set[Tuple[int, int]],
    enemy_aa_units: Optional[List[PieceState]] = None,
) -> bool:
    """Kiểm tra toàn bộ hành trình bay có chạm hoặc cắt qua vùng phòng không hay không."""
    def is_aa_point(x: int, y: int) -> bool:
        if (x, y) in enemy_aa_zones:
            return True
        if enemy_aa_units:
            return any(u.is_alive and u.position.x == x and u.position.y == y for u in enemy_aa_units)
        return False

    if is_aa_point(from_pos.x, from_pos.y) or is_aa_point(to_pos.x, to_pos.y):
        return True

    step_x = 1 if to_pos.x > from_pos.x else (-1 if to_pos.x < from_pos.x else 0)
    step_y = 1 if to_pos.y > from_pos.y else (-1 if to_pos.y < from_pos.y else 0)
    total_steps = max(abs(to_pos.x - from_pos.x), abs(to_pos.y - from_pos.y))
    for s in range(1, total_steps):
        if is_aa_point(from_pos.x + step_x * s, from_pos.y + step_y * s):
            return True
    return False


def is_commanders_facing(pieces: List[PieceState]) -> bool:
    """Kiểm tra hai Tư lệnh đối mặt trực tiếp không có quân chắn.
    Tư lệnh đang nằm trên phương tiện/trong Sở chỉ huy (bất kể Xe tăng, Máy bay, Tàu chiến hay HQ)
    đều được che chắn khỏi đối mặt trực tiếp với Tư lệnh đối phương.
    """
    red_cmd = next((p for p in pieces if p.is_alive and p.side == Side.RED and p.type == PieceType.COMMANDER), None)
    blue_cmd = next((p for p in pieces if p.is_alive and p.side == Side.BLUE and p.type == PieceType.COMMANDER), None)

    if not red_cmd or not blue_cmd:
        return False

    if red_cmd.carried_by_id is not None:
        if any(p.is_alive and p.piece_id == red_cmd.carried_by_id for p in pieces):
            return False
    if blue_cmd.carried_by_id is not None:
        if any(p.is_alive and p.piece_id == blue_cmd.carried_by_id for p in pieces):
            return False

    visible = [p for p in pieces if p.is_alive and p.carried_by_id is None]

    if red_cmd.position.x == blue_cmd.position.x:
        x = red_cmd.position.x
        min_y = min(red_cmd.position.y, blue_cmd.position.y)
        max_y = max(red_cmd.position.y, blue_cmd.position.y)
        has_obstacle = any(
            p.position.x == x and min_y < p.position.y < max_y
            for p in visible
        )
        if not has_obstacle:
            return True

    if red_cmd.position.y == blue_cmd.position.y:
        y = red_cmd.position.y
        min_x = min(red_cmd.position.x, blue_cmd.position.x)
        max_x = max(red_cmd.position.x, blue_cmd.position.x)
        has_obstacle = any(
            p.position.y == y and min_x < p.position.x < max_x
            for p in visible
        )
        if not has_obstacle:
            return True

    return False


def is_hq_facing_enemy_commander(hq: PieceState, enemy_cmd: PieceState, pieces: List[PieceState]) -> bool:
    if not enemy_cmd.is_alive or enemy_cmd.carried_by_id is not None:
        return False
    visible = [p for p in pieces if p.is_alive and p.carried_by_id is None]
    if hq.position.x == enemy_cmd.position.x:
        x = hq.position.x
        min_y = min(hq.position.y, enemy_cmd.position.y)
        max_y = max(hq.position.y, enemy_cmd.position.y)
        has_obstacle = any(
            p.position.x == x and min_y < p.position.y < max_y and p.piece_id not in (hq.piece_id, enemy_cmd.piece_id)
            for p in visible
        )
        if not has_obstacle:
            return True

    if hq.position.y == enemy_cmd.position.y:
        y = hq.position.y
        min_x = min(hq.position.x, enemy_cmd.position.x)
        max_x = max(hq.position.x, enemy_cmd.position.x)
        has_obstacle = any(
            p.position.y == y and min_x < p.position.x < max_x and p.piece_id not in (hq.piece_id, enemy_cmd.piece_id)
            for p in visible
        )
        if not has_obstacle:
            return True

    return False


def is_hq_sheltering_commander(target: PieceState, pieces: List[PieceState]) -> bool:
    if target.type != PieceType.HEADQUARTERS:
        return False
    return any(
        p.is_alive and p.type == PieceType.COMMANDER and p.carried_by_id == target.piece_id
        for p in pieces
    )


def _piece_threatens_square(
    pieces: List[PieceState],
    p: PieceState,
    target_x: int,
    target_y: int,
    piece_map: Dict[Tuple[int, int], PieceState],
) -> bool:
    """Kiểm tra một quân (kể cả đang ngồi trên phương tiện) có tấn công/chiếu được vào (target_x, target_y) không."""
    if p.type == PieceType.HEADQUARTERS and not p.is_hero:
        return False

    origin_piece = get_root_carrier(p, pieces) if p.carried_by_id is not None else p
    px, py = origin_piece.position.x, origin_piece.position.y
    if px == target_x and py == target_y:
        return False

    # Quân đang ngồi trên phương tiện địch muốn triển khai ăn trực tiếp: không thể thế chỗ trên biển (trừ Navy).
    if p.carried_by_id is not None and is_sea_square(target_x) and p.type != PieceType.NAVY:
        return False

    dx = target_x - px
    dy = target_y - py
    adx = abs(dx)
    ady = abs(dy)
    is_orth = (adx == 0 or ady == 0)
    is_diag = (adx == ady)
    if not is_orth and not is_diag:
        return False

    dist = max(adx, ady)
    step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
    step_y = 0 if dy == 0 else (1 if dy > 0 else -1)
    blocked = any((px + step_x * s, py + step_y * s) in piece_map for s in range(1, dist))

    if p.type == PieceType.COMMANDER:
        if p.is_hero:
            return dist <= 2 and not blocked
        return is_orth and dist == 1

    if p.type in (PieceType.INFANTRY, PieceType.ENGINEER, PieceType.ANTI_AIR):
        dirs_ok = True if p.is_hero else is_orth
        max_r = 2 if p.is_hero else 1
        return dirs_ok and dist <= max_r and not blocked

    if p.type == PieceType.MILITIA:
        return dist <= (2 if p.is_hero else 1) and not blocked

    if p.type == PieceType.TANK:
        dirs_ok = True if p.is_hero else is_orth
        max_r = 3 if p.is_hero else 2
        return dirs_ok and dist <= max_r and not blocked

    if p.type == PieceType.MISSILE:
        # Tên lửa được phép ăn xuyên vật cản (ngang/dọc và chéo)
        max_r = (3 if p.is_hero else 2) if is_orth else (2 if p.is_hero else 1)
        return dist <= max_r

    if p.type == PieceType.ARTILLERY:
        return dist <= (4 if p.is_hero else 3)

    if p.type == PieceType.AIRCRAFT:
        return dist <= (5 if p.is_hero else 4)

    if p.type == PieceType.NAVY:
        if not can_navy_occupy_square(px, py):
            return False
        target_occ = piece_map.get((target_x, target_y))
        if target_occ is not None and target_occ.type == PieceType.NAVY:
            max_nav = 5 if p.is_hero else 4
            if dist > max_nav:
                return False
            for s in range(1, dist + 1):
                nx, ny = px + step_x * s, py + step_y * s
                prev_x, prev_y = px + step_x * (s - 1), py + step_y * (s - 1)
                if is_ford_square(nx, ny) or not can_navy_occupy_square(nx, ny):
                    return False
                if is_navy_land_diagonal(prev_x, prev_y, nx, ny):
                    return False
                if s < dist:
                    occ = piece_map.get((nx, ny))
                    if occ is not None:
                        if occ.type == PieceType.NAVY or occ.side != p.side:
                            return False
            return True
        # Pháo hạm bắn vào đất liền / mục tiêu khác (tầm 3, Anh hùng 4), vượt đất liền/vật cản
        return dist <= (4 if p.is_hero else 3)

    if p.type == PieceType.HEADQUARTERS:
        return p.is_hero and dist <= 2 and not blocked

    return False


def is_square_attacked_by_enemy(
    pieces: List[PieceState],
    target_x: int,
    target_y: int,
    enemy_side: Side,
) -> bool:
    """Kiểm tra một ô (target_x, target_y) có đang nằm trong tầm tấn công/chiếu của bất kỳ quân địch nào không (kể cả quân ngồi trên phương tiện)."""
    piece_map: Dict[Tuple[int, int], PieceState] = {
        (p.position.x, p.position.y): p
        for p in pieces
        if p.is_alive and p.carried_by_id is None
    }

    for p in pieces:
        if not p.is_alive or p.side != enemy_side:
            continue
        if _piece_threatens_square(pieces, p, target_x, target_y, piece_map):
            return True

    return False


def is_commander_in_check(pieces: List[PieceState], side: Side) -> bool:
    """Kiểm tra xem Tư lệnh của một phe có đang bị chiếu hay không (DEC-019)."""
    cmd = next((p for p in pieces if p.is_alive and p.side == side and p.type == PieceType.COMMANDER), None)
    if not cmd:
        return False
    enemy_side = Side.BLUE if side == Side.RED else Side.RED
    if cmd.carried_by_id is not None:
        carrier = next((p for p in pieces if p.is_alive and p.piece_id == cmd.carried_by_id), None)
        if not carrier:
            return False
        if carrier.type == PieceType.HEADQUARTERS and not carrier.is_hero:
            return False  # Trú ẩn an toàn trong Sở chỉ huy thường
        root = get_root_carrier(carrier, pieces)
        return is_square_attacked_by_enemy(pieces, root.position.x, root.position.y, enemy_side)

    return is_square_attacked_by_enemy(pieces, cmd.position.x, cmd.position.y, enemy_side)


def _apply_hero_promotions(pieces: List[PieceState]) -> List[PieceState]:
    """Tự phong Anh hùng cho quân bảo vệ cuối cùng & Sở chỉ huy duy nhất (áp dụng quy tắc phong trễ)."""
    updated = pieces
    for s in (Side.RED, Side.BLUE):
        alive_pieces = [p for p in updated if p.is_alive and p.side == s]
        non_cmd_non_hq = [p for p in alive_pieces if p.type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS)]
        hq_pieces = [p for p in alive_pieces if p.type == PieceType.HEADQUARTERS]
        cmd = next((p for p in alive_pieces if p.type == PieceType.COMMANDER), None)
        if len(non_cmd_non_hq) == 1 and not non_cmd_non_hq[0].is_hero:
            hero_id = non_cmd_non_hq[0].piece_id
            updated = [p.model_copy(update={"is_hero": True}) if p.piece_id == hero_id else p for p in updated]
        elif len(non_cmd_non_hq) == 0 and len(hq_pieces) == 1 and not hq_pieces[0].is_hero:
            sole_hq = hq_pieces[0]
            if cmd is not None and cmd.carried_by_id == sole_hq.piece_id:
                continue  # Phong trễ: chờ Tư lệnh rời Sở chỉ huy
            hero_hq_id = sole_hq.piece_id
            updated = [
                p.model_copy(update={"is_hero": True})
                if p.piece_id == hero_hq_id else p
                for p in updated
            ]
    return updated


def _detach_cargo_map(
    actor: PieceState,
    origin: Position,
    pieces: List[PieceState],
) -> Dict[str, Tuple[Optional[str], Position]]:
    """Tính map {piece_id: (new_carried_by_id, new_pos)} cho quân được chở bị bỏ lại tại origin."""
    direct = [p for p in pieces if p.is_alive and p.carried_by_id == actor.piece_id]
    if not direct:
        return {}
    if len(direct) == 1:
        return {direct[0].piece_id: (None, origin)}
    p1, p2 = direct[0], direct[1]
    if _can_nest_pair(p2, p1, pieces, origin.y):
        root_p, nested_p = p1, p2
    else:
        root_p, nested_p = p2, p1
    result: Dict[str, Tuple[Optional[str], Position]] = {
        root_p.piece_id: (None, origin),
        nested_p.piece_id: (root_p.piece_id, origin),
    }
    for sub_id in get_all_carried_piece_ids(nested_p.piece_id, pieces):
        sub_p = next((x for x in pieces if x.piece_id == sub_id), None)
        if sub_p:
            result[sub_id] = (sub_p.carried_by_id, origin)
    return result


def simulate_action(action: LegalAction, pieces: List[PieceState]) -> List[PieceState]:
    if action.action_type == ActionType.END_TURN:
        return pieces

    actor = next((p for p in pieces if p.piece_id == action.piece_id and p.is_alive), None)
    if not actor:
        return pieces
    target = (
        next((p for p in pieces if p.piece_id == action.target_piece_id and p.is_alive), None)
        if action.target_piece_id
        else None
    )
    is_carrier_pickup = (
        action.action_type == ActionType.BOARD
        and target is not None
        and can_board_carrier(passenger=target, carrier=actor)
    )

    actor_origin = get_root_carrier(actor, pieces).position
    enemy_side = Side.BLUE if actor.side == Side.RED else Side.RED
    enemy_aa_zones = get_air_defense_zones(enemy_side, pieces)
    enemy_aa_units = [
        p for p in pieces
        if p.is_alive and p.carried_by_id is None and p.side == enemy_side
        and p.type in (PieceType.ANTI_AIR, PieceType.MISSILE, PieceType.NAVY)
    ]
    is_actor_aircraft = actor.type == PieceType.AIRCRAFT and not actor.is_hero
    is_target_aa_unit = any(
        u.position.x == action.to_pos.x and u.position.y == action.to_pos.y
        for u in enemy_aa_units
    )
    is_in_aa_zone = (
        is_actor_aircraft
        and action.action_type != ActionType.END_TURN
        and (
            is_target_aa_unit
            or is_aircraft_flight_affected_by_aa(actor_origin, action.to_pos, enemy_aa_zones, enemy_aa_units)
        )
    )

    actor_descendants = set(get_all_carried_piece_ids(actor.piece_id, pieces))
    target_descendants = set(get_all_carried_piece_ids(target.piece_id, pieces)) if target else set()

    leave_behind = (
        not action.carry_cargo
        and action.action_type in (ActionType.MOVE, ActionType.CAPTURE_REPLACE)
        and bool(actor_descendants)
    ) or (
        actor.type == PieceType.HEADQUARTERS
        and action.action_type in (ActionType.MOVE, ActionType.CAPTURE_REPLACE)
        and bool(actor_descendants)
    )
    detached_map = _detach_cargo_map(actor, actor_origin, pieces) if leave_behind else {}

    new_pieces: List[PieceState] = []
    for p in pieces:
        if action.action_type == ActionType.BOARD and is_carrier_pickup:
            if p.piece_id == action.piece_id:
                new_pieces.append(p.model_copy(update={"position": action.to_pos, "carried_by_id": None}))
            elif p.piece_id == action.target_piece_id:
                new_pieces.append(p.model_copy(update={"position": action.to_pos, "carried_by_id": action.piece_id}))
            elif p.piece_id in actor_descendants or p.piece_id in target_descendants:
                new_pieces.append(p.model_copy(update={"position": action.to_pos}))
            else:
                new_pieces.append(p)
            continue

        # Target destroyed / boarded
        if action.target_piece_id and p.piece_id == action.target_piece_id:
            if action.action_type == ActionType.BOARD:
                new_pieces.append(p.model_copy(update={
                    "carrying_piece_ids": p.carrying_piece_ids + [action.piece_id]
                }))
            else:
                new_pieces.append(p.model_copy(update={"is_alive": False, "carried_by_id": None}))
            continue

        # Target's carried passengers
        if (
            action.target_piece_id
            and action.action_type != ActionType.BOARD
            and p.piece_id in target_descendants
        ):
            if target and target.type == PieceType.HEADQUARTERS:
                if p.carried_by_id == target.piece_id:
                    new_pieces.append(p.model_copy(update={"carried_by_id": None, "is_alive": True, "position": target.position}))
                else:
                    new_pieces.append(p.model_copy(update={"position": target.position}))
            else:
                new_pieces.append(p.model_copy(update={"is_alive": False, "carried_by_id": None}))
            continue

        # Actor piece
        if p.piece_id == action.piece_id:
            if is_in_aa_zone:
                new_pieces.append(p.model_copy(update={
                    "is_alive": False,
                    "position": action.to_pos,
                    "carried_by_id": None,
                }))
            elif action.action_type == ActionType.CAPTURE_STAND:
                new_pieces.append(p)
            elif action.action_type == ActionType.BOARD:
                new_pieces.append(p.model_copy(update={
                    "position": action.to_pos,
                    "carried_by_id": action.target_piece_id,
                }))
            else:
                new_pieces.append(p.model_copy(update={
                    "position": action.to_pos,
                    "carried_by_id": None,
                }))
            continue

        # Actor's carried descendants
        if p.piece_id in actor_descendants:
            if p.piece_id in detached_map:
                new_cb, new_pos = detached_map[p.piece_id]
                new_pieces.append(p.model_copy(update={"carried_by_id": new_cb, "position": new_pos}))
            elif is_in_aa_zone:
                new_pieces.append(p.model_copy(update={"is_alive": False, "carried_by_id": None}))
            elif action.action_type == ActionType.CAPTURE_STAND:
                new_pieces.append(p)
            elif action.action_type == ActionType.BOARD:
                new_pieces.append(p.model_copy(update={"position": action.to_pos}))
            else:
                new_pieces.append(p.model_copy(update={"position": action.to_pos}))
            continue

        new_pieces.append(p)

    # Đồng bộ 2 chiều và tọa độ quân được chở theo quân gốc
    synced: List[PieceState] = []
    for p in new_pieces:
        updated_cargo = [
            other.piece_id for other in new_pieces
            if other.is_alive and other.carried_by_id == p.piece_id
        ]
        if p.is_alive and p.carried_by_id is not None:
            root = get_root_carrier(p, new_pieces)
            synced.append(p.model_copy(update={"carrying_piece_ids": updated_cargo, "position": root.position}))
        else:
            synced.append(p.model_copy(update={"carrying_piece_ids": updated_cargo}))

    return _apply_hero_promotions(synced)


def select_smart_ai_action(
    state: GameState,
    ai_side: Side,
    rng: Optional[Any] = None,
) -> Optional[LegalAction]:
    """Lựa chọn nước đi hợp lệ và an toàn cho Random / Smart AI (gồm cả tổ hợp cõng quân)."""
    import random
    choose_fn = rng.choice if rng is not None else random.choice

    if state.side_to_move == ai_side:
        state_for_ai = state
    else:
        state_for_ai = state.model_copy(
            update={
                "side_to_move": ai_side,
                "turn_phase": TurnPhase.NORMAL,
                "can_end_turn": False,
                "compound_origin": None,
                "compound_member_ids": [],
                "compound_moved_piece_ids": [],
            }
        )

    all_legal = default_engine_adapter.get_legal_actions(state_for_ai)
    end_turn_actions = [a for a in all_legal if a.action_type == ActionType.END_TURN]
    valid_actions = [
        a for a in all_legal
        if a.action_type != ActionType.END_TURN
        and any(p.piece_id == a.piece_id and p.side == ai_side and p.is_alive for p in state.pieces)
    ]

    cmd = next((p for p in state.pieces if p.is_alive and p.side == ai_side and p.type == PieceType.COMMANDER), None)

    safe_actions: List[LegalAction] = []
    for act in valid_actions:
        sim = simulate_action(act, state.pieces)
        if cmd is not None:
            cmd_after = next((p for p in sim if p.is_alive and p.piece_id == cmd.piece_id), None)
            if not cmd_after:
                continue
        if is_commanders_facing(sim) or is_commander_in_check(sim, ai_side):
            continue
        safe_actions.append(act)

    in_stack = state_for_ai.turn_phase == TurnPhase.STACK_ACTIVE

    if in_stack:
        stack_pool = list(safe_actions)
        if end_turn_actions and not is_commanders_facing(state.pieces) and not is_commander_in_check(state.pieces, ai_side):
            stack_pool.extend(end_turn_actions)
        if not stack_pool:
            return None
        return choose_fn(stack_pool)

    if not safe_actions:
        return None

    is_in_check = is_commander_in_check(state.pieces, ai_side)

    if is_in_check:
        blocking_or_capturing = [
            a for a in safe_actions
            if cmd is not None and a.piece_id != cmd.piece_id
        ]
        shelter_actions = [
            a for a in safe_actions
            if cmd is not None and a.piece_id == cmd.piece_id and a.action_type == ActionType.BOARD
        ]
        cmd_escape_actions = [
            a for a in safe_actions
            if cmd is not None and a.piece_id == cmd.piece_id and a.action_type != ActionType.BOARD
        ]
        if blocking_or_capturing:
            return choose_fn(blocking_or_capturing + shelter_actions + cmd_escape_actions)
        elif shelter_actions:
            return choose_fn(shelter_actions)
        else:
            return choose_fn(cmd_escape_actions or safe_actions)
    else:
        tactical_actions = [
            a for a in safe_actions
            if cmd is not None and a.piece_id != cmd.piece_id
        ]
        shelter_actions = [
            a for a in safe_actions
            if cmd is not None and a.piece_id == cmd.piece_id and a.action_type == ActionType.BOARD
        ]
        if tactical_actions:
            return choose_fn(tactical_actions + shelter_actions)
        return choose_fn(safe_actions)


class BaseEngineAdapter(ABC):
    @abstractmethod
    def create_initial_state(self, game_id: str, mode: GameMode) -> GameState:
        pass

    @abstractmethod
    def get_legal_actions(self, state: GameState) -> List[LegalAction]:
        pass

    @abstractmethod
    def apply_action(self, state: GameState, request: ActionRequest) -> Tuple[GameState, GameEvent]:
        pass

    @abstractmethod
    def resign(self, state: GameState, side: Side) -> GameState:
        pass

    @abstractmethod
    def draw(self, state: GameState) -> GameState:
        pass


class MockEngineAdapter(BaseEngineAdapter):
    """Rule-parity fallback & legacy-compound adapter aligned with packages/commander_game_engine."""

    def _get_initial_pieces(self) -> List[PieceState]:
        pieces: List[PieceState] = []

        # Red side (19 pieces)
        pieces.append(PieceState(piece_id="red_commander_1", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=6, y=0)))
        pieces.append(PieceState(piece_id="red_aircraft_1", side=Side.RED, type=PieceType.AIRCRAFT, position=Position(x=4, y=1)))
        pieces.append(PieceState(piece_id="red_aircraft_2", side=Side.RED, type=PieceType.AIRCRAFT, position=Position(x=8, y=1)))
        pieces.append(PieceState(piece_id="red_headquarters_1", side=Side.RED, type=PieceType.HEADQUARTERS, position=Position(x=5, y=1)))
        pieces.append(PieceState(piece_id="red_headquarters_2", side=Side.RED, type=PieceType.HEADQUARTERS, position=Position(x=7, y=1)))
        pieces.append(PieceState(piece_id="red_missile_1", side=Side.RED, type=PieceType.MISSILE, position=Position(x=6, y=2)))
        pieces.append(PieceState(piece_id="red_artillery_1", side=Side.RED, type=PieceType.ARTILLERY, position=Position(x=3, y=2)))
        pieces.append(PieceState(piece_id="red_artillery_2", side=Side.RED, type=PieceType.ARTILLERY, position=Position(x=9, y=2)))
        pieces.append(PieceState(piece_id="red_anti_air_1", side=Side.RED, type=PieceType.ANTI_AIR, position=Position(x=4, y=3)))
        pieces.append(PieceState(piece_id="red_anti_air_2", side=Side.RED, type=PieceType.ANTI_AIR, position=Position(x=8, y=3)))
        pieces.append(PieceState(piece_id="red_navy_1", side=Side.RED, type=PieceType.NAVY, position=Position(x=1, y=1)))
        pieces.append(PieceState(piece_id="red_navy_2", side=Side.RED, type=PieceType.NAVY, position=Position(x=2, y=3)))
        pieces.append(PieceState(piece_id="red_tank_1", side=Side.RED, type=PieceType.TANK, position=Position(x=5, y=3)))
        pieces.append(PieceState(piece_id="red_tank_2", side=Side.RED, type=PieceType.TANK, position=Position(x=7, y=3)))
        pieces.append(PieceState(piece_id="red_infantry_1", side=Side.RED, type=PieceType.INFANTRY, position=Position(x=2, y=4)))
        pieces.append(PieceState(piece_id="red_infantry_2", side=Side.RED, type=PieceType.INFANTRY, position=Position(x=10, y=4)))
        pieces.append(PieceState(piece_id="red_engineer_1", side=Side.RED, type=PieceType.ENGINEER, position=Position(x=3, y=4)))
        pieces.append(PieceState(piece_id="red_engineer_2", side=Side.RED, type=PieceType.ENGINEER, position=Position(x=9, y=4)))
        pieces.append(PieceState(piece_id="red_militia_1", side=Side.RED, type=PieceType.MILITIA, position=Position(x=6, y=4)))

        # Blue side (19 pieces)
        pieces.append(PieceState(piece_id="blue_commander_1", side=Side.BLUE, type=PieceType.COMMANDER, position=Position(x=6, y=11)))
        pieces.append(PieceState(piece_id="blue_aircraft_1", side=Side.BLUE, type=PieceType.AIRCRAFT, position=Position(x=4, y=10)))
        pieces.append(PieceState(piece_id="blue_aircraft_2", side=Side.BLUE, type=PieceType.AIRCRAFT, position=Position(x=8, y=10)))
        pieces.append(PieceState(piece_id="blue_headquarters_1", side=Side.BLUE, type=PieceType.HEADQUARTERS, position=Position(x=5, y=10)))
        pieces.append(PieceState(piece_id="blue_headquarters_2", side=Side.BLUE, type=PieceType.HEADQUARTERS, position=Position(x=7, y=10)))
        pieces.append(PieceState(piece_id="blue_missile_1", side=Side.BLUE, type=PieceType.MISSILE, position=Position(x=6, y=9)))
        pieces.append(PieceState(piece_id="blue_artillery_1", side=Side.BLUE, type=PieceType.ARTILLERY, position=Position(x=3, y=9)))
        pieces.append(PieceState(piece_id="blue_artillery_2", side=Side.BLUE, type=PieceType.ARTILLERY, position=Position(x=9, y=9)))
        pieces.append(PieceState(piece_id="blue_anti_air_1", side=Side.BLUE, type=PieceType.ANTI_AIR, position=Position(x=4, y=8)))
        pieces.append(PieceState(piece_id="blue_anti_air_2", side=Side.BLUE, type=PieceType.ANTI_AIR, position=Position(x=8, y=8)))
        pieces.append(PieceState(piece_id="blue_navy_1", side=Side.BLUE, type=PieceType.NAVY, position=Position(x=1, y=10)))
        pieces.append(PieceState(piece_id="blue_navy_2", side=Side.BLUE, type=PieceType.NAVY, position=Position(x=2, y=8)))
        pieces.append(PieceState(piece_id="blue_tank_1", side=Side.BLUE, type=PieceType.TANK, position=Position(x=5, y=8)))
        pieces.append(PieceState(piece_id="blue_tank_2", side=Side.BLUE, type=PieceType.TANK, position=Position(x=7, y=8)))
        pieces.append(PieceState(piece_id="blue_infantry_1", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=2, y=7)))
        pieces.append(PieceState(piece_id="blue_infantry_2", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=10, y=7)))
        pieces.append(PieceState(piece_id="blue_engineer_1", side=Side.BLUE, type=PieceType.ENGINEER, position=Position(x=3, y=7)))
        pieces.append(PieceState(piece_id="blue_engineer_2", side=Side.BLUE, type=PieceType.ENGINEER, position=Position(x=9, y=7)))
        pieces.append(PieceState(piece_id="blue_militia_1", side=Side.BLUE, type=PieceType.MILITIA, position=Position(x=6, y=7)))

        return pieces

    def create_initial_state(self, game_id: str, mode: GameMode) -> GameState:
        pieces = self._get_initial_pieces()
        state = GameState(
            game_id=game_id,
            mode=mode,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1800000, "BLUE": 1800000},
            pieces=pieces,
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )
        state.legal_actions = self.get_legal_actions(state)
        return state

    def get_legal_actions(self, state: GameState) -> List[LegalAction]:
        if state.status == GameStatus.GAME_OVER:
            return []

        active_side = state.side_to_move
        enemy_side = Side.BLUE if active_side == Side.RED else Side.RED
        actions: List[LegalAction] = []
        piece_map = {(p.position.x, p.position.y): p for p in state.pieces if p.is_alive and not p.carried_by_id}
        enemy_cmd = next((p for p in state.pieces if p.is_alive and p.side == enemy_side and p.type == PieceType.COMMANDER), None)
        own_cmd_before = next((p for p in state.pieces if p.is_alive and p.side == active_side and p.type == PieceType.COMMANDER), None)
        trap_cmd_id = delayed_solitary_hq_commander_id(state.pieces, active_side)

        in_compound_stack = state.turn_phase == TurnPhase.STACK_ACTIVE and bool(state.compound_member_ids)
        eligible_stack_ids: Optional[Set[str]] = None
        if in_compound_stack:
            if len(state.compound_moved_piece_ids) >= 3:
                eligible_stack_ids = set()
            else:
                eligible_stack_ids = set(state.compound_member_ids) - set(state.compound_moved_piece_ids)

        def can_occupy_square(piece: PieceState, nx: int, ny: int) -> bool:
            if piece.type == PieceType.NAVY:
                return can_navy_occupy_square(nx, ny)
            if is_sea_square(nx):
                target = piece_map.get((nx, ny))
                if target:
                    if target.side != piece.side or can_board_carrier(passenger=piece, carrier=target):
                        return True
                return False
            return True

        for piece in state.pieces:
            if not piece.is_alive or piece.side != active_side:
                continue
            if trap_cmd_id is not None and piece.piece_id != trap_cmd_id:
                continue

            is_carried = piece.carried_by_id is not None
            root = get_root_carrier(piece, state.pieces) if is_carried else piece
            x, y = root.position.x, root.position.y

            if eligible_stack_ids is not None:
                if piece.piece_id not in eligible_stack_ids:
                    continue
                if state.compound_origin and (x != state.compound_origin.x or y != state.compound_origin.y):
                    continue

            symbol = PIECE_NOTATION_SYMBOL.get(piece.type, "B")
            can_split_solo = (
                not is_carried
                and piece.type != PieceType.HEADQUARTERS
                and bool(piece.carrying_piece_ids)
                and can_carrier_leave_cargo_behind(piece, state.pieces)
            )

            def push_move(nx: int, ny: int):
                actions.append(
                    LegalAction(
                        action_id=f"mw_{piece.piece_id}_{nx}_{ny}",
                        action_type=ActionType.MOVE,
                        piece_id=piece.piece_id,
                        from_pos=Position(x=x, y=y),
                        to_pos=Position(x=nx, y=ny),
                        target_piece_id=None,
                        carry_cargo=True,
                        notation=f"{symbol} [{y} ; {x}] _ [{ny} ; {nx}]",
                        description=f"{piece.type.value} di chuyển đến [{ny} ; {nx}]",
                    )
                )
                if can_split_solo:
                    actions.append(
                        LegalAction(
                            action_id=f"ms_{piece.piece_id}_{nx}_{ny}",
                            action_type=ActionType.MOVE,
                            piece_id=piece.piece_id,
                            from_pos=Position(x=x, y=y),
                            to_pos=Position(x=nx, y=ny),
                            target_piece_id=None,
                            carry_cargo=False,
                            notation=f"{symbol} [{y} ; {x}] _ [{ny} ; {nx}]",
                            description=f"{piece.type.value} di chuyển một mình (để lại quân cõng) đến [{ny} ; {nx}]",
                        )
                    )

            def push_capture(nx: int, ny: int, target: PieceState, act_type: ActionType):
                if is_carried and act_type == ActionType.CAPTURE_STAND:
                    return
                act_sym = "_@_" if act_type == ActionType.CAPTURE_STAND else "@"
                target_sym = PIECE_NOTATION_SYMBOL.get(target.type, "B")
                actions.append(
                    LegalAction(
                        action_id=f"cw_{piece.piece_id}_{target.piece_id}_{act_type.value}",
                        action_type=act_type,
                        piece_id=piece.piece_id,
                        from_pos=Position(x=x, y=y),
                        to_pos=Position(x=nx, y=ny),
                        target_piece_id=target.piece_id,
                        carry_cargo=True,
                        notation=f"{symbol} [{y} ; {x}] {act_sym} {target_sym} [{ny} ; {nx}]",
                        description=f"{piece.type.value} tấn công {target.type.value} tại [{ny} ; {nx}]",
                    )
                )
                if can_split_solo and act_type == ActionType.CAPTURE_REPLACE:
                    actions.append(
                        LegalAction(
                            action_id=f"cs_{piece.piece_id}_{target.piece_id}_{act_type.value}",
                            action_type=act_type,
                            piece_id=piece.piece_id,
                            from_pos=Position(x=x, y=y),
                            to_pos=Position(x=nx, y=ny),
                            target_piece_id=target.piece_id,
                            carry_cargo=False,
                            notation=f"{symbol} [{y} ; {x}] {act_sym} {target_sym} [{ny} ; {nx}]",
                            description=f"{piece.type.value} tấn công một mình (để lại quân cõng) tại [{ny} ; {nx}]",
                        )
                    )

            def push_board(carrier: PieceState):
                if trap_cmd_id is not None and carrier.type == PieceType.HEADQUARTERS:
                    return
                carrier_sym = PIECE_NOTATION_SYMBOL.get(carrier.type, "T")
                actions.append(
                    LegalAction(
                        action_id=f"b_{piece.piece_id}_{carrier.piece_id}",
                        action_type=ActionType.BOARD,
                        piece_id=piece.piece_id,
                        from_pos=Position(x=x, y=y),
                        to_pos=Position(x=carrier.position.x, y=carrier.position.y),
                        target_piece_id=carrier.piece_id,
                        carry_cargo=True,
                        notation=f"{symbol} [{y} ; {x}] ^ {carrier_sym} [{carrier.position.y} ; {carrier.position.x}]",
                        description=f"{piece.type.value} lên {carrier.type.value} tại [{carrier.position.y} ; {carrier.position.x}]",
                    )
                )

            def push_pickup(passenger: PieceState):
                if is_carried:
                    return
                carrier_sym = PIECE_NOTATION_SYMBOL.get(piece.type, "T")
                passenger_sym = PIECE_NOTATION_SYMBOL.get(passenger.type, "B")
                actions.append(
                    LegalAction(
                        action_id=f"p_{piece.piece_id}_{passenger.piece_id}",
                        action_type=ActionType.BOARD,
                        piece_id=piece.piece_id,
                        from_pos=Position(x=x, y=y),
                        to_pos=Position(x=passenger.position.x, y=passenger.position.y),
                        target_piece_id=passenger.piece_id,
                        carry_cargo=True,
                        notation=f"{carrier_sym} [{y} ; {x}] ^ {passenger_sym} [{passenger.position.y} ; {passenger.position.x}]",
                        description=f"{piece.type.value} đến cõng {passenger.type.value} tại [{passenger.position.y} ; {passenger.position.x}]",
                    )
                )

            # 1. HEADQUARTERS
            if piece.type == PieceType.HEADQUARTERS:
                if piece.is_hero:
                    for dx, dy in ALL_8:
                        for step in range(1, 3):
                            nx, ny = x + dx * step, y + dy * step
                            if not is_inside_board(nx, ny) or not can_occupy_square(piece, nx, ny):
                                break
                            target = piece_map.get((nx, ny))
                            if not target:
                                push_move(nx, ny)
                            else:
                                if target.side != active_side:
                                    act_type = (
                                        ActionType.CAPTURE_STAND
                                        if is_sea_square(nx) or is_hq_sheltering_commander(target, state.pieces)
                                        else ActionType.CAPTURE_REPLACE
                                    )
                                    push_capture(nx, ny, target, act_type)
                                break
                continue

            # 2. MILITIA
            elif piece.type == PieceType.MILITIA:
                max_range = 2 if piece.is_hero else 1
                for dx, dy in ALL_8:
                    for step in range(1, max_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny) or not can_occupy_square(piece, nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if not target:
                            push_move(nx, ny)
                        else:
                            if target.side != active_side:
                                act_type = (
                                    ActionType.CAPTURE_STAND
                                    if is_sea_square(nx) or is_hq_sheltering_commander(target, state.pieces)
                                    else ActionType.CAPTURE_REPLACE
                                )
                                push_capture(nx, ny, target, act_type)
                            elif can_board_carrier(piece, target):
                                push_board(target)
                            break

            # 3. INFANTRY & ENGINEER
            elif piece.type in (PieceType.INFANTRY, PieceType.ENGINEER):
                dirs = ALL_8 if piece.is_hero else ORTHOGONAL
                max_range = 2 if piece.is_hero else 1
                for dx, dy in dirs:
                    for step in range(1, max_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny) or not can_occupy_square(piece, nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if not target:
                            push_move(nx, ny)
                        else:
                            if target.side != active_side:
                                act_type = (
                                    ActionType.CAPTURE_STAND
                                    if is_sea_square(nx) or is_hq_sheltering_commander(target, state.pieces)
                                    else ActionType.CAPTURE_REPLACE
                                )
                                push_capture(nx, ny, target, act_type)
                            elif piece.type == PieceType.ENGINEER and can_board_carrier(passenger=target, carrier=piece) and not target.carried_by_id:
                                push_pickup(target)
                            elif can_board_carrier(piece, target):
                                push_board(target)
                            break

            # 4. ANTI_AIR
            elif piece.type == PieceType.ANTI_AIR:
                dirs = ALL_8 if piece.is_hero else ORTHOGONAL
                max_range = 2 if piece.is_hero else 1
                for dx, dy in dirs:
                    for step in range(1, max_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny) or not can_occupy_square(piece, nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if not target:
                            if can_piece_cross_river_to_empty(PieceType.ANTI_AIR, x, y, nx, ny):
                                push_move(nx, ny)
                        else:
                            if target.side != active_side:
                                act_type = (
                                    ActionType.CAPTURE_STAND
                                    if is_sea_square(nx) or is_hq_sheltering_commander(target, state.pieces)
                                    else ActionType.CAPTURE_REPLACE
                                )
                                push_capture(nx, ny, target, act_type)
                            elif can_board_carrier(piece, target):
                                push_board(target)
                            break

            # 5. TANK
            elif piece.type == PieceType.TANK:
                dirs = ALL_8 if piece.is_hero else ORTHOGONAL
                max_range = 3 if piece.is_hero else 2
                for dx, dy in dirs:
                    for step in range(1, max_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny) or not can_occupy_square(piece, nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if not target:
                            push_move(nx, ny)
                        else:
                            if target.side != active_side:
                                act_type = (
                                    ActionType.CAPTURE_STAND
                                    if is_sea_square(nx) or is_hq_sheltering_commander(target, state.pieces)
                                    else ActionType.CAPTURE_REPLACE
                                )
                                push_capture(nx, ny, target, act_type)
                            elif can_board_carrier(passenger=target, carrier=piece) and not target.carried_by_id:
                                push_pickup(target)
                            elif can_board_carrier(passenger=piece, carrier=target):
                                push_board(target)
                            break

            # 6. MISSILE (không đi/BOARD xuyên vật cản, nhưng ĐƯỢC PHÉP ăn xuyên vật cản)
            elif piece.type == PieceType.MISSILE:
                straight_range = 3 if piece.is_hero else 2
                diag_range = 2 if piece.is_hero else 1

                for dx, dy in ORTHOGONAL:
                    # Pass 1: Move & Board (blocked by obstacles & sea)
                    for step in range(1, straight_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if not target:
                            if is_sea_square(nx):
                                break
                            if can_piece_cross_river_to_empty(PieceType.MISSILE, x, y, nx, ny):
                                push_move(nx, ny)
                        else:
                            if target.side == active_side and can_board_carrier(piece, target):
                                push_board(target)
                            break
                    # Pass 2: Penetrating capture over intermediate obstacles & deep river
                    for step in range(1, straight_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if target and target.side != active_side:
                            act_type = (
                                ActionType.CAPTURE_STAND
                                if is_sea_square(nx) or is_hq_sheltering_commander(target, state.pieces)
                                else ActionType.CAPTURE_REPLACE
                            )
                            push_capture(nx, ny, target, act_type)

                for dx, dy in DIAGONAL:
                    for step in range(1, diag_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if not target:
                            if is_sea_square(nx):
                                break
                            if can_piece_cross_river_to_empty(PieceType.MISSILE, x, y, nx, ny):
                                push_move(nx, ny)
                        else:
                            if target.side == active_side and can_board_carrier(piece, target):
                                push_board(target)
                            break
                    for step in range(1, diag_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if target and target.side != active_side:
                            act_type = (
                                ActionType.CAPTURE_STAND
                                if is_sea_square(nx) or is_hq_sheltering_commander(target, state.pieces)
                                else ActionType.CAPTURE_REPLACE
                            )
                            push_capture(nx, ny, target, act_type)

            # 7. ARTILLERY
            elif piece.type == PieceType.ARTILLERY:
                max_range = 4 if piece.is_hero else 3
                for dx, dy in ALL_8:
                    for step in range(1, max_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny) or not can_occupy_square(piece, nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if not target:
                            if can_piece_cross_river_to_empty(PieceType.ARTILLERY, x, y, nx, ny):
                                push_move(nx, ny)
                        else:
                            if step == 1 and can_board_carrier(piece, target):
                                push_board(target)
                            break

                    for step in range(1, max_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if target and target.side != active_side:
                            if is_sea_square(nx) or is_hq_sheltering_commander(target, state.pieces):
                                push_capture(nx, ny, target, ActionType.CAPTURE_STAND)
                            else:
                                push_capture(nx, ny, target, ActionType.CAPTURE_REPLACE)

            # 8. AIRCRAFT
            elif piece.type == PieceType.AIRCRAFT:
                max_range = 5 if piece.is_hero else 4
                for dx, dy in ALL_8:
                    for step in range(1, max_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if not target:
                            if not is_sea_square(nx):
                                push_move(nx, ny)
                        elif target.side == active_side:
                            if can_board_carrier(passenger=target, carrier=piece) and not target.carried_by_id and not is_sea_square(nx):
                                push_pickup(target)
                            elif target.type == PieceType.NAVY and can_board_carrier(piece, target):
                                push_board(target)
                        else:
                            if is_sea_square(nx) or is_hq_sheltering_commander(target, state.pieces):
                                push_capture(nx, ny, target, ActionType.CAPTURE_STAND)
                            else:
                                if target.type == PieceType.AIRCRAFT:
                                    push_capture(nx, ny, target, ActionType.CAPTURE_REPLACE)
                                else:
                                    push_capture(nx, ny, target, ActionType.CAPTURE_STAND)
                                    push_capture(nx, ny, target, ActionType.CAPTURE_REPLACE)

            # 9. COMMANDER
            elif piece.type == PieceType.COMMANDER:
                for dx, dy in ORTHOGONAL:
                    for step in range(1, 12):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny) or not can_occupy_square(piece, nx, ny):
                            break

                        sim_pieces = [
                            p.model_copy(update={"position": Position(x=nx, y=ny), "carried_by_id": None})
                            if p.piece_id == piece.piece_id else p
                            for p in state.pieces
                        ]
                        if is_commanders_facing(sim_pieces):
                            break

                        target = piece_map.get((nx, ny))
                        if not target:
                            push_move(nx, ny)
                        else:
                            if step == 1 and target.side != active_side:
                                act_type = (
                                    ActionType.CAPTURE_STAND
                                    if is_sea_square(nx) or is_hq_sheltering_commander(target, state.pieces)
                                    else ActionType.CAPTURE_REPLACE
                                )
                                push_capture(nx, ny, target, act_type)
                            elif step == 1 and target.side == active_side:
                                if target.type == PieceType.HEADQUARTERS and not target.is_hero:
                                    if not enemy_cmd or not is_hq_facing_enemy_commander(target, enemy_cmd, state.pieces):
                                        push_board(target)
                                elif can_board_carrier(piece, target):
                                    push_board(target)
                            break

            # 10. NAVY
            elif piece.type == PieceType.NAVY:
                max_straight = 5 if piece.is_hero else 4
                max_gun = 4 if piece.is_hero else 3
                shore_capture_coords: Set[Tuple[int, int]] = set()

                for dx, dy in ALL_8:
                    # Pha 1: Hải lộ trên biển/sông/bờ biển-bờ sông (được vượt quân ta ở bờ không phải tàu)
                    for step in range(1, max_straight + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny) or is_ford_square(nx, ny):
                            break
                        prev_x = x + dx * (step - 1)
                        prev_y = y + dy * (step - 1)
                        if is_navy_land_diagonal(prev_x, prev_y, nx, ny):
                            break
                        if not can_navy_occupy_square(nx, ny):
                            break

                        target = piece_map.get((nx, ny))
                        if not target:
                            push_move(nx, ny)
                        elif target.side == active_side:
                            if target.type == PieceType.NAVY:
                                break
                            if can_board_carrier(passenger=target, carrier=piece) and not target.carried_by_id:
                                push_pickup(target)
                            continue
                        else:
                            if target.type == PieceType.NAVY:
                                push_capture(nx, ny, target, ActionType.CAPTURE_REPLACE)
                            elif step <= max_gun:
                                act_type = (
                                    ActionType.CAPTURE_STAND
                                    if is_hq_sheltering_commander(target, state.pieces)
                                    else ActionType.CAPTURE_REPLACE
                                )
                                push_capture(nx, ny, target, act_type)
                                shore_capture_coords.add((nx, ny))
                            break

                    # Pha 2: Pháo hạm bắn đất liền / vượt vật cản tầm 3 (Anh hùng: 4)
                    for step in range(1, max_gun + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny):
                            break
                        if (nx, ny) in shore_capture_coords:
                            continue
                        target = piece_map.get((nx, ny))
                        if target and target.side != active_side and target.type != PieceType.NAVY:
                            push_capture(nx, ny, target, ActionType.CAPTURE_STAND)

        valid_actions: List[LegalAction] = []
        for act in actions:
            sim = simulate_action(act, state.pieces)
            if own_cmd_before is not None:
                if not any(p.is_alive and p.piece_id == own_cmd_before.piece_id for p in sim):
                    continue
            if not is_commanders_facing(sim) and not is_commander_in_check(sim, active_side):
                valid_actions.append(act)

        if in_compound_stack:
            origin = state.compound_origin or Position(x=0, y=0)
            valid_actions.append(
                LegalAction(
                    action_id=f"end_turn_{active_side.value}",
                    action_type=ActionType.END_TURN,
                    piece_id="COMPOUND",
                    from_pos=origin,
                    to_pos=origin,
                    target_piece_id=None,
                    carry_cargo=True,
                    notation="CONFIRM_DEPLOYMENT",
                    description="Xác nhận kết thúc lượt tổ hợp",
                )
            )

        return valid_actions

    def _finalize_handoff_outcome(
        self,
        state: GameState,
        actor_side: Side,
        new_pieces: List[PieceState],
        new_scores: Dict[str, int],
        score_delta: Dict[Side, int],
        notation: str,
        event: GameEvent,
        actor_id: str,
    ) -> Tuple[bool, Optional[GameResultDTO], str, Side, int, GameStatus]:
        next_side = Side.BLUE if actor_side == Side.RED else Side.RED
        turn_inc = 1 if actor_side == Side.BLUE else 0
        enemy_has_cmd = any(
            p.is_alive and p.side == next_side and p.type == PieceType.COMMANDER
            for p in new_pieces
        )
        if not enemy_has_cmd:
            return False, None, notation, next_side, turn_inc, GameStatus.IN_PROGRESS

        temp_next_state = state.model_copy(
            update={
                "status": GameStatus.IN_PROGRESS,
                "side_to_move": next_side,
                "turn_phase": TurnPhase.NORMAL,
                "can_end_turn": False,
                "compound_origin": None,
                "compound_member_ids": [],
                "compound_moved_piece_ids": [],
                "pieces": new_pieces,
                "scores": new_scores,
            }
        )
        enemy_moves = self.get_legal_actions(temp_next_state)
        if len(enemy_moves) > 0:
            return False, None, notation, next_side, turn_inc, GameStatus.IN_PROGRESS

        if is_commander_in_check(new_pieces, next_side):
            score_delta[actor_side] += 50
            new_scores[actor_side.value] += 50
            notation = f"{notation} #"
            event.notation = notation
            if event.details is not None:
                event.details["is_checkmate"] = True
                event.details["is_check"] = True
            result = GameResultDTO(
                winner=actor_side.value,
                reason=TerminationReason.CHECKMATE,
                final_scores=new_scores,
            )
        else:
            if event.details is not None:
                event.details["is_stalemate"] = True
            result = GameResultDTO(
                winner="DRAW",
                reason=TerminationReason.STALEMATE,
                final_scores=new_scores,
            )

        return True, result, notation, actor_side, 0, GameStatus.GAME_OVER

    def apply_action(self, state: GameState, request: ActionRequest) -> Tuple[GameState, GameEvent]:
        if request.state_version != state.state_version:
            raise ValueError(f"State version mismatch: expected {state.state_version}, got {request.state_version}")

        if request.action_type == ActionType.END_TURN:
            if state.turn_phase != TurnPhase.STACK_ACTIVE:
                raise ValueError("Không có lượt tổ hợp đang hoạt động để kết thúc.")
            actor_side = state.side_to_move
            next_side = Side.BLUE if actor_side == Side.RED else Side.RED
            score_delta = {Side.RED: 0, Side.BLUE: 0}
            new_scores = {"RED": state.scores["RED"], "BLUE": state.scores["BLUE"]}
            event = GameEvent(
                event_id=f"evt_{int(time.time() * 1000)}",
                event_type=EventType.PIECE_MOVED,
                actor_id="COMPOUND",
                target_id=None,
                notation="CONFIRM_DEPLOYMENT",
                score_delta=score_delta,
                details={"action_type": ActionType.END_TURN.value},
            )
            game_over, result, _, resolved_side, turn_inc, new_status = self._finalize_handoff_outcome(
                state, actor_side, state.pieces, new_scores, score_delta, "CONFIRM_DEPLOYMENT", event, "COMPOUND"
            )
            next_state = GameState(
                game_id=state.game_id,
                mode=state.mode,
                status=new_status,
                side_to_move=resolved_side,
                turn_index=state.turn_index + turn_inc,
                action_index=1,
                turn_phase=TurnPhase.NORMAL,
                state_version=state.state_version + 1,
                scores=new_scores,
                remaining_time_ms=state.remaining_time_ms,
                pieces=state.pieces,
                legal_actions=[],
                can_end_turn=False,
                compound_origin=None,
                compound_member_ids=[],
                compound_moved_piece_ids=[],
                last_event=event,
                result=result,
            )
            next_state.legal_actions = self.get_legal_actions(next_state)
            return next_state, event

        actor = next((p for p in state.pieces if p.piece_id == request.piece_id and p.is_alive), None)
        if not actor:
            raise ValueError(f"Piece {request.piece_id} not found or not alive")
        if actor.side != state.side_to_move and state.turn_phase != TurnPhase.STACK_ACTIVE:
            raise ValueError(f"Piece {request.piece_id} does not belong to active side {state.side_to_move}")

        had_own_cmd = any(p.is_alive and p.side == actor.side and p.type == PieceType.COMMANDER for p in state.pieces)
        actor_origin = get_root_carrier(actor, state.pieces).position
        captured_piece: Optional[PieceState] = None
        new_pieces: List[PieceState] = []
        score_delta = {Side.RED: 0, Side.BLUE: 0}

        enemy_side = Side.BLUE if actor.side == Side.RED else Side.RED
        enemy_aa_zones = get_air_defense_zones(enemy_side, state.pieces)
        enemy_aa_units = [
            p for p in state.pieces
            if p.is_alive and p.carried_by_id is None and p.side == enemy_side
            and p.type in (PieceType.ANTI_AIR, PieceType.MISSILE, PieceType.NAVY)
        ]
        is_actor_aircraft = actor.type == PieceType.AIRCRAFT and not actor.is_hero
        is_target_aa_unit = any(
            u.position.x == request.to_pos.x and u.position.y == request.to_pos.y
            for u in enemy_aa_units
        )
        is_in_aa_zone = (
            is_actor_aircraft
            and (
                is_target_aa_unit
                or is_aircraft_flight_affected_by_aa(actor_origin, request.to_pos, enemy_aa_zones, enemy_aa_units)
            )
        )
        target = next((p for p in state.pieces if p.piece_id == request.target_piece_id and p.is_alive), None) if request.target_piece_id else None
        is_carrier_pickup = (
            request.action_type == ActionType.BOARD
            and target is not None
            and can_board_carrier(passenger=target, carrier=actor)
        )
        actor_descendants = set(get_all_carried_piece_ids(actor.piece_id, state.pieces))
        target_descendants = set(get_all_carried_piece_ids(target.piece_id, state.pieces)) if target else set()

        leave_behind = (
            not request.carry_cargo
            and request.action_type in (ActionType.MOVE, ActionType.CAPTURE_REPLACE)
            and bool(actor_descendants)
        ) or (
            actor.type == PieceType.HEADQUARTERS
            and request.action_type in (ActionType.MOVE, ActionType.CAPTURE_REPLACE)
            and bool(actor_descendants)
        )
        detached_map = _detach_cargo_map(actor, actor_origin, state.pieces) if leave_behind else {}

        for p in state.pieces:
            if request.action_type == ActionType.BOARD:
                if is_carrier_pickup:
                    if p.piece_id == request.piece_id:
                        new_pieces.append(p.model_copy(update={"position": request.to_pos, "carried_by_id": None}))
                    elif p.piece_id == request.target_piece_id:
                        new_pieces.append(p.model_copy(update={"position": request.to_pos, "carried_by_id": request.piece_id}))
                    elif p.piece_id in actor_descendants or p.piece_id in target_descendants:
                        new_pieces.append(p.model_copy(update={"position": request.to_pos}))
                    else:
                        new_pieces.append(p)
                else:
                    if p.piece_id == request.piece_id:
                        new_pieces.append(p.model_copy(update={"position": request.to_pos, "carried_by_id": request.target_piece_id}))
                    elif p.piece_id == request.target_piece_id:
                        new_pieces.append(p.model_copy(update={"carrying_piece_ids": p.carrying_piece_ids + [request.piece_id]}))
                    elif p.piece_id in actor_descendants:
                        new_pieces.append(p.model_copy(update={"position": request.to_pos}))
                    else:
                        new_pieces.append(p)
                continue

            if request.target_piece_id and p.piece_id == request.target_piece_id:
                p_dead = p.model_copy(update={"is_alive": False, "carried_by_id": None})
                captured_piece = p_dead
                score_delta[actor.side] += PIECE_SCORES.get(p.type, 10) + (10 if p.is_hero else 0)
                new_pieces.append(p_dead)
                continue

            if request.target_piece_id and p.piece_id in target_descendants:
                if target and target.type == PieceType.HEADQUARTERS:
                    if p.carried_by_id == target.piece_id:
                        new_pieces.append(p.model_copy(update={"carried_by_id": None, "is_alive": True, "position": target.position}))
                    else:
                        new_pieces.append(p.model_copy(update={"position": target.position}))
                else:
                    p_dead = p.model_copy(update={"is_alive": False, "carried_by_id": None})
                    score_delta[actor.side] += PIECE_SCORES.get(p.type, 10) + (10 if p.is_hero else 0)
                    new_pieces.append(p_dead)
                continue

            if p.carrying_piece_ids and request.piece_id in p.carrying_piece_ids:
                p = p.model_copy(update={"carrying_piece_ids": [cid for cid in p.carrying_piece_ids if cid != request.piece_id]})

            if p.piece_id == request.piece_id:
                if is_in_aa_zone:
                    score_delta[enemy_side] += PIECE_SCORES.get(PieceType.AIRCRAFT, 40)
                    new_pieces.append(p.model_copy(update={"is_alive": False, "position": request.to_pos, "carried_by_id": None}))
                elif request.action_type == ActionType.CAPTURE_STAND:
                    new_pieces.append(p)
                else:
                    new_pieces.append(p.model_copy(update={"position": request.to_pos, "carried_by_id": None}))
            elif p.piece_id in actor_descendants:
                if p.piece_id in detached_map:
                    new_cb, new_pos = detached_map[p.piece_id]
                    new_pieces.append(p.model_copy(update={"carried_by_id": new_cb, "position": new_pos}))
                elif is_in_aa_zone:
                    score_delta[enemy_side] += PIECE_SCORES.get(p.type, 10) + (10 if p.is_hero else 0)
                    new_pieces.append(p.model_copy(update={"is_alive": False, "carried_by_id": None}))
                elif request.action_type == ActionType.CAPTURE_STAND:
                    new_pieces.append(p)
                else:
                    new_pieces.append(p.model_copy(update={"position": request.to_pos}))
            else:
                new_pieces.append(p)

        for p in new_pieces:
            p.carrying_piece_ids = [
                other.piece_id for other in new_pieces
                if other.is_alive and other.carried_by_id == p.piece_id
            ]
            if p.is_alive and p.carried_by_id is not None:
                root = get_root_carrier(p, new_pieces)
                p.position = root.position

        new_pieces = _apply_hero_promotions(new_pieces)

        if had_own_cmd:
            if not any(p.is_alive and p.side == actor.side and p.type == PieceType.COMMANDER for p in new_pieces):
                raise ValueError("Hành động khiến Tư lệnh phe mình bị tiêu diệt.")
            if is_commanders_facing(new_pieces):
                raise ValueError("Hành động khiến hai Tư lệnh đối mặt trực tiếp.")
            if is_commander_in_check(new_pieces, actor.side):
                raise ValueError("Nước đi để lộ Tư lệnh cho đối phương tấn công/ăn.")

        # 3. Auto-promote heroes on Check (RULE-HERO-CHECK)
        enemy_side_actor = Side.BLUE if actor.side == Side.RED else Side.RED
        enemy_cmd = next((p for p in new_pieces if p.is_alive and p.side == enemy_side_actor and p.type == PieceType.COMMANDER), None)
        actor_checked_commander = False
        actor_was_promoted = False
        if enemy_cmd and is_commander_in_check(new_pieces, enemy_side_actor):
            cmd_origin = get_root_carrier(enemy_cmd, new_pieces).position
            piece_map_after = {(p.position.x, p.position.y): p for p in new_pieces if p.is_alive and p.carried_by_id is None}
            checking_ids = set()
            for p in new_pieces:
                if p.is_alive and p.side == actor.side and p.type != PieceType.COMMANDER:
                    if _piece_threatens_square(new_pieces, p, cmd_origin.x, cmd_origin.y, piece_map_after):
                        checking_ids.add(p.piece_id)
                        if p.piece_id == request.piece_id:
                            actor_checked_commander = True
            if checking_ids:
                updated_pieces = []
                for p in new_pieces:
                    if p.piece_id in checking_ids and p.type != PieceType.COMMANDER:
                        if not p.is_hero and p.piece_id == request.piece_id:
                            actor_was_promoted = True
                        updated_pieces.append(p.model_copy(update={"is_hero": True}))
                    else:
                        updated_pieces.append(p)
                new_pieces = updated_pieces

        actor_sym = PIECE_NOTATION_SYMBOL.get(actor.type, "B")
        from_not = f"[{actor_origin.y} ; {actor_origin.x}]"
        to_not = f"[{request.to_pos.y} ; {request.to_pos.x}]"

        if is_in_aa_zone:
            if captured_piece or request.target_piece_id:
                target_sym = PIECE_NOTATION_SYMBOL.get(captured_piece.type, "B") if captured_piece else "B"
                notation = f"{actor_sym} {from_not} >< {target_sym} {to_not}"
                evt_type = EventType.AIR_EXCHANGE
                event_target_id = captured_piece.piece_id if captured_piece else request.target_piece_id
            else:
                notation = f"{actor_sym} {from_not} @\" {to_not}"
                evt_type = EventType.AIR_SHOT_DOWN
                event_target_id = actor.piece_id
        elif captured_piece:
            act_sym = "_@_" if request.action_type == ActionType.CAPTURE_STAND else "@"
            target_sym = PIECE_NOTATION_SYMBOL.get(captured_piece.type, "B")
            notation = f"{actor_sym} {from_not} {act_sym} {target_sym} {to_not}"
            evt_type = EventType.PIECE_CAPTURED
            event_target_id = captured_piece.piece_id
        elif request.action_type == ActionType.BOARD:
            if is_carrier_pickup:
                target_sym = PIECE_NOTATION_SYMBOL.get(target.type, "B") if target else "B"
                notation = f"{actor_sym} {from_not} ^ {target_sym} {to_not}"
            else:
                carrier = next((p for p in state.pieces if p.piece_id == request.target_piece_id), None)
                carrier_sym = PIECE_NOTATION_SYMBOL.get(carrier.type, "T") if carrier else "T"
                notation = f"{actor_sym} {from_not} ^ {carrier_sym} {to_not}"
            evt_type = EventType.PIECE_MOVED
            event_target_id = None
        else:
            notation = f"{actor_sym} {from_not} _ {to_not}"
            evt_type = EventType.PIECE_MOVED
            event_target_id = None

        if actor_checked_commander:
            if ">" not in notation:
                notation = f"{notation} > **{actor_sym}**" if actor_was_promoted else f"{notation} >"
            if evt_type == EventType.PIECE_MOVED:
                evt_type = EventType.HERO_PROMOTION

        event = GameEvent(
            event_id=f"evt_{int(time.time() * 1000)}",
            event_type=evt_type,
            actor_id=actor.piece_id,
            target_id=event_target_id,
            notation=notation,
            score_delta=score_delta,
            details={
                "action_type": request.action_type.value,
                "is_check": actor_checked_commander,
                "hero_promoted": actor_was_promoted,
                "from_pos": {"x": actor_origin.x, "y": actor_origin.y},
                "to_pos": {"x": request.to_pos.x, "y": request.to_pos.y},
            },
        )

        new_scores = {
            "RED": state.scores["RED"] + score_delta[Side.RED],
            "BLUE": state.scores["BLUE"] + score_delta[Side.BLUE],
        }

        game_over = False
        result: Optional[GameResultDTO] = None
        if captured_piece and captured_piece.type == PieceType.COMMANDER:
            game_over = True
            score_delta[actor.side] += 50
            new_scores[actor.side.value] += 50
            result = GameResultDTO(
                winner=actor.side.value,
                reason=TerminationReason.COMMANDER_CAPTURED,
                final_scores=new_scores,
            )

        # Compound stack state machine
        compound_origin: Optional[Position] = None
        compound_member_ids: List[str] = []
        compound_moved_ids: List[str] = []
        stay_in_stack = False

        if not game_over and request.action_type != ActionType.BOARD:
            if state.turn_phase == TurnPhase.STACK_ACTIVE:
                if state.compound_member_ids:
                    moved = list(state.compound_moved_piece_ids) + [actor.piece_id]
                    origin = state.compound_origin or actor_origin
                    remaining_at_origin = [
                        p for p in new_pieces
                        if p.is_alive and p.piece_id in state.compound_member_ids and p.piece_id not in moved
                        and p.position.x == origin.x and p.position.y == origin.y
                    ]
                    if len(moved) < 3 and len(remaining_at_origin) > 0 and (
                        request.is_compound_action or request.carry_cargo is not False
                    ):
                        stay_in_stack = True
                        compound_origin = origin
                        compound_member_ids = list(state.compound_member_ids)
                        compound_moved_ids = moved
                elif request.is_compound_action:
                    stay_in_stack = True
            else:
                old_root = get_root_carrier(actor, state.pieces)
                if actor.carried_by_id is not None and old_root.type != PieceType.HEADQUARTERS:
                    old_root_after = next((p for p in new_pieces if p.piece_id == old_root.piece_id and p.is_alive), None)
                    if old_root_after and old_root_after.position.x == actor_origin.x and old_root_after.position.y == actor_origin.y:
                        stay_in_stack = True
                        compound_origin = actor_origin
                        compound_member_ids = [old_root.piece_id, *get_all_carried_piece_ids(old_root.piece_id, state.pieces)]
                        compound_moved_ids = [actor.piece_id]
                elif actor.carried_by_id is None and actor.type != PieceType.HEADQUARTERS and bool(actor_descendants) and (
                    request.action_type == ActionType.CAPTURE_STAND
                    or (request.action_type in (ActionType.MOVE, ActionType.CAPTURE_REPLACE) and not request.carry_cargo)
                ):
                    stay_in_stack = True
                    compound_origin = actor_origin
                    compound_member_ids = [actor.piece_id, *sorted(actor_descendants)]
                    compound_moved_ids = [actor.piece_id]

            if not stay_in_stack and request.is_compound_action:
                # Legacy compatibility (e.g. standalone move with is_compound_action=True)
                stay_in_stack = True

        if stay_in_stack:
            next_side = actor.side
            turn_phase = TurnPhase.STACK_ACTIVE
            can_end_turn = True
            action_index = state.action_index + 1
            turn_inc = 0
            new_status = GameStatus.IN_PROGRESS
        else:
            next_side = Side.BLUE if actor.side == Side.RED else Side.RED
            turn_phase = TurnPhase.NORMAL
            can_end_turn = False
            action_index = 1
            turn_inc = 1 if actor.side == Side.BLUE else 0
            new_status = GameStatus.GAME_OVER if game_over else GameStatus.IN_PROGRESS

            if not game_over:
                game_over, result, notation, resolved_side, turn_inc, new_status = self._finalize_handoff_outcome(
                    state, actor.side, new_pieces, new_scores, score_delta, notation, event, actor.piece_id
                )
                next_side = resolved_side

        next_state = GameState(
            game_id=state.game_id,
            mode=state.mode,
            status=new_status,
            side_to_move=next_side if not game_over else actor.side,
            turn_index=state.turn_index + turn_inc,
            action_index=action_index,
            turn_phase=turn_phase,
            state_version=state.state_version + 1,
            scores=new_scores,
            remaining_time_ms=state.remaining_time_ms,
            pieces=new_pieces,
            legal_actions=[],
            can_end_turn=can_end_turn,
            compound_origin=compound_origin,
            compound_member_ids=compound_member_ids,
            compound_moved_piece_ids=compound_moved_ids,
            last_event=event,
            result=result,
        )
        next_state.legal_actions = self.get_legal_actions(next_state)
        return next_state, event

    def resign(self, state: GameState, side: Side) -> GameState:
        winner = Side.BLUE if side == Side.RED else Side.RED
        result = GameResultDTO(
            winner=winner.value,
            reason=TerminationReason.RESIGNATION,
            final_scores=state.scores,
        )
        return state.model_copy(
            update={
                "status": GameStatus.GAME_OVER,
                "state_version": state.state_version + 1,
                "result": result,
                "legal_actions": [],
            }
        )

    def draw(self, state: GameState) -> GameState:
        result = GameResultDTO(
            winner="DRAW",
            reason=TerminationReason.MUTUAL_DRAW,
            final_scores=state.scores,
        )
        return state.model_copy(
            update={
                "status": GameStatus.GAME_OVER,
                "state_version": state.state_version + 1,
                "result": result,
                "legal_actions": [],
            }
        )


class AuthoritativeEngineAdapter(BaseEngineAdapter):
    """Authoritative Engine Adapter — tích hợp trực tiếp với `packages/commander_game_engine`."""

    def __init__(self, fallback_adapter: Optional[BaseEngineAdapter] = None):
        self.fallback = fallback_adapter or MockEngineAdapter()

    def create_initial_state(self, game_id: str, mode: GameMode) -> GameState:
        try:
            from commander_game_engine.initial_setup import create_initial_state as create_pkg_initial_state
            pkg_state = create_pkg_initial_state()
            pieces = []
            for p in pkg_state.pieces.values():
                ptype = (
                    PieceType.ANTI_AIR
                    if p.piece_type.value == "anti_aircraft"
                    else PieceType(p.piece_type.value.upper())
                )
                pieces.append(
                    PieceState(
                        piece_id=p.id.replace("_anti_aircraft_", "_anti_air_"),
                        side=Side.RED if p.owner.value == "red" else Side.BLUE,
                        type=ptype,
                        position=Position(x=p.position[1], y=p.position[0]),
                        is_alive=True,
                        is_hero=p.is_heroic,
                        carrying_piece_ids=list(p.cargo),
                        carried_by_id=p.carried_by,
                    )
                )

            state = GameState(
                game_id=game_id,
                mode=mode,
                status=GameStatus.IN_PROGRESS,
                side_to_move=Side.RED,
                turn_index=1,
                action_index=1,
                turn_phase=TurnPhase.NORMAL,
                state_version=1,
                scores={"RED": 0, "BLUE": 0},
                remaining_time_ms={"RED": 1800000, "BLUE": 1800000},
                pieces=pieces,
                legal_actions=[],
                can_end_turn=False,
                last_event=None,
                result=None,
            )
            state.legal_actions = self.get_legal_actions(state)
            return state
        except Exception:
            return self.fallback.create_initial_state(game_id, mode)

    def _to_pkg_state(self, state: GameState):
        from commander_game_engine.board import Board
        from commander_game_engine.game_state import (
            CompoundTurnState,
            GameState as PkgGameState,
            Piece as PkgPiece,
            PieceType as PkgPieceType,
            Player as PkgPlayer,
        )

        board = Board()
        alive_ids = {p.piece_id for p in state.pieces if p.is_alive}
        pkg_pieces = {}
        for p in state.pieces:
            if not p.is_alive:
                continue
            ptype_val = "anti_aircraft" if p.type == PieceType.ANTI_AIR else p.type.value.lower()
            pkg_type = PkgPieceType(ptype_val)
            pkg_owner = PkgPlayer.RED if p.side == Side.RED else PkgPlayer.BLUE
            cb = p.carried_by_id if p.carried_by_id in alive_ids else None
            pos = (p.position.y, p.position.x) if cb is None else None
            cargo = [cid for cid in p.carrying_piece_ids if cid in alive_ids]
            pkg_pieces[p.piece_id] = PkgPiece(
                id=p.piece_id,
                piece_type=pkg_type,
                owner=pkg_owner,
                position=pos,
                carried_by=cb,
                cargo=cargo,
                is_heroic=p.is_hero,
            )

        cur_player = PkgPlayer.RED if state.side_to_move == Side.RED else PkgPlayer.BLUE
        scores = {
            PkgPlayer.RED: state.scores.get("RED", 0),
            PkgPlayer.BLUE: state.scores.get("BLUE", 0),
        }

        compound_turn = None
        if state.turn_phase == TurnPhase.STACK_ACTIVE and state.compound_member_ids and state.compound_origin:
            origin_tuple = (state.compound_origin.y, state.compound_origin.x)
            root_at_origin = next(
                (p.id for p in pkg_pieces.values() if p.carried_by is None and p.position == origin_tuple),
                state.compound_member_ids[0],
            )
            compound_turn = CompoundTurnState(
                root_transport_id=root_at_origin,
                origin=origin_tuple,
                actions_used=len(state.compound_moved_piece_ids),
                acted_piece_ids=set(state.compound_moved_piece_ids),
            )

        return PkgGameState(
            board=board,
            pieces=pkg_pieces,
            current_player=cur_player,
            turn_number=state.turn_index,
            compound_turn=compound_turn,
            scores=scores,
        )

    def get_legal_actions(self, state: GameState) -> List[LegalAction]:
        if state.status == GameStatus.GAME_OVER:
            return []
        if state.turn_phase == TurnPhase.STACK_ACTIVE and not state.compound_member_ids:
            return self.fallback.get_legal_actions(state)

        try:
            from commander_game_engine.move_generator import generate_legal_actions as generate_pkg_actions
            from commander_game_engine.actions import ActionType as PkgActionType, TurnCommand

            pkg_state = self._to_pkg_state(state)
            pkg_actions = generate_pkg_actions(pkg_state)

            actions: List[LegalAction] = []
            for act in pkg_actions:
                if isinstance(act, TurnCommand):
                    origin = state.compound_origin or Position(x=0, y=0)
                    actions.append(
                        LegalAction(
                            action_id=f"end_turn_{state.side_to_move.value}",
                            action_type=ActionType.END_TURN,
                            piece_id="COMPOUND",
                            from_pos=origin,
                            to_pos=origin,
                            target_piece_id=None,
                            carry_cargo=True,
                            notation="CONFIRM_DEPLOYMENT",
                            description="Xác nhận kết thúc lượt tổ hợp",
                        )
                    )
                    continue

                actor = next((p for p in state.pieces if p.piece_id == act.piece_id and p.is_alive), None)
                if not actor:
                    continue
                sym = PIECE_NOTATION_SYMBOL.get(actor.type, "B")
                from_x, from_y = act.start[1], act.start[0]
                to_x, to_y = act.end[1], act.end[0]
                target = next((p for p in state.pieces if p.piece_id == act.target_piece_id), None) if act.target_piece_id else None
                target_sym = PIECE_NOTATION_SYMBOL.get(target.type, "B") if target else "B"

                if act.action_type == PkgActionType.MOVE:
                    api_type = ActionType.MOVE
                    not_sym = "_"
                    desc = (
                        f"{actor.type.value} di chuyển đến [{to_y} ; {to_x}]"
                        if act.carry_cargo
                        else f"{actor.type.value} di chuyển một mình (để lại quân cõng) đến [{to_y} ; {to_x}]"
                    )
                elif act.action_type == PkgActionType.CAPTURE:
                    api_type = ActionType.CAPTURE_REPLACE
                    not_sym = "@"
                    desc = (
                        f"{actor.type.value} tiêu diệt {target.type.value if target else 'quân địch'} tại [{to_y} ; {to_x}]"
                        if act.carry_cargo
                        else f"{actor.type.value} tấn công một mình (để lại quân cõng) tại [{to_y} ; {to_x}]"
                    )
                elif act.action_type in (PkgActionType.BOMB, PkgActionType.BOMBARD):
                    api_type = ActionType.CAPTURE_STAND
                    not_sym = "_@_"
                    desc = f"{actor.type.value} tấn công tại chỗ {target.type.value if target else 'mục tiêu'} tại [{to_y} ; {to_x}]"
                elif act.action_type == PkgActionType.BOARD:
                    api_type = ActionType.BOARD
                    not_sym = "^"
                    desc = f"{actor.type.value} lên {target.type.value if target else 'phương tiện'} tại [{to_y} ; {to_x}]"
                elif act.action_type == PkgActionType.PICKUP:
                    api_type = ActionType.BOARD
                    not_sym = "^"
                    desc = f"{actor.type.value} đến cõng {target.type.value if target else 'quân'} tại [{to_y} ; {to_x}]"
                else:
                    continue

                if act.target_piece_id:
                    notation = f"{sym} [{from_y} ; {from_x}] {not_sym} {target_sym} [{to_y} ; {to_x}]"
                else:
                    notation = f"{sym} [{from_y} ; {from_x}] {not_sym} [{to_y} ; {to_x}]"

                tag = "w" if act.carry_cargo else "s"
                if act.action_type == PkgActionType.PICKUP:
                    tag = "p"
                elif act.action_type == PkgActionType.BOARD:
                    tag = "b"

                actions.append(
                    LegalAction(
                        action_id=f"a_{tag}_{act.piece_id}_{to_x}_{to_y}_{api_type.value}",
                        action_type=api_type,
                        piece_id=act.piece_id,
                        from_pos=Position(x=from_x, y=from_y),
                        to_pos=Position(x=to_x, y=to_y),
                        target_piece_id=act.target_piece_id,
                        carry_cargo=act.carry_cargo,
                        notation=notation,
                        description=desc,
                    )
                )

            return actions
        except Exception:
            return self.fallback.get_legal_actions(state)

    def apply_action(self, state: GameState, request: ActionRequest) -> Tuple[GameState, GameEvent]:
        if request.state_version != state.state_version:
            raise ValueError(f"State version mismatch: expected {state.state_version}, got {request.state_version}")
        if state.turn_phase == TurnPhase.STACK_ACTIVE and not state.compound_member_ids:
            return self.fallback.apply_action(state, request)

        try:
            from commander_game_engine.actions import (
                ActionType as PkgActionType,
                AtomicAction as PkgAtomicAction,
                TurnCommand,
                TurnCommandType,
            )
            from commander_game_engine.engine import EngineEventType as PkgEventType, apply_action as apply_pkg_action
            from commander_game_engine.game_state import Player as PkgPlayer
            from commander_game_engine import rules as pkg_rules

            if request.action_type == ActionType.END_TURN:
                pkg_state = self._to_pkg_state(state)
                res = apply_pkg_action(pkg_state, TurnCommand(TurnCommandType.END_TURN))
                if not res.accepted:
                    raise ValueError(res.verdict.reason or "Không thể kết thúc lượt tổ hợp.")
                actor_side = state.side_to_move
                score_delta = {
                    Side.RED: res.state.scores.get(PkgPlayer.RED, 0) - state.scores.get("RED", 0),
                    Side.BLUE: res.state.scores.get(PkgPlayer.BLUE, 0) - state.scores.get("BLUE", 0),
                }
                notation = "CONFIRM_DEPLOYMENT"
                result_dto = None
                if res.terminal:
                    reason = TerminationReason(res.terminal_reason) if res.terminal_reason else TerminationReason.STALEMATE
                    winner = res.winner.value.upper() if res.winner else "DRAW"
                    if reason == TerminationReason.CHECKMATE:
                        notation = f"{notation} #"
                    result_dto = GameResultDTO(
                        winner=winner,
                        reason=reason,
                        final_scores={
                            "RED": res.state.scores.get(PkgPlayer.RED, 0),
                            "BLUE": res.state.scores.get(PkgPlayer.BLUE, 0),
                        },
                    )
                event = GameEvent(
                    event_id=f"evt_{int(time.time() * 1000)}",
                    event_type=EventType.PIECE_MOVED,
                    actor_id="COMPOUND",
                    target_id=None,
                    notation=notation,
                    score_delta=score_delta,
                    details={
                        "action_type": ActionType.END_TURN.value,
                        "is_checkmate": res.terminal_reason == "CHECKMATE",
                        "is_stalemate": res.terminal_reason == "STALEMATE",
                    },
                )
                next_side = Side.RED if res.state.current_player == PkgPlayer.RED else Side.BLUE
                next_state = GameState(
                    game_id=state.game_id,
                    mode=state.mode,
                    status=GameStatus.GAME_OVER if res.terminal else GameStatus.IN_PROGRESS,
                    side_to_move=actor_side if res.terminal else next_side,
                    turn_index=res.state.turn_number,
                    action_index=1,
                    turn_phase=TurnPhase.NORMAL,
                    state_version=state.state_version + 1,
                    scores={
                        "RED": res.state.scores.get(PkgPlayer.RED, 0),
                        "BLUE": res.state.scores.get(PkgPlayer.BLUE, 0),
                    },
                    remaining_time_ms=state.remaining_time_ms,
                    pieces=state.pieces,
                    legal_actions=[],
                    can_end_turn=False,
                    compound_origin=None,
                    compound_member_ids=[],
                    compound_moved_piece_ids=[],
                    last_event=event,
                    result=result_dto,
                )
                next_state.legal_actions = self.get_legal_actions(next_state)
                return next_state, event

            actor = next((p for p in state.pieces if p.piece_id == request.piece_id and p.is_alive), None)
            if not actor:
                raise ValueError(f"Piece {request.piece_id} not found or not alive")

            target_piece = (
                next((p for p in state.pieces if p.piece_id == request.target_piece_id and p.is_alive), None)
                if request.target_piece_id
                else None
            )

            # Bảo toàn tương thích legacy test khi caller gửi `is_compound_action=True` trên nước đi đơn / mang cả cụm
            is_native_compound_trigger = (
                actor.carried_by_id is not None
                or (
                    actor.type != PieceType.HEADQUARTERS
                    and bool(actor.carrying_piece_ids)
                    and (request.action_type == ActionType.CAPTURE_STAND or not request.carry_cargo)
                )
            )
            if request.is_compound_action and state.turn_phase == TurnPhase.NORMAL and not is_native_compound_trigger:
                return self.fallback.apply_action(state, request)

            pkg_state = self._to_pkg_state(state)
            actor_origin = get_root_carrier(actor, state.pieces).position

            if request.action_type == ActionType.MOVE:
                pkg_action = PkgAtomicAction(
                    action_type=PkgActionType.MOVE,
                    piece_id=request.piece_id,
                    start=(actor_origin.y, actor_origin.x),
                    end=(request.to_pos.y, request.to_pos.x),
                    carry_cargo=request.carry_cargo,
                )
                is_carrier_pickup = False
            elif request.action_type == ActionType.CAPTURE_REPLACE:
                pkg_action = PkgAtomicAction(
                    action_type=PkgActionType.CAPTURE,
                    piece_id=request.piece_id,
                    start=(actor_origin.y, actor_origin.x),
                    end=(request.to_pos.y, request.to_pos.x),
                    target_piece_id=request.target_piece_id,
                    carry_cargo=request.carry_cargo,
                )
                is_carrier_pickup = False
            elif request.action_type == ActionType.CAPTURE_STAND:
                pkg_act_type = PkgActionType.BOMB if actor.type == PieceType.AIRCRAFT else PkgActionType.BOMBARD
                pkg_action = PkgAtomicAction(
                    action_type=pkg_act_type,
                    piece_id=request.piece_id,
                    start=(actor_origin.y, actor_origin.x),
                    end=(request.to_pos.y, request.to_pos.x),
                    target_piece_id=request.target_piece_id,
                )
                is_carrier_pickup = False
            elif request.action_type == ActionType.BOARD:
                is_carrier_pickup = (
                    target_piece is not None
                    and actor.carried_by_id is None
                    and target_piece.carried_by_id is None
                    and can_board_carrier(passenger=target_piece, carrier=actor)
                )
                if is_carrier_pickup:
                    pkg_action = PkgAtomicAction(
                        action_type=PkgActionType.PICKUP,
                        piece_id=request.piece_id,
                        start=(actor_origin.y, actor_origin.x),
                        end=(request.to_pos.y, request.to_pos.x),
                        target_piece_id=request.target_piece_id,
                        passenger_id=request.target_piece_id,
                    )
                else:
                    pkg_action = PkgAtomicAction(
                        action_type=PkgActionType.BOARD,
                        piece_id=request.piece_id,
                        start=(actor_origin.y, actor_origin.x),
                        end=(request.to_pos.y, request.to_pos.x),
                        target_piece_id=request.target_piece_id,
                        carrier_id=request.target_piece_id,
                    )
            else:
                return self.fallback.apply_action(state, request)

            res = apply_pkg_action(pkg_state, pkg_action)
            if not res.accepted:
                if res.verdict.code.value != "unsupported":
                    raise ValueError(res.verdict.reason or "Hành động bất hợp lệ theo luật engine")
                return self.fallback.apply_action(state, request)

            def _pkg_root_pos(pid: str) -> Tuple[int, int]:
                pos = pkg_rules._origin(res.state, res.state.pieces[pid])
                return pos if pos is not None else (0, 0)

            new_pieces: List[PieceState] = []
            for p in state.pieces:
                if p.piece_id not in res.state.pieces:
                    new_pieces.append(p.model_copy(update={"is_alive": False, "carried_by_id": None, "carrying_piece_ids": []}))
                else:
                    pkg_p = res.state.pieces[p.piece_id]
                    rpos = _pkg_root_pos(p.piece_id)
                    new_pieces.append(
                        p.model_copy(
                            update={
                                "position": Position(x=rpos[1], y=rpos[0]),
                                "is_alive": True,
                                "is_hero": pkg_p.is_heroic,
                                "carried_by_id": pkg_p.carried_by,
                                "carrying_piece_ids": list(pkg_p.cargo),
                            }
                        )
                    )

            for p in new_pieces:
                p.carrying_piece_ids = [
                    other.piece_id for other in new_pieces
                    if other.is_alive and other.carried_by_id == p.piece_id
                ]

            actor_sym = PIECE_NOTATION_SYMBOL.get(actor.type, "B")
            from_not = f"[{actor_origin.y} ; {actor_origin.x}]"
            to_not = f"[{request.to_pos.y} ; {request.to_pos.x}]"
            score_delta = {
                Side.RED: res.state.scores.get(PkgPlayer.RED, 0) - state.scores.get("RED", 0),
                Side.BLUE: res.state.scores.get(PkgPlayer.BLUE, 0) - state.scores.get("BLUE", 0),
            }

            has_air_exchange = any(e.event_type == PkgEventType.AIR_EXCHANGE for e in res.events)
            has_air_shot_down = any(e.event_type == PkgEventType.AIR_SHOT_DOWN for e in res.events)
            enemy_side_actor = Side.BLUE if actor.side == Side.RED else Side.RED

            enemy_cmd = next(
                (p for p in new_pieces if p.is_alive and p.side == enemy_side_actor and p.type == PieceType.COMMANDER),
                None,
            )
            actor_after = next((p for p in new_pieces if p.is_alive and p.piece_id == actor.piece_id), None)
            actor_checked_commander = False
            actor_was_promoted = any(
                e.event_type == PkgEventType.HERO_PROMOTED
                and e.piece_id == actor.piece_id
                and "chiếu" in e.detail
                for e in res.events
            )
            if enemy_cmd and actor_after and is_commander_in_check(new_pieces, enemy_side_actor):
                cmd_root_pos = get_root_carrier(enemy_cmd, new_pieces).position
                piece_map_after = {(p.position.x, p.position.y): p for p in new_pieces if p.is_alive and p.carried_by_id is None}
                if _piece_threatens_square(new_pieces, actor_after, cmd_root_pos.x, cmd_root_pos.y, piece_map_after):
                    actor_checked_commander = True

            if has_air_exchange:
                target_sym = PIECE_NOTATION_SYMBOL.get(target_piece.type, "B") if target_piece else "B"
                notation = f"{actor_sym} {from_not} >< {target_sym} {to_not}"
                evt_type = EventType.AIR_EXCHANGE
                event_target_id = request.target_piece_id
            elif has_air_shot_down:
                notation = f"{actor_sym} {from_not} @\" {to_not}"
                evt_type = EventType.AIR_SHOT_DOWN
                event_target_id = actor.piece_id
            elif request.action_type in (ActionType.CAPTURE_REPLACE, ActionType.CAPTURE_STAND) and target_piece:
                act_sym = "_@_" if request.action_type == ActionType.CAPTURE_STAND else "@"
                target_sym = PIECE_NOTATION_SYMBOL.get(target_piece.type, "B")
                notation = f"{actor_sym} {from_not} {act_sym} {target_sym} {to_not}"
                evt_type = EventType.PIECE_CAPTURED
                event_target_id = request.target_piece_id
            elif request.action_type == ActionType.BOARD:
                target_sym = PIECE_NOTATION_SYMBOL.get(target_piece.type, "T") if target_piece else "T"
                notation = f"{actor_sym} {from_not} ^ {target_sym} {to_not}"
                evt_type = EventType.PIECE_MOVED
                event_target_id = None
            else:
                notation = f"{actor_sym} {from_not} _ {to_not}"
                evt_type = EventType.PIECE_MOVED
                event_target_id = None

            if actor_checked_commander:
                if ">" not in notation:
                    notation = f"{notation} > **{actor_sym}**" if actor_was_promoted else f"{notation} >"
                if evt_type == EventType.PIECE_MOVED:
                    evt_type = EventType.HERO_PROMOTION

            if res.terminal_reason == "CHECKMATE":
                notation = f"{notation} #"

            event = GameEvent(
                event_id=f"evt_{int(time.time() * 1000)}",
                event_type=evt_type,
                actor_id=actor.piece_id,
                target_id=event_target_id,
                notation=notation,
                score_delta=score_delta,
                details={
                    "action_type": request.action_type.value,
                    "is_check": actor_checked_commander or res.terminal_reason == "CHECKMATE",
                    "hero_promoted": actor_was_promoted,
                    "is_checkmate": res.terminal_reason == "CHECKMATE",
                    "is_stalemate": res.terminal_reason == "STALEMATE",
                    "from_pos": {"x": actor_origin.x, "y": actor_origin.y},
                    "to_pos": {"x": request.to_pos.x, "y": request.to_pos.y},
                },
            )

            result = None
            if res.terminal:
                reason = (
                    TerminationReason(res.terminal_reason)
                    if res.terminal_reason
                    else TerminationReason.COMMANDER_CAPTURED
                )
                winner = res.winner.value.upper() if res.winner else "DRAW"
                result = GameResultDTO(
                    winner=winner,
                    reason=reason,
                    final_scores={
                        "RED": res.state.scores.get(PkgPlayer.RED, 0),
                        "BLUE": res.state.scores.get(PkgPlayer.BLUE, 0),
                    },
                )

            compound_origin: Optional[Position] = None
            compound_member_ids: List[str] = []
            compound_moved_ids: List[str] = []
            if res.state.compound_turn is not None:
                ct = res.state.compound_turn
                turn_phase = TurnPhase.STACK_ACTIVE
                can_end_turn = True
                action_index = ct.actions_used + 1
                compound_origin = Position(x=ct.origin[1], y=ct.origin[0])
                if state.compound_member_ids:
                    compound_member_ids = list(state.compound_member_ids)
                else:
                    origin_root_before = next(
                        (
                            p for p in state.pieces
                            if p.is_alive and p.carried_by_id is None
                            and p.position.x == compound_origin.x and p.position.y == compound_origin.y
                        ),
                        None,
                    )
                    compound_member_ids = (
                        [origin_root_before.piece_id, *get_all_carried_piece_ids(origin_root_before.piece_id, state.pieces)]
                        if origin_root_before
                        else list(ct.acted_piece_ids)
                    )
                compound_moved_ids = sorted(ct.acted_piece_ids)
            else:
                turn_phase = TurnPhase.NORMAL
                can_end_turn = False
                action_index = 1

            next_side = Side.RED if res.state.current_player == PkgPlayer.RED else Side.BLUE
            new_status = GameStatus.GAME_OVER if res.terminal else GameStatus.IN_PROGRESS

            next_state = GameState(
                game_id=state.game_id,
                mode=state.mode,
                status=new_status,
                side_to_move=actor.side if res.terminal else next_side,
                turn_index=res.state.turn_number,
                action_index=action_index,
                turn_phase=turn_phase,
                state_version=state.state_version + 1,
                scores={
                    "RED": res.state.scores.get(PkgPlayer.RED, 0),
                    "BLUE": res.state.scores.get(PkgPlayer.BLUE, 0),
                },
                remaining_time_ms=state.remaining_time_ms,
                pieces=new_pieces,
                legal_actions=[],
                can_end_turn=can_end_turn,
                compound_origin=compound_origin,
                compound_member_ids=compound_member_ids,
                compound_moved_piece_ids=compound_moved_ids,
                last_event=event,
                result=result,
            )
            next_state.legal_actions = self.get_legal_actions(next_state)
            return next_state, event
        except ValueError:
            raise
        except Exception:
            return self.fallback.apply_action(state, request)

    def resign(self, state: GameState, side: Side) -> GameState:
        return self.fallback.resign(state, side)

    def draw(self, state: GameState) -> GameState:
        return self.fallback.draw(state)


default_engine_adapter = AuthoritativeEngineAdapter()
