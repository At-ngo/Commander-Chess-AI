# packages/agents/evaluation/tactical.py
"""F7 — Tactical Evaluation, Stack Risk (`TR`), Realized Capture (`TC`), and Coordination (`CO`).

Tuân thủ tuyệt đối CCHEF §9 & §10:
- `V_stack(u, s)`: tổng điểm `{u} ∪ Desc(u, s)` (không trùng ID, không gộp Tư lệnh vào SCH thường).
- `TC(s, a, p) = Gain(s, a, p) - Loss(s, a, p)`: tính trên tập ID bị loại duy nhất sau `apply/preview_action`
  (đã bao gồm quân cõng theo `_casualties` và thiệt hại AA); KHÔNG BAO GIỜ cộng lần hai vào `M(s')`!
- `TR(s, p) = sum_{u in RootStack_p} RiskLoss(u, s) * V_stack(u, s)`: chỉ duyệt RootStack (tránh đếm trùng cha+con),
  phân biệt đòn bắn tại chỗ (`BOMB`/`BOMBARD`, quân giữ tại chỗ KHÔNG đánh trả được nếu không với tới vị trí xạ thủ)
  và đòn thế chỗ (`CAPTURE`), đồng thời tính yếu tố lượt đi (`tempo` từ `state.current_player` đối xứng Đỏ/Xanh).
- `T(s, p) = ThreatValue(s, p) - ThreatValue(s, opp(p)) - [TR(s, p) - TR(s, opp(p))]`.
- `CO(turn_start, steps, s_eot, p)`: đo phần *synergy* (Initiative + ForcedResponse + SynergyResidual)
  của cả lượt `CompoundAction` hoàn chỉnh.
"""

from __future__ import annotations

from typing import Sequence

from commander_game_engine import rules
from commander_game_engine.actions import ActionType, AtomicAction, TurnCommand
from commander_game_engine.board import Position
from commander_game_engine.engine import EngineResult
from commander_game_engine.game_state import GameState, Piece, PieceType, Player

from .context import EvalContext, navy_phase1_clear_grid, opponent_of
from .king_safety import side_king_risk
from .material_table import piece_value

_CHECK_CAPTURE_TYPES = frozenset({ActionType.CAPTURE, ActionType.BOMB, ActionType.BOMBARD})


def compute_action_tc(
    state_before: GameState,
    transition_res: EngineResult,
    perspective: Player,
) -> dict[str, float]:
    """Tính `Gain`, `Loss`, `TC = Gain - Loss` không đếm trùng từ diff ID trước/sau nước đi (`HE-01..HE-03, HE-07`).

    Lưu ý: Chỉ dùng để giải thích/xếp hạng/phân tích CO — KHÔNG cộng vào `M(next_state)`.
    """
    opp = opponent_of(perspective)
    after_ids = set(transition_res.state.pieces.keys())
    removed_ids = set(state_before.pieces.keys()) - after_ids

    gain = 0.0
    loss = 0.0
    opp_removed = 0
    own_removed = 0
    for pid in removed_ids:
        piece = state_before.pieces[pid]
        val = piece_value(piece)
        if piece.owner == opp:
            gain += val
            opp_removed += 1
        elif piece.owner == perspective:
            loss += val
            own_removed += 1

    return {
        "gain": gain,
        "loss": loss,
        "tc": gain - loss,
        "opp_removed_count": float(opp_removed),
        "own_removed_count": float(own_removed),
    }


def _is_stationary_threat(
    ctx: EvalContext,
    att: Piece,
    att_pos: Position,
    target_piece: Piece,
    target_pos: Position,
) -> bool:
    """Xác định `att` tấn công `target_piece` tại chỗ (`BOMB`/`BOMBARD`, không thế chỗ sang `target_pos`)."""
    side = target_piece.owner
    if target_piece is ctx.cmd_sheltered_hq.get(side):
        return True
    if att.piece_type == PieceType.AIRCRAFT:
        return target_piece.piece_type != PieceType.AIRCRAFT
    if att.piece_type == PieceType.NAVY:
        if target_piece.piece_type == PieceType.NAVY:
            return False
        if not rules.is_shore_square(target_pos):
            return True
        return not navy_phase1_clear_grid(
            ctx.occ_grid,
            att.owner,
            att_pos[0],
            att_pos[1],
            target_pos[0],
            target_pos[1],
            allow_enemy_target_at_end=True,
        )
    return rules.is_sea_square(target_pos)


