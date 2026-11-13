# packages/agents/evaluation/mobility.py
"""F5 — Mobility: hành động hữu ích và an toàn C(s, p).

C(s, p) = sum_{u in U_p(s)} m(u, s) - sum_{v in U_opp(p)(s)} m(v, s)
m(u, s) = sum_{a in A_u(s)} SafeMove(a) * UsefulMove(a)

Đánh giá nhất quán CẢ HAI PHE trên cùng trạng thái `s` bằng mô phỏng tia hình học
khớp `commander_game_engine.rules`, tối ưu mảng phẳng 132 ô để đạt `< 0.15 ms`.
"""

from __future__ import annotations

from commander_game_engine import rules
from commander_game_engine.game_state import Piece, PieceType, Player

from .context import EvalContext, can_navy_occupy_xy, is_navy_land_diagonal_xy, opponent_of
from .material_table import piece_value

_ORTH_DIRS: tuple[tuple[int, int], ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))
_ALL_DIRS: tuple[tuple[int, int], ...] = (
    (-1, 0), (1, 0), (0, -1), (0, 1),
    (-1, -1), (-1, 1), (1, -1), (1, 1),
)
_DEEP_CROSSERS = frozenset({
    PieceType.COMMANDER,
    PieceType.INFANTRY,
    PieceType.MILITIA,
    PieceType.TANK,
    PieceType.ENGINEER,
    PieceType.HEADQUARTERS,
})
_PIERCING_CAPTURE = frozenset({PieceType.ARTILLERY, PieceType.MISSILE, PieceType.AIRCRAFT})
_CARRIER_TYPES = rules._CARRIER_TYPES


def _build_side_square_control(ctx: EvalContext, side: Player) -> tuple[list[float], list[bool]]:
    """Tạo mảng 132 ô bị phe `side` kiểm soát tấn công (min attacker value) và cờ ô giữ."""
    min_att_val = [0.0] * 132
    guarded = [False] * 132
    occ_grid = ctx.occ_grid

    for att in ctx.pieces_by_player[side]:
        ptype = att.piece_type
        if ptype == PieceType.HEADQUARTERS and not att.is_heroic:
            continue
        start = ctx.origins.get(att.id)
        if start is None:
            continue
        aval = piece_value(att)
        sy, sx = start
        hero = att.is_heroic

        if ptype == PieceType.MISSILE:
            orth_r = 3 if hero else 2
            diag_r = 2 if hero else 1
            for dy, dx in _ALL_DIRS:
                max_s = orth_r if (dy == 0 or dx == 0) else diag_r
                for step in range(1, max_s + 1):
                    ny = sy + dy * step
                    nx = sx + dx * step
                    if not (0 <= ny < 12 and 0 <= nx < 11):
                        break
                    idx = ny * 11 + nx
                    if not guarded[idx]:
                        guarded[idx] = True
                        min_att_val[idx] = aval
                    elif aval < min_att_val[idx]:
                        min_att_val[idx] = aval
            continue

        if ptype == PieceType.ARTILLERY:
            reach = 4 if hero else 3
            for dy, dx in _ALL_DIRS:
                for step in range(1, reach + 1):
                    ny = sy + dy * step
                    nx = sx + dx * step
                    if not (0 <= ny < 12 and 0 <= nx < 11):
                        break
                    idx = ny * 11 + nx
                    if not guarded[idx]:
                        guarded[idx] = True
                        min_att_val[idx] = aval
                    elif aval < min_att_val[idx]:
                        min_att_val[idx] = aval
            continue

        if ptype == PieceType.AIRCRAFT:
            reach = 5 if hero else 4
            for dy, dx in _ALL_DIRS:
                for step in range(1, reach + 1):
                    ny = sy + dy * step
                    nx = sx + dx * step
                    if not (0 <= ny < 12 and 0 <= nx < 11):
                        break
                    idx = ny * 11 + nx
                    if not guarded[idx]:
                        guarded[idx] = True
                        min_att_val[idx] = aval
                    elif aval < min_att_val[idx]:
                        min_att_val[idx] = aval
            continue

        if ptype == PieceType.NAVY:
            if not can_navy_occupy_xy(sy, sx):
                continue
            reach = 4 if hero else 3
            for dy, dx in _ALL_DIRS:
                for step in range(1, reach + 1):
                    ny = sy + dy * step
                    nx = sx + dx * step
                    if not (0 <= ny < 12 and 0 <= nx < 11):
                        break
                    idx = ny * 11 + nx
                    if not guarded[idx]:
                        guarded[idx] = True
                        min_att_val[idx] = aval
                    elif aval < min_att_val[idx]:
                        min_att_val[idx] = aval
            continue

        if ptype == PieceType.COMMANDER or ptype in (PieceType.INFANTRY, PieceType.ENGINEER, PieceType.ANTI_AIRCRAFT):
            dirs = _ALL_DIRS if hero else _ORTH_DIRS
            reach = 2 if hero else 1
        elif ptype == PieceType.MILITIA:
            dirs = _ALL_DIRS
            reach = 2 if hero else 1
        elif ptype == PieceType.TANK:
            dirs = _ALL_DIRS if hero else _ORTH_DIRS
            reach = 3 if hero else 2
        else:  # Heroic HEADQUARTERS
            dirs = _ALL_DIRS
            reach = 2

        for dy, dx in dirs:
            for step in range(1, reach + 1):
                ny = sy + dy * step
                nx = sx + dx * step
                if not (0 <= ny < 12 and 0 <= nx < 11):
                    break
                idx = ny * 11 + nx
                if not guarded[idx]:
                    guarded[idx] = True
                    min_att_val[idx] = aval
                elif aval < min_att_val[idx]:
                    min_att_val[idx] = aval
                if occ_grid[idx] is not None:
                    break

    return min_att_val, guarded


