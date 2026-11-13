# packages/agents/evaluation/deployment.py
"""F6 — Deployment: triển khai đội hình và hành quân nhanh D(s, p).

D(s, p) = sum_{u in U_p(s)} Progress(u, s) - sum_{v in U_opp(p)(s)} Progress(v, s)

Tôn trọng CCHEF §8:
- `Progress` phản ánh mức tiếp cận vị trí chiến thuật ĐÚNG VAI TRÒ từng quân, khả năng
  bảo vệ/hỗ trợ và hiệu quả vận tải; KHÔNG đồng nhất với khoảng cách đi xa khỏi nhà.
- Phòng không bảo vệ tuyến nhà/trung tâm vẫn nhận Progress tốt.
- Công binh giữ bờ sông `y in {5, 6}` để nối cầu/chở vũ khí nặng được đánh giá cao.
"""

from __future__ import annotations

from commander_game_engine import rules
from commander_game_engine.game_state import Piece, PieceType, Player

from .context import EvalContext, opponent_of

_HEAVY_WEAPONS = frozenset({PieceType.ARTILLERY, PieceType.ANTI_AIRCRAFT, PieceType.MISSILE})


def _side_deployment(ctx: EvalContext, side: Player) -> float:
    opp = opponent_of(side)
    rows = ctx.state.board.ROWS
    opp_aa_danger = ctx.aa_danger_by[opp]
    opp_defended = ctx.defended_by[opp]
    pieces = ctx.pieces_by_player[side]

    # Pre-index tọa độ Công binh & vũ khí nặng phe mình để chấm phối hợp vượt sông
    engineer_positions = [
        ctx.origins[p.id]
        for p in pieces
        if p.piece_type == PieceType.ENGINEER and p.id in ctx.origins
    ]
    heavy_positions = [
        ctx.origins[p.id]
        for p in pieces
        if p.piece_type in _HEAVY_WEAPONS and p.id in ctx.origins
    ]
    cmd_pos = ctx.cmd_origin[side]
    own_river_row = 5 if side == Player.RED else 6

    # Điểm nhận thức pha mở cuộc (tổng vật chất hai bên) để không phạt Tư lệnh trễ tàn cuộc
    non_cmd_count = sum(
        1 for p in ctx.state.pieces.values() if p.piece_type not in (PieceType.COMMANDER, PieceType.HEADQUARTERS)
    )

    progress_sum = 0.0
    for p in pieces:
        pos = ctx.origins.get(p.id)
        if pos is None:
            continue
        y, x = pos
        adv_y = y if side == Player.RED else (rows - 1 - y)
        ptype = p.piece_type
        prog = 0.0

        if ptype == PieceType.TANK:
            # Xe tăng cần vượt trung tuyến / chiếm ngầm đá / chở Bộ binh-Dân quân tiến lên
            if adv_y >= 6:
                prog += 5.5
            elif adv_y == 5:
                prog += 4.2 if x in (5, 7) else 3.2
            elif adv_y == 4:
                prog += 2.2
            elif adv_y == 3:
                prog += 1.0
            # Vận chuyển tích cực quân bộ ra tuyến trên (không tính ở sân nhà adv_y <= 2)
            if p.cargo and adv_y >= 3:
                prog += 1.4

        elif ptype in (PieceType.INFANTRY, PieceType.MILITIA):
            # Bộ binh / Dân quân: phát triển qua sông, hoặc đang cơ động trên phương tiện tiến lên
            if adv_y >= 6:
                prog += 3.8
            elif adv_y >= 4:
                prog += 1.8
            elif adv_y >= 3:
                prog += 0.8
            if p.carried_by is not None:
                carrier = ctx.state.pieces.get(p.carried_by)
                if carrier is not None and carrier.piece_type in (PieceType.TANK, PieceType.AIRCRAFT, PieceType.NAVY):
                    prog += 1.6 if adv_y >= 3 else 0.9

        elif ptype == PieceType.ENGINEER:
            # Công binh: tốt nhất khi đứng trực chiến tại bờ sông y in (5, 6) gần hỏa lực nặng
            if y == own_river_row:
                prog += 4.5
                near_heavy = sum(1 for hy, hx in heavy_positions if abs(hy - y) <= 2 and abs(hx - x) <= 2)
                prog += 1.0 * min(near_heavy, 2)
            elif y in (5, 6):
                prog += 3.8
            elif 3 <= adv_y <= 4:
                prog += 1.8
            if p.cargo:
                prog += 2.2  # Đang trực tiếp chở Pháo/Tên lửa/AA vượt sông

        elif ptype == PieceType.ARTILLERY:
            # Pháo binh phát huy tốt ở tuyến 3..7; tăng giá trị nếu có Công binh áp sát bờ sông
            if 4 <= adv_y <= 7:
                prog += 4.0
            elif adv_y == 3 or adv_y >= 8:
                prog += 2.2
            else:
                prog -= 0.8  # Đóng chết ở hàng đáy adv_y <= 2
            if adv_y >= 4 and engineer_positions:
                if any(ey in (5, 6) and abs(ey - y) <= 2 and abs(ex - x) <= 2 for ey, ex in engineer_positions):
                    prog += 1.2

        elif ptype == PieceType.MISSILE:
            if 3 <= adv_y <= 6:
                prog += 3.5
            elif adv_y >= 7:
                prog += 2.6
            # Thưởng nhẹ nếu bảo vệ Tư lệnh / chủ lực quanh trung lộ
            if cmd_pos is not None and abs(y - cmd_pos[0]) <= 3 and abs(x - cmd_pos[1]) <= 3:
                prog += 1.0

        elif ptype == PieceType.ANTI_AIRCRAFT:
            # CCHEF §8: Phòng không đứng bảo vệ tuyến nhà & chủ lực vẫn được đánh giá TỐT
            if 2 <= adv_y <= 6:
                prog += 2.4
            elif adv_y == 7:
                prog += 1.6
            if cmd_pos is not None and max(abs(y - cmd_pos[0]), abs(x - cmd_pos[1])) <= 2:
                prog += 1.4
            covered_allies = sum(
                1
                for hy, hx in heavy_positions
                if (hy, hx) != pos and max(abs(y - hy), abs(x - hx)) <= 1
            )
            prog += 0.9 * min(covered_allies, 2)

        elif ptype == PieceType.AIRCRAFT:
            if not p.is_heroic and (pos in opp_defended or pos in opp_aa_danger):
                prog -= 6.0  # Đậu bừa trong vùng AA địch là triển khai sai
            elif p.carried_by is not None:
                carrier = ctx.state.pieces.get(p.carried_by)
                if carrier is not None and carrier.piece_type == PieceType.NAVY:
                    prog += 2.8 if adv_y >= 3 else 1.5
            else:
                if 4 <= adv_y <= 8:
                    prog += 4.2
                elif adv_y == 3 or adv_y >= 9:
                    prog += 2.5

        elif ptype == PieceType.NAVY:
            if y in (5, 6) and not rules.is_ford_square(pos):
                prog += 5.0  # Hải quân tiến vào cửa sông kiểm soát trung tuyến
            elif x == 2 and 3 <= adv_y <= 8:
                prog += 4.2
            elif x == 1 and 2 <= adv_y <= 8:
                prog += 2.8
            elif adv_y <= 1 and x == 0:
                prog -= 1.0  # Nằm kẹt góc đáy
            if p.cargo and (x in (1, 2) or y in (5, 6)) and adv_y >= 2:
                prog += 2.0  # Chở quân đổ bộ bờ biển / cửa sông

        elif ptype == PieceType.COMMANDER:
            if ctx.cmd_sheltered_hq[side] is not None:
                prog += 2.0
            elif adv_y <= 2:
                prog += 1.2
            elif adv_y >= 4 and non_cmd_count > 10:
                prog -= 2.2 * (adv_y - 3)  # Hạn chế Tư lệnh xông lên sớm khi quân còn đông

        elif ptype == PieceType.HEADQUARTERS and p.is_heroic:
            if adv_y >= 3:
                prog += 2.5

        progress_sum += prog

    return progress_sum


def evaluate_deployment(ctx: EvalContext, perspective: Player) -> float:
    """F6 — Deployment đối xứng D(s, p) = sum_p Progress(u, s) - sum_opp Progress(v, s)."""
    opp = opponent_of(perspective)
    return _side_deployment(ctx, perspective) - _side_deployment(ctx, opp)


__all__ = ["evaluate_deployment"]