def _threat_on_piece_fraction(
    ctx: EvalContext,
    piece: Piece,
    pos: Position,
    v_stack: float,
    att: Piece,
    guards: Sequence[Piece],
    defender_defended: frozenset[Position],
    defender_aa_danger: frozenset[Position],
) -> float:
    """Ước lượng tỷ lệ thiệt hại thực (`RiskLoss ∈ [0, 1]`) của `piece` trước mối đe dọa `att`."""
    side = piece.owner
    att_pos = ctx.origins.get(att.id)
    if att_pos is None:
        return 0.0
    aval = piece_value(att)

    # Kiểm tra Máy bay thường bay qua/tới vùng phòng không của phe phòng thủ (`side`)
    aa_kill_attacker = False
    if att.piece_type == PieceType.AIRCRAFT and not att.is_heroic:
        if pos in defender_defended or pos in defender_aa_danger:
            aa_kill_attacker = True

    stationary = _is_stationary_threat(ctx, att, att_pos, piece, pos)

    if stationary:
        # Đòn bắn xa tại chỗ (`BOMB`/`BOMBARD`): `guards` giữ tại `pos` KHÔNG đánh trả được `att` tại `att_pos`!
        if aa_kill_attacker:
            # Máy bay địch bắn sẽ nổ ngay trên đường bay (mất 40đ Máy bay)
            return max(0.10, (v_stack - aval) / max(10.0, v_stack)) if v_stack > aval else 0.10

        revenge_at_shooter = [g for g in ctx.attackers_to_square(side, att_pos) if g.id != piece.id]
        if not revenge_at_shooter:
            return 0.94  # Bắn hoàn toàn miễn phí!
        if aval < v_stack:
            return min(0.88, max(0.38, (v_stack - 0.65 * aval) / max(10.0, v_stack)))
        # Có quân nhắm sẵn vào vị trí xạ thủ với giá trị tương đương/hơn
        return 0.18

    # Đòn ăn thế chỗ (`CAPTURE`): quân giữ tại `pos` CÓ THỂ ăn lại `att` ở `pos`
    if aa_kill_attacker:
        if v_stack > aval:
            return min(0.80, (v_stack - aval) / max(10.0, v_stack))
        return 0.10

    if not guards:
        return 0.92
    if aval < v_stack:
        diff_ratio = (v_stack - aval) / max(10.0, v_stack)
        return min(0.85, max(0.32, diff_ratio))
    return 0.10


def _root_stack_risks(ctx: EvalContext, side: Player) -> list[float]:
    """Tính danh sách `RiskLoss(u, s) * V_stack(u, s)` cho từng `RootStack_side`."""
    ctx.ensure_root_threat_map()
    opp = opponent_of(side)
    opp_defended = ctx.defended_by[opp]
    opp_aa_danger = ctx.aa_danger_by[opp]
    own_defended = ctx.defended_by[side]
    own_aa_danger = ctx.aa_danger_by[side]

    risks: list[float] = []
    for piece in ctx.pieces_by_player[side]:
        # CHỈ duyệt RootStack (quân đứng độc lập trên bàn), tránh đếm trùng cả cha lẫn con
        if piece.carried_by is not None or piece.position is None:
            continue
        if piece.piece_type == PieceType.COMMANDER:
            continue  # Rủi ro Tư lệnh thuộc F2 (K)

        v_stack = ctx.stack_value(piece.id, include_hq_sheltered=False)
        if v_stack <= 0.0:
            continue

        atts = ctx.root_threats.get(piece.id, ())
        guards = ctx.root_defenders.get(piece.id, ())
        risk_loss = 0.0

        if atts:
            displacing_cnt = 0
            for att in atts:
                apos = ctx.origins.get(att.id)
                if apos is not None and not _is_stationary_threat(ctx, att, apos, piece, piece.position):
                    displacing_cnt += 1
                frac = _threat_on_piece_fraction(
                    ctx,
                    piece,
                    piece.position,
                    v_stack,
                    att,
                    guards,
                    own_defended,
                    own_aa_danger,
                )
                if frac > risk_loss:
                    risk_loss = frac
            # Đòn thế chỗ hội đồng nhiều hơn số quân giữ (overload)
            if displacing_cnt > len(guards) and len(guards) > 0:
                risk_loss = max(risk_loss, 0.55)
            elif len(atts) >= 2 and not guards:
                risk_loss = max(risk_loss, 0.96)

        # Rủi ro phòng không cho Máy bay thường (`HE-11` + `HE-10`): mất luôn cả cargo nếu có!
        if piece.piece_type == PieceType.AIRCRAFT and not piece.is_heroic:
            if piece.position in opp_defended:
                risk_loss = max(risk_loss, 0.90 if not guards else 0.72)
            elif piece.position in opp_aa_danger:
                risk_loss = max(risk_loss, 0.65)

        if risk_loss > 0.0:
            if piece.cargo:
                risk_loss = min(1.0, risk_loss + 0.05)
            risks.append(risk_loss * v_stack)

    return risks


