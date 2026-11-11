import React, { useMemo } from 'react';
import { ActiveCompoundState, PieceState } from '../../types';
import { Language } from '../../i18n';
import {
  getPieceImageUrl,
  PIECE_ENGLISH_NAMES,
  PIECE_VIETNAMESE_NAMES,
} from '../../utils/assets';
import {
  canCarrierLeaveCargoBehind,
  getAllCarriedPieceIds,
  getRootCarrier,
} from '../../services/mockGameService';
import styles from './CompoundControlBar.module.css';

interface CompoundControlBarProps {
  pieces: PieceState[];
  selectedPieceId: string | null;
  activeCompound?: ActiveCompoundState | null;
  carryCargo?: boolean;
  onToggleCarryCargo?: (carry: boolean) => void;
  onSelectPiece: (piece: PieceState) => void;
  onConfirmCompound?: () => void;
  lang: Language;
  readOnly?: boolean;
}

export const CompoundControlBar: React.FC<CompoundControlBarProps> = ({
  pieces,
  selectedPieceId,
  activeCompound,
  carryCargo = true,
  onToggleCarryCargo,
  onSelectPiece,
  onConfirmCompound,
  lang,
  readOnly = false,
}) => {
  const selectedPiece = pieces.find((p) => p.piece_id === selectedPieceId) || null;

  const isSelectedCarrierWithCargo = Boolean(
    selectedPiece &&
      !selectedPiece.carried_by_id &&
      selectedPiece.carrying_piece_ids &&
      selectedPiece.carrying_piece_ids.length > 0 &&
      selectedPiece.type !== 'HEADQUARTERS'
  );

  const canCarrierLeave = useMemo(() => {
    if (!selectedPiece || !isSelectedCarrierWithCargo) return true;
    return canCarrierLeaveCargoBehind(selectedPiece, pieces);
  }, [selectedPiece, isSelectedCarrierWithCargo, pieces]);

  const compoundCarrier = useMemo(() => {
    if (activeCompound) {
      const members = pieces.filter(
        (p) => p.is_alive && activeCompound.memberIds.includes(p.piece_id)
      );
      const root = members.find((p) => !p.carried_by_id) || members[0];
      return root || null;
    }
    if (!selectedPiece) return null;
    const root = getRootCarrier(selectedPiece, pieces);
    const hasActivePassengers = getAllCarriedPieceIds(root.piece_id, pieces).length > 0;
    if (selectedPiece.carried_by_id || hasActivePassengers) {
      return root;
    }
    return null;
  }, [selectedPiece, pieces, activeCompound]);

  const displayedCompoundMembers = useMemo(() => {
    if (activeCompound) {
      const members = pieces.filter(
        (p) => p.is_alive && activeCompound.memberIds.includes(p.piece_id)
      );
      return [...members].sort((a, b) => {
        if (!a.carried_by_id && b.carried_by_id) return -1;
        if (a.carried_by_id && !b.carried_by_id) return 1;
        return 0;
      });
    }
    if (!compoundCarrier) return [];
    const nestedIds = getAllCarriedPieceIds(compoundCarrier.piece_id, pieces);
    if (nestedIds.length === 0) return [];
    const passengers = nestedIds
      .map((id) => pieces.find((p) => p.is_alive && p.piece_id === id))
      .filter((p): p is PieceState => Boolean(p));
    return [compoundCarrier, ...passengers];
  }, [activeCompound, compoundCarrier, pieces]);

  if (displayedCompoundMembers.length <= 1) {
    return null;
  }

  const posY = compoundCarrier ? compoundCarrier.position.y : activeCompound?.originPos.y ?? 0;
  const posX = compoundCarrier ? compoundCarrier.position.x : activeCompound?.originPos.x ?? 0;

  return (
    <div className={styles.compoundBar}>
      <div className={styles.compoundHeader}>
        <div className={styles.compoundHeaderLeft}>
          {compoundCarrier && (
            <img
              src={getPieceImageUrl(compoundCarrier.type, compoundCarrier.side)}
              alt={compoundCarrier.type}
              className={styles.headerCarrierImg}
            />
          )}
          <span className={styles.compoundBadge}>
            {compoundCarrier?.type === 'HEADQUARTERS'
              ? lang === 'vi'
                ? 'SỞ CHỈ HUY & TƯ LỆNH'
                : 'HEADQUARTERS & COMMANDER'
              : lang === 'vi'
              ? 'TỔ HỢP CÕNG QUÂN'
              : 'COMPOUND TRANSPORT UNIT'}
            {activeCompound
              ? lang === 'vi'
                ? ' (ĐANG TÁC CHIẾN)'
                : ' (ACTIVE TURN)'
              : ''}
          </span>
        </div>
        <span className={styles.compoundCoords}>
          [{posY} ; {posX}]
        </span>
      </div>

      {isSelectedCarrierWithCargo && !readOnly && (
        <div className={styles.cargoToggleContainer}>
          <label className={styles.cargoToggleLabel}>
            <input
              type="checkbox"
              checked={carryCargo}
              disabled={!canCarrierLeave}
              onChange={(e) => onToggleCarryCargo?.(e.target.checked)}
            />
            <span className={styles.cargoToggleText}>
              {carryCargo
                ? lang === 'vi'
                  ? 'Cõng theo quân khi di chuyển'
                  : 'Carry passengers when moving'
                : lang === 'vi'
                ? 'Tách lẻ đi một mình (để lại quân ở gốc)'
                : 'Move solo (leave passengers at origin)'}
            </span>
          </label>
          {!canCarrierLeave && (
            <span
              className={styles.cargoWarningNotice}
              title={
                lang === 'vi'
                  ? 'Quy tắc 2: Phương tiện chở 2 quân không thể chở lẫn nhau thì không thể tách lẻ bỏ lại cả hai!'
                  : 'Rule 2: A carrier holding 2 pieces that cannot transport each other cannot depart alone!'
              }
            >
              ⚠️ {lang === 'vi' ? 'Bắt buộc cõng (Quy tắc 2)' : 'Must carry cargo (Rule 2)'}
            </span>
          )}
        </div>
      )}

      <div className={styles.compoundUnitsList}>
        {displayedCompoundMembers.map((member) => {
          const hasMoved = Boolean(activeCompound?.movedPieceIds.includes(member.piece_id));
          const isSelected = selectedPieceId === member.piece_id;
          const isHQ = member.type === 'HEADQUARTERS';
          const isCarrier = member.piece_id === compoundCarrier?.piece_id;
          const memberName =
            lang === 'vi'
              ? PIECE_VIETNAMESE_NAMES[member.type]
              : PIECE_ENGLISH_NAMES[member.type];
          const memberImg = getPieceImageUrl(member.type, member.side);

          if (isHQ && !member.is_hero) {
            return (
              <div key={member.piece_id} className={styles.immobileUnitBadge}>
                <img src={memberImg} alt={memberName} className={styles.unitImg} />
                <div className={styles.unitTextCol}>
                  <span className={styles.unitName}>{memberName}</span>
                  <span className={styles.unitMeta}>
                    {lang === 'vi' ? 'Bất động' : 'Immobile'}
                  </span>
                </div>
              </div>
            );
          }

          return (
            <button
              key={member.piece_id}
              type="button"
              disabled={!readOnly && hasMoved}
              className={`${styles.compoundUnitBtn} ${
                isSelected ? styles.compoundUnitBtnActive : ''
              } ${hasMoved ? styles.compoundUnitBtnDisabled : ''}`}
              onClick={() => onSelectPiece(member)}
              title={
                readOnly
                  ? lang === 'vi'
                    ? 'Bấm để xem thông tin quân này'
                    : 'Click to inspect this piece'
                  : hasMoved
                  ? lang === 'vi'
                    ? 'Quân này đã hoàn thành nước đi trong lượt tổ hợp'
                    : 'This piece already moved this compound turn'
                  : lang === 'vi'
                  ? 'Bấm để chọn quân này điều khiển'
                  : 'Click to select this piece'
              }
            >
              <div className={styles.unitImgWrapper}>
                <img src={memberImg} alt={memberName} className={styles.unitImg} />
                {member.is_hero && <span className={styles.unitHeroStar}>★</span>}
              </div>
              <div className={styles.unitTextCol}>
                <span className={styles.unitName}>{memberName}</span>
                <span className={styles.unitMeta}>
                  {hasMoved
                    ? lang === 'vi'
                      ? 'Đã đi'
                      : 'Acted'
                    : isSelected
                    ? lang === 'vi'
                      ? 'Đang chọn'
                      : 'Selected'
                    : isCarrier
                    ? lang === 'vi'
                      ? 'Phương tiện'
                      : 'Carrier'
                    : lang === 'vi'
                    ? 'Được cõng'
                    : 'Passenger'}
                </span>
              </div>
            </button>
          );
        })}

        {!readOnly && activeCompound && onConfirmCompound && (
          <button
            type="button"
            className={styles.compoundConfirmBtn}
            onClick={onConfirmCompound}
            title={
              lang === 'vi'
                ? 'Bấm để kết thúc lượt của tổ hợp ngay lập tức và chuyển quyền đi sang đối phương'
                : 'Finish this compound turn immediately and hand turn to opponent'
            }
          >
            ✓ {lang === 'vi' ? 'Hoàn tất lượt tổ hợp' : 'End Compound Turn'}
          </button>
        )}
      </div>
    </div>
  );
};

