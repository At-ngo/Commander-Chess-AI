"""
Commander Chess AI — Game Data Models & Schemas
Aligned with docs/API_CONTRACT.md Section 2.2 and Section 3.3
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from .enums import (
    Side,
    PieceType,
    ActionType,
    EventType,
    GameMode,
    GameStatus,
    TurnPhase,
    TerminationReason,
)
from .common import Position


class PieceState(BaseModel):
    """Trạng thái chi tiết của một quân cờ trên bàn cờ"""
    piece_id: str = Field(..., description="Mã định danh duy nhất của quân cờ")
    side: Side = Field(..., description="Phe của quân cờ (RED / BLUE)")
    type: PieceType = Field(..., description="Loại quân cờ trong 11 loại")
    position: Position = Field(..., description="Tọa độ hiện tại trên bàn cờ")
    is_alive: bool = Field(True, description="Quân cờ còn sống trên bàn hay không")
    is_hero: bool = Field(False, description="Quân cờ đã được phong Anh hùng hay chưa")
    carrying_piece_ids: List[str] = Field(default_factory=list, description="Danh sách quân đang được cõng")
    carried_by_id: Optional[str] = Field(None, description="Mã phương tiện đang cõng quân này nếu có")


class LegalAction(BaseModel):
    """Một hành động hợp lệ mà người chơi hoặc Agent có thể thực hiện"""
    action_id: str = Field(..., description="Mã hành động duy nhất trong lượt")
    action_type: ActionType = Field(..., description="Loại hành động (MOVE, CAPTURE_REPLACE, v.v.)")
    piece_id: str = Field(..., description="Quân cờ thực hiện hành động")
    from_pos: Position = Field(..., description="Tọa độ xuất phát")
    to_pos: Position = Field(..., description="Tọa độ đích đến")
    target_piece_id: Optional[str] = Field(None, description="Mục tiêu bị tấn công/ăn nếu có")
    notation: str = Field(..., description="Ký pháp chuẩn theo MOVE_NOTATION.md")
    description: str = Field(..., description="Mô tả hành động dễ hiểu cho giao diện")


class GameEvent(BaseModel):
    """Biến cố phát sinh sau khi thực hiện hành động"""
    event_id: str = Field(..., description="Mã biến cố duy nhất")
    event_type: EventType = Field(..., description="Loại biến cố")
    actor_id: Optional[str] = Field(None, description="Quân cờ gây ra biến cố")
    target_id: Optional[str] = Field(None, description="Quân cờ bị tác động")
    notation: str = Field(..., description="Ký pháp tương ứng")
    score_delta: Dict[Side, int] = Field(default_factory=lambda: {Side.RED: 0, Side.BLUE: 0})
    details: Optional[Dict[str, Any]] = Field(None, description="Thông tin chi tiết kèm theo")


class GameResultDTO(BaseModel):
    """Kết quả chung cuộc khi trận đấu kết thúc"""
    winner: Optional[str] = Field(None, description="'RED', 'BLUE', hoặc 'DRAW'")
    reason: Optional[TerminationReason] = Field(None, description="Lý do kết thúc trận đấu")
    final_scores: Dict[str, int] = Field(default_factory=dict, description="Điểm số cuối cùng của hai phe")


class GameState(BaseModel):
    """Toàn bộ trạng thái của một phiên chơi cờ"""
    game_id: str = Field(..., description="Mã ván đấu duy nhất")
    mode: GameMode = Field(..., description="Chế độ chơi")
    status: GameStatus = Field(..., description="Trạng thái ván đấu (NOT_STARTED, IN_PROGRESS, GAME_OVER)")
    side_to_move: Side = Field(..., description="Phe đang có quyền đi nước")
    turn_index: int = Field(1, description="Số thứ tự lượt (bắt đầu từ 1)")
    action_index: int = Field(1, description="Thứ tự hành động trong lượt hiện tại (1..3)")
    turn_phase: TurnPhase = Field(TurnPhase.NORMAL, description="Giai đoạn trong lượt (NORMAL / STACK_ACTIVE)")
    state_version: int = Field(1, description="Phiên bản trạng thái dùng để chống xung đột optimistic locking")
    scores: Dict[str, int] = Field(default_factory=lambda: {"RED": 0, "BLUE": 0})
    remaining_time_ms: Dict[str, int] = Field(default_factory=lambda: {"RED": 1800000, "BLUE": 1800000})
    pieces: List[PieceState] = Field(..., description="Danh sách trạng thái của 38 quân cờ")
    legal_actions: List[LegalAction] = Field(default_factory=list, description="Danh sách nước đi hợp lệ")
    can_end_turn: bool = Field(False, description="Có thể chủ động kết thúc lượt tổ hợp sớm hay không")
    last_event: Optional[GameEvent] = Field(None, description="Biến cố gần nhất")
    result: Optional[GameResultDTO] = Field(None, description="Kết quả trận đấu nếu đã kết thúc")


class CreateGameRequest(BaseModel):
    mode: GameMode = Field(GameMode.HUMAN_VS_AI, description="Chế độ chơi")
    player_side: Side = Field(Side.RED, description="Phe của người chơi nếu có")
    red_agent_id: Optional[str] = Field(None, description="Mã tác tử phe Đỏ nếu là AI")
    blue_agent_id: Optional[str] = Field(None, description="Mã tác tử phe Xanh nếu là AI")
    time_limit_seconds: int = Field(1800, ge=60, le=7200, description="Thời gian tối đa mỗi bên (giây)")
    agent_config: Optional[Dict[str, Any]] = Field(None, description="Cấu hình tùy chọn cho tác tử (seed, max_depth)")


class ActionRequest(BaseModel):
    action_type: ActionType = Field(..., description="Loại hành động")
    piece_id: str = Field(..., description="Mã quân cờ thực hiện")
    to_pos: Position = Field(..., description="Tọa độ đích")
    action_id: Optional[str] = Field(None, description="Mã hành động được server cấp")
    from_pos: Optional[Position] = Field(None, description="Tọa độ nguồn (kiểm tra tính nhất quán)")
    target_piece_id: Optional[str] = Field(None, description="Mã quân mục tiêu nếu ăn quân")
    state_version: int = Field(1, description="Phiên bản trạng thái mong đợi")


class EndTurnRequest(BaseModel):
    state_version: int = Field(1, description="Phiên bản trạng thái mong đợi")


class AiStepRequest(BaseModel):
    time_budget_ms: int = Field(1000, ge=100, le=30000, description="Thời gian suy nghĩ tối đa của AI (ms)")


class ResignRequest(BaseModel):
    side: Side = Field(..., description="Phe chấp nhận đầu hàng")


class DrawRequest(BaseModel):
    side: Side = Field(..., description="Phe đưa ra yêu cầu")
    action: str = Field("OFFER", description="'OFFER' (đề nghị) hoặc 'ACCEPT' (chấp thuận)")


class ActionResponse(BaseModel):
    state_version: int
    event: GameEvent
    game_state: GameState
