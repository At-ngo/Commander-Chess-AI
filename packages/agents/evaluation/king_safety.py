# packages/agents/evaluation/king_safety.py
"""F2 — King Safety K(s, p) = Risk(s, opp(p)) - Risk(s, p).

Phân biệt rõ:
- Chiếu an toàn có thể ăn quân chiếu hợp lệ/an toàn -> Cost_def ≈ 0 (`HE-05`).
- Chiếu nguy hiểm thực sự (ép thí quân, lộ tổ hợp, kẹt đường chạy, hoặc chiếu hết) -> Risk cao.
- Đe dọa chiếu tiềm ẩn 1 lượt và mức che chở Sở chỉ huy / quân bảo vệ.
"""

from __future__ import annotations

from copy import copy
from typing import Iterable

from commander_game_engine import rules
from commander_game_engine.actions import ActionType, AtomicAction
from commander_game_engine.board import Position
from commander_game_engine.engine import preview_action
from commander_game_engine.game_state import GameState, Piece, PieceType, Player
from commander_game_engine.move_generator import has_legal_action

from .context import (
    EvalContext,
    grid_path_blocked,
    grid_path_blocked_ignoring,
    movement_shape_ok,
    opponent_of,
)
from .material import side_material
from .material_table import piece_value

_ALL_DIRS: tuple[tuple[int, int], ...] = (
    (-1, 0), (1, 0), (0, -1), (0, 1),
    (-1, -1), (-1, 1), (1, -1), (1, 1),
)
_ORTH_DIRS: tuple[tuple[int, int], ...] = ((-1, 0), (1, 0), (0, -1), (0, 1))
_RANGED_PIERCING = frozenset({PieceType.ARTILLERY, PieceType.MISSILE, PieceType.AIRCRAFT})


def _lightweight_turn_copy(state: GameState, player_to_move: Player) -> GameState:
    """Tạo bản sao nông an toàn để giả lập nước đi của phe `player_to_move` không làm hỏng `state`."""
    temp = copy(state)
    temp.current_player = player_to_move
    temp.compound_turn = None
    return temp


