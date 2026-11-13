# packages/agents/evaluation/position.py
"""F4 — Position / Terrain Control:

P(s, p) = sum_{(y, x)} W(y, x) * [Control(s, p, y, x) - Control(s, opp(p), y, x)] + terrain_placement

Tôn trọng đặc thù Cờ Tư Lệnh:
- Không mặc nhiên gán trung tâm điểm cao như Cờ vua; trọng số `W(y, x)` bám sát
  bến ngầm `(5/6, 5)`, `(5/6, 7)`, bờ sông, bờ biển `x=2`, vùng biển & hành lang hỏa lực.
- Hải quân bắn tới đất nhưng chỉ được đứng trên vùng nước hợp lệ.
- Máy bay chịu trừ rủi ro khi đứng/hoạt động trong vành đai lửa Phòng không (trừ Anh hùng).
- Phòng không bảo vệ vùng trọng yếu và chống đường bay.
"""

from __future__ import annotations

from commander_game_engine.game_state import PieceType, Player

from .context import _AA_OFFSETS_CACHE, EvalContext, opponent_of

# Bảng trọng số chiến lược giao điểm `W[y][x]` (12x11), ĐỐI XỨNG TUYỆT ĐỐI theo `y <-> 11 - y`.
def _build_terrain_weight_grid() -> list[list[float]]:
    grid = [[0.65 for _ in range(11)] for _ in range(12)]
    for y in range(12):
        for x in range(11):
            w = 0.70
            # Vùng biển sâu (x=0..1): hành lang Hải quân
            if x == 0:
                w = 0.65
            elif x == 1:
                w = 1.05
            # Bờ biển (x=2): giao tranh đổ bộ & Hải quân
            elif x == 2:
                w = 1.30
            # Dải sông (y=5..6): điểm nóng vượt sông
            if y in (5, 6) and x >= 2:
                w = 1.45
                if x in (5, 7):  # Hai đường ngầm đá chiến lược
                    w = 1.85
            # Cận sông & hành lang trung tuyến (y=4,7; x=3..9)
            elif y in (4, 7) and 3 <= x <= 9:
                w = 1.25 if x in (5, 6, 7) else 1.10
            # Tuyến hỏa lực trung lộ (y=3,8; x=3..8)
            elif y in (3, 8) and 3 <= x <= 8:
                w = 1.00
            # Khu vực SCH / Tư lệnh hậu phương (y=0..2, 9..11; x=4..8)
            elif (y <= 2 or y >= 9) and 4 <= x <= 8:
                w = 1.05
            grid[y][x] = w
    return grid


TERRAIN_WEIGHT_GRID: list[list[float]] = _build_terrain_weight_grid()
_TERRAIN_WEIGHT_FLAT: tuple[float, ...] = tuple(
    TERRAIN_WEIGHT_GRID[y][x] for y in range(12) for x in range(11)
)

_NAVY_SEA_CONTROL_DIRS: tuple[tuple[int, int], ...] = (
    (-1, 0), (1, 0), (0, -1), (0, 1),
    (-1, -1), (-1, 1), (1, -1), (1, 1),
)


