import React from 'react';
import { PieceState } from '../../types';
import { getPieceImageUrl, PIECE_VIETNAMESE_NAMES, PIECE_ENGLISH_NAMES } from '../../utils/assets';
import { formatCoordinateNotation } from '../../utils/coordinates';
import { Language, translations } from '../../i18n';
import { getRootCarrier, getAllCarriedPieceIds } from '../../services/mockGameService';
import styles from './PieceDetail.module.css';

interface PieceDetailProps {
  piece: PieceState | null;
  allPieces?: PieceState[];
  onSelectPiece?: (piece: PieceState) => void;
  lang: Language;
  movedPieceIds?: string[];
  readOnly?: boolean;
}

export const PieceDetail: React.FC<PieceDetailProps> = ({
  piece,
  allPieces = [],
  onSelectPiece,
  lang,
  movedPieceIds = [],
  readOnly = false,
}) => {
  const t = translations[lang];

  if (!piece) {
    return (
      <div className={`tactical-panel ${styles.panel}`}>
        <h3 className={styles.title}>{t.game.selectedPiece}</h3>
        <p className={styles.emptyState}>{t.game.noPieceSelected}</p>
      </div>
    );
  }

  const pieceName =
    lang === 'vi' ? PIECE_VIETNAMESE_NAMES[piece.type] : PIECE_ENGLISH_NAMES[piece.type];
  const sideName = piece.side === 'RED' ? t.game.redSide : t.game.blueSide;
  const imgUrl = getPieceImageUrl(piece.type, piece.side);

  // Find root compound carrier and nested passengers if this piece is in a transport relationship
  const rootCarrier = getRootCarrier(piece, allPieces);
  const rootPassengers = getAllCarriedPieceIds(rootCarrier.piece_id, allPieces)
    .map((id) => allPieces.find((p) => p.is_alive && p.piece_id === id))
    .filter((p): p is PieceState => Boolean(p));
  const compoundCarrier =
    piece.carried_by_id || rootPassengers.length > 0 ? rootCarrier : null;
  const compoundPassengers = compoundCarrier ? rootPassengers : [];
  const directCarrier = piece.carried_by_id
    ? allPieces.find((p) => p.piece_id === piece.carried_by_id) || null
    : null;

  return (
    <div className={`tactical-panel ${styles.panel}`}>
      <h3 className={styles.title}>{t.game.selectedPiece}</h3>

      <div className={styles.pieceCard}>
        <img
          src={imgUrl}
          alt={pieceName}
          className={styles.pieceAvatar}
        />
        <div className={styles.pieceInfo}>
          <span className={styles.pieceName}>{pieceName}</span>
          <span
            className={
              piece.side === 'RED' ? styles.pieceSideRed : styles.pieceSideBlue
            }
          >
            {sideName}
          </span>
        </div>
      </div>

      <div className={styles.specsList}>
        <div className={styles.specRow}>
          <span className={styles.specLabel}>{t.game.coordinates}</span>
          <span className={styles.specValue}>
            {formatCoordinateNotation(piece.position)} (x={piece.position.x}, y={piece.position.y})
          </span>
        </div>
        <div className={styles.specRow}>
          <span className={styles.specLabel}>ID</span>
          <span className={styles.specValue}>{piece.piece_id}</span>
        </div>
        <div className={styles.specRow}>
          <span className={styles.specLabel}>{lang === 'vi' ? 'Anh hùng' : 'Heroic'}</span>
          <span className={styles.specValue}>
            {piece.is_hero ? (
              <span style={{ color: 'var(--gold-primary)' }}>★ {lang === 'vi' ? 'Đã phong' : 'Yes'}</span>
            ) : (
              lang === 'vi' ? 'Chưa' : 'No'
            )}
          </span>
        </div>
        <div className={styles.specRow}>
          <span className={styles.specLabel}>{lang === 'vi' ? 'Đang chở' : 'Carrying'}</span>
          <span className={styles.specValue}>
            {piece.carrying_piece_ids.length > 0
              ? `${piece.carrying_piece_ids.length} ${lang === 'vi' ? 'quân' : 'units'}`
              : lang === 'vi' ? 'Không' : 'None'}
          </span>
        </div>
        {piece.carried_by_id && (
          <div className={styles.specRow}>
            <span className={styles.specLabel}>{lang === 'vi' ? 'Nơi trú/xe' : 'Onboard'}</span>
            <span className={styles.specValue} style={{ color: 'var(--gold-primary)' }}>
              {directCarrier
                ? lang === 'vi'
                  ? PIECE_VIETNAMESE_NAMES[directCarrier.type]
                  : PIECE_ENGLISH_NAMES[directCarrier.type]
                : piece.carried_by_id}
            </span>
          </div>
        )}
      </div>

      {/* Compound Units Selector in Side Panel */}
      {compoundCarrier && (compoundPassengers.length > 0 || compoundCarrier.piece_id !== piece.piece_id) && (
        <div className={styles.compoundSection}>
          <span className={styles.compoundTitle}>
            {lang === 'vi' ? 'Tổ hợp tác chiến' : 'Compound Units'}
          </span>

          {/* Carrier */}
          {(() => {
            const carrierHasMoved = movedPieceIds.includes(compoundCarrier.piece_id);
            const carrierName =
              lang === 'vi'
                ? PIECE_VIETNAMESE_NAMES[compoundCarrier.type]
                : PIECE_ENGLISH_NAMES[compoundCarrier.type];
            const carrierDisabled =
              carrierHasMoved || (compoundCarrier.type === 'HEADQUARTERS' && !compoundCarrier.is_hero);
            return (
              <div
                className={`${styles.compoundRow} ${
                  piece.piece_id === compoundCarrier.piece_id ? styles.compoundItemActive : ''
                }`}
              >
                <span className={styles.compoundItemName}>
                  <img
                    src={getPieceImageUrl(compoundCarrier.type, compoundCarrier.side)}
                    alt={carrierName}
                    className={styles.compoundPieceImg}
                  />
                  <span>
                    {carrierName} ({lang === 'vi' ? 'Phương tiện' : 'Carrier'})
                  </span>
                </span>
                {onSelectPiece && piece.piece_id !== compoundCarrier.piece_id && !readOnly && (
                  <button
                    type="button"
                    disabled={carrierDisabled}
                    className={styles.compoundSelectBtn}
                    onClick={() => onSelectPiece(compoundCarrier)}
                  >
                    {carrierHasMoved
                      ? lang === 'vi'
                        ? 'Đã đi'
                        : 'Acted'
                      : compoundCarrier.type === 'HEADQUARTERS' && !compoundCarrier.is_hero
                      ? lang === 'vi'
                        ? 'Bất động'
                        : 'Immobile'
                      : lang === 'vi'
                      ? 'Chọn xe'
                      : 'Select'}
                  </button>
                )}
              </div>
            );
          })()}

          {/* Passengers */}
          {compoundPassengers.map((psg) => {
            const psgName =
              lang === 'vi' ? PIECE_VIETNAMESE_NAMES[psg.type] : PIECE_ENGLISH_NAMES[psg.type];
            const psgHasMoved = movedPieceIds.includes(psg.piece_id);
            return (
              <div
                key={psg.piece_id}
                className={`${styles.compoundRow} ${
                  piece.piece_id === psg.piece_id ? styles.compoundItemActive : ''
                }`}
              >
                <span className={styles.compoundItemName}>
                  <img
                    src={getPieceImageUrl(psg.type, psg.side)}
                    alt={psgName}
                    className={styles.compoundPieceImg}
                  />
                  <span>
                    {psgName}
                    {psg.type === 'COMMANDER'
                      ? lang === 'vi'
                        ? ' (Tư lệnh)'
                        : ' (Commander)'
                      : ''}
                  </span>
                </span>
                {onSelectPiece && piece.piece_id !== psg.piece_id && !readOnly && (
                  <button
                    type="button"
                    disabled={psgHasMoved}
                    className={styles.compoundSelectBtn}
                    onClick={() => onSelectPiece(psg)}
                  >
                    {psgHasMoved
                      ? lang === 'vi'
                        ? 'Đã đi'
                        : 'Acted'
                      : lang === 'vi'
                      ? 'Chọn quân'
                      : 'Select'}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
