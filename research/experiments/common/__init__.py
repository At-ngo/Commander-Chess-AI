"""Package `common` dùng chung cho chuỗi notebook thực nghiệm Cờ Tư Lệnh."""

from __future__ import annotations

from .agent_factory import (
    AgentBuilder,
    create_agent,
    is_custom_registered,
    list_configured_agents,
    list_registered_agents,
    normalize_agent_name,
    register_agent,
    resolve_agent_config_id,
)
from .config import (
    COMMON_DIR,
    DEFAULT_AGENT_CONFIGS,
    DEFAULT_CONFIG_PATH,
    DEFAULT_EXPERIMENT_SETTINGS,
    DEFAULT_SEED,
    POPULAR_SEEDS,
    PROJECT_ROOT,
    REQUIRED_CONFIG_KEYS,
    RESULTS_DIR,
    RUNS_DIR,
    deep_merge,
    list_experiments,
    load_experiment_config,
    load_raw_config,
    prepare_run_directory,
    validate_experiment_config,
)
from .data_logger import (
    ExperimentLogger,
    finish_wandb_run,
    init_wandb_run,
    log_wandb_metrics,
    log_wandb_table,
)
from .match_runner import (
    MatchResult,
    MoveRecord,
    compute_state_hash,
    format_action_str,
    run_match,
)
from .metrics import (
    AgentMetricsSummary,
    build_matchup_matrix,
    summarize_agent_matches,
    summarize_pair_results,
    summarize_red_blue_splits,
    summarize_tournament,
)
from .profiling import (
    ProfileResult,
    ProfileScope,
    capture_memory_snapshot,
    profile_callable,
)
from .reproducibility import (
    capture_reproducibility_metadata,
    get_environment_info,
    get_git_revision,
    set_global_seed,
)
from .statistics import (
    bootstrap_confidence_interval,
    sensitivity_analysis,
    wilson_confidence_interval,
)
from .tournament import TournamentResult, run_head_to_head, run_round_robin
from .visualization import (
    plot_decision_time_comparison,
    plot_matchup_heatmap,
    plot_metric_bar,
    plot_sensitivity_curve,
    plot_turn_length_distribution,
    plot_wdl_stacked_bar,
)

__all__ = [
    # config
    "COMMON_DIR",
    "DEFAULT_AGENT_CONFIGS",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_EXPERIMENT_SETTINGS",
    "DEFAULT_SEED",
    "POPULAR_SEEDS",
    "PROJECT_ROOT",
    "REQUIRED_CONFIG_KEYS",
    "RESULTS_DIR",
    "RUNS_DIR",
    "deep_merge",
    "list_experiments",
    "load_experiment_config",
    "load_raw_config",
    "prepare_run_directory",
    "validate_experiment_config",
    # agent_factory
    "AgentBuilder",
    "create_agent",
    "is_custom_registered",
    "list_configured_agents",
    "list_registered_agents",
    "normalize_agent_name",
    "register_agent",
    "resolve_agent_config_id",
    # match_runner & tournament
    "MatchResult",
    "MoveRecord",
    "TournamentResult",
    "compute_state_hash",
    "format_action_str",
    "run_head_to_head",
    "run_match",
    "run_round_robin",
    # metrics & statistics & visualization
    "AgentMetricsSummary",
    "bootstrap_confidence_interval",
    "build_matchup_matrix",
    "plot_decision_time_comparison",
    "plot_matchup_heatmap",
    "plot_metric_bar",
    "plot_sensitivity_curve",
    "plot_turn_length_distribution",
    "plot_wdl_stacked_bar",
    "sensitivity_analysis",
    "summarize_agent_matches",
    "summarize_pair_results",
    "summarize_red_blue_splits",
    "summarize_tournament",
    "wilson_confidence_interval",
    # data_logger & wandb
    "ExperimentLogger",
    "finish_wandb_run",
    "init_wandb_run",
    "log_wandb_metrics",
    "log_wandb_table",
    # profiling & reproducibility
    "ProfileResult",
    "ProfileScope",
    "capture_memory_snapshot",
    "capture_reproducibility_metadata",
    "get_environment_info",
    "get_git_revision",
    "profile_callable",
    "set_global_seed",
]
