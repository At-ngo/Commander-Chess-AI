import { Position } from '../types';

/**
 * Geometric constants for Commander Chess SVG board (viewBox: 0 0 1024 949)
 * Grid area: x from 63 to 943 (11 columns, step = 88)
 *            y from 61 to 880 (12 rows, step = 819 / 11 ≈ 74.4545)
 */
export const BOARD_GEOMETRY = {
  viewBoxWidth: 1024,
  viewBoxHeight: 949,
  xOrigin: 63,
  xStep: 88,
  yOrigin: 61,
  yBottom: 880,
  yStep: 819 / 11,
  totalCols: 11,
  totalRows: 12,
};

/**
 * Converts board logic coordinate (y, x) to SVG canvas coordinate (svgX, svgY).
 * Note: Logic coordinates have (0, 0) at the BOTTOM-LEFT.
 * SVG coordinates have (0, 0) at the TOP-LEFT.
 * Thus: svgY = 880 - y * (819 / 11)
 *       svgX = 63 + x * 88
 */
export function boardToSvgPoint(pos: Position): { svgX: number; svgY: number } {
  return {
    svgX: BOARD_GEOMETRY.xOrigin + pos.x * BOARD_GEOMETRY.xStep,
    svgY: BOARD_GEOMETRY.yBottom - pos.y * BOARD_GEOMETRY.yStep,
  };
}

/**
 * Validates whether a coordinate (y, x) is inside board boundaries
 */
export function isValidCoordinate(x: number, y: number): boolean {
  return x >= 0 && x <= 10 && y >= 0 && y <= 11;
}

/**
 * Format coordinate to traditional Commander Chess notation: [y ; x]
 */
export function formatCoordinateNotation(pos: Position): string {
  return `[${pos.y} ; ${pos.x}]`;
}
