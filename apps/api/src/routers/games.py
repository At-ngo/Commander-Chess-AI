"""
Commander Chess AI — Game Session Routes
Aligned with docs/API_CONTRACT.md Section 3.3
"""

import uuid
import random
from fastapi import APIRouter, HTTPException, status

from ..models.game import (
    GameState,
    CreateGameRequest,
    ActionRequest,
    ActionResponse,
    EndTurnRequest,
    AiStepRequest,
    ResignRequest,
    DrawRequest,
)
from ..services.engine_adapter import default_engine_adapter
from ..services.game_session_store import session_store

router = APIRouter(prefix="/games", tags=["Games"])


@router.post("", response_model=GameState, status_code=status.HTTP_201_CREATED)
def create_game(request: CreateGameRequest) -> GameState:
    """Khởi tạo một ván cờ mới (Người vs AI, AI vs AI, hoặc Người vs Người)"""
    game_id = f"game_{uuid.uuid4().hex[:12]}"
    state = default_engine_adapter.create_initial_state(game_id=game_id, mode=request.mode)
    session_store.save(state)
    return state


@router.get("/{game_id}", response_model=GameState)
def get_game(game_id: str) -> GameState:
    """Truy vấn trạng thái hiện tại của phiên chơi"""
    state = session_store.get(game_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail={"code": "GAME_NOT_FOUND", "message": f"Không tìm thấy ván đấu '{game_id}'"},
        )
    return state


@router.post("/{game_id}/actions", response_model=ActionResponse)
def execute_action(game_id: str, request: ActionRequest) -> ActionResponse:
    """Gửi và thực thi một hành động (di chuyển, ăn quân, cõng quân)"""
    state = session_store.get(game_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail={"code": "GAME_NOT_FOUND", "message": f"Không tìm thấy ván đấu '{game_id}'"},
        )

    if state.status.value == "GAME_OVER":
        raise HTTPException(
            status_code=409,
            detail={"code": "GAME_ALREADY_OVER", "message": "Ván đấu đã kết thúc, không thể thực hiện thêm nước đi."},
        )

    try:
        next_state, event = default_engine_adapter.apply_action(state, request)
        session_store.save(next_state)
        return ActionResponse(
            state_version=next_state.state_version,
            event=event,
            game_state=next_state,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=409,
            detail={"code": "ILLEGAL_ACTION", "message": str(e)},
        )


@router.post("/{game_id}/end-turn", response_model=GameState)
def end_turn(game_id: str, request: EndTurnRequest) -> GameState:
    """Chủ động kết thúc sớm lượt tổ hợp cõng quân"""
    state = session_store.get(game_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail={"code": "GAME_NOT_FOUND", "message": f"Không tìm thấy ván đấu '{game_id}'"},
        )

    # Chuyển lượt sang phe đối diện
    from ..models.enums import Side
    next_side = Side.BLUE if state.side_to_move == Side.RED else Side.RED
    next_state = state.model_copy(
        update={
            "side_to_move": next_side,
            "turn_index": state.turn_index + (1 if state.side_to_move == Side.BLUE else 0),
            "action_index": 1,
            "state_version": state.state_version + 1,
            "can_end_turn": False,
        }
    )
    next_state.legal_actions = default_engine_adapter.get_legal_actions(next_state)
    session_store.save(next_state)
    return next_state


@router.post("/{game_id}/ai-step", response_model=ActionResponse)
def ai_step(game_id: str, request: AiStepRequest) -> ActionResponse:
    """Kích hoạt một bước đi của AI từ các nước hợp lệ"""
    state = session_store.get(game_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail={"code": "GAME_NOT_FOUND", "message": f"Không tìm thấy ván đấu '{game_id}'"},
        )

    if not state.legal_actions:
        raise HTTPException(
            status_code=409,
            detail={"code": "NO_LEGAL_ACTIONS", "message": "Không còn nước đi hợp lệ cho phe hiện tại."},
        )

    # Chọn ngẫu nhiên trong tập nước hợp lệ (Baseline Random Agent)
    chosen_action = random.choice(state.legal_actions)
    action_req = ActionRequest(
        action_type=chosen_action.action_type,
        piece_id=chosen_action.piece_id,
        to_pos=chosen_action.to_pos,
        target_piece_id=chosen_action.target_piece_id,
        state_version=state.state_version,
    )
    next_state, event = default_engine_adapter.apply_action(state, action_req)
    session_store.save(next_state)
    return ActionResponse(
        state_version=next_state.state_version,
        event=event,
        game_state=next_state,
    )


@router.post("/{game_id}/resign", response_model=GameState)
def resign_game(game_id: str, request: ResignRequest) -> GameState:
    """Người chơi hoặc tác tử đầu hàng"""
    state = session_store.get(game_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail={"code": "GAME_NOT_FOUND", "message": f"Không tìm thấy ván đấu '{game_id}'"},
        )

    next_state = default_engine_adapter.resign(state, request.side)
    session_store.save(next_state)
    return next_state


@router.post("/{game_id}/draw", response_model=GameState)
def draw_game(game_id: str, request: DrawRequest) -> GameState:
    """Đề nghị hoặc chấp thuận hòa ván đấu"""
    state = session_store.get(game_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail={"code": "GAME_NOT_FOUND", "message": f"Không tìm thấy ván đấu '{game_id}'"},
        )

    next_state = default_engine_adapter.draw(state)
    session_store.save(next_state)
    return next_state
