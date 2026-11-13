# packages/agents/evaluation/evaluator.py
"""CCHEFEvaluator — Tổng hợp, chuẩn hóa clip(X / scale_X, -1, 1) và trọng số H1..H7.

Công thức (CCHEF §2.1 & §11):
    E(s, p) = +W                        nếu p thắng (ưu tiên tuyệt đối)
            = -W                        nếu p thua  (ưu tiên tuyệt đối)
            =  0                        nếu hòa
            = Σ_i w_i(g(s)) * x_hat_i   nếu chưa kết thúc, với x_hat_i = clip(X_i / scale_i, -1, 1)

Tách rời khỏi Agent để `HeuristicAgent`, `MinimaxAgent` và `AlphaBetaAgent`
cùng sử dụng duy nhất một nguồn chân lý đánh giá trạng thái bàn cờ.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping

from commander_game_engine.game_state import GameState, GameStatus, Player

from .context import EvalContext, opponent_of
from .deployment import evaluate_deployment
from .king_safety import evaluate_king_safety
from .material import evaluate_material
from .mobility import evaluate_mobility
from .position import evaluate_position
from .safe_check import evaluate_safe_check
from .tactical import evaluate_tactical
from .weights import (
    DEFAULT_CCHEF_WEIGHTS,
    FEATURE_NAMES,
    compute_observable_phase,
    normalize_weights,
    resolve_cchef_config,
)

TERMINAL_WIN_SCORE: float = 1_000_000.0
TERMINAL_DRAW_SCORE: float = 0.0


def _clip_unit(value: float) -> float:
    if not math.isfinite(value):
        return 0.0
    if value > 1.0:
        return 1.0
    if value < -1.0:
        return -1.0
    return float(value)


@dataclass(frozen=True)
class EvaluationBreakdown:
    """Chi tiết đầy đủ một phép lượng giá CCHEF."""

    total_score: float
    is_terminal: bool
    raw_components: dict[str, float]
    normalized_components: dict[str, float]
    weights_used: dict[str, float]
    phase_info: dict[str, Any]


class CCHEFEvaluator:
    """Bộ lượng giá tĩnh theo chuẩn CCHEF (hỗ trợ đầy đủ H1 -> H7 và bật/tắt đặc trưng)."""

    def __init__(self, config: Mapping[str, Any] | None = None) -> None:
        self.resolved_config = resolve_cchef_config(config)
        self.variant: str = self.resolved_config["variant"]
        self.enabled_features: tuple[str, ...] = self.resolved_config["enabled_features"]
        self.raw_weights: dict[str, float] = dict(self.resolved_config["raw_weights"])
        self.effective_weights: dict[str, float] = dict(self.resolved_config["effective_weights"])
        self.weight_normalization: str = self.resolved_config["weight_normalization"]
        self.scales: dict[str, float] = dict(self.resolved_config["scales"])
        self.phase_modifiers: dict[str, dict[str, float]] = self.resolved_config["phase_modifiers"]
        self.opening_material_threshold: float = self.resolved_config["opening_material_threshold"]
        self.endgame_material_threshold: float = self.resolved_config["endgame_material_threshold"]
        self.enable_compound_lookahead: bool = bool(self.resolved_config["enable_compound_lookahead"])
        self.enable_co_synergy: bool = bool(self.resolved_config["enable_co_synergy"])
        self.co_weight: float = float(self.resolved_config["co_weight"])

        self._active_set = frozenset(self.enabled_features)
        self._need_aa: bool = bool({"P", "C", "D", "T", "K", "Q"} & self._active_set)

    def weights_for_state(self, state: GameState) -> tuple[dict[str, float], dict[str, Any]]:
        """Trả về `(weights, phase_info)` dùng để chấm trạng thái `state`.

        Với H1..H6: giữ trọng số tĩnh `self.effective_weights`.
        Với H7: nội suy mượt các hệ số điều chỉnh pha (đối xứng Đỏ/Xanh) rồi tái chuẩn hóa.
        """
        phase_info = compute_observable_phase(
            state,
            opening_material_threshold=self.opening_material_threshold,
            endgame_material_threshold=self.endgame_material_threshold,
        )
        if self.variant != "H7":
            return dict(self.effective_weights), phase_info

        w_open = phase_info["opening"]
        w_mid = phase_info["middlegame"]
        w_end = phase_info["endgame"]
        mods_open = self.phase_modifiers["opening"]
        mods_mid = self.phase_modifiers["middlegame"]
        mods_end = self.phase_modifiers["endgame"]

        blended_raw: dict[str, float] = {}
        for feat in self.enabled_features:
            base_w = self.effective_weights.get(feat, 0.0)
            mult = w_open * mods_open[feat] + w_mid * mods_mid[feat] + w_end * mods_end[feat]
            blended_raw[feat] = max(0.0, base_w * mult)

        if self.weight_normalization == "none":
            out = {k: blended_raw.get(k, 0.0) for k in FEATURE_NAMES}
        else:
            out = normalize_weights(blended_raw, self.enabled_features, normalization="sum_to_one")
        return out, phase_info

    def compute_raw_components(
        self,
        state: GameState,
        perspective: Player,
        *,
        ctx: EvalContext | None = None,
        compute_all: bool = False,
    ) -> dict[str, float]:
        """Tính giá trị thô `(M, K, Q, P, C, D, T)` từ góc nhìn `perspective`."""
        need_aa = compute_all or bool({"P", "C", "D", "T", "K", "Q"} & self._active_set)
        ev_ctx = ctx or EvalContext.from_state(state, compute_aa=need_aa)

        raw: dict[str, float] = {k: 0.0 for k in FEATURE_NAMES}
        active = frozenset(FEATURE_NAMES) if compute_all else self._active_set

        if "M" in active:
            raw["M"] = evaluate_material(ev_ctx, perspective)
        if "K" in active:
            raw["K"] = evaluate_king_safety(ev_ctx, perspective)
        if "Q" in active:
            raw["Q"] = evaluate_safe_check(ev_ctx, perspective)
        if "P" in active:
            raw["P"] = evaluate_position(ev_ctx, perspective)
        if "C" in active:
            raw["C"] = evaluate_mobility(ev_ctx, perspective)
        if "D" in active:
            raw["D"] = evaluate_deployment(ev_ctx, perspective)
        if "T" in active:
            raw["T"] = evaluate_tactical(ev_ctx, perspective)
        return raw

    def evaluate_breakdown(
        self,
        state: GameState,
        perspective: Player,
        *,
        ctx: EvalContext | None = None,
        is_checkmate_override: bool = False,
        is_stalemate_override: bool = False,
        mate_distance_ply: int = 0,
    ) -> EvaluationBreakdown:
        """Tính đầy đủ điểm CCHEF kèm `raw_components`, `normalized_components`, `phase_info`."""
        ev_ctx = ctx or EvalContext.from_state(state, compute_aa=self._need_aa)
        raw = self.compute_raw_components(state, perspective, ctx=ev_ctx, compute_all=False)
        norm = {
            k: (_clip_unit(raw[k] / self.scales[k]) if k in self._active_set else 0.0)
            for k in FEATURE_NAMES
        }
        w_used, phase_info = self.weights_for_state(state)

        opp = opponent_of(perspective)
        mate_bonus = max(0.0, float(mate_distance_ply))

        # Ưu tiên tuyệt đối trạng thái kết thúc (CCHEF §2.1)
        if not ev_ctx.cmd_alive[perspective]:
            return EvaluationBreakdown(
                total_score=-TERMINAL_WIN_SCORE + mate_bonus,
                is_terminal=True,
                raw_components=raw,
                normalized_components=norm,
                weights_used=w_used,
                phase_info=phase_info,
            )
        if not ev_ctx.cmd_alive[opp] or is_checkmate_override:
            return EvaluationBreakdown(
                total_score=TERMINAL_WIN_SCORE - mate_bonus,
                is_terminal=True,
                raw_components=raw,
                normalized_components=norm,
                weights_used=w_used,
                phase_info=phase_info,
            )
        if is_stalemate_override:
            return EvaluationBreakdown(
                total_score=TERMINAL_DRAW_SCORE,
                is_terminal=True,
                raw_components=raw,
                normalized_components=norm,
                weights_used=w_used,
                phase_info=phase_info,
            )

        status = getattr(state, "game_status", GameStatus.ONGOING)
        if status == GameStatus.RED_WIN:
            sc = (TERMINAL_WIN_SCORE - mate_bonus) if perspective == Player.RED else (-TERMINAL_WIN_SCORE + mate_bonus)
            return EvaluationBreakdown(sc, True, raw, norm, w_used, phase_info)
        if status == GameStatus.BLUE_WIN:
            sc = (TERMINAL_WIN_SCORE - mate_bonus) if perspective == Player.BLUE else (-TERMINAL_WIN_SCORE + mate_bonus)
            return EvaluationBreakdown(sc, True, raw, norm, w_used, phase_info)
        if status == GameStatus.DRAW:
            return EvaluationBreakdown(TERMINAL_DRAW_SCORE, True, raw, norm, w_used, phase_info)

        total = sum(w_used.get(k, 0.0) * norm[k] for k in self.enabled_features)
        if not math.isfinite(total):
            total = 0.0
        return EvaluationBreakdown(
            total_score=float(total),
            is_terminal=False,
            raw_components=raw,
            normalized_components=norm,
            weights_used=w_used,
            phase_info=phase_info,
        )

    def evaluate_state(
        self,
        state: GameState,
        perspective: Player,
        *,
        is_checkmate_override: bool = False,
        is_stalemate_override: bool = False,
        mate_distance_ply: int = 0,
    ) -> tuple[float, dict[str, float], bool]:
        """Giao diện gọn dùng chung cho `HeuristicAgent`, `MinimaxAgent` và `AlphaBetaAgent`.

        Trả về `(total_score, normalized_components, is_terminal)`.
        """
        bd = self.evaluate_breakdown(
            state,
            perspective,
            is_checkmate_override=is_checkmate_override,
            is_stalemate_override=is_stalemate_override,
            mate_distance_ply=mate_distance_ply,
        )
        return bd.total_score, bd.normalized_components, bd.is_terminal


__all__ = [
    "CCHEFEvaluator",
    "DEFAULT_CCHEF_WEIGHTS",
    "EvaluationBreakdown",
    "TERMINAL_DRAW_SCORE",
    "TERMINAL_WIN_SCORE",
]

