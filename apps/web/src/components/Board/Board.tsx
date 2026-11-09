import React, { useMemo } from 'react';
import { PieceState, LegalAction, MoveRecord, ActiveCompoundState } from '../../types';
import { boardToSvgPoint, formatCoordinateNotation, BOARD_GEOMETRY } from '../../utils/coordinates';
import { getPieceImageUrl, PIECE_VIETNAMESE_NAMES } from '../../utils/assets';
import { getAirDefenseZones, canCarrierLeaveCargoBehind } from '../../services/mockGameService';
import styles from './Board.module.css';

interface BoardProps {
  pieces: PieceState[];
  selectedPieceId: string | null;
  onSelectPiece: (piece: PieceState) => void;
  legalActions?: LegalAction[];
  onExecuteAction?: (action: LegalAction) => void;
  onConfirmCompound?: () => void;
  lastMove?: MoveRecord | null;
  activeCompound?: ActiveCompoundState | null;
  carryCargo?: boolean;
  onToggleCarryCargo?: (carry: boolean) => void;
}

const PIECE_SIZE = 60; // Kích thước quân cờ (to rõ hơn, tăng từ 54 -> 60)
const HIT_RADIUS = 30; // Bán kính 30px < 37.23px (nghiêm ngặt < 1/2 đoạn thẳng 74.45px giữa 2 giao điểm)