def _generate_targeted_defense_candidates(
    ctx: EvalContext,
    temp_state: GameState,
    defender: Player,
    checkers: list[Piece],
    cmd: Piece,
) -> list[AtomicAction]:
    """Sinh nhanh các ứng viên giải chiếu trọng tâm (ăn quân chiếu, né Tư lệnh, vào SCH, chắn đường)."""
    candidates: list[AtomicAction] = []
    seen_actions: set[AtomicAction] = set()
    opp = opponent_of(defender)
    rows, cols = ctx.state.board.ROWS, ctx.state.board.COLS
    cmd_pos = ctx.cmd_origin[defender]

    def _add_if_structurally_valid(act: AtomicAction) -> None:
        if act in seen_actions:
            return
        if rules.validate_structural_action(temp_state, act).valid:
            seen_actions.add(act)
            candidates.append(act)

    # 1. Ăn quân đang chiếu (nếu chỉ có 1 quân đang chiếu)
    if len(checkers) == 1:
        chk = checkers[0]
        chk_pos = ctx.origins.get(chk.id)
        if chk_pos is not None:
            for att in ctx.attackers_to_square(defender, chk_pos):
                att_start = ctx.origins.get(att.id)
                if att_start is None:
                    continue
                for atype in (
                    ActionType.CAPTURE,
                    ActionType.BOMB if att.piece_type == PieceType.AIRCRAFT else ActionType.BOMBARD,
                ):
                    if atype == ActionType.BOMB and att.piece_type != PieceType.AIRCRAFT:
                        continue
                    if atype == ActionType.BOMBARD and att.piece_type == PieceType.AIRCRAFT:
                        continue
                    _add_if_structurally_valid(
                        AtomicAction(
                            action_type=atype,
                            piece_id=att.id,
                            start=att_start,
                            end=chk_pos,
                            target_piece_id=chk.id,
                            carry_cargo=True,
                        )
                    )
                    if att.carried_by is None and att.cargo:
                        _add_if_structurally_valid(
                            AtomicAction(
                                action_type=atype,
                                piece_id=att.id,
                                start=att_start,
                                end=chk_pos,
                                target_piece_id=chk.id,
                                carry_cargo=False,
                            )
                        )

    # 2. Di chuyển / vào Sở chỉ huy hoặc tách chạy bằng Tư lệnh (hoặc phương tiện đang chở Tư lệnh)
    mover = cmd if cmd.carried_by is None else ctx.state.pieces.get(cmd.carried_by)
    if mover is not None:
        root_mover = rules._root_piece(ctx.state, mover) or mover
        mover_start = ctx.origins.get(mover.id)
        if mover_start is not None:
            sy, sx = mover_start
            actors_to_move = [cmd]
            if root_mover.id != cmd.id:
                actors_to_move.append(root_mover)

            occ_grid = ctx.occ_grid
            opp_aa_grid = ctx.aa_danger_grid[opp]

            for actor in actors_to_move:
                dirs = _ALL_DIRS if (actor.is_heroic or actor.piece_type in (PieceType.AIRCRAFT, PieceType.NAVY)) else _ORTH_DIRS
                max_r = 11 if actor.piece_type == PieceType.COMMANDER else (5 if actor.is_heroic else 4)
                is_nonhero_air = actor.piece_type == PieceType.AIRCRAFT and not actor.is_heroic
                for dy, dx in dirs:
                    for step in range(1, max_r + 1):
                        y, x = sy + dy * step, sx + dx * step
                        if not (0 <= y < rows and 0 <= x < cols):
                            break
                        end: Position = (y, x)
                        occ = occ_grid[y * 11 + x]
                        if occ is None:
                            # Nếu ô trống đã bị địch nhắm tới hoặc Aircraft thường bay vào vùng AA -> chắc chắn tự sát
                            if is_nonhero_air and opp_aa_grid[y * 11 + x]:
                                break
                            if ctx.attackers_to_square(opp, end):
                                continue
                            _add_if_structurally_valid(
                                AtomicAction(ActionType.MOVE, actor.id, mover_start, end, carry_cargo=True)
                            )
                        elif occ.owner == defender:
                            _add_if_structurally_valid(
                                AtomicAction(
                                    ActionType.BOARD,
                                    actor.id,
                                    mover_start,
                                    end,
                                    target_piece_id=occ.id,
                                    carrier_id=occ.id,
                                )
                            )
                            if actor.piece_type != PieceType.AIRCRAFT:
                                break
                        else:
                            _add_if_structurally_valid(
                                AtomicAction(
                                    ActionType.CAPTURE,
                                    actor.id,
                                    mover_start,
                                    end,
                                    target_piece_id=occ.id,
                                    carry_cargo=True,
                                )
                            )
                            if actor.piece_type != PieceType.AIRCRAFT:
                                break

    # 3. Đưa quân chắn đường (chỉ hiệu quả nếu 1 quân chiếu không phải loại bắn xuyên)
    if len(checkers) == 1 and cmd_pos is not None:
        chk = checkers[0]
        chk_pos = ctx.origins.get(chk.id)
        if (
            chk_pos is not None
            and chk.piece_type not in _RANGED_PIERCING
            and not (chk.piece_type == PieceType.NAVY and rules.can_navy_occupy_square(chk_pos) and not rules.is_sea_square(cmd_pos))
        ):
            block_squares = rules.path_points(chk_pos, cmd_pos)
            if block_squares:
                for pt in block_squares:
                    for ally in ctx.pieces_by_player[defender]:
                        if ally.piece_type in (PieceType.COMMANDER, PieceType.HEADQUARTERS) and not ally.is_heroic:
                            continue
                        astart = ctx.origins.get(ally.id)
                        if astart is None or astart == pt:
                            continue
                        if not movement_shape_ok(ally.piece_type, ally.is_heroic, astart[0], astart[1], pt[0], pt[1], False):
                            continue
                        _add_if_structurally_valid(
                            AtomicAction(ActionType.MOVE, ally.id, astart, pt, carry_cargo=True)
                        )
    return candidates


