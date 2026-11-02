# packages/commander_game_engine/board.py

from dataclasses import dataclass, field
from enum import Enum

Position = tuple[int, int] # (y, x)

class Terrain(Enum):  # Các giao điểm địa hình trên bàn cờ
    LAND = "land"
    SEA = "sea"
    RIVER_BANK = "river_bank"
    COAST = "coast"


class EdgeType(Enum): # Các đoạn nối giữa hai giao điểm kề nhau
    NORMAL = "normal"
    COAST = "coast"
    RIVER_BANK = "river_bank"
    FORD = "ford"
    DEEP_RIVER = "deep_river"


@dataclass
class Board:
    ROWS = 12 # từ 0 đến 11
    COLS = 11 # từ 0 đến 10

    def is_valid_position(self, pos: Position) -> bool:
        y, x = pos
        return 0 <= y < self.ROWS and 0 <= x < self.COLS

    def get_region(self, y: int, x: int) -> Terrain:
        """Phân loại các giao điểm trên bàn cờ"""
        if not (0 <= y < self.ROWS and 0 <= x < self.COLS):
            raise ValueError("Invalid region coordinate")

        if x < 2:
            return Terrain.SEA

        if (y == 5 or y == 6) and x >= 2:
            return Terrain.RIVER_BANK
        
        if x == 2 and (y != 5 and y != 6):
            return Terrain.COAST

        return Terrain.LAND

    def get_edge_type(self, start: Position, end: Position) -> EdgeType:
        """Phân loại đoạn nối giữa hai giao điểm kề nhau."""

        y1, x1 = start
        y2, x2 = end

        if not (self.is_valid_position(start) and self.is_valid_position(end)):
            raise ValueError("Invalid position")

        if abs(y2 - y1) + abs(x2 - x1) != 1:
            raise ValueError("Points must be adjacent")

        # Hai đoạn ngầm vượt sông
        if {y1, y2} == {5, 6} and x1 == x2 and x1 >= 2:
            if x1 in (5, 7):
                return EdgeType.FORD

            return EdgeType.DEEP_RIVER

        # Đoạn nằm trên bờ biển
        if x1 == x2 == 2:
            return EdgeType.COAST

        # Đoạn nằm trên bờ sông
        if y1 == y2 and y1 in (5, 6) and min(x1, x2) >= 2:
            return EdgeType.RIVER_BANK

        return EdgeType.NORMAL

# board = Board()
