"""
Commander Chess AI — Replay Routes
Aligned with docs/API_CONTRACT.md Section 3.4
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query

from ..models.replay import ReplaySummary, ReplayListResponse, ReplayExportResponse
from ..models.enums import GameMode

router = APIRouter(prefix="/replays", tags=["Replays"])

# Initial in-memory replay fixture
REPLAY_FIXTURES: List[ReplaySummary] = [
    ReplaySummary(
        replay_id="rep_sample_001",
        game_id="game_sample_001",
        date="2026-10-26",
        mode=GameMode.HUMAN_VS_AI,
        red_player="Human Commander",
        blue_player="Random Tactical Agent",
        winner="RED",
        total_turns=12,
        total_moves=24,
    )
]


@router.get("", response_model=ReplayListResponse)
def list_replays(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    winner: Optional[str] = None,
) -> ReplayListResponse:
    """Lấy danh sách các ván đấu đã được lưu trong hệ thống"""
    filtered = REPLAY_FIXTURES
    if winner:
        filtered = [r for r in filtered if r.winner == winner]
    
    start_idx = (page - 1) * page_size
    items = filtered[start_idx : start_idx + page_size]
    return ReplayListResponse(
        total=len(filtered),
        page=page,
        page_size=page_size,
        items=items,
    )


@router.get("/{replay_id}", response_model=ReplaySummary)
def get_replay(replay_id: str) -> ReplaySummary:
    """Lấy thông tin chi tiết của một bản ghi ván đấu"""
    replay = next((r for r in REPLAY_FIXTURES if r.replay_id == replay_id), None)
    if not replay:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPLAY_NOT_FOUND", "message": f"Không tìm thấy ván đấu '{replay_id}'"},
        )
    return replay


@router.post("/{replay_id}/export", response_model=ReplayExportResponse)
def export_replay(replay_id: str) -> ReplayExportResponse:
    """Xuất biên bản ký pháp chuẩn COTULENH-NOTATION theo MOVE_NOTATION.md"""
    replay = next((r for r in REPLAY_FIXTURES if r.replay_id == replay_id), None)
    if not replay:
        raise HTTPException(
            status_code=404,
            detail={"code": "REPLAY_NOT_FOUND", "message": f"Không tìm thấy ván đấu '{replay_id}'"},
        )

    content = (
        f'[Format "COTULENH-NOTATION"]\n'
        f'[Version "1.1"]\n'
        f'[Date "{replay.date}"]\n'
        f'[Mode "{replay.mode.value}"]\n'
        f'[Red "{replay.red_player}"]\n'
        f'[Blue "{replay.blue_player}"]\n'
        f'[Result "{replay.winner}"]\n'
        f'[TotalMoves "{replay.total_moves}"]\n'
        f'\n'
        f'1. Đỏ:  H [1 ; 1] _ [5 ; 1]\n'
        f'   Xanh: K [10 ; 8] _ [8 ; 6]\n'
    )
    return ReplayExportResponse(format="COTULENH-NOTATION", content=content)