def _evaluate_defense_cost(
    ctx_before: EvalContext,
    action: AtomicAction,
    after_state: GameState,
    defender: Player,
    *,
    mat_before: float,
    attacker_captured_value: float,
) -> float:
    """Ước lượng chi phí phòng thủ chuẩn hóa `Cost_def(T(s_b, r), defender)` (>= 0).

    - Nếu ăn được quân đang chiếu một cách hợp lệ & an toàn (không thiệt hại quân,
      quân ăn không bị treo mất lỗ): Cost_def ≈ 0 (`HE-05`).
    """
    opp = opponent_of(defender)
    mat_after = sum(piece_value(p) for p in after_state.pieces.values() if p.owner == defender)
    material_sacrificed = max(0.0, mat_before - mat_after)

    # Kiểm tra hậu quả quân vừa thực hiện nước giải chiếu (có bị phơi ở ô đích lỗ không?)
    hang_loss = 0.0
    moved_piece = after_state.pieces.get(action.piece_id)
    after_ctx: EvalContext | None = None

    if moved_piece is not None and action.end is not None and moved_piece.piece_type != PieceType.COMMANDER:
        is_nonhero_air = moved_piece.piece_type == PieceType.AIRCRAFT and not moved_piece.is_heroic
        after_ctx = EvalContext.from_state(after_state, compute_aa=is_nonhero_air)
        dest_pos = after_ctx.origins.get(moved_piece.id)
        if dest_pos is not None:
            enemy_retakers = after_ctx.attackers_to_square(opp, dest_pos)
            if is_nonhero_air:
                if dest_pos in after_ctx.defended_by[opp]:
                    hang_loss = max(hang_loss, piece_value(moved_piece) * 0.85)
            if enemy_retakers:
                moved_stack_val = after_ctx.stack_value(moved_piece.id)
                min_retaker_val = min(piece_value(r) for r in enemy_retakers)
                # Kiểm tra có đồng minh giữ ô đích sau nước đi không
                after_ctx.ensure_root_threat_map()
                is_guarded = bool(after_ctx.root_defenders.get(moved_piece.id))
                if not is_guarded:
                    hang_loss = max(hang_loss, moved_stack_val * 0.8)
                elif moved_stack_val > min_retaker_val:
                    hang_loss = max(hang_loss, (moved_stack_val - min_retaker_val) * 0.7)

    # Kiểm tra nếu Tư lệnh buộc phải chạy (hoặc vào SCH) -> có còn bị uy hiếp sát hoặc kẹt không
    disruption = 0.0
    if attacker_captured_value <= 0.0:
        # Không tiêu diệt được quân chiếu -> vẫn chịu áp lực thế trận
        if after_ctx is None:
            after_ctx = EvalContext.from_state(after_state, compute_aa=False)
        cmd_after = after_ctx.cmd_piece[defender]
        if cmd_after is not None and after_ctx.cmd_sheltered_hq[defender] is None:
            cpos = after_ctx.cmd_origin[defender]
            if cpos is not None:
                # Đếm số ô thoát kề của Tư lệnh sau khi chạy
                safe_steps = 0
                cy_a, cx_a = cpos
                occ_grid_a = after_ctx.occ_grid
                for dy, dx in _ORTH_DIRS:
                    ny, nx = cy_a + dy, cx_a + dx
                    if 0 <= ny < 12 and 0 <= nx < 11:
                        occ = occ_grid_a[ny * 11 + nx]
                        if occ is None or occ.owner == defender:
                            if not after_ctx.attackers_to_square(opp, (ny, nx)):
                                safe_steps += 1
                disruption = 4.0 + (4.0 if safe_steps <= 1 else 0.0)
        elif after_ctx.cmd_sheltered_hq[defender] is not None:
            # Trú vào SCH -> tương đối an toàn nhưng vẫn bị áp lực
            disruption = 2.0

    # Nếu ăn sạch quân chiếu AN TOÀN (hang_loss == 0, material_sacrificed == 0) -> ~0!
    return min(100.0, material_sacrificed + hang_loss + disruption)


_DEFENSE_TYPE_PRIORITY = {
    ActionType.CAPTURE: 0,
    ActionType.BOMB: 0,
    ActionType.BOMBARD: 0,
    ActionType.BOARD: 1,
}


