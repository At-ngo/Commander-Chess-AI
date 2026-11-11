import React, { useMemo } from 'react';
import { PieceState, LegalAction, MoveRecord, ActiveCompoundState } from '../../types';
import { boardToSvgPoint, formatCoordinateNotation, BOARD_GEOMETRY } from '../../utils/coordinates';
import {
  getPieceImageUrl,
  PIECE_ENGLISH_NAMES,
  PIECE_VIETNAMESE_NAMES,
} from '../../utils/assets';
import { getAirDefenseZones, getAllCarriedPieceIds } from '../../services/mockGameService';
import { Language } from '../../i18n';
import styles from './Board.module.css';

interface BoardProps {
  pieces: PieceState[];
  selectedPieceId: string | null;
  onSelectPiece: (piece: PieceState) => void;
  legalActions?: LegalAction[];
  onExecuteAction?: (action: LegalAction) => void;
  lastMove?: MoveRecord | null;
  activeCompound?: ActiveCompoundState | null;
  flipped?: boolean;
  readOnly?: boolean;
  lang?: Language;
}

const PIECE_SIZE = 60;
const HIT_RADIUS = 30;

export const Board: React.FC<BoardProps> = ({
  pieces,
  selectedPieceId,
  onSelectPiece,
  legalActions = [],
  onExecuteAction,
  lastMove,
  activeCompound,
  flipped = false,
  readOnly = false,
  lang = 'vi',
}) => {
  const selectedPiece = pieces.find((p) => p.piece_id === selectedPieceId);
  const selectedX = selectedPiece ? selectedPiece.position.x : null;
  const selectedY = selectedPiece ? selectedPiece.position.y : null;

  // Khi click chọn quân Máy bay, tính toán Vành đai lửa phòng không bên đối phương
  const isAircraftSelected =
    !readOnly && selectedPiece?.type === 'AIRCRAFT' && !selectedPiece.is_hero;
  const enemySide = selectedPiece ? (selectedPiece.side === 'RED' ? 'BLUE' : 'RED') : null;
  const enemyAaZones = useMemo(() => {
    if (!isAircraftSelected || !enemySide) return [];
    return getAirDefenseZones(enemySide, pieces);
  }, [isAircraftSelected, enemySide, pieces]);

  // Tính toán quỹ đạo nước vừa đi (Vị trí xuất phát, vector mũi tên và vị trí đích đến)
  const lastMoveGeometry = useMemo(() => {
    if (!lastMove || !lastMove.action) return null;
    const { from_pos, to_pos } = lastMove.action;
    if (!from_pos || !to_pos) return null;

    const fromSvg = boardToSvgPoint(from_pos, flipped);
    const toSvg = boardToSvgPoint(to_pos, flipped);
    const dx = toSvg.svgX - fromSvg.svgX;
    const dy = toSvg.svgY - fromSvg.svgY;
    const dist = Math.hypot(dx, dy);

    const isSameSquare = dist < 2;
    let lineStart = { x: fromSvg.svgX, y: fromSvg.svgY };
    let lineEnd = { x: toSvg.svgX, y: toSvg.svgY };

    if (!isSameSquare) {
      const ux = dx / dist;
      const uy = dy / dist;
      const startOffset = 18;
      const endOffset = 28;
      if (dist > startOffset + endOffset) {
        lineStart = {
          x: fromSvg.svgX + ux * startOffset,
          y: fromSvg.svgY + uy * startOffset,
        };
        lineEnd = {
          x: fromSvg.svgX + ux * (dist - endOffset),
          y: fromSvg.svgY + uy * (dist - endOffset),
        };
      } else {
        lineStart = {
          x: fromSvg.svgX + ux * (dist * 0.25),
          y: fromSvg.svgY + uy * (dist * 0.25),
        };
        lineEnd = {
          x: fromSvg.svgX + ux * (dist * 0.75),
          y: fromSvg.svgY + uy * (dist * 0.75),
        };
      }
    }

    return {
      fromSvg,
      toSvg,
      isSameSquare,
      lineStart,
      lineEnd,
      side: lastMove.side,
    };
  }, [lastMove, flipped]);

  const cols = Array.from({ length: BOARD_GEOMETRY.totalCols }, (_, i) => i);
  const rows = Array.from({ length: BOARD_GEOMETRY.totalRows }, (_, i) => i);
  const visibleLegalActions = readOnly ? [] : legalActions;

  return (
    <div className={styles.boardContainer}>
      <svg
        viewBox="0 0 1024 949"
        className={styles.boardSvg}
        preserveAspectRatio="none"
      >
        <defs>
          <marker
            id="lastMoveArrowheadRed"
            viewBox="0 0 10 10"
            refX="6"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#ef4444" />
          </marker>
          <marker
            id="lastMoveArrowheadBlue"
            viewBox="0 0 10 10"
            refX="6"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#38bdf8" />
          </marker>
          <clipPath id="carriedBadgeClip1" clipPathUnits="userSpaceOnUse">
            <circle cx="0" cy="0" r="10.2" />
          </clipPath>
          <clipPath id="carriedBadgeClip2" clipPathUnits="userSpaceOnUse">
            <circle cx="0" cy="0" r="9.2" />
          </clipPath>
        </defs>

        {/* Layer 1: Background SVG Board Asset (rotates cleanly around grid center (503, 470.5) when flipped) */}
        <image
          href="/assets/board/board.svg"
          x="0"
          y="0"
          width="1024"
          height="949"
          preserveAspectRatio="none"
          transform={flipped ? 'rotate(180 503 470.5)' : undefined}
        />

        {/* Layer 2: CR-001 Board Coordinates (X and Y Axis Labels) */}
        <g className={styles.coordGroup}>
          <text x={28} y={32} className={styles.axisIndicator}>Y (Tung)</text>
          <text x={983} y={918} className={styles.axisIndicator}>X (Hoành)</text>
          <text x={28} y={918} className={styles.axisIndicator}>
            {flipped ? '[11;10]' : '[0;0]'}
          </text>

          {/* Bottom X Coordinates */}
          {cols.map((x) => {
            const displayCol = flipped ? BOARD_GEOMETRY.totalCols - 1 - x : x;
            const svgX = BOARD_GEOMETRY.xOrigin + displayCol * BOARD_GEOMETRY.xStep;
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

          {/* Top X Coordinates */}
          {cols.map((x) => {
            const displayCol = flipped ? BOARD_GEOMETRY.totalCols - 1 - x : x;
            const svgX = BOARD_GEOMETRY.xOrigin + displayCol * BOARD_GEOMETRY.xStep;
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

          {/* Left Y Coordinates */}
          {rows.map((y) => {
            const displayRow = flipped ? BOARD_GEOMETRY.totalRows - 1 - y : y;
            const svgY = BOARD_GEOMETRY.yBottom - displayRow * BOARD_GEOMETRY.yStep;
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

          {/* Right Y Coordinates */}
          {rows.map((y) => {
            const displayRow = flipped ? BOARD_GEOMETRY.totalRows - 1 - y : y;
            const svgY = BOARD_GEOMETRY.yBottom - displayRow * BOARD_GEOMETRY.yStep;
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

        {/* Layer 2.7: Enemy Air Defense Zone */}
        {enemyAaZones.length > 0 && (
          <g className={styles.airDefenseLayer}>
            {enemyAaZones.map(({ x, y }) => {
              const { svgX, svgY } = boardToSvgPoint({ x, y }, flipped);
              return (
                <g key={`aa-${x}-${y}`} transform={`translate(${svgX}, ${svgY})`} className={styles.aaZoneGroup}>
                  <circle cx={0} cy={0} r={22} className={styles.aaZoneCircle} />
                  <circle cx={0} cy={0} r={4.5} className={styles.aaHazardCore} />
                  <text x={0} y={1} className={styles.aaFlameIcon}>
                    🔥
                  </text>
                  <title>
                    {lang === 'vi'
                      ? 'Vành đai lửa phòng không đối phương (Vùng cấm bay)'
                      : 'Enemy Air Defense Envelope (No-Fly Zone)'}
                  </title>
                </g>
              );
            })}
          </g>
        )}

        {/* Layer 2.8: Last Move Trajectory Layer */}
        {lastMoveGeometry && (
          <g className={styles.lastMoveLayer} pointerEvents="none">
            <g transform={`translate(${lastMoveGeometry.fromSvg.svgX}, ${lastMoveGeometry.fromSvg.svgY})`}>
              <circle
                cx={0}
                cy={0}
                r={22}
                className={
                  lastMoveGeometry.side === 'RED'
                    ? styles.lastMoveFromRingRed
                    : styles.lastMoveFromRingBlue
                }
              />
              <circle
                cx={0}
                cy={0}
                r={4}
                className={
                  lastMoveGeometry.side === 'RED'
                    ? styles.lastMoveFromDotRed
                    : styles.lastMoveFromDotBlue
                }
              />
            </g>

            {!lastMoveGeometry.isSameSquare && (
              <line
                x1={lastMoveGeometry.lineStart.x}
                y1={lastMoveGeometry.lineStart.y}
                x2={lastMoveGeometry.lineEnd.x}
                y2={lastMoveGeometry.lineEnd.y}
                className={
                  lastMoveGeometry.side === 'RED'
                    ? styles.lastMoveLineRed
                    : styles.lastMoveLineBlue
                }
                markerEnd={
                  lastMoveGeometry.side === 'RED'
                    ? 'url(#lastMoveArrowheadRed)'
                    : 'url(#lastMoveArrowheadBlue)'
                }
              />
            )}

            <g transform={`translate(${lastMoveGeometry.toSvg.svgX}, ${lastMoveGeometry.toSvg.svgY})`}>
              <circle
                cx={0}
                cy={0}
                r={28}
                className={
                  lastMoveGeometry.side === 'RED'
                    ? styles.lastMoveToRingRed
                    : styles.lastMoveToRingBlue
                }
              />
            </g>
          </g>
        )}

        {/* Layer 3: Pieces Rendering Layer */}
        {pieces.map((piece) => {
          if (!piece.is_alive || piece.carried_by_id) return null;

          const { svgX, svgY } = boardToSvgPoint(piece.position, flipped);
          const isSelected = selectedPieceId === piece.piece_id;
          const imgUrl = getPieceImageUrl(piece.type, piece.side);
          const pieceName =
            lang === 'vi'
              ? PIECE_VIETNAMESE_NAMES[piece.type]
              : PIECE_ENGLISH_NAMES[piece.type];
          const coordText = formatCoordinateNotation(piece.position);

          const isBlockedByActiveCompound =
            !readOnly && activeCompound && !activeCompound.memberIds.includes(piece.piece_id);

          const carriedUnits = getAllCarriedPieceIds(piece.piece_id, pieces)
            .map((id) => pieces.find((p) => p.is_alive && p.piece_id === id))
            .filter((p): p is PieceState => Boolean(p));

          return (
            <g
              key={piece.piece_id}
              className={`${styles.pieceGroup} ${isBlockedByActiveCompound ? styles.pieceGroupBlocked : ''}`}
              onClick={() => {
                if (isBlockedByActiveCompound) return;
                if (!readOnly && piece.type === 'HEADQUARTERS' && !piece.is_hero) {
                  const cmdInside = pieces.find(
                    (p) =>
                      p.is_alive &&
                      p.carried_by_id === piece.piece_id &&
                      p.type === 'COMMANDER'
                  );
                  if (cmdInside) {
                    onSelectPiece(cmdInside);
                    return;
                  }
                }
                onSelectPiece(piece);
              }}
              transform={`translate(${svgX}, ${svgY})`}
            >
              <circle cx={0} cy={0} r={HIT_RADIUS} className={styles.pieceHitArea} />
              <circle cx={0} cy={0} r={HIT_RADIUS + 1} className={styles.hoverRing} />

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

              <image
                href={imgUrl}
                x={-PIECE_SIZE / 2}
                y={-PIECE_SIZE / 2}
                width={PIECE_SIZE}
                height={PIECE_SIZE}
                className={styles.pieceImage}
              >
                <title>
                  {pieceName} ({piece.side === 'RED' ? (lang === 'vi' ? 'Đỏ' : 'Red') : (lang === 'vi' ? 'Xanh' : 'Blue')}) {coordText}
                </title>
              </image>

              {/* Hero Star Badge */}
              {piece.is_hero && (
                <g className={styles.heroBadge} transform="translate(18, -18)">
                  <circle cx={0} cy={0} r={9} className={styles.heroBadgeBg} />
                  <text x={0} y={1} className={styles.heroBadgeStar}>
                    ★
                  </text>
                </g>
              )}

              {/* Circular Carried Piece Image Badges at Bottom */}
              {carriedUnits.length === 1 && (() => {
                const passenger = carriedUnits[0];
                const pImg = getPieceImageUrl(passenger.type, passenger.side);
                const pName =
                  lang === 'vi'
                    ? PIECE_VIETNAMESE_NAMES[passenger.type]
                    : PIECE_ENGLISH_NAMES[passenger.type];
                return (
                  <g className={styles.passengerBadge} transform="translate(0, 22)">
                    <circle
                      cx={0}
                      cy={0}
                      r={11.5}
                      className={`${styles.passengerBadgeBg} ${
                        passenger.is_hero ? styles.passengerBadgeHeroBg : ''
                      }`}
                    />
                    <image
                      href={pImg}
                      x={-11.5}
                      y={-11.5}
                      width={23}
                      height={23}
                      clipPath="url(#carriedBadgeClip1)"
                      preserveAspectRatio="xMidYMid slice"
                    />
                    <title>
                      {pieceName}{' '}
                      {lang === 'vi' ? `đang cõng ${pName}` : `carrying ${pName}`}
                    </title>
                  </g>
                );
              })()}

              {carriedUnits.length >= 2 && (
                <g className={styles.passengerBadge}>
                  {carriedUnits.slice(0, 2).map((passenger, idx) => {
                    const pImg = getPieceImageUrl(passenger.type, passenger.side);
                    const pName =
                      lang === 'vi'
                        ? PIECE_VIETNAMESE_NAMES[passenger.type]
                        : PIECE_ENGLISH_NAMES[passenger.type];
                    const offsetX = idx === 0 ? -11 : 11;
                    return (
                      <g
                        key={`carried-badge-${passenger.piece_id}`}
                        transform={`translate(${offsetX}, 22)`}
                      >
                        <circle
                          cx={0}
                          cy={0}
                          r={10.3}
                          className={`${styles.passengerBadgeBg} ${
                            passenger.is_hero ? styles.passengerBadgeHeroBg : ''
                          }`}
                        />
                        <image
                          href={pImg}
                          x={-10.5}
                          y={-10.5}
                          width={21}
                          height={21}
                          clipPath="url(#carriedBadgeClip2)"
                          preserveAspectRatio="xMidYMid slice"
                        />
                        <title>{pName}</title>
                      </g>
                    );
                  })}
                </g>
              )}
            </g>
          );
        })}

        {/* Layer 4: Tactical Legal Action Targets Layer */}
        {Array.from(
          visibleLegalActions.reduce((map, act) => {
            const key = `${act.to_pos.x}_${act.to_pos.y}`;
            if (!map.has(key)) map.set(key, []);
            map.get(key)!.push(act);
            return map;
          }, new Map<string, LegalAction[]>())
        ).map(([key, acts]) => {
          const sample = acts[0];
          const { svgX, svgY } = boardToSvgPoint(sample.to_pos, flipped);

          if (acts.length > 1) {
            return (
              <g key={`group-${key}`} transform={`translate(${svgX}, ${svgY})`}>
                {acts.map((act, idx) => {
                  const offsetX = idx === 0 ? -16 : 16;
                  const isStand = act.action_type === 'CAPTURE_STAND';
                  const isHazard =
                    act.description.includes('1 đổi 1') ||
                    act.description.includes('bắn hạ') ||
                    act.description.includes('⚠️');
                  return (
                    <g
                      key={act.action_id}
                      className={styles.actionTargetGroup}
                      onClick={(e) => {
                        e.stopPropagation();
                        onExecuteAction?.(act);
                      }}
                      transform={`translate(${offsetX}, 0)`}
                    >
                      <rect
                        x={-14}
                        y={-14}
                        width={28}
                        height={28}
                        rx={6}
                        className={`${styles.dualChoiceBadge} ${isHazard ? styles.dualChoiceBadgeHazard : ''}`}
                      />
                      <text className={styles.dualChoiceText}>
                        {isStand ? '💣' : '🎯'}
                      </text>
                      <title>{act.description}</title>
                    </g>
                  );
                })}
              </g>
            );
          }

          const action = acts[0];
          const isCapture =
            action.action_type === 'CAPTURE_REPLACE' ||
            action.action_type === 'CAPTURE_STAND';
          const isBoard = action.action_type === 'BOARD';
          const isHazardAction =
            action.description.includes('bắn hạ') ||
            action.description.includes('1 đổi 1') ||
            action.description.includes('⚠️');

          return (
            <g
              key={action.action_id}
              className={styles.actionTargetGroup}
              onClick={(e) => {
                e.stopPropagation();
                onExecuteAction?.(action);
              }}
              transform={`translate(${svgX}, ${svgY})`}
            >
              <circle cx={0} cy={0} r={HIT_RADIUS} className={styles.actionHitArea} />

              {isCapture ? (
                <g>
                  <circle
                    cx={0}
                    cy={0}
                    r={HIT_RADIUS + 3}
                    className={`${styles.captureReticle} ${isHazardAction ? styles.captureReticleHazard : ''}`}
                  >
                    <title>{action.description}</title>
                  </circle>
                  {isHazardAction && (
                    <text x={0} y={-HIT_RADIUS - 2} className={styles.hazardActionText}>
                      ⚠️ 1 đổi 1
                    </text>
                  )}
                </g>
              ) : isBoard ? (
                <g className={styles.boardActionGroup}>
                  <circle cx={0} cy={0} r={HIT_RADIUS + 2} className={styles.boardReticle} />
                  <rect x={-11} y={-11} width={22} height={22} rx={4} className={styles.boardBadge} />
                  <text x={0} y={3} className={styles.boardBadgeText}>🚛</text>
                  <title>{action.description}</title>
                </g>
              ) : (
                <>
                  <circle
                    cx={0}
                    cy={0}
                    r={14}
                    className={isHazardAction ? styles.moveHaloHazard : styles.moveHalo}
                  />
                  <circle
                    cx={0}
                    cy={0}
                    r={6.5}
                    className={isHazardAction ? styles.moveDotHazard : styles.moveDot}
                  >
                    <title>{action.description}</title>
                  </circle>
                  {isHazardAction && (
                    <text x={0} y={-16} className={styles.hazardActionText}>
                      ⚠️ Bị diệt
                    </text>
                  )}
                </>
              )}
            </g>
          );
        })}
      </svg>
    </div>
  );
};