export const Board: React.FC<BoardProps> = ({
  pieces,
  selectedPieceId,
  onSelectPiece,
  legalActions = [],
  onExecuteAction,
  onConfirmCompound,
  lastMove,
  activeCompound,
  carryCargo = true,
  onToggleCarryCargo,
}) => {
  // Find selected piece coordinates to subtly highlight its axis indicators
  const selectedPiece = pieces.find((p) => p.piece_id === selectedPieceId);
  const selectedX = selectedPiece ? selectedPiece.position.x : null;
  const selectedY = selectedPiece ? selectedPiece.position.y : null;

  const isSelectedCarrierWithCargo = Boolean(
    selectedPiece &&
      selectedPiece.carrying_piece_ids &&
      selectedPiece.carrying_piece_ids.length > 0 &&
      selectedPiece.type !== 'HEADQUARTERS'
  );

  const canCarrierLeave = useMemo(() => {
    if (!selectedPiece || !isSelectedCarrierWithCargo) return true;
    return canCarrierLeaveCargoBehind(selectedPiece, pieces);
  }, [selectedPiece, isSelectedCarrierWithCargo, pieces]);

  // Check if selected piece belongs to a compound (carrier or passenger)
  const compoundCarrier = useMemo(() => {
    if (activeCompound) {
      const members = pieces.filter((p) => activeCompound.memberIds.includes(p.piece_id));
      const root = members.find((p) => !p.carried_by_id) || members[0];
      return root || null;
    }
    if (!selectedPiece) return null;
    if (selectedPiece.carried_by_id) {
      return pieces.find((p) => p.piece_id === selectedPiece.carried_by_id) || null;
    }
    const hasActivePassengers = pieces.some(
      (p) => p.is_alive && p.carried_by_id === selectedPiece.piece_id
    );
    if (hasActivePassengers) {
      return selectedPiece;
    }
    return null;
  }, [selectedPiece, pieces, activeCompound]);

  const displayedCompoundMembers = useMemo(() => {
    if (activeCompound) {
      return pieces.filter((p) => activeCompound.memberIds.includes(p.piece_id));
    }
    if (!compoundCarrier) return [];
    const passengers = pieces.filter(
      (p) => p.is_alive && p.carried_by_id === compoundCarrier.piece_id
    );
    if (passengers.length === 0) return [];
    return [compoundCarrier, ...passengers];
  }, [activeCompound, compoundCarrier, pieces]);

  // Khi click chọn quân Máy bay, tính toán Vành đai lửa phòng không bên đối phương
  const isAircraftSelected = selectedPiece?.type === 'AIRCRAFT' && !selectedPiece.is_hero;
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

    const fromSvg = boardToSvgPoint(from_pos);
    const toSvg = boardToSvgPoint(to_pos);
    const dx = toSvg.svgX - fromSvg.svgX;
    const dy = toSvg.svgY - fromSvg.svgY;
    const dist = Math.hypot(dx, dy);

    const isSameSquare = dist < 2;
    let lineStart = { x: fromSvg.svgX, y: fromSvg.svgY };
    let lineEnd = { x: toSvg.svgX, y: toSvg.svgY };

    if (!isSameSquare) {
      const ux = dx / dist;
      const uy = dy / dist;
      const startOffset = 18; // Điểm bắt đầu bên ngoài vòng tròn xuất phát
      const endOffset = 28;   // Điểm kết thúc vừa chạm rìa ngoài quân cờ ở đích đến
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
  }, [lastMove]);

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
        {/* SVG Marker Definitions for Last Move Arrowheads */}
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
        </defs>

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

        {/* Layer 2.7: Enemy Air Defense Zone (Vành đai lửa phòng không đối phương khi chọn Máy bay) */}
        {enemyAaZones.length > 0 && (
          <g className={styles.airDefenseLayer}>
            {enemyAaZones.map(({ x, y }) => {
              const { svgX, svgY } = boardToSvgPoint({ x, y });
              return (
                <g key={`aa-${x}-${y}`} transform={`translate(${svgX}, ${svgY})`} className={styles.aaZoneGroup}>
                  <circle cx={0} cy={0} r={22} className={styles.aaZoneCircle} />
                  <circle cx={0} cy={0} r={4.5} className={styles.aaHazardCore} />
                  <text x={0} y={1} className={styles.aaFlameIcon}>
                    🔥
                  </text>
                  <title>Vành đai lửa phòng không đối phương (Vùng cấm bay)</title>
                </g>
              );
            })}
          </g>
        )}

        {/* Layer 2.8: Last Move Trajectory Layer (Hiển thị nước vừa đi: vòng tròn xuất phát, đường thẳng mũi tên, vòng tròn đích đến) */}
        {lastMoveGeometry && (
          <g className={styles.lastMoveLayer} pointerEvents="none">
            {/* 1. Vòng tròn vị trí xuất phát (Departure Square Highlight) */}
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

            {/* 2. Đường thẳng mũi tên chỉ hướng nước vừa đi đến đích */}
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

            {/* 3. Vòng tròn đánh dấu vị trí đích đến của quân cờ (Arrival Square Highlight) */}
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

        {/* Layer 3: Pieces Rendering Layer (Fixed BUG-001) */}
        {pieces.map((piece) => {
          if (!piece.is_alive || piece.carried_by_id) return null;

          const { svgX, svgY } = boardToSvgPoint(piece.position);
          const isSelected = selectedPieceId === piece.piece_id;
          const imgUrl = getPieceImageUrl(piece.type, piece.side);
          const pieceName = PIECE_VIETNAMESE_NAMES[piece.type];
          const coordText = formatCoordinateNotation(piece.position);

          // QUY TẮC 3: Khi đang trong lượt của tổ hợp (STACK_ACTIVE), người chơi không thể điều khiển quân ở ngoài tổ hợp đó!
          const isBlockedByActiveCompound =
            activeCompound && !activeCompound.memberIds.includes(piece.piece_id);

          return (
            <g
              key={piece.piece_id}
              className={`${styles.pieceGroup} ${isBlockedByActiveCompound ? styles.pieceGroupBlocked : ''}`}
              onClick={() => {
                if (isBlockedByActiveCompound) return;
                // Ở sở chỉ huy, sở chỉ huy không thể di chuyển nên nếu có Tư lệnh trong đó,
                // click vào sẽ tự động chọn Tư lệnh để di chuyển ra ngoài!
                if (piece.type === 'HEADQUARTERS') {
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

              {/* Hero Star Badge if heroic - Ngôi sao vàng nhỏ nằm ở góc trên quân cờ */}
              {piece.is_hero && (
                <g className={styles.heroBadge} transform="translate(18, -18)">
                  <circle cx={0} cy={0} r={9} className={styles.heroBadgeBg} />
                  <text x={0} y={1} className={styles.heroBadgeStar}>
                    ★
                  </text>
                </g>
              )}

              {/* Passenger Badge if carrier unit has passengers on board */}
              {(() => {
                const passengerCount = pieces.filter(
                  (p) => p.is_alive && p.carried_by_id === piece.piece_id
                ).length;
                if (passengerCount === 0) return null;
                return (
                  <g className={styles.passengerBadge} transform="translate(18, 18)">
                    <circle cx={0} cy={0} r={9} className={styles.passengerBadgeBg} />
                    <text x={0} y={1} className={styles.passengerBadgeText}>
                      +{passengerCount}
                    </text>
                    <title>
                      {pieceName} đang cõng {passengerCount} quân
                    </title>
                  </g>
                );
              })()}
            </g>
          );
        })}

        {/* Layer 4: Tactical Legal Action Targets Layer (Move dots & Attack reticles) */}
        {Array.from(
          legalActions.reduce((map, act) => {
            const key = `${act.to_pos.x}_${act.to_pos.y}`;
            if (!map.has(key)) map.set(key, []);
            map.get(key)!.push(act);
            return map;
          }, new Map<string, LegalAction[]>())
        ).map(([key, acts]) => {
          const sample = acts[0];
          const { svgX, svgY } = boardToSvgPoint(sample.to_pos);

          if (acts.length > 1) {
            // Multiple actions on same square (e.g. Bombing vs Occupying for Aircraft/Artillery)
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

          // Single action on square
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
              {/* Stable hit area for target */}
              <circle cx={0} cy={0} r={HIT_RADIUS} className={styles.actionHitArea} />

              {isCapture ? (
                // Capture / Bombardment Reticle
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
                // Boarding / Transport Reticle (distinct cyan/gold ring with transport icon)
                <g className={styles.boardActionGroup}>
                  <circle cx={0} cy={0} r={HIT_RADIUS + 2} className={styles.boardReticle} />
                  <rect x={-11} y={-11} width={22} height={22} rx={4} className={styles.boardBadge} />
                  <text x={0} y={3} className={styles.boardBadgeText}>🚛</text>
                  <title>{action.description}</title>
                </g>
              ) : (
                // Move destination dot & halo
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

      {/* Floating Compound Dock */}
      {displayedCompoundMembers.length > 1 && (
        <div className={styles.compoundDock}>
          <div className={styles.compoundHeader}>
            <span className={styles.compoundBadge}>
              {compoundCarrier?.type === 'HEADQUARTERS' ? '🏛️ SỞ CHỈ HUY' : '🚜 TỔ HỢP CÕNG QUÂN'}
              {activeCompound ? ' (ĐANG TÁC CHIẾN)' : ''}
            </span>
            <span className={styles.compoundCoords}>
              [{compoundCarrier ? compoundCarrier.position.y : activeCompound?.originPos.y} ; {compoundCarrier ? compoundCarrier.position.x : activeCompound?.originPos.x}]
            </span>
          </div>
          {isSelectedCarrierWithCargo && (
            <div className={styles.cargoToggleContainer}>
              <label className={styles.cargoToggleLabel}>
                <input
                  type="checkbox"
                  checked={carryCargo}
                  disabled={!canCarrierLeave}
                  onChange={(e) => onToggleCarryCargo?.(e.target.checked)}
                />
                <span className={styles.cargoToggleText}>
                  🎒 {carryCargo ? 'Cõng theo quân khi di chuyển' : 'Tách lẻ đi một mình (để lại quân)'}
                </span>
              </label>
              {!canCarrierLeave && (
                <span
                  className={styles.cargoWarningNotice}
                  title="Quy tắc 2: Quân chở chở hai quân không thể chở nhau thì không thể tách lẻ bỏ lại cả hai!"
                >
                  ⚠️ Bắt buộc cõng (Quy tắc 2)
                </span>
              )}
            </div>
          )}
          <div className={styles.compoundUnitsList}>
            {displayedCompoundMembers.map((member) => {
              const hasMoved = activeCompound?.movedPieceIds.includes(member.piece_id);
              const isSelected = selectedPieceId === member.piece_id;
              const isCarrier = member.piece_id === compoundCarrier?.piece_id;
              const isHQ = member.type === 'HEADQUARTERS';
              const icon = isHQ
                ? '🏛️'
                : member.type === 'COMMANDER'
                ? '⭐'
                : isCarrier
                ? '🚜'
                : '🪖';

              if (isHQ && !member.is_hero) {
                return (
                  <span
                    key={member.piece_id}
                    className={styles.compoundCoords}
                    style={{ color: '#fbbf24', padding: '4px 6px' }}
                  >
                    🏛️ Sở chỉ huy (Bất động)
                  </span>
                );
              }

              return (
                <button
                  key={member.piece_id}
                  type="button"
                  disabled={hasMoved}
                  className={`${styles.compoundUnitBtn} ${isSelected ? styles.compoundUnitBtnActive : ''} ${hasMoved ? styles.compoundUnitBtnDisabled : ''}`}
                  onClick={() => onSelectPiece(member)}
                  title={hasMoved ? 'Quân này đã hoàn thành nước đi trong lượt tổ hợp' : 'Bấm để chọn quân này di chuyển'}
                >
                  {icon} {PIECE_VIETNAMESE_NAMES[member.type]}
                  {hasMoved ? ' (Đã đi)' : isSelected ? ' (Đang chọn)' : ''}
                </button>
              );
            })}
            {onConfirmCompound && (
              <button
                type="button"
                className={styles.compoundConfirmBtn}
                onClick={onConfirmCompound}
                title="Bấm để kết thúc lượt của tổ hợp ngay lập tức và chuyển quyền đi sang đối phương"
              >
                ✅ Hoàn tất lượt tổ hợp
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
