"""
Commander Chess AI — Engine Adapter Interface & Mock Implementation
[MOCK ADAPTER - FOR API SCAFFOLDING & INTEGRATION]

NOTE (AGENTS.md Rule 3 & 6):
The authoritative game rules and state transitions belong solely to
packages/game-engine (managed by the Project Owner / Student).
This adapter defines the clean dependency injection boundary:
- When packages/game-engine is implemented, AuthoritativeEngineAdapter
  will replace this mock without breaking any API routes or UI contracts.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Dict
import uuid
import time

from ..models.enums import (
    Side,
    PieceType,
    ActionType,
    EventType,
    GameMode,
    GameStatus,
    TurnPhase,
    TerminationReason,
)
from ..models.common import Position
from ..models.game import (
    PieceState,
    LegalAction,
    GameEvent,
    GameState,
    GameResultDTO,
    ActionRequest,
)

PIECE_NOTATION_SYMBOL: Dict[PieceType, str] = {
    PieceType.COMMANDER: "⋆",
    PieceType.MISSILE: "L",
    PieceType.HEADQUARTERS: "S",
    PieceType.TANK: "T",
    PieceType.AIRCRAFT: "K",
    PieceType.INFANTRY: "B",
    PieceType.NAVY: "H",
    PieceType.ANTI_AIR: "F",
    PieceType.ENGINEER: "C",
    PieceType.MILITIA: "D",
    PieceType.ARTILLERY: "A",
}

PIECE_SCORES: Dict[PieceType, int] = {
    PieceType.COMMANDER: 50,
    PieceType.HEADQUARTERS: 100,
    PieceType.AIRCRAFT: 40,
    PieceType.NAVY: 80,
    PieceType.MISSILE: 20,
    PieceType.TANK: 30,
    PieceType.ARTILLERY: 30,
    PieceType.ANTI_AIR: 10,
    PieceType.ENGINEER: 10,
    PieceType.INFANTRY: 10,
    PieceType.MILITIA: 10,
}


class BaseEngineAdapter(ABC):
    @abstractmethod
    def create_initial_state(self, game_id: str, mode: GameMode) -> GameState:
        pass

    @abstractmethod
    def get_legal_actions(self, state: GameState) -> List[LegalAction]:
        pass

    @abstractmethod
    def apply_action(self, state: GameState, request: ActionRequest) -> Tuple[GameState, GameEvent]:
        pass

    @abstractmethod
    def resign(self, state: GameState, side: Side) -> GameState:
        pass

    @abstractmethod
    def draw(self, state: GameState) -> GameState:
        pass


class MockEngineAdapter(BaseEngineAdapter):
    """
    Mock Adapter implementing standard movement & capture rules for API tests
    until packages/game-engine is integrated.
    """

    def _get_initial_pieces(self) -> List[PieceState]:
        pieces: List[PieceState] = []
        
        # Red side (19 pieces)
        pieces.append(PieceState(piece_id="red_commander_1", side=Side.RED, type=PieceType.COMMANDER, position=Position(x=6, y=0)))
        pieces.append(PieceState(piece_id="red_aircraft_1", side=Side.RED, type=PieceType.AIRCRAFT, position=Position(x=4, y=1)))
        pieces.append(PieceState(piece_id="red_aircraft_2", side=Side.RED, type=PieceType.AIRCRAFT, position=Position(x=8, y=1)))
        pieces.append(PieceState(piece_id="red_headquarters_1", side=Side.RED, type=PieceType.HEADQUARTERS, position=Position(x=5, y=1)))
        pieces.append(PieceState(piece_id="red_headquarters_2", side=Side.RED, type=PieceType.HEADQUARTERS, position=Position(x=7, y=1)))
        pieces.append(PieceState(piece_id="red_missile_1", side=Side.RED, type=PieceType.MISSILE, position=Position(x=6, y=2)))
        pieces.append(PieceState(piece_id="red_artillery_1", side=Side.RED, type=PieceType.ARTILLERY, position=Position(x=3, y=2)))
        pieces.append(PieceState(piece_id="red_artillery_2", side=Side.RED, type=PieceType.ARTILLERY, position=Position(x=9, y=2)))
        pieces.append(PieceState(piece_id="red_anti_air_1", side=Side.RED, type=PieceType.ANTI_AIR, position=Position(x=4, y=3)))
        pieces.append(PieceState(piece_id="red_anti_air_2", side=Side.RED, type=PieceType.ANTI_AIR, position=Position(x=8, y=3)))
        pieces.append(PieceState(piece_id="red_navy_1", side=Side.RED, type=PieceType.NAVY, position=Position(x=0, y=1)))
        pieces.append(PieceState(piece_id="red_navy_2", side=Side.RED, type=PieceType.NAVY, position=Position(x=2, y=3)))
        pieces.append(PieceState(piece_id="red_tank_1", side=Side.RED, type=PieceType.TANK, position=Position(x=4, y=2)))
        pieces.append(PieceState(piece_id="red_tank_2", side=Side.RED, type=PieceType.TANK, position=Position(x=8, y=2)))
        pieces.append(PieceState(piece_id="red_engineer_1", side=Side.RED, type=PieceType.ENGINEER, position=Position(x=5, y=4)))
        pieces.append(PieceState(piece_id="red_engineer_2", side=Side.RED, type=PieceType.ENGINEER, position=Position(x=7, y=4)))
        pieces.append(PieceState(piece_id="red_infantry_1", side=Side.RED, type=PieceType.INFANTRY, position=Position(x=3, y=4)))
        pieces.append(PieceState(piece_id="red_infantry_2", side=Side.RED, type=PieceType.INFANTRY, position=Position(x=9, y=4)))
        pieces.append(PieceState(piece_id="red_militia_1", side=Side.RED, type=PieceType.MILITIA, position=Position(x=6, y=3)))

        # Blue side (19 pieces) - Mirrored deployment
        pieces.append(PieceState(piece_id="blue_commander_1", side=Side.BLUE, type=PieceType.COMMANDER, position=Position(x=6, y=11)))
        pieces.append(PieceState(piece_id="blue_aircraft_1", side=Side.BLUE, type=PieceType.AIRCRAFT, position=Position(x=4, y=10)))
        pieces.append(PieceState(piece_id="blue_aircraft_2", side=Side.BLUE, type=PieceType.AIRCRAFT, position=Position(x=8, y=10)))
        pieces.append(PieceState(piece_id="blue_headquarters_1", side=Side.BLUE, type=PieceType.HEADQUARTERS, position=Position(x=5, y=10)))
        pieces.append(PieceState(piece_id="blue_headquarters_2", side=Side.BLUE, type=PieceType.HEADQUARTERS, position=Position(x=7, y=10)))
        pieces.append(PieceState(piece_id="blue_missile_1", side=Side.BLUE, type=PieceType.MISSILE, position=Position(x=6, y=9)))
        pieces.append(PieceState(piece_id="blue_artillery_1", side=Side.BLUE, type=PieceType.ARTILLERY, position=Position(x=3, y=9)))
        pieces.append(PieceState(piece_id="blue_artillery_2", side=Side.BLUE, type=PieceType.ARTILLERY, position=Position(x=9, y=9)))
        pieces.append(PieceState(piece_id="blue_anti_air_1", side=Side.BLUE, type=PieceType.ANTI_AIR, position=Position(x=4, y=8)))
        pieces.append(PieceState(piece_id="blue_anti_air_2", side=Side.BLUE, type=PieceType.ANTI_AIR, position=Position(x=8, y=8)))
        pieces.append(PieceState(piece_id="blue_navy_1", side=Side.BLUE, type=PieceType.NAVY, position=Position(x=0, y=10)))
        pieces.append(PieceState(piece_id="blue_navy_2", side=Side.BLUE, type=PieceType.NAVY, position=Position(x=2, y=8)))
        pieces.append(PieceState(piece_id="blue_tank_1", side=Side.BLUE, type=PieceType.TANK, position=Position(x=4, y=9)))
        pieces.append(PieceState(piece_id="blue_tank_2", side=Side.BLUE, type=PieceType.TANK, position=Position(x=8, y=9)))
        pieces.append(PieceState(piece_id="blue_engineer_1", side=Side.BLUE, type=PieceType.ENGINEER, position=Position(x=5, y=7)))
        pieces.append(PieceState(piece_id="blue_engineer_2", side=Side.BLUE, type=PieceType.ENGINEER, position=Position(x=7, y=7)))
        pieces.append(PieceState(piece_id="blue_infantry_1", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=3, y=7)))
        pieces.append(PieceState(piece_id="blue_infantry_2", side=Side.BLUE, type=PieceType.INFANTRY, position=Position(x=9, y=7)))
        pieces.append(PieceState(piece_id="blue_militia_1", side=Side.BLUE, type=PieceType.MILITIA, position=Position(x=6, y=8)))

        return pieces

    def create_initial_state(self, game_id: str, mode: GameMode) -> GameState:
        pieces = self._get_initial_pieces()
        state = GameState(
            game_id=game_id,
            mode=mode,
            status=GameStatus.IN_PROGRESS,
            side_to_move=Side.RED,
            turn_index=1,
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=1,
            scores={"RED": 0, "BLUE": 0},
            remaining_time_ms={"RED": 1800000, "BLUE": 1800000},
            pieces=pieces,
            legal_actions=[],
            can_end_turn=False,
            last_event=None,
            result=None,
        )
        state.legal_actions = self.get_legal_actions(state)
        return state

    def get_legal_actions(self, state: GameState) -> List[LegalAction]:
        if state.status == GameStatus.GAME_OVER:
            return []

        active_side = state.side_to_move
        actions: List[LegalAction] = []
        piece_map = {(p.position.x, p.position.y): p for p in state.pieces if p.is_alive}

        for piece in state.pieces:
            if not piece.is_alive or piece.side != active_side:
                continue
            if piece.type == PieceType.HEADQUARTERS:
                continue

            x, y = piece.position.x, piece.position.y
            symbol = PIECE_NOTATION_SYMBOL.get(piece.type, "B")

            # Basic directional moves (ortho 1 step)
            for dx, dy in [(0, 1), (0, -1), (-1, 0), (1, 0)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx <= 10 and 0 <= ny <= 11:
                    target = piece_map.get((nx, ny))
                    if not target:
                        actions.append(
                            LegalAction(
                                action_id=f"act_{piece.piece_id}_{nx}_{ny}_move",
                                action_type=ActionType.MOVE,
                                piece_id=piece.piece_id,
                                from_pos=Position(x=x, y=y),
                                to_pos=Position(x=nx, y=ny),
                                target_piece_id=None,
                                notation=f"{symbol} [{y} ; {x}] _ [{ny} ; {nx}]",
                                description=f"{piece.type.value} di chuyển đến [{ny} ; {nx}]",
                            )
                        )
                    elif target.side != active_side:
                        target_sym = PIECE_NOTATION_SYMBOL.get(target.type, "B")
                        actions.append(
                            LegalAction(
                                action_id=f"act_{piece.piece_id}_{target.piece_id}_cap",
                                action_type=ActionType.CAPTURE_REPLACE,
                                piece_id=piece.piece_id,
                                from_pos=Position(x=x, y=y),
                                to_pos=Position(x=nx, y=ny),
                                target_piece_id=target.piece_id,
                                notation=f"{symbol} [{y} ; {x}] @ {target_sym} [{ny} ; {nx}]",
                                description=f"{piece.type.value} tấn công {target.type.value} tại [{ny} ; {nx}]",
                            )
                        )
        return actions

    def apply_action(self, state: GameState, request: ActionRequest) -> Tuple[GameState, GameEvent]:
        # Validate optimistic locking
        if request.state_version != state.state_version:
            raise ValueError(f"State version mismatch: expected {state.state_version}, got {request.state_version}")

        actor = next((p for p in state.pieces if p.piece_id == request.piece_id and p.is_alive), None)
        if not actor:
            raise ValueError(f"Piece {request.piece_id} not found or not alive")
        if actor.side != state.side_to_move:
            raise ValueError(f"Piece {request.piece_id} does not belong to active side {state.side_to_move}")

        captured_piece: Optional[PieceState] = None
        new_pieces: List[PieceState] = []
        score_delta = {Side.RED: 0, Side.BLUE: 0}

        for p in state.pieces:
            if request.target_piece_id and p.piece_id == request.target_piece_id:
                p_copy = p.model_copy(update={"is_alive": False})
                captured_piece = p_copy
                score_val = PIECE_SCORES.get(p.type, 10)
                score_delta[actor.side] += score_val
                new_pieces.append(p_copy)
            elif p.piece_id == request.piece_id:
                if request.action_type == ActionType.CAPTURE_STAND:
                    new_pieces.append(p)
                else:
                    new_pieces.append(p.model_copy(update={"position": request.to_pos}))
            else:
                new_pieces.append(p)

        # Generate event
        actor_sym = PIECE_NOTATION_SYMBOL.get(actor.type, "B")
        from_not = f"[{actor.position.y} ; {actor.position.x}]"
        to_not = f"[{request.to_pos.y} ; {request.to_pos.x}]"

        if captured_piece:
            act_sym = "_@_" if request.action_type == ActionType.CAPTURE_STAND else "@"
            target_sym = PIECE_NOTATION_SYMBOL.get(captured_piece.type, "B")
            notation = f"{actor_sym} {from_not} {act_sym} {target_sym} {to_not}"
            evt_type = EventType.PIECE_CAPTURED
        else:
            notation = f"{actor_sym} {from_not} _ {to_not}"
            evt_type = EventType.PIECE_MOVED

        event = GameEvent(
            event_id=f"evt_{int(time.time() * 1000)}",
            event_type=evt_type,
            actor_id=actor.piece_id,
            target_id=captured_piece.piece_id if captured_piece else None,
            notation=notation,
            score_delta=score_delta,
            details={"action_type": request.action_type.value},
        )

        # Update scores
        new_scores = {
            "RED": state.scores["RED"] + score_delta[Side.RED],
            "BLUE": state.scores["BLUE"] + score_delta[Side.BLUE],
        }

        # Check terminal condition: Commander captured!
        game_over = False
        result = None
        if captured_piece and captured_piece.type == PieceType.COMMANDER:
            game_over = True
            result = GameResultDTO(
                winner=actor.side.value,
                reason=TerminationReason.COMMANDER_CAPTURED,
                final_scores=new_scores,
            )

        next_side = Side.BLUE if actor.side == Side.RED else Side.RED
        new_status = GameStatus.GAME_OVER if game_over else GameStatus.IN_PROGRESS

        next_state = GameState(
            game_id=state.game_id,
            mode=state.mode,
            status=new_status,
            side_to_move=next_side if not game_over else actor.side,
            turn_index=state.turn_index + (1 if actor.side == Side.BLUE else 0),
            action_index=1,
            turn_phase=TurnPhase.NORMAL,
            state_version=state.state_version + 1,
            scores=new_scores,
            remaining_time_ms=state.remaining_time_ms,
            pieces=new_pieces,
            legal_actions=[],
            can_end_turn=False,
            last_event=event,
            result=result,
        )
        next_state.legal_actions = self.get_legal_actions(next_state)
        return next_state, event

    def resign(self, state: GameState, side: Side) -> GameState:
        winner = Side.BLUE if side == Side.RED else Side.RED
        result = GameResultDTO(
            winner=winner.value,
            reason=TerminationReason.RESIGNATION,
            final_scores=state.scores,
        )
        return state.model_copy(
            update={
                "status": GameStatus.GAME_OVER,
                "state_version": state.state_version + 1,
                "result": result,
                "legal_actions": [],
            }
        )

    def draw(self, state: GameState) -> GameState:
        result = GameResultDTO(
            winner="DRAW",
            reason=TerminationReason.MUTUAL_DRAW,
            final_scores=state.scores,
        )
        return state.model_copy(
            update={
                "status": GameStatus.GAME_OVER,
                "state_version": state.state_version + 1,
                "result": result,
                "legal_actions": [],
            }
        )


default_engine_adapter = MockEngineAdapter()
