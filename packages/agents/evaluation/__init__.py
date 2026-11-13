# packages/agents/evaluation/__init__.py
"""Gói lượng giá CCHEF (Commander Chess Heuristic Evaluation Function) dùng chung cho Heuristic, Minimax và Alpha-Beta."""

from .context import EvalContext, opponent_of
from .deployment import evaluate_deployment
from .evaluator import (
    CCHEFEvaluator,
    EvaluationBreakdown,
    TERMINAL_DRAW_SCORE,
    TERMINAL_WIN_SCORE,
)
from .king_safety import evaluate_king_safety, side_king_risk
from .material import evaluate_material, side_material
from .material_table import CCHEF_BASE_POINTS, HERO_BONUS, piece_value
from .mobility import evaluate_mobility
from .position import TERRAIN_WEIGHT_GRID, evaluate_position
from .safe_check import evaluate_safe_check
from .tactical import (
    compute_action_tc,
    compute_co_synergy,
    evaluate_tactical,
    side_threat_value,
    side_tr_risk,
)
from .weights import (
    DEFAULT_CCHEF_WEIGHTS,
    DEFAULT_FEATURE_SCALES,
    DEFAULT_PHASE_MODIFIERS,
    FEATURE_NAMES,
    VARIANT_ENABLED_FEATURES,
    VARIANT_NAMES,
    compute_observable_phase,
    normalize_feature_key,
    normalize_weights,
    resolve_cchef_config,
    resolve_scales,
)

__all__ = [
    "CCHEF_BASE_POINTS",
    "CCHEFEvaluator",
    "DEFAULT_CCHEF_WEIGHTS",
    "DEFAULT_FEATURE_SCALES",
    "DEFAULT_PHASE_MODIFIERS",
    "EvalContext",
    "EvaluationBreakdown",
    "FEATURE_NAMES",
    "HERO_BONUS",
    "TERRAIN_WEIGHT_GRID",
    "TERMINAL_DRAW_SCORE",
    "TERMINAL_WIN_SCORE",
    "VARIANT_ENABLED_FEATURES",
    "VARIANT_NAMES",
    "compute_action_tc",
    "compute_co_synergy",
    "compute_observable_phase",
    "evaluate_deployment",
    "evaluate_king_safety",
    "evaluate_material",
    "evaluate_mobility",
    "evaluate_position",
    "evaluate_safe_check",
    "evaluate_tactical",
    "normalize_feature_key",
    "normalize_weights",
    "opponent_of",
    "piece_value",
    "resolve_cchef_config",
    "resolve_scales",
    "side_king_risk",
    "side_material",
    "side_threat_value",
    "side_tr_risk",
]

