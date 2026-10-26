import React from 'react';
import { PieceState } from '../../types';
import { getPieceImageUrl, PIECE_VIETNAMESE_NAMES, PIECE_ENGLISH_NAMES } from '../../utils/assets';
import { formatCoordinateNotation } from '../../utils/coordinates';
import { Language, translations } from '../../i18n';
import styles from './PieceDetail.module.css';

interface PieceDetailProps {
  piece: PieceState | null;
  lang: Language;
}

export const PieceDetail: React.FC<PieceDetailProps> = ({ piece, lang }) => {
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
      </div>
    </div>
  );
};