def _compute_active_check_risk(ctx: EvalContext, defender: Player) -> float:
    """Tính `Risk(s, defender)` khi Tư lệnh đang trực tiếp bị chiếu."""
    opp = opponent_of(defender)
    cmd = ctx.cmd_piece[defender]
    cmd_pos = ctx.cmd_origin[defender]
    if cmd is None or cmd_pos is None:
        return 100.0

    checkers = ctx.attackers_to_square(opp, cmd_pos)
    if not checkers:
        return 0.0

    temp_state = _lightweight_turn_copy(ctx.state, defender)
    candidates = _generate_targeted_defense_candidates(ctx, temp_state, defender, checkers, cmd)

    can_certify_legal = (
        ctx.state.compound_turn is None
        and ctx.state.current_player == defender
        and getattr(ctx.state.game_status, "value", "ongoing") == "ongoing"
        and not getattr(ctx.state, "_engine_terminal", False)
    )

    mat_before = side_material(ctx, defender)
    best_cost: float | None = None

    # Thứ tự toán học chặt chẽ: Ăn quân chiếu (cận dưới 0.0) -> BOARD vào SCH (cận dưới 2.0) -> MOVE né/chắn (cận dưới 4.0)
    ordered = sorted(candidates, key=lambda a: _DEFENSE_TYPE_PRIORITY.get(a.action_type, 2))

    for act in ordered:
        prio = _DEFENSE_TYPE_PRIORITY.get(act.action_type, 2)
        if best_cost is not None:
            if prio == 1 and best_cost <= 2.0 + 1e-12:
                if can_certify_legal:
                    ctx._defender_has_legal[defender] = True
                return float(best_cost)
            if prio == 2 and best_cost <= 4.0 + 1e-12:
                if can_certify_legal:
                    ctx._defender_has_legal[defender] = True
                return float(best_cost)

        res = preview_action(temp_state, act)
        if not res.accepted:
            continue
        captured_chk_val = 0.0
        if len(checkers) == 1 and act.target_piece_id == checkers[0].id and checkers[0].id not in res.state.pieces:
            captured_chk_val = piece_value(checkers[0])
        cost = _evaluate_defense_cost(
            ctx,
            act,
            res.state,
            defender,
            mat_before=mat_before,
            attacker_captured_value=captured_chk_val,
        )
        if best_cost is None or cost < best_cost:
            best_cost = cost
        if best_cost <= 0.05:
            if can_certify_legal:
                ctx._defender_has_legal[defender] = True
            return 0.0

    if best_cost is not None:
        if can_certify_legal:
            ctx._defender_has_legal[defender] = True
        return float(best_cost)

    # Nếu không có ứng viên trọng tâm nào hợp lệ, hỏi Engine xem có còn nước hợp lệ nào không
    has_leg = has_legal_action(temp_state)
    if can_certify_legal:
        ctx._defender_has_legal[defender] = has_leg
    if not has_leg:
        return 100.0
    return 45.0


