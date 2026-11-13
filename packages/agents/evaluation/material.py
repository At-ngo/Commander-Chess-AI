# packages/agents/evaluation/material.py
"""F1 — Material: Giá trị quân cờ, quân Anh hùng (+10đ) và toàn bộ quân đang được chở."""

from __future__ import annotations

from commander_game_engine.game_state import Player

from .context import EvalContext, opponent_of
from .material_table import piece_value


def side_material(ctx: EvalContext, side: Player) -> float:
    """Tổng điểm vật chất ∑ V(u, s) cho mọi quân còn sống của `side` (gồm cả quân đang được chở)."""
    total = 0.0
    for p in ctx.pieces_by_player[side]:
        total += piece_value(p)
    return total


def evaluate_material(ctx: EvalContext, perspective: Player) -> float:
    """Đặc trưng đối xứng M(s, p) = Material(p) - Material(opp(p))."""
    opp = opponent_of(perspective)
    return side_material(ctx, perspective) - side_material(ctx, opp)


__all__ = ["evaluate_material", "side_material"]

