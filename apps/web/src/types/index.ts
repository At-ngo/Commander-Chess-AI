/**
 * Commander Chess AI — Core Type Definitions
 * Aligned with docs/API_CONTRACT.md and docs/GAME_RULES_PHAN_1_TOA_DO.md
 */

export type Side = 'RED' | 'BLUE';

export type PieceType =
  | 'COMMANDER'
  | 'INFANTRY'
  | 'TANK'
  | 'MILITIA'
  | 'ENGINEER'
  | 'ARTILLERY'
  | 'ANTI_AIR'
  | 'MISSILE'
  | 'AIRCRAFT'
  | 'NAVY'
  | 'HEADQUARTERS';

export interface Position {
  x: number; // 0..10
  y: number; // 0..11
}

export interface PieceState {
  piece_id: string;
  side: Side;
  type: PieceType;
  position: Position;
  is_alive: boolean;
  is_hero: boolean;
  carrying_piece_ids: string[];
  carried_by_id: string | null;
}

export type ActionType =
  | 'MOVE'
  | 'CAPTURE_REPLACE'
  | 'CAPTURE_STAND'
  | 'BOARD'
  | 'DEPLOY'
  | 'STACK_MOVE'
  | 'END_TURN';

export type EventType =
  | 'PIECE_MOVED'
  | 'PIECE_CAPTURED'
  | 'AIR_SHOT_DOWN'
  | 'AIR_EXCHANGE'
  | 'HERO_PROMOTION'
  | 'HQ_DESTROYED'
  | 'GAME_OVER';

export type GameStatus = 'NOT_STARTED' | 'IN_PROGRESS' | 'GAME_OVER';
export type TurnPhase = 'NORMAL' | 'STACK_ACTIVE';
export type GameMode = 'HUMAN_VS_AI' | 'AI_VS_AI' | 'HUMAN_VS_HUMAN';