def side_tr_risk(ctx: EvalContext, side: Player) -> float:
    """Tính `TR(s, side) = sum_{u in RootStack_side} RiskLoss(u, s) * V_stack(u, s)` (`HE-10`, `HE-11`)."""
    return sum(_root_stack_risks(ctx, side))


def _tempo_adjusted_tr(ctx: EvalContext, side: Player) -> float:
    """Tính `TR` có trọng số nhịp lượt (`tempo`) đối xứng giữa Đỏ và Xanh.

    - Nếu `side != ctx.state.current_player`: đối phương ĐANG ĐẾN LƯỢT đánh ngay ->
      mục tiêu treo cao nhất gánh trọn `1.00`, mục tiêu tiếp theo `0.40`.
    - Nếu `side == ctx.state.current_player`: `side` ĐANG ĐẾN LƯỢT nên kịp chạy/che/ăn trả
      mục tiêu #1 (chỉ mất `0.20`tempo), chỉ bị nặng ở mục tiêu #2 (`0.42`) nếu trúng đòn đôi (fork).
    Vì dựa hoàn toàn vào `ctx.state.current_player`, phép trừ hai phe luôn bảo toàn
    `E(s, RED) == -E(s, BLUE)` (`HE-12`).
    """
    risks = _root_stack_risks(ctx, side)
    if not risks:
        return 0.0
    risks.sort(reverse=True)
    is_passive = side != ctx.state.current_player
    if is_passive:
        total = risks[0]
        for r in risks[1:]:
            total += 0.40 * r
        return total

    # Phe đang có lượt: hóa giải được mối đe dọa #1, nhưng không thoát hết cả nếu bị đòn đôi thật sự
    total = 0.20 * risks[0]
    for r in risks[1:]:
        total += 0.42 * r
    return total


def side_threat_value(ctx: EvalContext, attacker_side: Player) -> float:
    """Tính `ThreatValue(s, side)`: áp lực đòn đôi (fork) & quân địch kẹt chưa thể hóa giải."""
    ctx.ensure_root_threat_map()
    opp = opponent_of(attacker_side)
    opp_aa_defender = ctx.aa_danger_by[opp]  # Quân địch phòng không

    # Bỏ qua đe dọa đến từ quân bản thân đang treo miễn phí ở vị trí hiện tại
    own_free_hanging: set[str] = set()
    for u in ctx.pieces_by_player[attacker_side]:
        if u.carried_by is not None or u.position is None:
            continue
        atts_on_u = ctx.root_threats.get(u.id, ())
        guards_on_u = ctx.root_defenders.get(u.id, ())
        if atts_on_u and not guards_on_u and attacker_side != ctx.state.current_player:
            own_free_hanging.add(u.id)

    per_attacker_targets: dict[str, list[float]] = {}
    threat_score = 0.0

    for victim in ctx.pieces_by_player[opp]:
        if victim.carried_by is not None or victim.position is None:
            continue
        if victim.piece_type == PieceType.COMMANDER:
            continue
        v_stack = ctx.stack_value(victim.id, include_hq_sheltered=False)
        if v_stack <= 0.0:
            continue

        atts = ctx.root_threats.get(victim.id, ())
        if not atts:
            continue
        guards = ctx.root_defenders.get(victim.id, ())

        best_gain = 0.0
        for att in atts:
            if att.id in own_free_hanging:
                continue
            aval = piece_value(att)
            if att.piece_type == PieceType.AIRCRAFT and not att.is_heroic and victim.position in opp_aa_defender:
                if v_stack <= aval:
                    continue
            apos = ctx.origins.get(att.id)
            stationary = apos is not None and _is_stationary_threat(ctx, att, apos, victim, victim.position)
            clean = False
            if stationary:
                revenge = [g for g in ctx.attackers_to_square(opp, apos) if g.id != victim.id] if apos else []
                clean = (not revenge) or (v_stack > aval)
            else:
                clean = (not guards) or (aval < v_stack)
            if clean:
                per_attacker_targets.setdefault(att.id, []).append(v_stack)
                best_gain = max(best_gain, v_stack if not guards else (v_stack - aval))

        if best_gain > 0.0:
            threat_score += min(6.0, 0.10 * best_gain)

    # Đòn đôi (Fork) thực sự từ cùng 1 quân lành lặn
    for hits in per_attacker_targets.values():
        if len(hits) >= 2:
            hits.sort(reverse=True)
            threat_score += min(10.0, 0.20 * hits[1])

    return threat_score


