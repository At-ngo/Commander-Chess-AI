# packages/agents/evaluation/safe_check.py
"""F3 — Safe Check Potential (Q / SPC):

q(a) = (Benefit(a) * Safety(a) * Force(a)) / (1 + Distance(a))
Q(s, p) = max_{a in CheckPlan_p} q(a) - max_{b in CheckPlan_opp(p)} q(b)
"""

from __future__ import annotations

from commander_game_engine.board import Position
from commander_game_engine.game_state import Piece, PieceType, Player

from .context import (
    EvalContext,
    MAX_THREAT_RANGE,
    grid_path_blocked,
    grid_path_blocked_ignoring,
    movement_shape_ok,
    opponent_of,
    terrain_ok_grid,
)
from .material_table import HERO_BONUS, piece_value

_ALL_DIRS: tuple[tuple[int, int], ...] = (
    (-1, 0), (1, 0), (0, -1), (0, 1),
    (-1, -1), (-1, 1), (1, -1), (1, 1),
)
_PIERCING_CHECKERS = frozenset({PieceType.ARTILLERY, PieceType.MISSILE, PieceType.AIRCRAFT})


def _square_safety_for_attacker(
    ctx: EvalContext,
    attacker: Piece,
    pos: Position,
    defender: Player,
) -> float:
    """Hệ số `Safety ∈ [0, 1]`: quân chiếu tại `pos` có tránh bị ăn an toàn ngay không?"""
    if attacker.piece_type == PieceType.AIRCRAFT and not attacker.is_heroic:
        if ctx.aa_danger_grid[defender][pos[0] * 11 + pos[1]]:
            return 0.08  # Vào vùng Phòng không dễ mất Máy bay (1 đổi 1 hoặc rơi)

    counters = ctx.attackers_to_square(defender, pos)
    if not counters:
        return 1.0  # Không bị bất kỳ quân địch nào nhắm tới

    # Kiểm tra xem quân ta có đồng minh bọc lót tại `pos` không
    att_val = piece_value(attacker)
    own_guards = ctx.attackers_to_square(attacker.owner, pos)
    has_other_guard = any(g.id != attacker.id for g in own_guards)
    min_counter_val = min(piece_value(c) for c in counters)

    if not has_other_guard:
        return 0.10  # Không người bảo vệ, dễ bị ăn miễn phí
    if min_counter_val < att_val:
        return 0.25  # Quân yếu hơn của địch ăn đổi lời
    return 0.60      # Trao đổi cân bằng/có bảo vệ


def _force_against_commander(ctx: EvalContext, defender: Player, check_from: Position, checker: Piece) -> float:
    """Hệ số `Force ∈ [0, 1]`: mức độ ép đối phương xử lý tốn kém."""
    cpos = ctx.cmd_origin[defender]
    if cpos is None:
        return 0.0
    if ctx.cmd_sheltered_hq[defender] is not None:
        return 0.45  # Đang núp SCH thường -> ép đánh phá/rời chỗ nhưng không ép chạy ngay

    safe_escapes = 0
    att_side = checker.owner
    cy, cx = cpos
    occ_grid = ctx.occ_grid
    for dy, dx in _ALL_DIRS[:4]:
        ny, nx = cy + dy, cx + dx
        if not (0 <= ny < 12 and 0 <= nx < 11):
            continue
        occ = occ_grid[ny * 11 + nx]
        if occ is not None and occ.owner != defender:
            continue
        if not ctx.attackers_to_square(att_side, (ny, nx)):
            safe_escapes += 1

    # Nếu quân chiếu xuyên vật cản (Pháo/Tên lửa/Máy bay/Pháo hạm) thì khó chặn -> Force cao hơn
    piercing_bonus = 0.15 if (
        checker.piece_type in _PIERCING_CHECKERS
        or (checker.piece_type == PieceType.NAVY and cx >= 2)
    ) else 0.0

    base = 0.90 if safe_escapes == 0 else (0.72 if safe_escapes == 1 else (0.52 if safe_escapes == 2 else 0.35))
    return min(1.0, base + piercing_bonus)


