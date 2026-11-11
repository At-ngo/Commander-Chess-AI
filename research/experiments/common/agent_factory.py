"""Khởi tạo và đăng ký tác tử AI theo tên và cấu hình thực nghiệm."""

from __future__ import annotations

from copy import deepcopy
import importlib
from typing import Any, Callable

from .config import DEFAULT_AGENT_CONFIGS, DEFAULT_SEED, deep_merge
from .imports import BaseAgent, RandomAgent

AgentBuilder = Callable[..., BaseAgent]

_CUSTOM_REGISTRY: dict[str, AgentBuilder] = {}

_BUILTIN_CANDIDATES: dict[str, tuple[str, str]] = {
    "random": ("agents.random_agent", "RandomAgent"),
    "rules": ("agents.rule_based_agent", "RuleBasedAgent"),
    "heuristic": ("agents.heuristic_agent", "HeuristicAgent"),
    "minimax": ("agents.minimax_agent", "MinimaxAgent"),
    "alphabeta": ("agents.alphabeta_agent", "AlphaBetaAgent"),
    "mcts": ("agents.mcts_agent", "MCTSAgent"),
}

_ALIASES: dict[str, str] = {
    "randomagent": "random",
    "rule_based": "rules",
    "rule_based_agent": "rules",
    "rulebasedagent": "rules",
    "rulesagent": "rules",
    "rules_agent": "rules",
    "heuristicagent": "heuristic",
    "minimaxagent": "minimax",
    "alphabetaagent": "alphabeta",
    "alpha_beta": "alphabeta",
    "mctsagent": "mcts",
}


def normalize_agent_name(name: str) -> str:
    """Chuẩn hóa tên/bí danh của tác tử."""
    key = name.strip().lower().replace("-", "_")
    return _ALIASES.get(key, key)


def register_agent(name: str, builder: AgentBuilder) -> None:
    """Đăng ký lớp hoặc hàm khởi tạo tác tử tùy biến (hữu ích khi thử nghiệm trong notebook)."""
    canonical = normalize_agent_name(name)
    _CUSTOM_REGISTRY[canonical] = builder


def is_custom_registered(name: str) -> bool:
    """Kiểm tra tên agent có dùng builder tùy biến trong `_CUSTOM_REGISTRY` không."""
    return normalize_agent_name(name) in _CUSTOM_REGISTRY


def _resolve_agent_builder(canonical_name: str) -> AgentBuilder:
    if canonical_name in _CUSTOM_REGISTRY:
        return _CUSTOM_REGISTRY[canonical_name]
    if canonical_name == "random":
        return RandomAgent
    if canonical_name in _BUILTIN_CANDIDATES:
        module_path, class_name = _BUILTIN_CANDIDATES[canonical_name]
        try:
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            return cls
        except (ImportError, AttributeError) as exc:
            raise NotImplementedError(
                f"Tác tử '{canonical_name}' ({class_name}) chưa được cài đặt tại `{module_path}`. "
                "Hãy hoàn thiện trong `packages/agents/` hoặc đăng ký qua `register_agent(...)`."
            ) from exc
    raise KeyError(f"Không nhận diện được tên tác tử '{canonical_name}'.")


def resolve_agent_config_id(name: str, config: dict[str, Any] | None = None) -> str:
    """Xác định mã cấu hình chuẩn để ghi nhận vào log moves/games."""
    canonical = normalize_agent_name(name)
    merged = deep_merge(DEFAULT_AGENT_CONFIGS.get(canonical, {}), config or {})
    for key in ("agent_config_id", "weight_config_id", "ruleset_name"):
        if merged.get(key):
            return str(merged[key])
    return canonical


def list_registered_agents() -> list[str]:
    """Liệt kê các tác tử hiện đã có code thực thi sẵn sàng khởi tạo."""
    available: list[str] = []
    for name in sorted(set(_BUILTIN_CANDIDATES) | set(_CUSTOM_REGISTRY)):
        try:
            _resolve_agent_builder(name)
            available.append(name)
        except NotImplementedError:
            pass
    return available


def list_configured_agents() -> list[str]:
    """Liệt kê toàn bộ tên tác tử được định nghĩa trong cấu hình thực nghiệm."""
    return list(DEFAULT_AGENT_CONFIGS.keys())


def create_agent(
    name: str,
    *,
    config: dict[str, Any] | None = None,
    seed: int | None = None,
    instance_name: str | None = None,
) -> BaseAgent:
    """Khởi tạo một instance `BaseAgent` từ tên chuẩn và dict cấu hình."""
    canonical = normalize_agent_name(name)
    builder = _resolve_agent_builder(canonical)

    base_cfg = deepcopy(DEFAULT_AGENT_CONFIGS.get(canonical, {}))
    merged_cfg = deep_merge(base_cfg, config or {})
    merged_cfg.pop("algorithm", None)
    merged_cfg.pop("class_name", None)

    resolved_seed = seed if seed is not None else merged_cfg.pop("seed", DEFAULT_SEED)
    merged_cfg.pop("seed", None)
    agent_label = instance_name or merged_cfg.pop("name", canonical)

    return builder(name=agent_label, seed=resolved_seed, config=merged_cfg)


__all__ = [
    "AgentBuilder",
    "create_agent",
    "is_custom_registered",
    "list_configured_agents",
    "list_registered_agents",
    "normalize_agent_name",
    "register_agent",
    "resolve_agent_config_id",
]
