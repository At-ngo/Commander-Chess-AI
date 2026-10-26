"""
Commander Chess AI — Replay Models
Aligned with docs/API_CONTRACT.md Section 3.4
"""

from typing import List, Optional
from pydantic import BaseModel, Field
from .enums import GameMode


class ReplaySummary(BaseModel):
    replay_id: str
    game_id: str
    date: str
    mode: GameMode
    red_player: str
    blue_player: str
    winner: str
    total_turns: int
    total_moves: int


class ReplayListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[ReplaySummary]


class ReplayExportResponse(BaseModel):
    format: str = "COTULENH-NOTATION"
    content: str
