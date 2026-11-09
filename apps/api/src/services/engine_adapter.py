"""
Commander Chess AI — Engine Adapter Interface & Mock Implementation
[MOCK ADAPTER - FOR API SCAFFOLDING & INTEGRATION]

NOTE (AGENTS.md Rule 3 & 6):
The authoritative game rules and state transitions belong solely to
packages/game-engine (managed by the Project Owner / Student).
This adapter defines the clean dependency injection boundary:
- When packages/game-engine is implemented, AuthoritativeEngineAdapter
  will replace this mock without breaking any API routes or UI contracts.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict, Set, Any
import uuid
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
    (-2, -1), (2, -1), (-2, 1), (2, 1)
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
    """Kiểm tra xem bước đi chéo của Hải quân có cắt qua vùng đất liền giữa bờ biển và bờ sông hay không.
    Ví dụ: giữa (x=2, y=7) và (x=3, y=6) thuộc đất liền bên Xanh (không thể đi đến (6, 3) hoặc (5, 4)).
    Giữa (x=2, y=4) và (x=3, y=5) thuộc đất liền bên Đỏ.
    """
    if x1 == x2 or y1 == y2:
        return False
    if min(x1, x2) >= 2 and ((y1 >= 7 and y2 <= 6) or (y2 >= 7 and y1 <= 6)):
        return True
    if min(x1, x2) >= 2 and ((y1 <= 4 and y2 >= 5) or (y2 <= 4 and y1 >= 5)):
        return True
    return False


def can_piece_cross_river_to_empty(piece_type: PieceType, from_x: int, from_y: int, to_x: int, to_y: int) -> bool:
    """Kiểm tra xem quân có được tự vượt sông sâu sang ô trống không (RULE-RIVER-001 & DEC-018)
    - Sông ngầm: Chỉ đi qua theo ĐƯỜNG THẲNG tại cột x = 5 và x = 7 (from_x == to_x and from_x in (5, 7)).
    - Tên lửa, pháo binh không thể đi qua sông sâu theo đường chéo sang ô trống.
    - Muốn đi qua sông sâu chỉ có thể nhờ công binh chở qua hoặc ăn quân thế chỗ bên kia sông.
    """
    if not is_crossing_river(from_y, to_y):
        return True
    if from_x == to_x and from_x in (5, 7):
        return True
    if piece_type in (PieceType.ANTI_AIR, PieceType.ARTILLERY, PieceType.MISSILE):
        return False
    return True


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


def get_air_defense_zones(target_side: Side, pieces: List[PieceState]) -> Set[Tuple[int, int]]:
    zones: Set[Tuple[int, int]] = set()
    aa_units = [
        p for p in pieces
        if p.is_alive and p.side == target_side and p.type in (PieceType.ANTI_AIR, PieceType.MISSILE, PieceType.NAVY)
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
    """Kiểm tra xem toàn bộ hành trình bay có chạm hoặc cắt qua vùng phòng không hay không (AIR-01, Q11)"""
    def is_aa_point(x: int, y: int) -> bool:
        if (x, y) in enemy_aa_zones:
            return True
        if enemy_aa_units:
            return any(u.is_alive and u.position.x == x and u.position.y == y for u in enemy_aa_units)
        return False

    # 1. Điểm xuất phát hoặc điểm đến nằm trong vành đai lửa / trên đầu đơn vị phòng không
    if is_aa_point(from_pos.x, from_pos.y):
        return True
    if is_aa_point(to_pos.x, to_pos.y):
        return True

    # 2. Toàn bộ các giao điểm trung gian trên đường bay
    step_x = 1 if to_pos.x > from_pos.x else (-1 if to_pos.x < from_pos.x else 0)
    step_y = 1 if to_pos.y > from_pos.y else (-1 if to_pos.y < from_pos.y else 0)
    total_steps = max(abs(to_pos.x - from_pos.x), abs(to_pos.y - from_pos.y))
    for s in range(1, total_steps):
        inter_x = from_pos.x + step_x * s
        inter_y = from_pos.y + step_y * s
        if is_aa_point(inter_x, inter_y):
            return True
    return False


def is_commanders_facing(pieces: List[PieceState]) -> bool:
    red_cmd = next((p for p in pieces if p.is_alive and p.side == Side.RED and p.type == PieceType.COMMANDER), None)
    blue_cmd = next((p for p in pieces if p.is_alive and p.side == Side.BLUE and p.type == PieceType.COMMANDER), None)

    if not red_cmd or not blue_cmd:
        return False

    # Check if either Commander is in HQ
    red_in_hq = any(
        p.is_alive and p.side == Side.RED and p.type == PieceType.HEADQUARTERS and
        p.position.x == red_cmd.position.x and p.position.y == red_cmd.position.y and
        red_cmd.carried_by_id == p.piece_id
        for p in pieces
    )
    blue_in_hq = any(
        p.is_alive and p.side == Side.BLUE and p.type == PieceType.HEADQUARTERS and
        p.position.x == blue_cmd.position.x and p.position.y == blue_cmd.position.y and
        blue_cmd.carried_by_id == p.piece_id
        for p in pieces
    )
    if red_in_hq or blue_in_hq:
        return False

    # Same column
    if red_cmd.position.x == blue_cmd.position.x:
        x = red_cmd.position.x
        min_y = min(red_cmd.position.y, blue_cmd.position.y)
        max_y = max(red_cmd.position.y, blue_cmd.position.y)
        has_obstacle = any(
            p.is_alive and p.position.x == x and min_y < p.position.y < max_y
            for p in pieces
        )
        if not has_obstacle:
            return True

    # Same row
    if red_cmd.position.y == blue_cmd.position.y:
        y = red_cmd.position.y
        min_x = min(red_cmd.position.x, blue_cmd.position.x)
        max_x = max(red_cmd.position.x, blue_cmd.position.x)
        has_obstacle = any(
            p.is_alive and p.position.y == y and min_x < p.position.x < max_x
            for p in pieces
        )
        if not has_obstacle:
            return True

    return False


def is_hq_facing_enemy_commander(hq: PieceState, enemy_cmd: PieceState, pieces: List[PieceState]) -> bool:
    if hq.position.x == enemy_cmd.position.x:
        x = hq.position.x
        min_y = min(hq.position.y, enemy_cmd.position.y)
        max_y = max(hq.position.y, enemy_cmd.position.y)
        has_obstacle = any(
            p.is_alive and p.position.x == x and min_y < p.position.y < max_y and
            p.piece_id not in (hq.piece_id, enemy_cmd.piece_id)
            for p in pieces
        )
        if not has_obstacle:
            return True

    if hq.position.y == enemy_cmd.position.y:
        y = hq.position.y
        min_x = min(hq.position.x, enemy_cmd.position.x)
        max_x = max(hq.position.x, enemy_cmd.position.x)
        has_obstacle = any(
            p.is_alive and p.position.y == y and min_x < p.position.x < max_x and
            p.piece_id not in (hq.piece_id, enemy_cmd.piece_id)
            for p in pieces
        )
        if not has_obstacle:
            return True

    return False


def is_square_attacked_by_enemy(
    pieces: List[PieceState],
    target_x: int,
    target_y: int,
    enemy_side: Side,
) -> bool:
    """Kiểm tra xem một ô (target_x, target_y) có đang nằm trong tầm tấn công/chiếu của bất kỳ quân địch nào không."""
    piece_map: Dict[Tuple[int, int], PieceState] = {}
    for p in pieces:
        if p.is_alive and p.carried_by_id is None:
            piece_map[(p.position.x, p.position.y)] = p

    for p in pieces:
        if not p.is_alive or p.side != enemy_side or p.carried_by_id is not None:
            continue

        px, py = p.position.x, p.position.y
        dx = target_x - px
        dy = target_y - py
        adx = abs(dx)
        ady = abs(dy)

        if adx == 0 and ady == 0:
            continue

        is_orth = (adx == 0 or ady == 0)
        is_diag = (adx == ady)
        if not is_orth and not is_diag:
            continue

        dist = max(adx, ady)
        step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_y = 0 if dy == 0 else (1 if dy > 0 else -1)

        # 1. COMMANDER
        if p.type == PieceType.COMMANDER:
            if is_orth:
                blocked = False
                for s in range(1, dist):
                    if (px + step_x * s, py + step_y * s) in piece_map:
                        blocked = True
                        break
                if not blocked:
                    return True
            if (is_orth and dist == 1) or (p.is_hero and dist <= 2):
                return True

        # 2. INFANTRY & ENGINEER
        elif p.type in (PieceType.INFANTRY, PieceType.ENGINEER):
            dirs_ok = True if p.is_hero else is_orth
            max_r = 2 if p.is_hero else 1
            if dirs_ok and dist <= max_r:
                blocked = False
                for s in range(1, dist):
                    if (px + step_x * s, py + step_y * s) in piece_map:
                        blocked = True
                        break
                if not blocked:
                    return True

        # 3. MILITIA
        elif p.type == PieceType.MILITIA:
            max_r = 2 if p.is_hero else 1
            if dist <= max_r:
                blocked = False
                for s in range(1, dist):
                    if (px + step_x * s, py + step_y * s) in piece_map:
                        blocked = True
                        break
                if not blocked:
                    return True

        # 4. ANTI_AIR
        elif p.type == PieceType.ANTI_AIR:
            dirs_ok = True if p.is_hero else is_orth
            max_r = 2 if p.is_hero else 1
            if dirs_ok and dist <= max_r:
                blocked = False
                for s in range(1, dist):
                    if (px + step_x * s, py + step_y * s) in piece_map:
                        blocked = True
                        break
                if not blocked:
                    return True

        # 5. TANK
        elif p.type == PieceType.TANK:
            dirs_ok = True if p.is_hero else is_orth
            max_r = 3 if p.is_hero else 2
            if dirs_ok and dist <= max_r:
                blocked = False
                for s in range(1, dist):
                    if (px + step_x * s, py + step_y * s) in piece_map:
                        blocked = True
                        break
                if not blocked:
                    return True

        # 6. MISSILE
        elif p.type == PieceType.MISSILE:
            max_r = (3 if p.is_hero else 2) if is_orth else (2 if p.is_hero else 1)
            if dist <= max_r:
                blocked = False
                for s in range(1, dist):
                    if (px + step_x * s, py + step_y * s) in piece_map:
                        blocked = True
                        break
                if not blocked:
                    return True

        # 7. ARTILLERY
        elif p.type == PieceType.ARTILLERY:
            max_r = 4 if p.is_hero else 3
            if dist <= max_r:
                return True

        # 8. AIRCRAFT
        elif p.type == PieceType.AIRCRAFT:
            max_r = 5 if p.is_hero else 4
            if dist <= max_r:
                return True

        # 9. NAVY
        elif p.type == PieceType.NAVY:
            max_r = 4 if p.is_hero else 3
            if dist <= max_r and can_navy_occupy_square(px, py):
                if is_diag and is_navy_land_diagonal(px, py, target_x, target_y):
                    continue
                blocked = False
                for s in range(1, dist):
                    occ = piece_map.get((px + step_x * s, py + step_y * s))
                    if occ and occ.type == PieceType.NAVY:
                        blocked = True
                        break
                if not blocked:
                    return True

        # 10. HEADQUARTERS
        elif p.type == PieceType.HEADQUARTERS:
            if p.is_hero and dist <= 2:
                blocked = False
                for s in range(1, dist):
                    if (px + step_x * s, py + step_y * s) in piece_map:
                        blocked = True
                        break
                if not blocked:
                    return True

    return False


def is_commander_in_check(pieces: List[PieceState], side: Side) -> bool:
    """Kiểm tra xem Tư lệnh của một phe có đang bị chiếu hay không (DEC-019)."""
    cmd = next((p for p in pieces if p.is_alive and p.side == side and p.type == PieceType.COMMANDER), None)
    if not cmd:
        return False
    if cmd.carried_by_id is not None:
        carrier = next((p for p in pieces if p.is_alive and p.piece_id == cmd.carried_by_id), None)
        if not carrier:
            return False
        if carrier.type == PieceType.HEADQUARTERS:
            return False  # Trú ẩn an toàn trong Sở chỉ huy
        enemy_side = Side.BLUE if side == Side.RED else Side.RED
        return is_square_attacked_by_enemy(pieces, carrier.position.x, carrier.position.y, enemy_side)

    enemy_side = Side.BLUE if side == Side.RED else Side.RED
    return is_square_attacked_by_enemy(pieces, cmd.position.x, cmd.position.y, enemy_side)


def select_smart_ai_action(
    state: GameState,
    ai_side: Side,
    rng: Optional[Any] = None,
) -> Optional[LegalAction]:
    """
    Lựa chọn nước đi thông minh và an toàn cho tác tử AI (DEC-019 & AI-KING-SAFETY):
    1. Khi Tư lệnh KHÔNG bị chiếu:
       - Ưu tiên 100% các quân tác chiến (Bộ binh, Xe tăng, Dân quân, Pháo, Cao xạ, Tên lửa, Máy bay, Hải quân, Công binh),
         hoặc đưa Tư lệnh vào Sở chỉ huy / lên phương tiện an toàn.
       - Tuyệt đối không chọn nước đi của Tư lệnh lang thang ra ngoài bàn cờ cho đối phương ăn.
       - Nếu toàn bộ quân khác hết nước đi (chỉ còn Tư lệnh có thể đi), Tư lệnh chỉ được đi vào ô
         hoàn toàn an toàn mà đối phương không thể ăn được!
    2. Khi Tư lệnh ĐANG BỊ CHIẾU:
       - Bắt buộc chọn nước đi hóa giải chiếu (hóa giải thế bị đe dọa):
         a) Dùng quân khác chặn đường chiếu (nếu quân đối phương chiếu từ xa và đường chiếu có thể bị chặn).
         b) Dùng quân khác hoặc chính Tư lệnh ăn quân địch đang chiếu.
         c) Chạy Tư lệnh sang ô an toàn không bị đối phương ăn.
         d) Đưa Tư lệnh trú ẩn vào Sở chỉ huy.
    """
    import random
    choose_fn = rng.choice if rng is not None else random.choice

    state_for_ai = state.model_copy(
        update={
            "side_to_move": ai_side,
            "turn_phase": TurnPhase.NORMAL,
            "can_end_turn": False,
        }
    )
    all_legal = default_engine_adapter.get_legal_actions(state_for_ai)
    valid_actions = [
        a for a in all_legal
        if any(p.piece_id == a.piece_id and p.side == ai_side and p.is_alive for p in state.pieces)
    ]
    if not valid_actions:
        return None

    cmd = next((p for p in state.pieces if p.is_alive and p.side == ai_side and p.type == PieceType.COMMANDER), None)
    enemy_side = Side.RED if ai_side == Side.BLUE else Side.BLUE

    # Lọc an toàn tuyệt đối: Không để Tư lệnh bị chiếu sau nước đi,
    # và nếu Tư lệnh di chuyển thì ô đến tuyệt đối không bị đối phương ăn!
    safe_actions: List[LegalAction] = []
    for act in valid_actions:
        sim = simulate_action(act, state.pieces)
        if is_commander_in_check(sim, ai_side):
            continue
        if cmd and act.piece_id == cmd.piece_id and act.action_type != ActionType.BOARD:
            if is_square_attacked_by_enemy(sim, act.to_pos.x, act.to_pos.y, enemy_side):
                continue
        safe_actions.append(act)

    pool = safe_actions if safe_actions else valid_actions
    is_in_check = is_commander_in_check(state.pieces, ai_side)

    if is_in_check:
        # TÌNH HUỐNG 1: ĐANG BỊ CHIẾU
        # a) Dùng quân khác chặn đường chiếu hoặc ăn quân đang chiếu
        blocking_or_capturing = [
            a for a in pool
            if cmd is not None and a.piece_id != cmd.piece_id
        ]
        # b) Tư lệnh trú ẩn vào Sở chỉ huy
        shelter_actions = [
            a for a in pool
            if cmd is not None and a.piece_id == cmd.piece_id and a.action_type == ActionType.BOARD
        ]
        # c) Tư lệnh chạy sang ô an toàn (không bị ăn)
        cmd_escape_actions = [
            a for a in pool
            if cmd is not None and a.piece_id == cmd.piece_id and a.action_type != ActionType.BOARD
        ]

        if blocking_or_capturing:
            preferred = blocking_or_capturing + shelter_actions + cmd_escape_actions
            return choose_fn(preferred)
        elif shelter_actions:
            return choose_fn(shelter_actions)
        elif cmd_escape_actions:
            return choose_fn(cmd_escape_actions)
        else:
            return choose_fn(pool)
    else:
        # TÌNH HUỐNG 2: KHÔNG BỊ CHIẾU
        # Ưu tiên các quân tác chiến hoặc trú ẩn, tuyệt đối không đi Tư lệnh lang thang cho đối phương ăn
        tactical_actions = [
            a for a in pool
            if cmd is not None and a.piece_id != cmd.piece_id
        ]
        shelter_actions = [
            a for a in pool
            if cmd is not None and a.piece_id == cmd.piece_id and a.action_type == ActionType.BOARD
        ]

        if tactical_actions:
            preferred = tactical_actions + shelter_actions
            return choose_fn(preferred)
        else:
            return choose_fn(pool)


def simulate_action(action: LegalAction, pieces: List[PieceState]) -> List[PieceState]:
    new_pieces: List[PieceState] = []
    actor = next((p for p in pieces if p.piece_id == action.piece_id), None)
    target = next((p for p in pieces if p.piece_id == action.target_piece_id), None) if action.target_piece_id else None
    is_carrier_pickup = (
        action.action_type == ActionType.BOARD and
        actor is not None and target is not None and
        can_board_carrier(passenger=target, carrier=actor)
    )

    for p in pieces:
        if action.action_type == ActionType.BOARD and is_carrier_pickup:
            if p.piece_id == action.piece_id:
                new_pieces.append(p.model_copy(update={
                    "position": action.to_pos,
                    "carried_by_id": None,
                }))
            elif p.piece_id == action.target_piece_id:
                new_pieces.append(p.model_copy(update={
                    "position": action.to_pos,
                    "carried_by_id": action.piece_id,
                }))
            elif p.carried_by_id == action.piece_id:
                new_pieces.append(p.model_copy(update={"position": action.to_pos}))
            else:
                new_pieces.append(p)
            continue

        if action.target_piece_id and p.piece_id == action.target_piece_id:
            if action.action_type == ActionType.BOARD:
                new_pieces.append(p.model_copy(update={
                    "carrying_piece_ids": p.carrying_piece_ids + [action.piece_id]
                }))
            else:
                new_pieces.append(p.model_copy(update={"is_alive": False}))
        elif p.piece_id == action.piece_id:
            if action.action_type == ActionType.CAPTURE_STAND:
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
        elif p.carried_by_id == action.piece_id and action.action_type != ActionType.CAPTURE_STAND:
            new_pieces.append(p.model_copy(update={"position": action.to_pos}))
        else:
            new_pieces.append(p)
    return new_pieces


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
    """
    Mock Adapter implementing standard movement & capture rules matching
    docs/GAME_RULES.md, docs/BUG_REPORT.md, and docs/OPEN_QUESTIONS.md.
    """

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

        # Blue side (19 pieces) - Mirrored deployment with Navy 2 at y=8, x=2
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
        enemy_aa_zones = get_air_defense_zones(enemy_side, state.pieces)

        def can_occupy_square(piece: PieceState, nx: int, ny: int) -> bool:
            if piece.type == PieceType.NAVY:
                return can_navy_occupy_square(nx, ny)
            # Tên lửa và máy bay KHÔNG thể di chuyển/đáp trên biển trống (x <= 1)
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

            x, y = piece.position.x, piece.position.y
            symbol = PIECE_NOTATION_SYMBOL.get(piece.type, "B")

            def push_move(nx: int, ny: int):
                actions.append(
                    LegalAction(
                        action_id=f"m_{piece.piece_id}_{nx}_{ny}",
                        action_type=ActionType.MOVE,
                        piece_id=piece.piece_id,
                        from_pos=Position(x=x, y=y),
                        to_pos=Position(x=nx, y=ny),
                        target_piece_id=None,
                        notation=f"{symbol} [{y} ; {x}] _ [{ny} ; {nx}]",
                        description=f"{piece.type.value} di chuyển đến [{ny} ; {nx}]",
                    )
                )

            def push_capture(nx: int, ny: int, target: PieceState, act_type: ActionType):
                act_sym = "_@_" if act_type == ActionType.CAPTURE_STAND else "@"
                target_sym = PIECE_NOTATION_SYMBOL.get(target.type, "B")
                actions.append(
                    LegalAction(
                        action_id=f"c_{piece.piece_id}_{target.piece_id}_{act_type.value}",
                        action_type=act_type,
                        piece_id=piece.piece_id,
                        from_pos=Position(x=x, y=y),
                        to_pos=Position(x=nx, y=ny),
                        target_piece_id=target.piece_id,
                        notation=f"{symbol} [{y} ; {x}] {act_sym} {target_sym} [{ny} ; {nx}]",
                        description=f"{piece.type.value} tấn công {target.type.value} tại [{ny} ; {nx}]",
                    )
                )

            def push_board(carrier: PieceState):
                carrier_sym = PIECE_NOTATION_SYMBOL.get(carrier.type, "T")
                actions.append(
                    LegalAction(
                        action_id=f"b_{piece.piece_id}_{carrier.piece_id}",
                        action_type=ActionType.BOARD,
                        piece_id=piece.piece_id,
                        from_pos=Position(x=x, y=y),
                        to_pos=Position(x=carrier.position.x, y=carrier.position.y),
                        target_piece_id=carrier.piece_id,
                        notation=f"{symbol} [{y} ; {x}] ^ {carrier_sym} [{carrier.position.y} ; {carrier.position.x}]",
                        description=f"{piece.type.value} lên {carrier.type.value} tại [{carrier.position.y} ; {carrier.position.x}]",
                    )
                )

            def push_pickup(passenger: PieceState):
                carrier_sym = PIECE_NOTATION_SYMBOL.get(piece.type, "T")
                passenger_sym = PIECE_NOTATION_SYMBOL.get(passenger.type, "B")
                actions.append(
                    LegalAction(
                        action_id=f"b_{piece.piece_id}_{passenger.piece_id}",
                        action_type=ActionType.BOARD,
                        piece_id=piece.piece_id,
                        from_pos=Position(x=x, y=y),
                        to_pos=Position(x=passenger.position.x, y=passenger.position.y),
                        target_piece_id=passenger.piece_id,
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
                                    push_capture(nx, ny, target, ActionType.CAPTURE_REPLACE)
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
                                act_type = ActionType.CAPTURE_STAND if is_sea_square(nx) else ActionType.CAPTURE_REPLACE
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
                                act_type = ActionType.CAPTURE_STAND if is_sea_square(nx) else ActionType.CAPTURE_REPLACE
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
                                act_type = ActionType.CAPTURE_STAND if is_sea_square(nx) else ActionType.CAPTURE_REPLACE
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
                                act_type = ActionType.CAPTURE_STAND if is_sea_square(nx) else ActionType.CAPTURE_REPLACE
                                push_capture(nx, ny, target, act_type)
                            elif can_board_carrier(passenger=target, carrier=piece) and not target.carried_by_id:
                                push_pickup(target)
                            elif can_board_carrier(passenger=piece, carrier=target):
                                push_board(target)
                            break

            # 6. MISSILE
            elif piece.type == PieceType.MISSILE:
                straight_range = 3 if piece.is_hero else 2
                diag_range = 2 if piece.is_hero else 1

                for dx, dy in ORTHOGONAL:
                    for step in range(1, straight_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if not target:
                            if is_sea_square(nx):
                                break # Tên lửa không thể di chuyển trên biển
                            if can_piece_cross_river_to_empty(PieceType.MISSILE, x, y, nx, ny):
                                push_move(nx, ny)
                        else:
                            if target.side != active_side:
                                act_type = ActionType.CAPTURE_STAND if is_sea_square(nx) else ActionType.CAPTURE_REPLACE
                                push_capture(nx, ny, target, act_type)
                            elif can_board_carrier(piece, target):
                                push_board(target)
                            break

                for dx, dy in DIAGONAL:
                    for step in range(1, diag_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if not target:
                            if is_sea_square(nx):
                                break # Tên lửa không thể di chuyển trên biển
                            if can_piece_cross_river_to_empty(PieceType.MISSILE, x, y, nx, ny):
                                push_move(nx, ny)
                        else:
                            if target.side != active_side:
                                act_type = ActionType.CAPTURE_STAND if is_sea_square(nx) else ActionType.CAPTURE_REPLACE
                                push_capture(nx, ny, target, act_type)
                            elif can_board_carrier(passenger=target, carrier=piece) and not target.carried_by_id:
                                push_pickup(target)
                            elif can_board_carrier(passenger=piece, carrier=target):
                                push_board(target)
                            break

            # 7. ARTILLERY
            elif piece.type == PieceType.ARTILLERY:
                max_range = 4 if piece.is_hero else 3
                for dx, dy in ALL_8:
                    # Move to empty (blocked)
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

                    # Penetrating attack: chỉ ăn thế chỗ trên đất liền, bắn tại chỗ khi diệt tàu ngoài biển
                    for step in range(1, max_range + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny):
                            break
                        target = piece_map.get((nx, ny))
                        if target and target.side != active_side:
                            if is_sea_square(nx):
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
                            # Máy bay không thể dừng chân trên biển trống
                            if not is_sea_square(nx):
                                push_move(nx, ny)
                        elif target.side == active_side:
                            if can_board_carrier(passenger=target, carrier=piece) and not target.carried_by_id and not is_sea_square(nx):
                                push_pickup(target)
                            elif target.type == PieceType.NAVY and can_board_carrier(piece, target):
                                push_board(target)
                            break
                        else:
                            # Quân địch
                            if is_sea_square(nx):
                                push_capture(nx, ny, target, ActionType.CAPTURE_STAND)
                            else:
                                if target.type == PieceType.AIRCRAFT:
                                    push_capture(nx, ny, target, ActionType.CAPTURE_REPLACE)
                                else:
                                    push_capture(nx, ny, target, ActionType.CAPTURE_STAND)
                                    push_capture(nx, ny, target, ActionType.CAPTURE_REPLACE)
                            break

            # 9. COMMANDER
            elif piece.type == PieceType.COMMANDER:
                for dx, dy in ORTHOGONAL:
                    for step in range(1, 12):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny) or not can_occupy_square(piece, nx, ny):
                            break

                        # Check if intermediate step faces enemy Commander (BUG-CMD-001)
                        sim_pieces = [
                            p.model_copy(update={"position": Position(x=nx, y=ny)}) if p.piece_id == piece.piece_id else p
                            for p in state.pieces
                        ]
                        if is_commanders_facing(sim_pieces):
                            break

                        target = piece_map.get((nx, ny))
                        if not target:
                            push_move(nx, ny)
                        else:
                            if step == 1 and target.side != active_side:
                                push_capture(nx, ny, target, ActionType.CAPTURE_REPLACE)
                            elif step == 1 and target.side == active_side:
                                if target.type == PieceType.HEADQUARTERS and not target.is_hero:
                                    if enemy_cmd and not is_hq_facing_enemy_commander(target, enemy_cmd, state.pieces):
                                        push_board(target)
                                elif can_board_carrier(piece, target):
                                    push_board(target)
                            break

            # 10. NAVY
            elif piece.type == PieceType.NAVY:
                max_straight = 5 if piece.is_hero else 4
                for dx, dy in ALL_8:
                    enemy_navy_encountered = False
                    for step in range(1, max_straight + 1):
                        nx, ny = x + dx * step, y + dy * step
                        if not is_inside_board(nx, ny) or is_ford_square(nx, ny):
                            break

                        prev_x = x + dx * (step - 1)
                        prev_y = y + dy * (step - 1)
                        if is_navy_land_diagonal(prev_x, prev_y, nx, ny):
                            break  # Đường chéo thuộc đất liền: dừng tia ngay lập tức!

                        target = piece_map.get((nx, ny))
                        is_water = can_navy_occupy_square(nx, ny)

                        if not target:
                            if not is_water:
                                break  # Giữa đường vướng đất liền: dừng tia ngay, không thể đi xuyên qua đất liền (RULE-NAVY-002)
                            if not enemy_navy_encountered:
                                push_move(nx, ny)
                        else:
                            if target.side == active_side:
                                if target.type == PieceType.NAVY:
                                    break
                                elif is_water and can_board_carrier(passenger=target, carrier=piece) and not target.carried_by_id:
                                    push_pickup(target)
                                    break
                                else:
                                    if not is_water:
                                        break
                                    continue
                            else:
                                if target.type == PieceType.NAVY:
                                    if not is_water:
                                        break
                                    if not enemy_navy_encountered:
                                        push_capture(nx, ny, target, ActionType.CAPTURE_REPLACE)
                                        enemy_navy_encountered = True
                                    continue
                                else:
                                    if step <= (4 if piece.is_hero else 3):
                                        if is_shore_square(nx, ny):
                                            push_capture(nx, ny, target, ActionType.CAPTURE_REPLACE)
                                        else:
                                            push_capture(nx, ny, target, ActionType.CAPTURE_STAND)
                                    if not is_water:
                                        break

        # Filter out actions that result in Commander facing (BUG-CMD-001) or Commander in check (DEC-019)
        valid_actions = []
        for act in actions:
            sim = simulate_action(act, state.pieces)
            if not is_commanders_facing(sim) and not is_commander_in_check(sim, active_side):
                valid_actions.append(act)

        return valid_actions

    def apply_action(self, state: GameState, request: ActionRequest) -> Tuple[GameState, GameEvent]:
        if request.state_version != state.state_version:
            raise ValueError(f"State version mismatch: expected {state.state_version}, got {request.state_version}")

        actor = next((p for p in state.pieces if p.piece_id == request.piece_id and p.is_alive), None)
        if not actor:
            raise ValueError(f"Piece {request.piece_id} not found or not alive")
        if actor.side != state.side_to_move and state.turn_phase != TurnPhase.STACK_ACTIVE:
            raise ValueError(f"Piece {request.piece_id} does not belong to active side {state.side_to_move}")

        captured_piece: Optional[PieceState] = None
        new_pieces: List[PieceState] = []
        score_delta = {Side.RED: 0, Side.BLUE: 0}

        enemy_side = Side.BLUE if actor.side == Side.RED else Side.RED
        enemy_aa_zones = get_air_defense_zones(enemy_side, state.pieces)
        enemy_aa_units = [
            p for p in state.pieces
            if p.is_alive and p.side == enemy_side and p.type in (PieceType.ANTI_AIR, PieceType.MISSILE, PieceType.NAVY)
        ]
        is_actor_aircraft = actor.type == PieceType.AIRCRAFT and not actor.is_hero
        is_target_aa_unit = any(
            u.position.x == request.to_pos.x and u.position.y == request.to_pos.y
            for u in enemy_aa_units
        )
        is_in_aa_zone = (
            is_actor_aircraft and
            (
                is_target_aa_unit or
                is_aircraft_flight_affected_by_aa(actor.position, request.to_pos, enemy_aa_zones, enemy_aa_units)
            )
        )
        target = next((p for p in state.pieces if p.piece_id == request.target_piece_id), None) if request.target_piece_id else None
        is_carrier_pickup = (
            request.action_type == ActionType.BOARD and
            actor is not None and target is not None and
            can_board_carrier(passenger=target, carrier=actor)
        )
        all_carried_ids = actor.carrying_piece_ids if actor else []

        for p in state.pieces:
            # 1. BOARD
            if request.action_type == ActionType.BOARD:
                if is_carrier_pickup:
                    if p.piece_id == request.piece_id:
                        new_pieces.append(p.model_copy(update={
                            "position": request.to_pos,
                            "carried_by_id": None,
                        }))
                    elif p.piece_id == request.target_piece_id:
                        new_pieces.append(p.model_copy(update={
                            "position": request.to_pos,
                            "carried_by_id": request.piece_id,
                        }))
                    elif p.piece_id in all_carried_ids:
                        new_pieces.append(p.model_copy(update={
                            "position": request.to_pos,
                        }))
                    else:
                        new_pieces.append(p)
                else:
                    if p.piece_id == request.piece_id:
                        new_pieces.append(p.model_copy(update={
                            "position": request.to_pos,
                            "carried_by_id": request.target_piece_id,
                        }))
                    elif p.piece_id == request.target_piece_id:
                        new_pieces.append(p.model_copy(update={
                            "carrying_piece_ids": p.carrying_piece_ids + [request.piece_id]
                        }))
                    else:
                        new_pieces.append(p)
                continue

            # 2. Target piece
            if request.target_piece_id and p.piece_id == request.target_piece_id:
                # Headquarters protection: if Commander inside, Commander survives (Q9)
                has_commander = any(
                    other.is_alive and other.type == PieceType.COMMANDER and other.carried_by_id == p.piece_id
                    for other in state.pieces
                )
                p_dead = p.model_copy(update={"is_alive": False})
                captured_piece = p_dead
                score_val = PIECE_SCORES.get(p.type, 10)
                score_delta[actor.side] += score_val
                new_pieces.append(p_dead)
                continue

            # 3. Commander in Headquarters being attacked
            if (
                request.target_piece_id and
                p.type == PieceType.COMMANDER and
                p.carried_by_id == request.target_piece_id
            ):
                target_unit = next((u for u in state.pieces if u.piece_id == request.target_piece_id), None)
                if target_unit and target_unit.type == PieceType.HEADQUARTERS:
                    new_pieces.append(p.model_copy(update={"carried_by_id": None, "is_alive": True}))
                    continue

            # 4. Passengers in normal vehicles killed together
            if request.target_piece_id and p.carried_by_id == request.target_piece_id:
                target_unit = next((u for u in state.pieces if u.piece_id == request.target_piece_id), None)
                if target_unit and target_unit.type != PieceType.HEADQUARTERS:
                    p_dead = p.model_copy(update={"is_alive": False, "carried_by_id": None})
                    score_val = PIECE_SCORES.get(p.type, 10)
                    score_delta[actor.side] += score_val
                    new_pieces.append(p_dead)
                    continue

            # Update carrier if actor passenger just moved out / deployed
            if p.carrying_piece_ids and request.piece_id in p.carrying_piece_ids:
                p = p.model_copy(update={
                    "carrying_piece_ids": [cid for cid in p.carrying_piece_ids if cid != request.piece_id]
                })

            # 5. Actor piece
            if p.piece_id == request.piece_id:
                if is_in_aa_zone:
                    # Máy bay bay vào vùng phòng không:
                    # - Tấn công: 1 đổi 1 (máy bay bị diệt cùng mục tiêu)
                    # - Di chuyển (MOVE): bị tiêu diệt ngay lập tức
                    score_val = PIECE_SCORES.get(PieceType.AIRCRAFT, 40)
                    score_delta[enemy_side] += score_val
                    new_pieces.append(p.model_copy(update={
                        "is_alive": False,
                        "position": request.to_pos,
                        "carried_by_id": None,
                    }))
                elif request.action_type == ActionType.CAPTURE_STAND:
                    new_pieces.append(p)
                else:
                    new_pieces.append(p.model_copy(update={
                        "position": request.to_pos,
                        "carried_by_id": None,
                    }))
            # 6. Carried by actor
            elif p.carried_by_id == request.piece_id and request.action_type != ActionType.CAPTURE_STAND:
                new_pieces.append(p.model_copy(update={"position": request.to_pos}))
            else:
                new_pieces.append(p)

        # Đảm bảo tính nhất quán 2 chiều tuyệt đối giữa carried_by_id và carrying_piece_ids:
        # Nếu quân được chở rời đi hoặc bị tiêu diệt, quân chở lập tức trở về trạng thái bình thường (xóa id khỏi carrying_piece_ids)
        for p in new_pieces:
            p.carrying_piece_ids = [
                other.piece_id for other in new_pieces
                if other.is_alive and other.carried_by_id == p.piece_id
            ]

        # Auto-promote heroes (DEC-015: Solitary HQ only)
        for s in (Side.RED, Side.BLUE):
            alive_pieces = [p for p in new_pieces if p.is_alive and p.side == s]
            non_cmd_non_hq = [p for p in alive_pieces if p.type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS)]
            hq_pieces = [p for p in alive_pieces if p.type == PieceType.HEADQUARTERS]
            if len(non_cmd_non_hq) == 1 and not non_cmd_non_hq[0].is_hero:
                hero_id = non_cmd_non_hq[0].piece_id
                new_pieces = [p.model_copy(update={"is_hero": True}) if p.piece_id == hero_id else p for p in new_pieces]
            elif len(non_cmd_non_hq) == 0 and len(hq_pieces) == 1 and not hq_pieces[0].is_hero:
                hero_hq_id = hq_pieces[0].piece_id
                new_pieces = [
                    p.model_copy(update={"is_hero": True})
                    if p.piece_id == hero_hq_id else p
                    for p in new_pieces
                ]

        # 3. Auto-promote heroes on Check (RULE-HERO-CHECK)
        enemy_side_actor = Side.BLUE if actor.side == Side.RED else Side.RED
        enemy_cmd = next(
            (p for p in new_pieces if p.is_alive and p.side == enemy_side_actor and p.type == PieceType.COMMANDER and not p.carried_by_id),
            None
        )
        actor_checked_commander = False
        actor_was_promoted = False
        if enemy_cmd:
            temp_state = state.model_copy(update={"pieces": new_pieces, "side_to_move": actor.side})
            all_actions = self.get_legal_actions(temp_state)
            checking_ids = set()
            for act in all_actions:
                if act.action_type in (ActionType.CAPTURE_REPLACE, ActionType.CAPTURE_STAND):
                    if act.target_piece_id == enemy_cmd.piece_id or (act.to_pos.x == enemy_cmd.position.x and act.to_pos.y == enemy_cmd.position.y):
                        checking_ids.add(act.piece_id)
                        if act.piece_id == request.piece_id:
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

        # Generate event
        actor_sym = PIECE_NOTATION_SYMBOL.get(actor.type, "B")
        from_not = f"[{actor.position.y} ; {actor.position.x}]"
        to_not = f"[{request.to_pos.y} ; {request.to_pos.x}]"

        if is_in_aa_zone:
            if captured_piece or request.target_piece_id:
                # 1 đổi 1
                target_sym = PIECE_NOTATION_SYMBOL.get(captured_piece.type, "B") if captured_piece else "B"
                notation = f"{actor_sym} {from_not} >< {target_sym} {to_not}"
                evt_type = EventType.AIR_EXCHANGE
                event_target_id = captured_piece.piece_id if captured_piece else request.target_piece_id
            else:
                # Bị bắn hạ ngay lập tức khi bay vào/xuyên qua vùng phòng không
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
                if actor_was_promoted:
                    notation = f"{notation} > **{actor_sym}**"
                else:
                    notation = f"{notation} >"
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
                "from_pos": {"x": actor.position.x, "y": actor.position.y},
                "to_pos": {"x": request.to_pos.x, "y": request.to_pos.y},
            },
        )

        new_scores = {
            "RED": state.scores["RED"] + score_delta[Side.RED],
            "BLUE": state.scores["BLUE"] + score_delta[Side.BLUE],
        }

        # Terminal check: Commander captured
        game_over = False
        result = None
        if captured_piece and captured_piece.type == PieceType.COMMANDER:
            game_over = True
            score_delta[actor.side] += 50
            new_scores[actor.side.value] += 50
            result = GameResultDTO(
                winner=actor.side.value,
                reason=TerminationReason.COMMANDER_CAPTURED,
                final_scores=new_scores,
            )

        if request.is_compound_action:
            next_side = actor.side
            turn_phase = TurnPhase.STACK_ACTIVE
            can_end_turn = True
            action_index = state.action_index + 1
        else:
            next_side = Side.BLUE if actor.side == Side.RED else Side.RED
            turn_phase = TurnPhase.NORMAL
            can_end_turn = False
            action_index = 1

        # Checkmate check: Opposing Commander in check and no legal moves (DEC-019)
        if not game_over and not request.is_compound_action:
            is_enemy_in_check = is_commander_in_check(new_pieces, next_side)
            if is_enemy_in_check:
                temp_next_state = GameState(
                    game_id=state.game_id,
                    mode=state.mode,
                    status=GameStatus.IN_PROGRESS,
                    side_to_move=next_side,
                    turn_index=state.turn_index,
                    action_index=1,
                    turn_phase=TurnPhase.NORMAL,
                    state_version=state.state_version + 1,
                    scores=new_scores,
                    remaining_time_ms=state.remaining_time_ms,
                    pieces=new_pieces,
                    legal_actions=[],
                    can_end_turn=False,
                    last_event=None,
                    result=None,
                )
                enemy_moves = self.get_legal_actions(temp_next_state)
                if len(enemy_moves) == 0:
                    game_over = True
                    score_delta[actor.side] += 50
                    new_scores[actor.side.value] += 50
                    notation = f"{notation} #"
                    event.notation = notation
                    if event.details:
                        event.details["is_checkmate"] = True
                        event.details["is_check"] = True
                    result = GameResultDTO(
                        winner=actor.side.value,
                        reason=TerminationReason.CHECKMATE,
                        final_scores=new_scores,
                    )

        new_status = GameStatus.GAME_OVER if game_over else GameStatus.IN_PROGRESS

        next_state = GameState(
            game_id=state.game_id,
            mode=state.mode,
            status=new_status,
            side_to_move=next_side if not game_over else actor.side,
            turn_index=state.turn_index + (1 if actor.side == Side.BLUE and not request.is_compound_action else 0),
            action_index=action_index,
            turn_phase=turn_phase,
            state_version=state.state_version + 1,
            scores=new_scores,
            remaining_time_ms=state.remaining_time_ms,
            pieces=new_pieces,
            legal_actions=[],
            can_end_turn=can_end_turn,
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
    """
    Authoritative Engine Adapter — tích hợp trực tiếp với packages/commander_game_engine
    như đặc tả tại AGENTS.md (Rule 3 & 6).
    
    Tự động chuyển đổi giữa schema API và schema nội bộ của game-engine.
    Hỗ trợ fallback sang MockEngineAdapter cho các tính năng chưa hoàn thiện trong engine
    (như Máy bay hay Cõng quân) để bảo đảm trải nghiệm không bị gián đoạn.
    """

    def __init__(self, fallback_adapter: Optional[BaseEngineAdapter] = None):
        self.fallback = fallback_adapter or MockEngineAdapter()

    def create_initial_state(self, game_id: str, mode: GameMode) -> GameState:
        try:
            from commander_game_engine.initial_setup import create_initial_state as create_pkg_initial_state
            pkg_state = create_pkg_initial_state()
            pieces = []
            for pid, p in pkg_state.pieces.items():
                ptype = (
                    PieceType.ANTI_AIR
                    if p.piece_type.value == "anti_aircraft"
                    else PieceType(p.piece_type.value.upper())
                )
                pieces.append(
                    PieceState(
                        piece_id=p.id,
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
            GameState as PkgGameState,
            Piece as PkgPiece,
            PieceType as PkgPieceType,
            Player as PkgPlayer,
        )

        board = Board()
        pkg_pieces = {}
        for p in state.pieces:
            if not p.is_alive:
                continue
            ptype_val = "anti_aircraft" if p.type == PieceType.ANTI_AIR else p.type.value.lower()
            pkg_type = PkgPieceType(ptype_val)
            pkg_owner = PkgPlayer.RED if p.side == Side.RED else PkgPlayer.BLUE
            pos = (p.position.y, p.position.x) if p.carried_by_id is None else None
            pkg_pieces[p.piece_id] = PkgPiece(
                id=p.piece_id,
                piece_type=pkg_type,
                owner=pkg_owner,
                position=pos,
                carried_by=p.carried_by_id,
                cargo=list(p.carrying_piece_ids),
                is_heroic=p.is_hero,
            )

        cur_player = PkgPlayer.RED if state.side_to_move == Side.RED else PkgPlayer.BLUE
        scores = {
            PkgPlayer.RED: state.scores.get("RED", 0),
            PkgPlayer.BLUE: state.scores.get("BLUE", 0),
        }
        return PkgGameState(
            board=board,
            pieces=pkg_pieces,
            current_player=cur_player,
            turn_number=state.turn_index,
            scores=scores,
        )

    def get_legal_actions(self, state: GameState) -> List[LegalAction]:
        if state.status == GameStatus.GAME_OVER:
            return []

        try:
            from commander_game_engine.move_generator import generate_legal_actions as generate_pkg_actions
            from commander_game_engine.actions import ActionType as PkgActionType

            pkg_state = self._to_pkg_state(state)
            pkg_actions = generate_pkg_actions(pkg_state)

            actions = []
            for act in pkg_actions:
                actor = next((p for p in state.pieces if p.piece_id == act.piece_id), None)
                if not actor:
                    continue
                sym = PIECE_NOTATION_SYMBOL.get(actor.type, "B")
                from_x, from_y = act.start[1], act.start[0]
                to_x, to_y = act.end[1], act.end[0]

                if act.action_type == PkgActionType.MOVE:
                    api_type = ActionType.MOVE
                    not_sym = "_"
                    desc = f"{actor.type.value} di chuyển đến [{to_y} ; {to_x}]"
                elif act.action_type == PkgActionType.CAPTURE:
                    api_type = ActionType.CAPTURE_REPLACE
                    not_sym = "@"
                    target = next((p for p in state.pieces if p.piece_id == act.target_piece_id), None)
                    target_sym = PIECE_NOTATION_SYMBOL.get(target.type, "B") if target else "B"
                    desc = f"{actor.type.value} tiêu diệt {target.type.value if target else 'quân địch'} tại [{to_y} ; {to_x}]"
                elif act.action_type == PkgActionType.BOMBARD:
                    api_type = ActionType.CAPTURE_STAND
                    not_sym = "_@_"
                    target = next((p for p in state.pieces if p.piece_id == act.target_piece_id), None)
                    target_sym = PIECE_NOTATION_SYMBOL.get(target.type, "B") if target else "B"
                    desc = f"{actor.type.value} pháo kích tiêu diệt {target.type.value if target else 'mục tiêu'} tại [{to_y} ; {to_x}]"
                else:
                    continue

                if act.target_piece_id:
                    notation = f"{sym} [{from_y} ; {from_x}] {not_sym} {target_sym} [{to_y} ; {to_x}]"
                else:
                    notation = f"{sym} [{from_y} ; {from_x}] {not_sym} [{to_y} ; {to_x}]"

                actions.append(
                    LegalAction(
                        action_id=f"a_{act.piece_id}_{to_x}_{to_y}_{api_type.value}",
                        action_type=api_type,
                        piece_id=act.piece_id,
                        from_pos=Position(x=from_x, y=from_y),
                        to_pos=Position(x=to_x, y=to_y),
                        target_piece_id=act.target_piece_id,
                        notation=notation,
                        description=desc,
                    )
                )

            # Bổ sung các hành động đặc thù (Aircraft, Board) từ fallback
            fallback_actions = self.fallback.get_legal_actions(state)
            pkg_keys = {(a.piece_id, a.to_pos.x, a.to_pos.y, a.action_type) for a in actions}
            for fa in fallback_actions:
                if (fa.piece_id, fa.to_pos.x, fa.to_pos.y, fa.action_type) not in pkg_keys:
                    actor = next((p for p in state.pieces if p.piece_id == fa.piece_id), None)
                    if actor and (
                        actor.type == PieceType.AIRCRAFT
                        or fa.action_type == ActionType.BOARD
                        or actor.carried_by_id is not None
                        or len(actor.carrying_piece_ids) > 0
                    ):
                        actions.append(fa)

            # Filter out actions that result in Commander facing (BUG-CMD-001) or Commander in check (DEC-019)
            valid_actions = []
            for act in actions:
                sim = simulate_action(act, state.pieces)
                if not is_commanders_facing(sim) and not is_commander_in_check(sim, state.side_to_move):
                    valid_actions.append(act)
            return valid_actions
        except Exception:
            return self.fallback.get_legal_actions(state)

    def apply_action(self, state: GameState, request: ActionRequest) -> Tuple[GameState, GameEvent]:
        try:
            from commander_game_engine.actions import ActionType as PkgActionType, AtomicAction as PkgAtomicAction
            from commander_game_engine.engine import apply_action as apply_pkg_action

            actor = next((p for p in state.pieces if p.piece_id == request.piece_id), None)
            if not actor:
                return self.fallback.apply_action(state, request)

            if (
                request.action_type == ActionType.BOARD
                or actor.type == PieceType.AIRCRAFT
                or actor.carried_by_id is not None
                or len(actor.carrying_piece_ids) > 0
                or request.is_compound_action
                or state.turn_phase == TurnPhase.STACK_ACTIVE
            ):
                return self.fallback.apply_action(state, request)

            pkg_state = self._to_pkg_state(state)
            if request.action_type == ActionType.MOVE:
                pkg_act_type = PkgActionType.MOVE
            elif request.action_type == ActionType.CAPTURE_REPLACE:
                pkg_act_type = PkgActionType.CAPTURE
            elif request.action_type == ActionType.CAPTURE_STAND:
                pkg_act_type = PkgActionType.BOMBARD
            else:
                return self.fallback.apply_action(state, request)

            pkg_action = PkgAtomicAction(
                action_type=pkg_act_type,
                piece_id=request.piece_id,
                start=(actor.position.y, actor.position.x),
                end=(request.to_pos.y, request.to_pos.x),
                target_piece_id=request.target_piece_id,
            )

            res = apply_pkg_action(pkg_state, pkg_action)
            if not res.accepted:
                if res.verdict.code.value != "unsupported":
                    raise ValueError(res.verdict.reason or "Hành động bất hợp lệ theo luật engine")
                return self.fallback.apply_action(state, request)

            new_pieces = []
            for p in state.pieces:
                if p.piece_id not in res.state.pieces:
                    new_pieces.append(p.model_copy(update={"is_alive": False}))
                else:
                    pkg_p = res.state.pieces[p.piece_id]
                    pos = Position(x=pkg_p.position[1], y=pkg_p.position[0]) if pkg_p.position else p.position
                    new_pieces.append(p.model_copy(update={
                        "position": pos,
                        "is_alive": True,
                        "is_hero": pkg_p.is_heroic,
                        "carried_by_id": pkg_p.carried_by,
                        "carrying_piece_ids": list(pkg_p.cargo),
                    }))

            # Đảm bảo tính nhất quán 2 chiều tuyệt đối giữa carried_by_id và carrying_piece_ids
            for p in new_pieces:
                p.carrying_piece_ids = [
                    other.piece_id for other in new_pieces
                    if other.is_alive and other.carried_by_id == p.piece_id
                ]

            # Auto-promote heroes (Last defender & solitary HQ - DEC-015)
            for s in (Side.RED, Side.BLUE):
                alive_pieces = [p for p in new_pieces if p.is_alive and p.side == s]
                non_cmd_non_hq = [p for p in alive_pieces if p.type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS)]
                hq_pieces = [p for p in alive_pieces if p.type == PieceType.HEADQUARTERS]
                if len(non_cmd_non_hq) == 1 and not non_cmd_non_hq[0].is_hero:
                    hero_id = non_cmd_non_hq[0].piece_id
                    new_pieces = [p.model_copy(update={"is_hero": True}) if p.piece_id == hero_id else p for p in new_pieces]
                elif len(non_cmd_non_hq) == 0 and len(hq_pieces) == 1 and not hq_pieces[0].is_hero:
                    hero_hq_id = hq_pieces[0].piece_id
                    new_pieces = [
                        p.model_copy(update={"is_hero": True})
                        if p.piece_id == hero_hq_id else p
                        for p in new_pieces
                    ]

            # 3. Auto-promote heroes on Check (RULE-HERO-CHECK)
            enemy_side_actor = Side.BLUE if actor.side == Side.RED else Side.RED
            enemy_cmd = next(
                (p for p in new_pieces if p.is_alive and p.side == enemy_side_actor and p.type == PieceType.COMMANDER and not p.carried_by_id),
                None
            )
            actor_checked_commander = False
            actor_was_promoted = False
            if enemy_cmd:
                temp_state = state.model_copy(update={"pieces": new_pieces, "side_to_move": actor.side})
                all_actions = self.fallback.get_legal_actions(temp_state)
                checking_ids = set()
                for act in all_actions:
                    if act.action_type in (ActionType.CAPTURE_REPLACE, ActionType.CAPTURE_STAND):
                        if act.target_piece_id == enemy_cmd.piece_id or (act.to_pos.x == enemy_cmd.position.x and act.to_pos.y == enemy_cmd.position.y):
                            checking_ids.add(act.piece_id)
                            if act.piece_id == request.piece_id:
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
            from_not = f"[{actor.position.y} ; {actor.position.x}]"
            to_not = f"[{request.to_pos.y} ; {request.to_pos.x}]"
            from commander_game_engine.game_state import Player as PkgPlayer
            score_delta = {
                Side.RED: res.state.scores.get(PkgPlayer.RED, 0) - state.scores.get("RED", 0),
                Side.BLUE: res.state.scores.get(PkgPlayer.BLUE, 0) - state.scores.get("BLUE", 0),
            }

            if request.target_piece_id:
                act_sym = "_@_" if request.action_type == ActionType.CAPTURE_STAND else "@"
                target = next((p for p in state.pieces if p.piece_id == request.target_piece_id), None)
                target_sym = PIECE_NOTATION_SYMBOL.get(target.type, "B") if target else "B"
                notation = f"{actor_sym} {from_not} {act_sym} {target_sym} {to_not}"
                evt_type = EventType.PIECE_CAPTURED
            else:
                notation = f"{actor_sym} {from_not} _ {to_not}"
                evt_type = EventType.PIECE_MOVED

            if actor_checked_commander:
                if ">" not in notation:
                    if actor_was_promoted:
                        notation = f"{notation} > **{actor_sym}**"
                    else:
                        notation = f"{notation} >"
                if evt_type == EventType.PIECE_MOVED:
                    evt_type = EventType.HERO_PROMOTION

            event = GameEvent(
                event_id=f"evt_{int(time.time() * 1000)}",
                event_type=evt_type,
                actor_id=actor.piece_id,
                target_id=request.target_piece_id,
                notation=notation,
                score_delta=score_delta,
                details={
                    "action_type": request.action_type.value,
                    "is_check": actor_checked_commander,
                    "hero_promoted": actor_was_promoted,
                    "from_pos": {"x": actor.position.x, "y": actor.position.y},
                    "to_pos": {"x": request.to_pos.x, "y": request.to_pos.y},
                },
            )

            result = None
            if res.terminal:
                result = GameResultDTO(
                    winner=res.winner.value.upper() if res.winner else "DRAW",
                    reason=TerminationReason.COMMANDER_CAPTURED,
                    final_scores={
                        "RED": res.state.scores.get(PkgPlayer.RED, 0),
                        "BLUE": res.state.scores.get(PkgPlayer.BLUE, 0),
                    },
                )
            else:
                # Checkmate check (DEC-019)
                candidate_next_side = Side.BLUE if res.state.current_player.value == "blue" else Side.RED
                is_enemy_in_check = is_commander_in_check(new_pieces, candidate_next_side)
                if is_enemy_in_check:
                    temp_next_state = GameState(
                        game_id=state.game_id,
                        mode=state.mode,
                        status=GameStatus.IN_PROGRESS,
                        side_to_move=candidate_next_side,
                        turn_index=res.state.turn_number,
                        action_index=1,
                        turn_phase=TurnPhase.NORMAL,
                        state_version=state.state_version + 1,
                        scores={
                            "RED": res.state.scores.get(PkgPlayer.RED, 0),
                            "BLUE": res.state.scores.get(PkgPlayer.BLUE, 0),
                        },
                        remaining_time_ms=state.remaining_time_ms,
                        pieces=new_pieces,
                        legal_actions=[],
                        can_end_turn=False,
                        last_event=None,
                        result=None,
                    )
                    enemy_moves = self.get_legal_actions(temp_next_state)
                    if len(enemy_moves) == 0:
                        score_delta[actor.side] += 50
                        notation = f"{notation} #"
                        event.notation = notation
                        if event.details:
                            event.details["is_checkmate"] = True
                            event.details["is_check"] = True
                        result = GameResultDTO(
                            winner=actor.side.value,
                            reason=TerminationReason.CHECKMATE,
                            final_scores={
                                "RED": res.state.scores.get(PkgPlayer.RED, 0) + (50 if actor.side == Side.RED else 0),
                                "BLUE": res.state.scores.get(PkgPlayer.BLUE, 0) + (50 if actor.side == Side.BLUE else 0),
                            },
                        )

            next_side = Side.BLUE if res.state.current_player.value == "blue" else Side.RED
            is_game_over = res.terminal or (result is not None and result.reason == TerminationReason.CHECKMATE)
            new_status = GameStatus.GAME_OVER if is_game_over else GameStatus.IN_PROGRESS

            next_state = GameState(
                game_id=state.game_id,
                mode=state.mode,
                status=new_status,
                side_to_move=next_side,
                turn_index=res.state.turn_number,
                action_index=1,
                turn_phase=TurnPhase.NORMAL,
                state_version=state.state_version + 1,
                scores={
                    "RED": res.state.scores.get(PkgPlayer.RED, 0) + (50 if result is not None and result.reason == TerminationReason.CHECKMATE and actor.side == Side.RED else 0),
                    "BLUE": res.state.scores.get(PkgPlayer.BLUE, 0) + (50 if result is not None and result.reason == TerminationReason.CHECKMATE and actor.side == Side.BLUE else 0),
                },
                remaining_time_ms=state.remaining_time_ms,
                pieces=new_pieces,
                legal_actions=[],
                can_end_turn=False,
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
