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
from ..services.engine_adapter import default_engine_adapter, select_smart_ai_action
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

    from ..models.common import Position
    from ..models.enums import ActionType, GameStatus, PieceType, Side, TerminationReason, TurnPhase
    from ..models.game import GameResultDTO
    from ..services.engine_adapter import is_commander_in_check

    if state.turn_phase == TurnPhase.STACK_ACTIVE:
        try:
            end_req = ActionRequest(
                action_type=ActionType.END_TURN,
                piece_id="COMPOUND",
                to_pos=state.compound_origin or Position(x=0, y=0),
                target_piece_id=None,
                state_version=state.state_version,
                is_compound_action=False,
            )
            next_state, _ = default_engine_adapter.apply_action(state, end_req)
            session_store.save(next_state)
            return next_state
        except ValueError:
            pass

    if state.side_to_move == Side.BLUE and state.turn_phase != TurnPhase.STACK_ACTIVE and state.mode.value == "HUMAN_VS_AI":
        # Đã là lượt của AI trong HUMAN_VS_AI, không lật ngược lại lượt của người chơi
        return state

    actor_side = state.side_to_move
    next_side = Side.BLUE if actor_side == Side.RED else Side.RED
    next_state = state.model_copy(
        update={
            "side_to_move": next_side,
            "turn_index": state.turn_index + (1 if actor_side == Side.BLUE else 0),
            "action_index": 1,
            "turn_phase": TurnPhase.NORMAL,
            "state_version": state.state_version + 1,
            "can_end_turn": False,
            "compound_origin": None,
            "compound_member_ids": [],
            "compound_moved_piece_ids": [],
        }
    )
    next_state.legal_actions = default_engine_adapter.get_legal_actions(next_state)

    enemy_has_cmd = any(
        p.is_alive and p.side == next_side and p.type == PieceType.COMMANDER
        for p in next_state.pieces
    )
    if enemy_has_cmd and len(next_state.legal_actions) == 0:
        scores = dict(next_state.scores)
        if is_commander_in_check(next_state.pieces, next_side):
            scores[actor_side.value] = scores.get(actor_side.value, 0) + 50
            result = GameResultDTO(
                winner=actor_side.value,
                reason=TerminationReason.CHECKMATE,
                final_scores=scores,
            )
        else:
            result = GameResultDTO(
                winner="DRAW",
                reason=TerminationReason.STALEMATE,
                final_scores=scores,
            )
        next_state = next_state.model_copy(
            update={
                "status": GameStatus.GAME_OVER,
                "side_to_move": actor_side,
                "scores": scores,
                "result": result,
            }
        )

    session_store.save(next_state)
    return next_state


@router.post("/{game_id}/ai-step", response_model=ActionResponse)
def ai_step(game_id: str, request: AiStepRequest) -> ActionResponse:
    """Kích hoạt một bước đi của AI từ các nước hợp lệ (gồm cả tổ hợp cõng quân)"""
    state = session_store.get(game_id)
    if not state:
        raise HTTPException(
            status_code=404,
            detail={"code": "GAME_NOT_FOUND", "message": f"Không tìm thấy ván đấu '{game_id}'"},
        )

    if state.status.value == "GAME_OVER":
        raise HTTPException(
            status_code=409,
            detail={"code": "GAME_ALREADY_OVER", "message": "Ván đấu đã kết thúc, AI không thể đi."},
        )

    from ..models.enums import ActionType, Side, TurnPhase
    # Trong chế độ HUMAN_VS_AI: AI luôn điều khiển phe BLUE
    ai_side = Side.BLUE if state.mode.value == "HUMAN_VS_AI" else state.side_to_move
    if state.mode.value == "HUMAN_VS_AI" and state.side_to_move != Side.BLUE:
        # Tự động đồng bộ lượt về BLUE cho AI nếu backend bị lệch lượt
        state = state.model_copy(
            update={
                "side_to_move": Side.BLUE,
                "turn_phase": TurnPhase.NORMAL,
                "can_end_turn": False,
                "compound_origin": None,
                "compound_member_ids": [],
                "compound_moved_piece_ids": [],
            }
        )
        state.legal_actions = default_engine_adapter.get_legal_actions(state)
        session_store.save(state)

    try:
        from agents import RandomAgent
        agent = RandomAgent(name="RandomAgent")
        chosen_action = select_smart_ai_action(state, ai_side, rng=agent.rng)
    except Exception:
        chosen_action = select_smart_ai_action(state, ai_side)

    if not chosen_action:
        raise HTTPException(
            status_code=409,
            detail={"code": "NO_LEGAL_ACTIONS", "message": f"Không còn nước đi hợp lệ cho phe {ai_side.value}."},
        )

    if chosen_action.action_type == ActionType.END_TURN:
        action_req = ActionRequest(
            action_type=ActionType.END_TURN,
            piece_id="COMPOUND",
            to_pos=chosen_action.to_pos,
            target_piece_id=None,
            state_version=state.state_version,
            carry_cargo=True,
            is_compound_action=False,
        )
    else:
        action_req = ActionRequest(
            action_type=chosen_action.action_type,
            piece_id=chosen_action.piece_id,
            to_pos=chosen_action.to_pos,
            target_piece_id=chosen_action.target_piece_id,
            state_version=state.state_version,
            carry_cargo=chosen_action.carry_cargo,
            is_compound_action=(state.turn_phase == TurnPhase.STACK_ACTIVE),
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
