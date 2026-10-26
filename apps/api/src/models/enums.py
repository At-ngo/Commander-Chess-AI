"""
Commander Chess AI — Core Enums
Aligned with docs/API_CONTRACT.md Section 2.1
"""

from enum import Enum


class Side(str, Enum):
    RED = "RED"
    BLUE = "BLUE"


class PieceType(str, Enum):
    COMMANDER = "COMMANDER"      # Tư lệnh (⋆)
    INFANTRY = "INFANTRY"        # Bộ binh (B)
    TANK = "TANK"                # Xe tăng (T)
    MILITIA = "MILITIA"          # Dân quân (D)
    ENGINEER = "ENGINEER"        # Công binh (C)
    ARTILLERY = "ARTILLERY"      # Pháo binh (A)
    ANTI_AIR = "ANTI_AIR"        # Cao xạ (F)
    MISSILE = "MISSILE"          # Tên lửa (L)
    AIRCRAFT = "AIRCRAFT"        # Không quân / Máy bay (K)
    NAVY = "NAVY"                # Tàu chiến / Hải quân (H)
    HEADQUARTERS = "HEADQUARTERS"# Sở chỉ huy (S)


class ActionType(str, Enum):
    MOVE = "MOVE"                        # Di chuyển không ăn quân (_)
    CAPTURE_REPLACE = "CAPTURE_REPLACE"  # Ăn quân và thế chỗ (@)
    CAPTURE_STAND = "CAPTURE_STAND"      # Ăn/bắn tại chỗ (_@_)
    BOARD = "BOARD"                      # Quân lên phương tiện cõng
    DEPLOY = "DEPLOY"                    # Quân triển khai rời phương tiện cõng
    STACK_MOVE = "STACK_MOVE"            # Phương tiện mang theo quân cõng di chuyển
    END_TURN = "END_TURN"                # Chủ động kết thúc sớm lượt tổ hợp


class EventType(str, Enum):
    PIECE_MOVED = "PIECE_MOVED"          # Quân di chuyển
    PIECE_CAPTURED = "PIECE_CAPTURED"    # Quân bị tiêu diệt
    AIR_SHOT_DOWN = "AIR_SHOT_DOWN"      # Máy bay bị bắn hạ bởi vùng phòng không (@”)
    AIR_EXCHANGE = "AIR_EXCHANGE"        # Máy bay 1 đổi 1 trong vùng phòng không (><)
    HERO_PROMOTION = "HERO_PROMOTION"    # Quân được phong Anh hùng
    HQ_DESTROYED = "HQ_DESTROYED"        # Sở chỉ huy bị phá hủy, Tư lệnh lộ diện
    GAME_OVER = "GAME_OVER"              # Trận đấu kết thúc


class GameMode(str, Enum):
    HUMAN_VS_AI = "HUMAN_VS_AI"
    AI_VS_AI = "AI_VS_AI"
    HUMAN_VS_HUMAN = "HUMAN_VS_HUMAN"


class GameStatus(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    GAME_OVER = "GAME_OVER"


class TurnPhase(str, Enum):
    NORMAL = "NORMAL"              # Lượt thông thường (1 hành động duy nhất)
    STACK_ACTIVE = "STACK_ACTIVE"  # Đang trong chuỗi hành động của tổ hợp cõng quân (tối đa 3 hành động)


class TerminationReason(str, Enum):
    COMMANDER_CAPTURED = "COMMANDER_CAPTURED"  # Tư lệnh bị tiêu diệt (+50 điểm)
    TIMEOUT = "TIMEOUT"                        # Hết thời gian (so điểm số)
    RESIGNATION = "RESIGNATION"                # Một bên đầu hàng
    MUTUAL_DRAW = "MUTUAL_DRAW"                # Hai bên đồng thuận hòa
    MAX_MOVES_EXCEEDED = "MAX_MOVES_EXCEEDED"  # Quá số nước quy định
    RULE_VIOLATION = "RULE_VIOLATION"          # Phạm luật cờ
