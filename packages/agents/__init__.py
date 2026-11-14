# packages/agents/__init__.py
"""Gói tác tử AI cho Cờ Tư Lệnh (Commander Chess AI)."""

from .base import (
    AgentAction,
    AgentDecision,
    AgentError,
    BaseAgent,
    InvalidActionReturnedError,
    NoLegalActionsError,
    format_action_str,
)
from .random_agent import RandomAgent

__all__ = [
    "AgentAction",
    "AgentDecision",
    "AgentError",
    "BaseAgent",
    "InvalidActionReturnedError",
    "NoLegalActionsError",
    "RandomAgent",
    "format_action_str",
]

try:
    from .rule_based_agent import RuleBasedAgent, RulesAgent
except ImportError:
    pass
else:
    __all__.extend(["RuleBasedAgent", "RulesAgent"])

try:
    from .evaluation import CCHEFEvaluator, DEFAULT_CCHEF_WEIGHTS, FEATURE_NAMES
    from .heuristic_agent import HeuristicAgent
except ImportError:
    pass
else:
    __all__.extend(["CCHEFEvaluator", "DEFAULT_CCHEF_WEIGHTS", "FEATURE_NAMES", "HeuristicAgent"])

try:
    from .minimax_agent import DEFAULT_MINIMAX_EVALUATOR_CFG, MinimaxAgent
    from .tree_exporter import (
        export_minimax_tree_json,
        export_minimax_tree_to_dict,
        plot_minimax_tree_from_json,
    )
except ImportError:
    pass
else:
    __all__.extend([
        "DEFAULT_MINIMAX_EVALUATOR_CFG",
        "MinimaxAgent",
        "export_minimax_tree_json",
        "export_minimax_tree_to_dict",
        "plot_minimax_tree_from_json",
    ])