def _side_position_and_control(ctx: EvalContext, side: Player) -> float:
    """Tính tổng điểm kiểm soát địa hình + đóng quân hợp lệ cho `side`."""
    opp = opponent_of(side)
    is_red = side == Player.RED
    opp_aa_grid = ctx.aa_danger_grid[opp]
    opp_defended = ctx.defended_by[opp]
    occ_grid = ctx.occ_grid

    # Tích lũy kiểm soát trên 132 ô (mảng phẳng 1D giữ nguyên thứ tự cộng từng hàng)
    ctrl = [0.0] * 132
    placement = 0.0

    for p in ctx.pieces_by_player[side]:
        pos = ctx.origins.get(p.id)
        if pos is None:
            continue
        y, x = pos
        adv_y = y if is_red else (11 - y)
        ptype = p.piece_type
        hero = p.is_heroic

        # 1. Điểm vị trí đứng đặc thù từng loại quân theo địa hình thực tế
        if ptype == PieceType.NAVY:
            if x == 2:
                placement += 3.2
            elif x == 1:
                placement += 2.2
            if y in (5, 6):
                placement += 3.5
            elif 3 <= adv_y <= 8:
                placement += 1.6
            reach = 4 if hero else 3
            for ddy, ddx in _NAVY_SEA_CONTROL_DIRS:
                for step in range(1, reach + 1):
                    ny, nx = y + ddy * step, x + ddx * step
                    if 0 <= ny < 12 and 0 <= nx < 11:
                        ctrl[ny * 11 + nx] += 0.45

        elif ptype == PieceType.AIRCRAFT:
            if p.carried_by is not None:
                placement += 2.0
            elif not hero and pos in opp_defended:
                placement -= 18.0
            elif not hero and opp_aa_grid[y * 11 + x]:
                placement -= 10.0
            else:
                if adv_y >= 4:
                    placement += 2.8
            reach = 5 if hero else 4
            for ddy, ddx in _NAVY_SEA_CONTROL_DIRS:
                for step in range(1, reach + 1):
                    ny, nx = y + ddy * step, x + ddx * step
                    if not (0 <= ny < 12 and 0 <= nx < 11):
                        break
                    n_idx = ny * 11 + nx
                    if not hero and opp_aa_grid[n_idx]:
                        ctrl[n_idx] += 0.08
                    else:
                        ctrl[n_idx] += 0.42

        elif ptype in (PieceType.ANTI_AIRCRAFT, PieceType.MISSILE):
            if p.carried_by is None:
                aa_zone = _AA_OFFSETS_CACHE[(ptype, hero)]
                protected_allies = 0
                covered_fords = 0
                for oy, ox in aa_zone:
                    ny, nx = y + oy, x + ox
                    if 0 <= ny < 12 and 0 <= nx < 11:
                        n_idx = ny * 11 + nx
                        ctrl[n_idx] += 0.35
                        occ = occ_grid[n_idx]
                        if occ is not None and occ.owner == side and occ.piece_type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS):
                            protected_allies += 1
                        if (ny == 5 or ny == 6) and (nx == 5 or nx == 7):
                            covered_fords += 1
                placement += 1.2 * min(protected_allies, 4) + 1.5 * min(covered_fords, 2)
            if 3 <= adv_y <= 7:
                placement += 1.8

        elif ptype == PieceType.ARTILLERY:
            if 3 <= adv_y <= 7:
                placement += 2.5
            elif adv_y >= 8:
                placement += 1.5
            reach = 4 if hero else 3
            for ddy, ddx in _NAVY_SEA_CONTROL_DIRS:
                for step in range(1, reach + 1):
                    ny, nx = y + ddy * step, x + ddx * step
                    if 0 <= ny < 12 and 0 <= nx < 11:
                        ctrl[ny * 11 + nx] += 0.38

        elif ptype == PieceType.TANK:
            if y in (5, 6) and x in (5, 7):
                placement += 3.5
            elif adv_y >= 6:
                placement += 3.0
            elif adv_y >= 4:
                placement += 1.5
            reach = 3 if hero else 2
            dirs = _NAVY_SEA_CONTROL_DIRS if hero else _NAVY_SEA_CONTROL_DIRS[:4]
            for ddy, ddx in dirs:
                for step in range(1, reach + 1):
                    ny, nx = y + ddy * step, x + ddx * step
                    if not (0 <= ny < 12 and 0 <= nx < 11):
                        break
                    n_idx = ny * 11 + nx
                    ctrl[n_idx] += 0.40
                    if occ_grid[n_idx] is not None:
                        break

        elif ptype == PieceType.ENGINEER:
            if (is_red and y == 5) or (not is_red and y == 6):
                placement += 3.2
            elif adv_y >= 4:
                placement += 1.2
            for ddy, ddx in (_NAVY_SEA_CONTROL_DIRS if hero else _NAVY_SEA_CONTROL_DIRS[:4]):
                ny, nx = y + ddy, x + ddx
                if 0 <= ny < 12 and 0 <= nx < 11:
                    ctrl[ny * 11 + nx] += 0.30

        elif ptype in (PieceType.INFANTRY, PieceType.MILITIA):
            if adv_y >= 6:
                placement += 2.4
            elif adv_y >= 4:
                placement += 1.1
            dirs = _NAVY_SEA_CONTROL_DIRS if (hero or ptype == PieceType.MILITIA) else _NAVY_SEA_CONTROL_DIRS[:4]
            reach = 2 if hero else 1
            for ddy, ddx in dirs:
                for step in range(1, reach + 1):
                    ny, nx = y + ddy * step, x + ddx * step
                    if not (0 <= ny < 12 and 0 <= nx < 11):
                        break
                    n_idx = ny * 11 + nx
                    ctrl[n_idx] += 0.32
                    if occ_grid[n_idx] is not None:
                        break

        elif ptype == PieceType.HEADQUARTERS and hero:
            if adv_y >= 4:
                placement += 1.5
            for ddy, ddx in _NAVY_SEA_CONTROL_DIRS:
                for step in (1, 2):
                    ny, nx = y + ddy * step, x + ddx * step
                    if not (0 <= ny < 12 and 0 <= nx < 11):
                        break
                    n_idx = ny * 11 + nx
                    ctrl[n_idx] += 0.30
                    if occ_grid[n_idx] is not None:
                        break

        if p.carried_by is None and ptype not in (PieceType.COMMANDER, PieceType.HEADQUARTERS):
            ctrl[y * 11 + x] += 0.80

    # Cộng trọng số chiến lược bàn cờ W(y, x) * Control(s, side, y, x)
    weighted_control = 0.0
    w_flat = _TERRAIN_WEIGHT_FLAT
    for idx in range(132):
        c_val = ctrl[idx]
        if c_val > 0.0:
            weighted_control += w_flat[idx] * (c_val if c_val < 2.2 else 2.2)

    return placement + weighted_control


def evaluate_position(ctx: EvalContext, perspective: Player) -> float:
    """F4 — Position & Terrain Control đối xứng P(s, p)."""
    opp = opponent_of(perspective)
    return _side_position_and_control(ctx, perspective) - _side_position_and_control(ctx, opp)


__all__ = ["TERRAIN_WEIGHT_GRID", "evaluate_position"]
