import { PieceType, Side } from '../types';

/**
 * Mapping between PieceType and file asset code
 * According to UI_SPECIFICATION.md:
 * TL (Tư lệnh), B (Bộ binh), T (Xe tăng), D (Dân quân), C (Công binh),
 * A (Pháo binh), F (Cao xạ), L (Tên lửa), K (Máy bay), H (Hải quân), S (Sở chỉ huy)
 */
export const PIECE_ASSET_CODE: Record<PieceType, string> = {
  COMMANDER: 'TL',
  INFANTRY: 'B',
  TANK: 'T',
  MILITIA: 'D',
  ENGINEER: 'C',
  ARTILLERY: 'A',
  ANTI_AIR: 'F',
  MISSILE: 'L',
  AIRCRAFT: 'K',
  NAVY: 'H',
  HEADQUARTERS: 'S',
};

/**
 * Official Move Notation Symbols according to docs/MOVE_NOTATION.md (Section 1):
 * ⋆ (Tư lệnh), L (Tên lửa), S (Sở chỉ huy), T (Xe tăng), K (Máy bay),
 * B (Bộ binh), H (Hải quân), F (Cao xạ), C (Công binh), D (Dân quân), A (Pháo binh)
 */
export const PIECE_NOTATION_SYMBOL: Record<PieceType, string> = {
  COMMANDER: '⋆',
  MISSILE: 'L',
  HEADQUARTERS: 'S',
  TANK: 'T',
  AIRCRAFT: 'K',
  INFANTRY: 'B',
  NAVY: 'H',
  ANTI_AIR: 'F',
  ENGINEER: 'C',
  MILITIA: 'D',
  ARTILLERY: 'A',
};

/**
 * Get the asset URL for a given piece type and side.
 * Files are located in /assets/pieces/{side}/{code}_{side}.png
 */
export function getPieceImageUrl(type: PieceType, side: Side): string {
  const code = PIECE_ASSET_CODE[type];
  const sideLower = side.toLowerCase();
  return `/assets/pieces/${sideLower}/${code}_${sideLower}.png`;
}

/**
 * Vietnamese display names for pieces
 */
export const PIECE_VIETNAMESE_NAMES: Record<PieceType, string> = {
  COMMANDER: 'Tư lệnh',
  INFANTRY: 'Bộ binh',
  TANK: 'Xe tăng',
  MILITIA: 'Dân quân',
  ENGINEER: 'Công binh',
  ARTILLERY: 'Pháo binh',
  ANTI_AIR: 'Cao xạ',
  MISSILE: 'Tên lửa',
  AIRCRAFT: 'Không quân',
  NAVY: 'Tàu chiến',
  HEADQUARTERS: 'Sở chỉ huy',
};

/**
 * English display names for pieces
 */
export const PIECE_ENGLISH_NAMES: Record<PieceType, string> = {
  COMMANDER: 'Commander',
  INFANTRY: 'Infantry',
  TANK: 'Tank',
  MILITIA: 'Militia',
  ENGINEER: 'Engineer',
  ARTILLERY: 'Artillery',
  ANTI_AIR: 'Anti-Air',
  MISSILE: 'Missile',
  AIRCRAFT: 'Aircraft',
  NAVY: 'Navy Ship',
  HEADQUARTERS: 'Headquarters',
};