def _side_max_safe_check_q(ctx: EvalContext, attacker_side: Player) -> float:
    """Tính `max_{a ∈ CheckPlan_side(s)} q(a)`."""
    opp = opponent_of(attacker_side)
    if not ctx.cmd_alive[opp]:
        return 0.0
    target_pos = ctx.cmd_origin[opp]
    if target_pos is None:
        return 0.0

    is_sheltered = ctx.cmd_sheltered_hq[opp] is not None
    ty, tx = target_pos
    occ_grid = ctx.occ_grid
    direct_ids = {p.id for p in ctx.attackers_to_square(attacker_side, target_pos)}
    best_q = 0.0

    for u in ctx.pieces_by_player[attacker_side]:
        ptype = u.piece_type
        hero = u.is_heroic
        if ptype == PieceType.COMMANDER or (ptype == PieceType.HEADQUARTERS and not hero):
            continue
        ustart = ctx.origins.get(u.id)
        if ustart is None:
            continue

        # 1. Distance = 0: quân `u` đang trực tiếp uy hiếp Tư lệnh (hoặc SCH che Tư lệnh) ngay lúc này
        if u.id in direct_ids:
            benefit = (18.0 if is_sheltered else 32.0) + (HERO_BONUS * 0.6 if not hero else 4.0)
            safety = _square_safety_for_attacker(ctx, u, ustart, opp)
            force = _force_against_commander(ctx, opp, ustart, u)
            q_val = (benefit * safety * force) / 1.0
            if q_val > best_q:
                best_q = q_val

        # 2. Distance = 1: chỉ 1 bước di chuyển hợp lệ tới vị trí chiếu an toàn (lọc tầm O(1))
        sy, sx = ustart
        max_r = MAX_THREAT_RANGE[ptype][1 if hero else 0]
        dy_t = ty - sy
        dx_t = tx - sx
        lim = max_r + 2
        if dy_t > lim or dy_t < -lim or dx_t > lim or dx_t < -lim:
            continue

        candidate_dests: list[Position] = []
        # Giao điểm nhanh trên hàng/cột với Tư lệnh đối phương
        if ty != sy and 0 <= ty < 12 and 0 <= sx < 11:
            candidate_dests.append((ty, sx))
        if tx != sx and 0 <= sy < 12 and 0 <= tx < 11:
            if (sy, tx) != (ty, sx):
                candidate_dests.append((sy, tx))
        # Và chiếu chéo gần nếu quân có khả năng đi/đánh chéo
        if hero or ptype in (PieceType.ARTILLERY, PieceType.AIRCRAFT, PieceType.NAVY, PieceType.MILITIA, PieceType.MISSILE):
            dy_sig = (ty > sy) - (ty < sy)
            dx_sig = (tx > sx) - (tx < sx)
            for step in (1, 2):
                ny, nx = sy + dy_sig * step, sx + dx_sig * step
                if 0 <= ny < 12 and 0 <= nx < 11 and (ny != sy or nx != sx) and (ny != ty or nx != tx):
                    cand = (ny, nx)
                    if cand not in candidate_dests:
                        candidate_dests.append(cand)

        for dest in candidate_dests[:3]:
            dy_pos, dx_pos = dest
            occ_dest = occ_grid[dy_pos * 11 + dx_pos]
            if occ_dest is not None and occ_dest.owner == attacker_side:
                continue
            capture_on_dest = occ_dest is not None and occ_dest.owner == opp
            if not movement_shape_ok(ptype, hero, sy, sx, dy_pos, dx_pos, capture_on_dest):
                continue
            if ptype != PieceType.AIRCRAFT and not (capture_on_dest and ptype in (PieceType.ARTILLERY, PieceType.MISSILE)):
                if ptype != PieceType.NAVY and grid_path_blocked(occ_grid, sy, sx, dy_pos, dx_pos):
                    continue
            if not terrain_ok_grid(occ_grid, u, sy, sx, dy_pos, dx_pos, capture_on_dest):
                continue

            # Sau khi đứng tại `dest`, `u` có chiếu được `target_pos` không?
            if not movement_shape_ok(ptype, hero, dy_pos, dx_pos, ty, tx, True):
                continue
            if ptype not in _PIERCING_CHECKERS and ptype != PieceType.NAVY:
                if grid_path_blocked_ignoring(occ_grid, dy_pos, dx_pos, ty, tx, sy, sx):
                    continue

            benefit = (16.0 if is_sheltered else 28.0) + (HERO_BONUS * 0.5 if not hero else 3.0)
            safety = _square_safety_for_attacker(ctx, u, dest, opp)
            force = _force_against_commander(ctx, opp, dest, u)
            q_val = (benefit * safety * force) / 2.0  # Distance = 1 => 1 + 1 = 2
            if q_val > best_q:
                best_q = q_val

    return best_q


def evaluate_safe_check(ctx: EvalContext, perspective: Player) -> float:
    """F3 — Safe Check Potential đối xứng Q(s, p) = max_p q(a) - max_opp q(b)."""
    opp = opponent_of(perspective)
    return _side_max_safe_check_q(ctx, perspective) - _side_max_safe_check_q(ctx, opp)


__all__ = ["evaluate_safe_check"]
