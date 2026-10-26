import React from 'react';
import { PieceState, PieceType } from '../../types';
import { getPieceImageUrl, PIECE_VIETNAMESE_NAMES } from '../../utils/assets';
import { Language } from '../../i18n';
import styles from './CapturedPieces.module.css';

interface CapturedPiecesProps {
  capturedPieces: PieceState[];
  lang: Language;
}

export const CapturedPieces: React.FC<CapturedPiecesProps> = ({ capturedPieces, lang }) => {
  const redCaptured = capturedPieces.filter((p) => p.side === 'RED');
  const blueCaptured = capturedPieces.filter((p) => p.side === 'BLUE');

  const groupByType = (pieces: PieceState[]) => {
    const map = new Map<PieceType, number>();
    for (const p of pieces) {
      map.set(p.type, (map.get(p.type) || 0) + 1);
    }
    return Array.from(map.entries());
  };

  const redGroups = groupByType(redCaptured);
  const blueGroups = groupByType(blueCaptured);

  return (
    <div className={`tactical-panel ${styles.container}`}>
      <div className={styles.header}>
        <span className={styles.title}>
          {lang === 'vi' ? 'Tổn thất chiến trường' : 'Casualties Tracker'}
        </span>
        <span className="badge">
          {capturedPieces.length} {lang === 'vi' ? 'quân' : 'lost'}
        </span>
      </div>

      {/* Red Casualties */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>
          <span className={styles.labelRed}>
            {lang === 'vi' ? 'Phe Đỏ tổn thất' : 'Red Casualties'}
          </span>
          <span className={styles.labelRed}>{redCaptured.length}</span>
        </div>
        <div className={styles.piecesRow}>
          {redGroups.length === 0 ? (
            <span className={styles.emptyText}>
              {lang === 'vi' ? 'Chưa có tổn thất' : 'No casualties'}
            </span>
          ) : (
            redGroups.map(([type, count]) => (
              <div
                key={`red-cap-${type}`}
                className={styles.pieceBadge}
                title={`${PIECE_VIETNAMESE_NAMES[type] || type} x${count}`}
              >
                <img
                  src={getPieceImageUrl(type, 'RED')}
                  alt={type}
                  className={styles.pieceImg}
                />
                {count > 1 && <span className={styles.pieceCount}>x{count}</span>}
              </div>
            ))
          )}
        </div>
      </div>

      {/* Blue Casualties */}
      <div className={styles.section}>
        <div className={styles.sectionLabel}>
          <span className={styles.labelBlue}>
            {lang === 'vi' ? 'Phe Xanh tổn thất' : 'Blue Casualties'}
          </span>
          <span className={styles.labelBlue}>{blueCaptured.length}</span>
        </div>
        <div className={styles.piecesRow}>
          {blueGroups.length === 0 ? (
            <span className={styles.emptyText}>
              {lang === 'vi' ? 'Chưa có tổn thất' : 'No casualties'}
            </span>
          ) : (
            blueGroups.map(([type, count]) => (
              <div
                key={`blue-cap-${type}`}
                className={styles.pieceBadge}
                title={`${PIECE_VIETNAMESE_NAMES[type] || type} x${count}`}
              >
                <img
                  src={getPieceImageUrl(type, 'BLUE')}
                  alt={type}
                  className={styles.pieceImg}
                />
                {count > 1 && <span className={styles.pieceCount}>x{count}</span>}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
};
