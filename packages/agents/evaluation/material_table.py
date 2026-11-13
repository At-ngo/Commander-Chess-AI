# packages/agents/evaluation/material_table.py
"""Bảng giá trị quân CCHEF chính thức (F1): Sở chỉ huy = 10đ, Tư lệnh không quy đổi tĩnh."""

from __future__ import annotations

from commander_game_engine.game_state import Piece, PieceType

# Xác nhận từ Project Owner: Sở chỉ huy = 10 điểm; Tư lệnh = 0 điểm tĩnh (xử lý qua ±W).
CCHEF_BASE_POINTS: dict[PieceType, float] = {
    PieceType.COMMANDER: 0.0,
    PieceType.HEADQUARTERS: 10.0,
    PieceType.INFANTRY: 10.0,
    PieceType.ANTI_AIRCRAFT: 10.0,
    PieceType.MILITIA: 10.0,
    PieceType.ENGINEER: 10.0,
    PieceType.TANK: 20.0,
    PieceType.MISSILE: 20.0,
    PieceType.ARTILLERY: 30.0,
    PieceType.AIRCRAFT: 40.0,
    PieceType.NAVY: 80.0,
}

HERO_BONUS: float = 10.0


def piece_value(piece: Piece) -> float:
    """Giá trị CCHEF V(u, s) = V_base(u) + 10 * 1_hero(u, s)."""
    return CCHEF_BASE_POINTS[piece.piece_type] + (HERO_BONUS if piece.is_heroic else 0.0)


__all__ = ["CCHEF_BASE_POINTS", "HERO_BONUS", "piece_value"]

