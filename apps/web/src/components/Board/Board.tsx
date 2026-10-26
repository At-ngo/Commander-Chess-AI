import React from 'react';
import { PieceState } from '../../types';
import { boardToSvgPoint, formatCoordinateNotation, BOARD_GEOMETRY } from '../../utils/coordinates';
import { getPieceImageUrl, PIECE_VIETNAMESE_NAMES } from '../../utils/assets';
import styles from './Board.module.css';

interface BoardProps {
  pieces: PieceState[];
  selectedPieceId: string | null;
  onSelectPiece: (piece: PieceState) => void;
}

const PIECE_SIZE = 60; // Kích thước quân cờ (to rõ hơn, tăng từ 54 -> 60)
const HIT_RADIUS = 30; // Bán kính 30px < 37.23px (nghiêm ngặt < 1/2 đoạn thẳng 74.45px giữa 2 giao điểm)

export const Board: React.FC<BoardProps> = ({
  pieces,
  selectedPieceId,
  onSelectPiece,
}) => {
  // Find selected piece coordinates to subtly highlight its axis indicators
  const selectedPiece = pieces.find((p) => p.piece_id === selectedPieceId);
  const selectedX = selectedPiece ? selectedPiece.position.x : null;
  const selectedY = selectedPiece ? selectedPiece.position.y : null;

  // Array of columns X: 0 to 10
  const cols = Array.from({ length: BOARD_GEOMETRY.totalCols }, (_, i) => i);
  // Array of rows Y: 0 to 11
  const rows = Array.from({ length: BOARD_GEOMETRY.totalRows }, (_, i) => i);

  return (
    <div className={styles.boardContainer}>
      <svg
        viewBox="0 0 1024 949"
        className={styles.boardSvg}
        preserveAspectRatio="none"
      >
        {/* Layer 1: Background SVG Board Asset */}
        <image
          href="/assets/board/board.svg"
          x="0"
          y="0"
          width="1024"
          height="949"
          preserveAspectRatio="none"
        />

        {/* Layer 2: CR-001 Board Coordinates (X and Y Axis Labels) */}
        <g className={styles.coordGroup}>
          {/* Axis Indicators in corners */}
          <text x={28} y={32} className={styles.axisIndicator}>Y (Tung)</text>
          <text x={983} y={918} className={styles.axisIndicator}>X (Hoành)</text>
          <text x={28} y={918} className={styles.axisIndicator}>[0;0]</text>

          {/* Bottom X Coordinates (x = 0..10) */}
          {cols.map((x) => {
            const svgX = BOARD_GEOMETRY.xOrigin + x * BOARD_GEOMETRY.xStep;
            const isColSelected = selectedX === x;
            return (
              <g key={`coord-b-x-${x}`} transform={`translate(${svgX}, 918)`}>
                <rect
                  x={-13}
                  y={-10}
                  width={26}
                  height={20}
                  rx={3}
                  className={`${styles.coordBadge} ${isColSelected ? styles.coordBadgeActive : ''}`}
                />
                <text className={styles.coordLabel} y={1}>
                  {x}
                </text>
              </g>
            );
          })}

          {/* Top X Coordinates (x = 0..10) */}
          {cols.map((x) => {
            const svgX = BOARD_GEOMETRY.xOrigin + x * BOARD_GEOMETRY.xStep;
            const isColSelected = selectedX === x;
            return (
              <g key={`coord-t-x-${x}`} transform={`translate(${svgX}, 32)`}>
                <rect
                  x={-13}
                  y={-10}
                  width={26}
                  height={20}
                  rx={3}
                  className={`${styles.coordBadge} ${isColSelected ? styles.coordBadgeActive : ''}`}
                />
                <text className={styles.coordLabel} y={1}>
                  {x}
                </text>
              </g>
            );
          })}

          {/* Left Y Coordinates (y = 0..11) */}
          {rows.map((y) => {
            const svgY = BOARD_GEOMETRY.yBottom - y * BOARD_GEOMETRY.yStep;
            const isRowSelected = selectedY === y;
            return (
              <g key={`coord-l-y-${y}`} transform={`translate(28, ${svgY})`}>
                <rect
                  x={-13}
                  y={-10}
                  width={26}
                  height={20}
                  rx={3}
                  className={`${styles.coordBadge} ${isRowSelected ? styles.coordBadgeActive : ''}`}
                />
                <text className={styles.coordLabel} y={1}>
                  {y}
                </text>
              </g>
            );
          })}

          {/* Right Y Coordinates (y = 0..11) */}
          {rows.map((y) => {
            const svgY = BOARD_GEOMETRY.yBottom - y * BOARD_GEOMETRY.yStep;
            const isRowSelected = selectedY === y;
            return (
              <g key={`coord-r-y-${y}`} transform={`translate(983, ${svgY})`}>
                <rect
                  x={-13}
                  y={-10}
                  width={26}
                  height={20}
                  rx={3}
                  className={`${styles.coordBadge} ${isRowSelected ? styles.coordBadgeActive : ''}`}
                />
                <text className={styles.coordLabel} y={1}>
                  {y}
                </text>
              </g>
            );
          })}
        </g>

        {/* Layer 3: Pieces Rendering Layer (Fixed BUG-001) */}
        {pieces.map((piece) => {
          if (!piece.is_alive) return null;

          const { svgX, svgY } = boardToSvgPoint(piece.position);
          const isSelected = selectedPieceId === piece.piece_id;
          const imgUrl = getPieceImageUrl(piece.type, piece.side);
          const pieceName = PIECE_VIETNAMESE_NAMES[piece.type];
          const coordText = formatCoordinateNotation(piece.position);

          return (
            <g
              key={piece.piece_id}
              className={styles.pieceGroup}
              onClick={() => onSelectPiece(piece)}
              transform={`translate(${svgX}, ${svgY})`}
            >
              {/* Stable hit area circle - fixes BUG-001 by guaranteeing cursor hit target remains invariant */}
              <circle cx={0} cy={0} r={HIT_RADIUS} className={styles.pieceHitArea} />

              {/* Hover ring indicator */}
              <circle cx={0} cy={0} r={HIT_RADIUS + 1} className={styles.hoverRing} />

              {/* Selection Highlight Ring */}
              {isSelected && (
                <circle
                  cx={0}
                  cy={0}
                  r={34}
                  className={`${styles.selectionRing} ${
                    piece.side === 'BLUE' ? styles.selectionRingBlue : ''
                  }`}
                />
              )}

              {/* Piece Image centered on intersection - pointer-events: none ensures mouse events target the group */}
              <image
                href={imgUrl}
                x={-PIECE_SIZE / 2}
                y={-PIECE_SIZE / 2}
                width={PIECE_SIZE}
                height={PIECE_SIZE}
                className={styles.pieceImage}
              >
                <title>
                  {pieceName} ({piece.side === 'RED' ? 'Đỏ' : 'Xanh'}) {coordText}
                </title>
              </image>

              {/* Hero Star Badge if heroic */}
              {piece.is_hero && (
                <text
                  x={18}
                  y={-16}
                  fontSize="15"
                  fill="#ffcd00"
                  fontWeight="bold"
                  filter="drop-shadow(0 1px 2px rgba(0,0,0,0.8))"
                  pointerEvents="none"
                >
                  ★
                </text>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
};
