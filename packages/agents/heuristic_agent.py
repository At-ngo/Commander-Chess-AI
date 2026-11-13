# packages/agents/heuristic_agent.py
"""Level 2+ Agent — CCHEF Heuristic Agent cho Cờ Tư Lệnh (H1 -> H7 + CompoundTurn + CO).

Kiến trúc tách biệt:
- Hàm lượng giá tĩnh `CCHEFEvaluator` (M, K, Q, P, C, D, T, chuẩn hóa `scale_X`, pha H7)
  nằm tại `packages/agents/evaluation/` để Minimax và Alpha-Beta dùng chung công thức.
- `HeuristicAgent` gọi Game Engine (`preview_action`, `generate_legal_actions`, `has_legal_action`)
  làm chuẩn chuyển trạng thái, hỗ trợ lập kế hoạch toàn lượt `CompoundTurn` (Hành quân thần tốc, CO on/off),
  không sửa đổi `GameState` và không sinh nước đi ngoài `legal_actions`.
"""

from __future__ import annotations

from copy import copy, deepcopy
import math
import time
from typing import Any

from commander_game_engine import rules
from commander_game_engine.actions import (
    ActionType,
    AtomicAction,
    TurnCommand,
    TurnCommandType,
)
from commander_game_engine.engine import EngineResult, preview_action
from commander_game_engine.game_state import GameState, PieceType, Player
from commander_game_engine.move_generator import generate_legal_actions, has_legal_action

from .base import AgentAction, BaseAgent, format_action_str
from .evaluation import (
    CCHEFEvaluator,
    DEFAULT_CCHEF_WEIGHTS,
    EvaluationBreakdown,
    FEATURE_NAMES,
    TERMINAL_DRAW_SCORE,
    TERMINAL_WIN_SCORE,
    EvalContext,
    compute_action_tc,
    compute_co_synergy,
    opponent_of,
)

COMPONENT_NAMES: tuple[str, ...] = FEATURE_NAMES
DEFAULT_WEIGHTS: dict[str, float] = dict(DEFAULT_CCHEF_WEIGHTS)

_CAPTURE_LIKE_TYPES = frozenset({ActionType.CAPTURE, ActionType.BOMB, ActionType.BOMBARD})


def _safe_float(val: Any, default: float = 0.0) -> float:
    if not isinstance(val, (int, float)):
        return default
    fv = float(val)
    return fv if math.isfinite(fv) else default