def _river_cross_ok_xy(
    ptype: PieceType,
    ay: int,
    ax: int,
    by: int,
    bx: int,
) -> bool:
    if not ((ay == 5 and by == 6) or (ay == 6 and by == 5)) or (ax if ax < bx else bx) < 2:
        return True
    if ptype in _DEEP_CROSSERS:
        return True
    if ax != bx:
        return False
    return ax == 5 or ax == 7


def _piece_mobility_score(
    ctx: EvalContext,
    piece: Piece,
    opp_min_att: list[float],
    opp_guarded: list[bool],
    own_guards: list[bool],
    opp_aa_grid: list[bool],
) -> float:
    """Tính `m(u, s) = sum SafeMove(a) * UsefulMove(a)` cho một quân `piece`."""
    ptype = piece.piece_type
    hero = piece.is_heroic
    if ptype == PieceType.HEADQUARTERS and not hero:
        return 0.0
    start = ctx.origins.get(piece.id)
    if start is None:
        return 0.0

    side = piece.owner
    opp = opponent_of(side)
    sy, sx = start
    start_idx = sy * 11 + sx
    occ_grid = ctx.occ_grid
    pval = ctx.stack_value(piece.id) if piece.carried_by is None else piece_value(piece)

    if ptype == PieceType.COMMANDER:
        dirs = _ALL_DIRS if hero else _ORTH_DIRS
        max_reach = 2 if hero else 5
        base_scale = 0.28
    elif ptype == PieceType.HEADQUARTERS:
        dirs = _ALL_DIRS
        max_reach = 2
        base_scale = 0.85
    elif ptype in (PieceType.INFANTRY, PieceType.ENGINEER, PieceType.ANTI_AIRCRAFT):
        dirs = _ALL_DIRS if hero else _ORTH_DIRS
        max_reach = 2 if hero else 1
        base_scale = 1.00
    elif ptype == PieceType.MILITIA:
        dirs = _ALL_DIRS
        max_reach = 2 if hero else 1
        base_scale = 1.00
    elif ptype == PieceType.TANK:
        dirs = _ALL_DIRS if hero else _ORTH_DIRS
        max_reach = 3 if hero else 2
        base_scale = 1.00
    elif ptype == PieceType.MISSILE:
        dirs = _ALL_DIRS
        max_reach = 3 if hero else 2
        base_scale = 0.90
    elif ptype == PieceType.ARTILLERY:
        dirs = _ALL_DIRS
        max_reach = 4 if hero else 3
        base_scale = 0.90
    elif ptype == PieceType.AIRCRAFT:
        dirs = _ALL_DIRS
        max_reach = 5 if hero else 4
        base_scale = 0.85
    else:  # NAVY
        if not can_navy_occupy_xy(sy, sx):
            return 0.0
        dirs = _ALL_DIRS
        max_reach = 5 if hero else 4
        base_scale = 0.85

    is_red = side == Player.RED
    adv_before = sy if is_red else (11 - sy)
    navy_land_limit = 4 if hero else 3
    total_m = 0.0

    for dy, dx in dirs:
        diag = dy != 0 and dx != 0
        aa_cut = False
        py, px = sy, sx
        p_idx = start_idx
        navy_phase1_ok = True

        for step in range(1, max_reach + 1):
            if ptype == PieceType.MISSILE and diag and not hero and step > 1:
                break
            ny = sy + dy * step
            nx = sx + dx * step
            if not (0 <= ny < 12 and 0 <= nx < 11):
                break
            d_idx = ny * 11 + nx
            occ = occ_grid[d_idx]

            if ptype == PieceType.NAVY:
                if (
                    is_navy_land_diagonal_xy(py, px, ny, nx)
                    or ((ny == 5 or ny == 6) and (nx == 5 or nx == 7))
                    or not (nx <= 2 or ny == 5 or ny == 6)
                ):
                    navy_phase1_ok = False
                if occ is not None and occ.owner == side:
                    if occ.piece_type == PieceType.NAVY:
                        navy_phase1_ok = False
                elif occ is not None and occ.owner == opp:
                    cap_ok = (occ.piece_type == PieceType.NAVY and navy_phase1_ok) or (
                        occ.piece_type != PieceType.NAVY and step <= navy_land_limit
                    )
                    if cap_ok:
                        safe = 1.0 if not opp_guarded[d_idx] else (0.6 if own_guards[d_idx] else 0.25)
                        total_m += base_scale * safe * 1.35
                    break
                if not navy_phase1_ok:
                    break
                useful = 1.05 if (nx in (1, 2) or ny in (5, 6)) else 0.65
                safe = 1.0 if not opp_guarded[d_idx] else (0.55 if own_guards[d_idx] else 0.20)
                total_m += base_scale * safe * useful
                py, px = ny, nx
                p_idx = d_idx
                continue

            if ptype == PieceType.AIRCRAFT:
                if not hero and opp_aa_grid[d_idx]:
                    aa_cut = True
                if occ is not None:
                    if occ.owner == opp:
                        if aa_cut and not hero:
                            tval = ctx.stack_value(occ.id)
                            if tval >= pval:
                                total_m += base_scale * 0.35 * 1.25
                        else:
                            safe = 1.0 if not opp_guarded[d_idx] else (0.6 if own_guards[d_idx] else 0.30)
                            total_m += base_scale * safe * 1.35
                    elif occ.owner == side and piece.carried_by is None:
                        if occ.piece_type == PieceType.NAVY and not aa_cut:
                            total_m += base_scale * 0.55
                else:
                    if not aa_cut and nx >= 2:
                        adv_after = ny if is_red else (11 - ny)
                        useful = 1.05 if adv_after >= adv_before else 0.70
                        safe = 1.0 if not opp_guarded[d_idx] else (0.55 if own_guards[d_idx] else 0.22)
                        total_m += base_scale * safe * useful
                if aa_cut and not hero:
                    break
                py, px = ny, nx
                p_idx = d_idx
                continue

            # Quân trên bộ còn lại: Pháo & Tên lửa xuyên vật cản khi bắn mục tiêu (không đi xuyên!)
            if occ is not None:
                if occ.owner == opp:
                    tval = ctx.stack_value(occ.id)
                    if not opp_guarded[d_idx]:
                        safe = 1.0
                    else:
                        enemy_retake = opp_min_att[d_idx]
                        if own_guards[d_idx] and pval <= tval + enemy_retake:
                            safe = 0.75
                        elif pval <= tval:
                            safe = 0.55
                        else:
                            safe = 0.15
                    total_m += base_scale * safe * 1.40
                elif occ.owner == side and step <= 2 and occ.carried_by is None and (occ.piece_type != PieceType.ENGINEER or ny in (5, 6)):
                    if ptype in _CARRIER_TYPES.get(occ.piece_type, frozenset()):
                        total_m += base_scale * 0.45

                if ptype in _PIERCING_CAPTURE:
                    py, px = ny, nx
                    p_idx = d_idx
                    continue
                break

            # Ô trống
            if nx < 2:
                break
            if not _river_cross_ok_xy(ptype, py, px, ny, nx):
                break
            if p_idx != start_idx and occ_grid[p_idx] is not None:
                break

            adv_after = ny if is_red else (11 - ny)
            useful = 1.12 if (adv_after > adv_before or ((ny == 5 or ny == 6) and (nx == 5 or nx == 7))) else (0.92 if adv_after == adv_before else 0.65)
            if not opp_guarded[d_idx]:
                safe = 1.0
            elif own_guards[d_idx] and opp_min_att[d_idx] >= pval:
                safe = 0.55
            else:
                safe = 0.18 if pval >= 20.0 else 0.30
            total_m += base_scale * safe * useful
            py, px = ny, nx
            p_idx = d_idx

    if piece.carried_by is not None:
        total_m *= 0.65
    if ptype == PieceType.COMMANDER and not hero:
        if total_m > 2.5:
            total_m = 2.5
    return total_m


def evaluate_mobility(ctx: EvalContext, perspective: Player) -> float:
    """F5 — Mobility đối xứng C(s, p) = sum_p m(u, s) - sum_opp m(v, s)."""
    opp = opponent_of(perspective)
    persp_min_att, persp_guards = _build_side_square_control(ctx, perspective)
    opp_min_att, opp_guards = _build_side_square_control(ctx, opp)

    persp_aa = ctx.aa_danger_grid[perspective]
    opp_aa = ctx.aa_danger_grid[opp]

    mob_persp = 0.0
    for p in ctx.pieces_by_player[perspective]:
        mob_persp += _piece_mobility_score(ctx, p, opp_min_att, opp_guards, persp_guards, opp_aa)

    mob_opp = 0.0
    for p in ctx.pieces_by_player[opp]:
        mob_opp += _piece_mobility_score(ctx, p, persp_min_att, persp_guards, opp_guards, persp_aa)

    return mob_persp - mob_opp


__all__ = ["evaluate_mobility"]
