"""Tập hợp các import thường dùng (stdlib, khoa học dữ liệu, thống kê, profiling, wandb, Game Engine, Agents)."""

from __future__ import annotations

from collections import Counter, defaultdict
from copy import deepcopy
import csv
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import random
import statistics
import subprocess
import sys
import time
import tracemalloc
from typing import Any, Callable, Iterable, Optional, Sequence
import warnings

# ---------------------------------------------------------------------------
# 1. Định vị thư mục gốc dự án và cấu hình sys.path
# ---------------------------------------------------------------------------
_HERE = Path(__file__).resolve()
PROJECT_ROOT = next(
    (p for p in (_HERE, *_HERE.parents) if (p / "packages").is_dir() and (p / "research").is_dir()),
    None,
)
if PROJECT_ROOT is None:
    raise FileNotFoundError("Không tìm thấy thư mục gốc dự án chứa `packages/` và `research/`.")

PACKAGES_DIR = PROJECT_ROOT / "packages"
EXPERIMENTS_DIR = PROJECT_ROOT / "research" / "experiments"
COMMON_DIR = EXPERIMENTS_DIR / "common"
RESULTS_DIR = PROJECT_ROOT / "research" / "results"
RUNS_DIR = PROJECT_ROOT / "research" / "runs"

for _path in (PACKAGES_DIR, EXPERIMENTS_DIR):
    _path_str = str(_path)
    if _path_str not in sys.path:
        sys.path.insert(0, _path_str)

# ---------------------------------------------------------------------------
# 2. Thư viện khoa học dữ liệu, thống kê, trực quan hóa, kiểm thử & tracking
# ---------------------------------------------------------------------------
from dotenv import load_dotenv
import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import psutil
import pytest
import scipy
from scipy import stats
import seaborn as sns
import statsmodels
import statsmodels.api as sm
from statsmodels.stats.proportion import proportion_confint
from tqdm.auto import tqdm, trange
import wandb
import yaml

HAS_WANDB = True

try:
    import torch
except ImportError:
    torch = None  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# 3. Commander Game Engine & Agents
# ---------------------------------------------------------------------------
from commander_game_engine import rules
from commander_game_engine.actions import (
    ActionType,
    AtomicAction,
    CompoundAction,
    TurnCommand,
    TurnCommandType,
)
from commander_game_engine.board import Board, EdgeType, Position, Terrain
from commander_game_engine.engine import (
    PIECE_POINTS,
    EngineEvent,
    EngineEventType,
    EngineResult,
    apply_action,
    preview_action,
    preview_action_safety,
)
from commander_game_engine.game_state import (
    CompoundTurnState,
    GameState,
    GameStatus,
    Piece,
    PieceType,
    Player,
)
from commander_game_engine.initial_setup import (
    EXPECTED_COUNTS,
    INITIAL_POSITIONS,
    create_initial_state,
)
from commander_game_engine.move_generator import (
    generate_legal_actions,
    generate_piece_actions,
    has_legal_action,
)
from agents import (
    AgentDecision,
    AgentError,
    BaseAgent,
    InvalidActionReturnedError,
    NoLegalActionsError,
    RandomAgent,
)

try:
    from agents import HeuristicAgent
except ImportError:
    HeuristicAgent = None  # type: ignore[assignment,misc]

try:
    from agents import RuleBasedAgent, RulesAgent
except ImportError:
    RuleBasedAgent = None  # type: ignore[assignment,misc]
    RulesAgent = None  # type: ignore[assignment,misc]

DEFAULT_SEED = 2026


__all__ = [
    # Stdlib
    "Any",
    "Callable",
    "Counter",
    "Iterable",
    "Optional",
    "Path",
    "Sequence",
    "asdict",
    "csv",
    "dataclass",
    "datetime",
    "deepcopy",
    "defaultdict",
    "field",
    "hashlib",
    "importlib",
    "json",
    "math",
    "os",
    "random",
    "statistics",
    "subprocess",
    "sys",
    "time",
    "timezone",
    "tracemalloc",
    "warnings",
    # Paths & defaults
    "PROJECT_ROOT",
    "PACKAGES_DIR",
    "EXPERIMENTS_DIR",
    "COMMON_DIR",
    "RESULTS_DIR",
    "RUNS_DIR",
    "DEFAULT_SEED",
    # Data science / Stats / Viz / Config / Profiling / Testing / Tracking
    "matplotlib",
    "plt",
    "np",
    "pd",
    "sns",
    "scipy",
    "stats",
    "statsmodels",
    "sm",
    "proportion_confint",
    "psutil",
    "tqdm",
    "trange",
    "pytest",
    "yaml",
    "load_dotenv",
    "wandb",
    "HAS_WANDB",
    "torch",
    # Game Engine & Rules
    "ActionType",
    "AtomicAction",
    "Board",
    "CompoundAction",
    "CompoundTurnState",
    "EXPECTED_COUNTS",
    "EdgeType",
    "EngineEvent",
    "EngineEventType",
    "EngineResult",
    "GameState",
    "GameStatus",
    "INITIAL_POSITIONS",
    "PIECE_POINTS",
    "Piece",
    "PieceType",
    "Player",
    "Position",
    "Terrain",
    "TurnCommand",
    "TurnCommandType",
    "apply_action",
    "create_initial_state",
    "generate_legal_actions",
    "generate_piece_actions",
    "has_legal_action",
    "preview_action",
    "preview_action_safety",
    "rules",
    # Agents
    "AgentDecision",
    "AgentError",
    "BaseAgent",
    "HeuristicAgent",
    "InvalidActionReturnedError",
    "NoLegalActionsError",
    "RandomAgent",
    "RuleBasedAgent",
    "RulesAgent",
]