class HeuristicAgent(BaseAgent):
    """Tác tử Heuristic theo chuẩn CCHEF (H1-H7, CO on/off, Grid-search weights & Phase H7)."""

    def __init__(
        self,
        name: str = "HeuristicAgent",
        seed: int | None = None,
        config: dict[str, Any] | None = None,
    ) -> None:
        cfg = deepcopy(config) if config else {}
        super().__init__(name=name, seed=seed, config=cfg)

        self.evaluator = CCHEFEvaluator(cfg)
        self.variant: str = self.evaluator.variant
        self.enabled_components: tuple[str, ...] = self.evaluator.enabled_features
        self.weights: dict[str, float] = dict(self.evaluator.raw_weights)
        self.effective_weights: dict[str, float] = dict(self.evaluator.effective_weights)
        self.normalization: str = self.evaluator.weight_normalization
        self.scales: dict[str, float] = dict(self.evaluator.scales)
        self.enable_compound_lookahead: bool = bool(self.evaluator.enable_compound_lookahead)
        self.enable_co_synergy: bool = bool(self.evaluator.enable_co_synergy)
        self.co_weight: float = float(self.evaluator.co_weight)

        self.tie_breaking = str(cfg.get("tie_breaking", "random")).strip().lower()
        if self.tie_breaking not in ("random", "first", "deterministic"):
            raise ValueError(
                f"tie_breaking không hợp lệ '{self.tie_breaking}'. Chỉ hỗ trợ: 'random', 'first', 'deterministic'."
            )

        self.weight_config_id = str(
            cfg.get("weight_config_id")
            or cfg.get("agent_config_id")
            or f"{self.variant}_cchef"
        )
        # Giới hạn mở rộng nhánh CompoundTurn nhằm bảo đảm luôn dưới ngân sách 1000 ms
        self.max_compound_roots = max(1, int(cfg.get("max_compound_roots", 5)))
        self.max_compound_children = max(2, int(cfg.get("max_compound_children", 5)))
        self.soft_compound_deadline_ms = float(cfg.get("soft_compound_deadline_ms", 550.0))

    @property
    def algorithm(self) -> str:
        return "heuristic"

    @property
    def version(self) -> str:
        return "2.0.0"

    def evaluate_components(self, state: GameState, perspective: Player) -> dict[str, float]:
        """Tính vector thành phần thô `(M, K, Q, P, C, D, T)` từ góc nhìn `perspective`."""
        return self.evaluator.compute_raw_components(state, perspective, compute_all=False)

    def evaluate_normalized_components(self, state: GameState, perspective: Player) -> dict[str, float]:
        """Tính vector thành phần đã chuẩn hóa `clip(X / scale_X, -1, 1)`."""
        bd = self.evaluator.evaluate_breakdown(state, perspective)
        return dict(bd.normalized_components)

    def evaluate_state(
        self,
        state: GameState,
        perspective: Player,
        *,
        is_checkmate_override: bool = False,
        is_stalemate_override: bool = False,
    ) -> tuple[float, dict[str, float], bool]:
        """Lượng giá trạng thái `state` từ góc nhìn `perspective`.

        Trả về `(total_score, normalized_components, is_terminal_score)`.
        """
        return self.evaluator.evaluate_state(
            state,
            perspective,
            is_checkmate_override=is_checkmate_override,
            is_stalemate_override=is_stalemate_override,
        )

    def _evaluate_end_of_turn(
        self,
        next_state: GameState,
        perspective: Player,
        transition_res: EngineResult,
        *,
        ply_steps: int = 1,
    ) -> EvaluationBreakdown:
        """Lượng giá trạng thái khi lượt vừa hoàn tất (kể cả kiểm tra Chiếu hết / Hòa bí chọn lọc)."""
        opp = opponent_of(perspective)
        ev_ctx = EvalContext.from_state(next_state, compute_aa=self.evaluator._need_aa)

        if transition_res.terminal_reason == "COMMANDER_CAPTURED" or not ev_ctx.cmd_alive[opp]:
            return self.evaluator.evaluate_breakdown(
                next_state,
                perspective,
                ctx=ev_ctx,
                is_checkmate_override=True,
                mate_distance_ply=ply_steps,
            )

        if (
            next_state.compound_turn is None
            and not ev_ctx.cmd_in_check[opp]
            and len(ev_ctx.pieces_by_player[opp]) <= 3
            and not has_legal_action(next_state)
        ):
            return self.evaluator.evaluate_breakdown(
                next_state,
                perspective,
                ctx=ev_ctx,
                is_stalemate_override=True,
                mate_distance_ply=ply_steps,
            )

        bd = self.evaluator.evaluate_breakdown(
            next_state,
            perspective,
            ctx=ev_ctx,
            mate_distance_ply=ply_steps,
        )

        # Tận dụng kết quả kiểm tra hợp lệ từ `_compute_active_check_risk` khi `"K"` đã chạy
        # để tránh gọi trùng `has_legal_action(next_state)` trên mọi nước đang chiếu.
        if (
            not bd.is_terminal
            and next_state.compound_turn is None
            and ev_ctx.cmd_in_check[opp]
        ):
            has_leg = ev_ctx._defender_has_legal.get(opp)
            if has_leg is None:
                has_leg = has_legal_action(next_state)
            if not has_leg:
                mate_bonus = max(0.0, float(ply_steps))
                return EvaluationBreakdown(
                    total_score=TERMINAL_WIN_SCORE - mate_bonus,
                    is_terminal=True,
                    raw_components=bd.raw_components,
                    normalized_components=bd.normalized_components,
                    weights_used=bd.weights_used,
                    phase_info=bd.phase_info,
                )

        return bd

    def _expand_compound_plan(
        self,
        turn_start_state: GameState,
        mid_state: GameState,
        steps_so_far: list[AgentAction],
        perspective: Player,
        *,
        max_children: int,
        eval_counter: list[int],
        deadline_perf: float | None = None,
    ) -> tuple[float, EvaluationBreakdown, list[AgentAction], GameState, dict[str, float]]:
        """Tìm chuỗi hoàn tất lượt CompoundTurn (tối đa 3 AtomicAction + END_TURN) tối ưu trong 1 ply."""
        if mid_state.compound_turn is None:
            eval_counter[0] += 1
            bd = self._evaluate_end_of_turn(
                mid_state,
                perspective,
                EngineResult(True, mid_state, rules.accept()),
                ply_steps=len(steps_so_far),
            )
            co = (
                compute_co_synergy(turn_start_state, steps_so_far, mid_state, perspective)
                if self.enable_co_synergy
                else {"initiative": 0.0, "forced_response": 0.0, "synergy_residual": 0.0, "co_total": 0.0, "is_compound": 0.0}
            )
            score = bd.total_score if bd.is_terminal else (bd.total_score + self.co_weight * co["co_total"])
            return score, bd, list(steps_so_far), mid_state, co

        if deadline_perf is not None and time.perf_counter() >= deadline_perf:
            end_cmd = TurnCommand(TurnCommandType.END_TURN)
            res_end = preview_action(mid_state, end_cmd)
            eot_state = res_end.state if res_end.accepted else mid_state
            eval_counter[0] += 1
            bd = self._evaluate_end_of_turn(eot_state, perspective, res_end, ply_steps=len(steps_so_far))
            co = (
                compute_co_synergy(turn_start_state, steps_so_far, eot_state, perspective)
                if self.enable_co_synergy
                else {"initiative": 0.0, "forced_response": 0.0, "synergy_residual": 0.0, "co_total": 0.0, "is_compound": 0.0}
            )
            score = bd.total_score if bd.is_terminal else (bd.total_score + self.co_weight * co["co_total"])
            return score, bd, [*steps_so_far, end_cmd], eot_state, co

        sub_actions = generate_legal_actions(mid_state)
        best_tuple: tuple[float, EvaluationBreakdown, list[AgentAction], GameState, dict[str, float]] | None = None

        # Ưu tiên đánh giá `END_TURN` trước làm mốc cơ sở (khi tổ hợp dừng ở đây)
        end_cmd = next((a for a in sub_actions if isinstance(a, TurnCommand)), None)
        atomic_subs = [a for a in sub_actions if isinstance(a, AtomicAction)]

        if end_cmd is not None:
            res_end = preview_action(mid_state, end_cmd)
            if res_end.accepted:
                eval_counter[0] += 1
                bd_end = self._evaluate_end_of_turn(res_end.state, perspective, res_end, ply_steps=len(steps_so_far))
                co_end = (
                    compute_co_synergy(turn_start_state, steps_so_far, res_end.state, perspective)
                    if self.enable_co_synergy
                    else {"initiative": 0.0, "forced_response": 0.0, "synergy_residual": 0.0, "co_total": 0.0, "is_compound": 0.0}
                )
                sc_end = bd_end.total_score if bd_end.is_terminal else (bd_end.total_score + self.co_weight * co_end["co_total"])
                best_tuple = (sc_end, bd_end, [*steps_so_far, end_cmd], res_end.state, co_end)
                if bd_end.is_terminal and sc_end > TERMINAL_WIN_SCORE * 0.5:
                    return best_tuple

        # Xếp hạng sơ bộ các nhánh con bằng TC / ăn quân / chiếu để chỉ mở top `child_limit`
        if atomic_subs:
            pre_ranked: list[tuple[float, AtomicAction, EngineResult]] = []
            opp = opponent_of(perspective)
            opp_cmd_ori: tuple[int, int] | None = None
            opp_cmd = next(
                (p for p in mid_state.pieces.values() if p.owner == opp and p.piece_type == PieceType.COMMANDER),
                None,
            )
            if opp_cmd is not None:
                opp_cmd_ori = rules._origin(mid_state, opp_cmd)
            for sa in atomic_subs:
                res_sa = preview_action(mid_state, sa)
                if not res_sa.accepted:
                    continue
                if res_sa.terminal_reason == "COMMANDER_CAPTURED":
                    # Thắng ngay trong lượt ghép!
                    eval_counter[0] += 1
                    bd_win = self.evaluator.evaluate_breakdown(res_sa.state, perspective, is_checkmate_override=True, mate_distance_ply=len(steps_so_far) + 1)
                    co_win = {"initiative": 1.0, "forced_response": 1.0, "synergy_residual": 1.0, "co_total": 1.0, "is_compound": 1.0}
                    return bd_win.total_score, bd_win, [*steps_so_far, sa], res_sa.state, co_win

                tc_sa = compute_action_tc(mid_state, res_sa, perspective)
                prio = tc_sa["tc"] + (18.0 if sa.action_type in _CAPTURE_LIKE_TYPES else 0.0)
                if sa.end is not None and opp_cmd_ori is not None:
                    if opp_cmd_ori[0] == sa.end[0] or opp_cmd_ori[1] == sa.end[1]:
                        prio += 14.0
                pre_ranked.append((prio, sa, res_sa))

            pre_ranked.sort(key=lambda item: item[0], reverse=True)
            child_limit = max_children if len(steps_so_far) <= 1 else max(2, max_children - 2)
            for _, sa, res_sa in pre_ranked[:child_limit]:
                if deadline_perf is not None and best_tuple is not None and time.perf_counter() >= deadline_perf:
                    break
                sub_steps = [*steps_so_far, sa]
                if res_sa.state.compound_turn is not None:
                    cand = self._expand_compound_plan(
                        turn_start_state,
                        res_sa.state,
                        sub_steps,
                        perspective,
                        max_children=max_children,
                        eval_counter=eval_counter,
                        deadline_perf=deadline_perf,
                    )
                else:
                    eval_counter[0] += 1
                    bd_leaf = self._evaluate_end_of_turn(res_sa.state, perspective, res_sa, ply_steps=len(sub_steps))
                    co_leaf = (
                        compute_co_synergy(turn_start_state, sub_steps, res_sa.state, perspective)
                        if self.enable_co_synergy
                        else {"initiative": 0.0, "forced_response": 0.0, "synergy_residual": 0.0, "co_total": 0.0, "is_compound": 0.0}
                    )
                    sc_leaf = bd_leaf.total_score if bd_leaf.is_terminal else (bd_leaf.total_score + self.co_weight * co_leaf["co_total"])
                    cand = (sc_leaf, bd_leaf, sub_steps, res_sa.state, co_leaf)

                if best_tuple is None or cand[0] > best_tuple[0]:
                    best_tuple = cand
                if best_tuple[1].is_terminal and best_tuple[0] > TERMINAL_WIN_SCORE * 0.5:
                    return best_tuple

        assert best_tuple is not None
        return best_tuple

    def score_legal_actions(
        self,
        state: GameState,
        legal_actions: list[AgentAction],
        *,
        soft_deadline_ms: float | None = None,
    ) -> list[dict[str, Any]]:
        """Chấm điểm toàn bộ nước đi hợp lệ trong `legal_actions` từ góc nhìn `state.current_player`.

        - Nếu `enable_compound_lookahead=True` (`CO on`, mặc định ở H6/H7), các hành động khởi phát hoặc
          tiếp nối `CompoundTurnState` được đánh giá theo **trạng thái cuối lượt tổ hợp hoàn chỉnh** `s_eot`
          cùng thành phần synergy `CO`.
        - Nếu `enable_compound_lookahead=False` (`CO off`), mỗi hành động chỉ đánh giá trực tiếp 1 bước sau đó.
        """
        t_start = time.perf_counter()
        deadline_perf = (
            t_start + (soft_deadline_ms / 1000.0)
            if soft_deadline_ms is not None and soft_deadline_ms > 0.0
            else (t_start + self.soft_compound_deadline_ms / 1000.0)
        )

        perspective = state.current_player
        opp_persp = opponent_of(perspective)
        eval_counter = [0]
        scored: list[dict[str, Any]] = []
        compound_candidates: list[tuple[int, EngineResult]] = []

        for idx, action in enumerate(legal_actions):
            astr = format_action_str(action)
            res = preview_action(state, action)
            if not res.accepted:
                continue

            next_state = res.state
            eval_counter[0] += 1
            if next_state.compound_turn is not None:
                # Chốt trạng thái cuối lượt (END_TURN) bằng bản sao nông (nhanh, an toàn vì `next_state` không đổi)
                eot_state = copy(next_state)
                eot_state.compound_turn = None
                eot_state.current_player = opp_persp
                eot_state.turn_number += 1
                eot_state.action_count += 1
                bd = self._evaluate_end_of_turn(eot_state, perspective, res, ply_steps=1)
            else:
                bd = self._evaluate_end_of_turn(next_state, perspective, res, ply_steps=1)
            tc_info = compute_action_tc(state, res, perspective)
            co_zero = {
                "initiative": 0.0,
                "forced_response": 0.0,
                "synergy_residual": 0.0,
                "co_total": 0.0,
                "is_compound": 0.0,
            }

            item: dict[str, Any] = {
                "index": idx,
                "action": action,
                "action_str": astr,
                "score": float(bd.total_score),
                "base_score": float(bd.total_score),
                "components": dict(bd.normalized_components),
                "raw_components": dict(bd.raw_components),
                "weights_used": dict(bd.weights_used),
                "phase_info": dict(bd.phase_info),
                "is_terminal": bool(bd.is_terminal),
                "tc": tc_info,
                "co": co_zero,
                "plan": [astr],
                "is_compound_plan": False,
                "evaluated_states_count_ref": eval_counter,
            }
            scored.append(item)

            if self.enable_compound_lookahead and next_state.compound_turn is not None and not bd.is_terminal:
                compound_candidates.append((len(scored) - 1, res))

        # Mở rộng các phương án tổ hợp (CO on) nếu còn ngân sách thời gian
        compound_expanded = 0
        if self.enable_compound_lookahead and compound_candidates:
            # Ưu tiên các tổ hợp đã có ăn quân / điểm step-1 cao (giới hạn nhánh ngay cả khi đang ở trong CompoundTurn)
            in_compound = state.compound_turn is not None
            compound_candidates.sort(
                key=lambda pair: (
                    1 if scored[pair[0]]["tc"]["tc"] > 0 else 0,
                    scored[pair[0]]["tc"]["tc"],
                    scored[pair[0]]["score"],
                ),
                reverse=True,
            )
            limit = min(len(compound_candidates), self.max_compound_roots + 1 if in_compound else self.max_compound_roots)
            for item_pos, res in compound_candidates[:limit]:
                if time.perf_counter() >= deadline_perf:
                    break
                item = scored[item_pos]
                comp_score, comp_bd, comp_steps, comp_eot, comp_co = self._expand_compound_plan(
                    state,
                    res.state,
                    [item["action"]],
                    perspective,
                    max_children=self.max_compound_children,
                    eval_counter=eval_counter,
                    deadline_perf=deadline_perf,
                )
                compound_expanded += 1
                item["score"] = float(comp_score)
                item["base_score"] = float(comp_bd.total_score)
                item["components"] = dict(comp_bd.normalized_components)
                item["raw_components"] = dict(comp_bd.raw_components)
                item["weights_used"] = dict(comp_bd.weights_used)
                item["phase_info"] = dict(comp_bd.phase_info)
                item["is_terminal"] = bool(comp_bd.is_terminal)
                item["co"] = dict(comp_co)
                item["plan"] = [format_action_str(a) for a in comp_steps]
                item["is_compound_plan"] = len(comp_steps) >= 2
                # Cập nhật TC toàn chuỗi nếu là kế hoạch đa bước
                item["tc"] = compute_action_tc(state, EngineResult(True, comp_eot, res.verdict), perspective)

        for item in scored:
            item["evaluated_states_count"] = eval_counter[0]
            item["compound_actions_count"] = compound_expanded
        return scored

    def _choose_action(
        self,
        state: GameState,
        legal_actions: list[AgentAction],
        **kwargs: Any,
    ) -> tuple[AgentAction, dict[str, Any]]:
        perspective = state.current_player
        opp_persp = opponent_of(perspective)
        soft_budget = kwargs.get("soft_deadline_ms")
        scored = self.score_legal_actions(
            state,
            legal_actions,
            soft_deadline_ms=_safe_float(soft_budget) if soft_budget is not None else None,
        )

        if not scored:
            fallback_action = legal_actions[0]
            comp_zero = {k: 0.0 for k in FEATURE_NAMES}
            return fallback_action, {
                "agent_config_id": self.weight_config_id,
                "weight_config_id": self.weight_config_id,
                "heuristic_variant": self.variant,
                "perspective": perspective.value,
                "evaluation_basis": "post_action_perspective",
                "normalization": self.normalization,
                "normalization_scales": dict(self.scales),
                "tie_breaking": self.tie_breaking,
                "enabled_components": list(self.enabled_components),
                "weights": dict(self.weights),
                "effective_weights": dict(self.effective_weights),
                "heuristic_score": 0.0,
                "heuristic_components": comp_zero,
                "raw_components": comp_zero,
                "game_phase": {},
                "co_enabled": bool(self.enable_compound_lookahead or self.enable_co_synergy),
                "co_synergy": {},
                "compound_plan": [format_action_str(fallback_action)],
                "is_compound_action": False,
                "tc_summary": {"gain": 0.0, "loss": 0.0, "tc": 0.0},
                "evaluated_states_count": 0,
                "compound_actions_count": 0,
                "candidate_rank": 1,
                "total_candidates": len(legal_actions),
                "tied_best_count": 1,
                "is_terminal_candidate": False,
                "top_candidates_preview": [],
            }

        best_score = max(item["score"] for item in scored)
        best_items = [
            item
            for item in scored
            if math.isclose(item["score"], best_score, rel_tol=0.0, abs_tol=1e-9)
        ]

        if len(best_items) == 1:
            chosen = best_items[0]
        elif self.tie_breaking == "random":
            chosen = self.rng.choice(best_items)
        elif self.tie_breaking == "deterministic":
            best_items.sort(key=lambda item: item["action_str"])
            chosen = best_items[0]
        else:  # "first"
            best_items.sort(key=lambda item: item["index"])
            chosen = best_items[0]

        ranked = sorted(scored, key=lambda item: (-item["score"], item["action_str"]))
        top_preview = [
            {
                "action": item["action_str"],
                "score": round(float(item["score"]), 5),
                "plan": item["plan"],
            }
            for item in ranked[:3]
        ]

        is_compound_chosen = bool(chosen["is_compound_plan"] or state.compound_turn is not None)
        eval_basis = "compound_turn_eot_perspective" if is_compound_chosen else "post_action_perspective"

        metadata: dict[str, Any] = {
            "agent_config_id": self.weight_config_id,
            "weight_config_id": self.weight_config_id,
            "heuristic_variant": self.variant,
            "perspective": perspective.value,
            "evaluation_basis": eval_basis,
            "normalization": self.normalization,
            "normalization_scales": dict(self.scales),
            "tie_breaking": self.tie_breaking,
            "enabled_components": list(self.enabled_components),
            "weights": dict(self.weights),
            "effective_weights": dict(chosen["weights_used"]),
            "heuristic_score": float(chosen["score"]),
            "heuristic_components": dict(chosen["components"]),
            "raw_components": dict(chosen["raw_components"]),
            "game_phase": dict(chosen["phase_info"]),
            "co_enabled": bool(self.enable_compound_lookahead or self.enable_co_synergy),
            "co_synergy": dict(chosen["co"]),
            "compound_plan": list(chosen["plan"]),
            "is_compound_action": is_compound_chosen,
            "tc_summary": dict(chosen["tc"]),
            "evaluated_states_count": int(chosen["evaluated_states_count"]),
            "compound_actions_count": int(chosen["compound_actions_count"]),
            "candidate_rank": 1,
            "total_candidates": len(scored),
            "tied_best_count": len(best_items),
            "is_terminal_candidate": bool(chosen["is_terminal"]),
            "top_candidates_preview": top_preview,
        }
        return chosen["action"], metadata


__all__ = [
    "COMPONENT_NAMES",
    "DEFAULT_WEIGHTS",
    "FEATURE_NAMES",
    "HeuristicAgent",
    "TERMINAL_DRAW_SCORE",
    "TERMINAL_WIN_SCORE",
]