def evaluate_tactical(ctx: EvalContext, perspective: Player) -> float:
    """F7 — T(s, p) = ThreatValue(p) - ThreatValue(opp) - [TR_tempo(p) - TR_tempo(opp)]."""
    opp = opponent_of(perspective)
    active = ctx.state.current_player

    tv_persp = side_threat_value(ctx, perspective) * (0.65 if perspective == active else 0.25)
    tv_opp = side_threat_value(ctx, opp) * (0.65 if opp == active else 0.25)
    tr_persp = _tempo_adjusted_tr(ctx, perspective)
    tr_opp = _tempo_adjusted_tr(ctx, opp)

    return (tv_persp - tv_opp) - (tr_persp - tr_opp)


def compute_co_synergy(
    start_state: GameState,
    steps: Sequence[AtomicAction | TurnCommand],
    end_state: GameState,
    perspective: Player,
    *,
    ctx_eot: EvalContext | None = None,
    lambda_initiative: float = 0.45,
    lambda_forced: float = 0.40,
    lambda_synergy: float = 0.35,
) -> dict[str, float]:
    """Đo lường phần thưởng phối hợp `CO(s, a, p)` chưa được phản ánh đủ ở M/K/Q/P (`HE-08`, §10).

    - Chỉ kích hoạt giá trị đáng kể cho `CompoundAction` có >= 2 hành động nguyên tử phối hợp
      (ví dụ: quân mạnh ăn + quân yếu chiếu, hoặc 2+ quân cùng dồn hỏa lực/tiến công).
    - Không cộng lại giá trị vật chất hay điểm chiếu vốn đã nằm trong M/K/Q.
    """
    atomic_steps = [s for s in steps if isinstance(s, AtomicAction)]
    if len(atomic_steps) < 2:
        return {
            "initiative": 0.0,
            "forced_response": 0.0,
            "synergy_residual": 0.0,
            "co_total": 0.0,
            "is_compound": 0.0,
        }

    ctx = ctx_eot or EvalContext.from_state(end_state)
    opp = opponent_of(perspective)
    rows = end_state.board.ROWS

    capture_steps = [a for a in atomic_steps if a.action_type in _CHECK_CAPTURE_TYPES]
    check_issued = ctx.cmd_in_check[opp]

    weak_checker_present = False
    distinct_actors: set[str] = {a.piece_id for a in atomic_steps}
    river_crossers = 0
    for a in atomic_steps:
        p = end_state.pieces.get(a.piece_id)
        if p is not None and a.end is not None:
            adv_y = a.end[0] if perspective == Player.RED else (rows - 1 - a.end[0])
            if adv_y >= 5:
                river_crossers += 1
        if check_issued and p is not None and ctx.cmd_origin[opp] is not None:
            if rules._piece_threatens_square(end_state, p, ctx.cmd_origin[opp], ctx.occ_map):
                if piece_value(p) <= 20.0:
                    weak_checker_present = True

    # 1. Initiative: phối hợp nhiều mục tiêu trong cùng 1 ply (ví dụ ăn quân + mở tuyến / ăn đa quân)
    initiative = 0.0
    if len(capture_steps) >= 2:
        initiative += 1.0
    elif capture_steps and (check_issued or river_crossers >= 2):
        initiative += 0.80
    elif len(distinct_actors) >= 2 and river_crossers >= 2:
        initiative += 0.45

    # 2. ForcedResponse: vừa ăn quân vừa ép chiếu nguy hiểm buộc đối phương đỡ (`HE-08`)
    forced_response = 0.0
    if check_issued:
        opp_risk = side_king_risk(ctx, opp)
        if opp_risk >= 6.0:
            forced_response = min(1.0, 0.45 + 0.03 * min(opp_risk, 18.0))
        elif opp_risk >= 1.5:
            forced_response = 0.30
        if capture_steps and weak_checker_present and forced_response > 0.0:
            forced_response = min(1.0, forced_response + 0.20)

    # 3. SynergyResidual: khai thác triệt để sức mạnh cõng quân (3 bước hoặc 2 bước ăn+chiếm thế)
    synergy_residual = 0.0
    if len(atomic_steps) == 3:
        synergy_residual += 0.65
    elif len(atomic_steps) == 2:
        synergy_residual += 0.35
    if capture_steps and check_issued:
        synergy_residual = min(1.0, synergy_residual + 0.35)

    co_total = (
        lambda_initiative * initiative
        + lambda_forced * forced_response
        + lambda_synergy * synergy_residual
    )
    return {
        "initiative": float(initiative),
        "forced_response": float(forced_response),
        "synergy_residual": float(synergy_residual),
        "co_total": float(co_total),
        "is_compound": 1.0,
    }


__all__ = [
    "compute_action_tc",
    "compute_co_synergy",
    "evaluate_tactical",
    "side_threat_value",
    "side_tr_risk",
]