def _latent_check_risk(ctx: EvalContext, defender: Player) -> float:
    """Ước lượng nguy cơ bị đối phương chiếu sau 1 nước đi (`CheckOpp(s, p)`) + trạng thái SCH/chắn.

    Thiết kế chọn lọc để giữ chi phí dưới ngân sách `< 1000 ms`: chỉ mô phỏng
    nhanh các đường chiếu 1 bước thực sự có khả năng ép phòng thủ tốn kém.
    """
    opp = opponent_of(defender)
    cmd = ctx.cmd_piece[defender]
    cmd_pos = ctx.cmd_origin[defender]
    if cmd is None or cmd_pos is None:
        return 100.0

    # 1. Nếu Tư lệnh đang trú trong Sở chỉ huy thường: kiểm tra đe dọa phá Sở chỉ huy
    sheltered_hq = ctx.cmd_sheltered_hq[defender]
    if sheltered_hq is not None:
        hq_attackers = ctx.attackers_to_square(opp, cmd_pos)
        if not hq_attackers:
            return 0.0
        # Nếu HQ đang bị đe dọa phá -> kiểm tra quân tấn công có đang treo miễn phí không
        ctx.ensure_root_threat_map()
        max_threat = 0.0
        for att in hq_attackers:
            apos = ctx.origins.get(att.id)
            can_capture_safely = bool(apos is not None and ctx.attackers_to_square(defender, apos) and not ctx.root_defenders.get(att.id))
            t_cost = 4.0 if can_capture_safely else 14.0
            if t_cost > max_threat:
                max_threat = t_cost
        return max_threat

    # 2. Tư lệnh ở ngoài: tìm tối đa 3 đòn chiếu tiềm ẩn 1 nước mạnh nhất (lọc hình học nhanh)
    cy, cx = cmd_pos
    worst_latent = 0.0
    occ_grid = ctx.occ_grid
    def_aa_grid = ctx.aa_danger_grid[defender]
    opp_attackers = ctx.attackers_with_range[opp]

    # Các ô giao cắt hàng/cột/chéo với Tư lệnh trong tầm bắn địch
    for att, (sy, sx), max_r in opp_attackers:
        ptype = att.piece_type
        if ptype == PieceType.COMMANDER:
            continue
        dc_y = cy - sy
        dc_x = cx - sx
        lim = max_r + 1
        if dc_y > lim or dc_y < -lim or dc_x > lim or dc_x < -lim:
            continue
        hero = att.is_heroic

        check_squares: list[Position] = []
        # Chiếu theo hàng/cột với Tư lệnh: điểm chiếu nằm ở (cy, sx) hoặc (sy, cx) hoặc gần cmd
        if cy != sy and sx != cx and 0 <= cy < 12 and 0 <= sx < 11:
            if movement_shape_ok(ptype, hero, sy, sx, cy, sx, False):
                check_squares.append((cy, sx))
        if cx != sx and sy != cy and 0 <= sy < 12 and 0 <= cx < 11:
            if movement_shape_ok(ptype, hero, sy, sx, sy, cx, False):
                check_squares.append((sy, cx))
        if not check_squares:
            # Kiểm tra các ô lân cận trên 8 tia từ Tư lệnh nằm trong tầm 1..2 của `att`
            for dy, dx in _ALL_DIRS:
                ny, nx = cy + dy, cx + dx
                if 0 <= ny < 12 and 0 <= nx < 11 and (ny != sy or nx != sx):
                    if movement_shape_ok(ptype, hero, sy, sx, ny, nx, False):
                        check_squares.append((ny, nx))
                        if len(check_squares) >= 2:
                            break

        for dest in check_squares[:2]:
            dest_y, dest_x = dest
            occ_d = occ_grid[dest_y * 11 + dest_x]
            if occ_d is not None and occ_d.owner == opp:
                continue
            # Kiểm tra nhanh xem ô `dest` có đường đi không (trừ máy bay)
            if ptype != PieceType.AIRCRAFT and grid_path_blocked(occ_grid, sy, sx, dest_y, dest_x):
                continue
            # Mô phỏng hình học: tại `dest`, quân `att` có chiếu được `cmd_pos` không?
            if not movement_shape_ok(ptype, hero, dest_y, dest_x, cy, cx, True):
                continue
            if ptype not in _RANGED_PIERCING and ptype != PieceType.NAVY:
                if grid_path_blocked_ignoring(occ_grid, dest_y, dest_x, cy, cx, sy, sx):
                    continue

            # Đánh giá quân `att` tại `dest` có bị `defender` ăn an toàn ngay không (`HE-05`)
            if ptype == PieceType.AIRCRAFT and not hero and def_aa_grid[dest_y * 11 + dest_x]:
                continue  # Máy bay tự sát vào AA

            def_counters = ctx.attackers_to_square(defender, dest)
            # Nếu `defender` có quân bảo vệ sẵn tại `dest` mà `att` giá trị >= hoặc không được hỗ trợ -> đòn chiếu yếu
            att_supported = False
            for f, (fy, fx), mr in opp_attackers:
                if f.id != att.id:
                    ady = dest_y - fy
                    if ady < 0:
                        ady = -ady
                    if ady <= mr:
                        adx = dest_x - fx
                        if adx < 0:
                            adx = -adx
                        if adx <= mr:
                            att_supported = True
                            break
            if def_counters and not att_supported:
                est_risk = 1.5  # Dễ bị ăn lại miễn phí nếu chiếu từ đó
            elif def_counters:
                est_risk = 5.5
            else:
                # Không ai canh ô `dest` -> chiếu nguy hiểm thực sự!
                est_risk = 14.0 if ptype in (PieceType.ARTILLERY, PieceType.AIRCRAFT, PieceType.NAVY, PieceType.TANK) else 10.0

            if est_risk > worst_latent:
                worst_latent = est_risk

    # Phạt nhẹ cấu trúc nếu Tư lệnh đi lạc lên tuyến trước không có che chắn
    adv_y = cy if defender == Player.RED else (ctx.state.board.ROWS - 1 - cy)
    adj_friends = 0
    for dy, dx in _ALL_DIRS:
        ny, nx = cy + dy, cx + dx
        if 0 <= ny < 12 and 0 <= nx < 11:
            occ = occ_grid[ny * 11 + nx]
            if occ is not None and occ.owner == defender:
                adj_friends += 1
    structural = max(0.0, adv_y - 2) * 1.2 + (2.5 if adj_friends == 0 else 0.0)
    return min(100.0, worst_latent + structural)


def side_king_risk(ctx: EvalContext, side: Player) -> float:
    """Tính `Risk(s, side)` >= 0 cho Tư lệnh của `side`."""
    if not ctx.cmd_alive[side]:
        return 100.0
    if ctx.cmd_in_check[side]:
        return _compute_active_check_risk(ctx, side)
    return _latent_check_risk(ctx, side)


def evaluate_king_safety(ctx: EvalContext, perspective: Player) -> float:
    """F2 — Đặc trưng hai chiều đối xứng K(s, p) = Risk(s, opp(p)) - Risk(s, p)."""
    opp = opponent_of(perspective)
    return side_king_risk(ctx, opp) - side_king_risk(ctx, perspective)


__all__ = ["evaluate_king_safety", "side_king_risk"]

