import React, { useState } from 'react';
import { GameResult, MoveRecord, Side } from '../../types';
import { Language, translations } from '../../i18n';
import { getPieceImageUrl } from '../../utils/assets';
import styles from './GameOverModal.module.css';

interface GameOverModalProps {
  isOpen: boolean;
  result: GameResult | null;
  moves: MoveRecord[];
  lang: Language;
  onNewGame: () => void;
  onClose: () => void;
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

export const GameOverModal: React.FC<GameOverModalProps> = ({
  isOpen,
  result,
  moves,
  lang,
  onNewGame,
  onClose,
}) => {
  const [copied, setCopied] = useState(false);
  const t = translations[lang];

  if (!isOpen || !result) return null;

  const isRedWin = result.winner === 'RED';
  const isBlueWin = result.winner === 'BLUE';
  const isDraw = result.winner === 'DRAW';

  const title = isRedWin
    ? t.game.victoryRed
    : isBlueWin
    ? t.game.victoryBlue
    : t.game.drawMatch;

  let reasonDesc = '';
  if (result.reason === 'COMMANDER_CAPTURED') {
    reasonDesc = t.game.reasonCommanderCaptured;
  } else if (result.reason === 'RESIGNATION') {
    reasonDesc = t.game.reasonResignation;
  } else if (result.reason === 'MUTUAL_DRAW') {
    reasonDesc = t.game.reasonDraw;
  }

  // Format full match export with COTULENH-NOTATION header
  const handleCopyFullMatch = () => {
    const today = new Date().toISOString().split('T')[0];
    const resStr = isRedWin ? 'RED_WIN' : isBlueWin ? 'BLUE_WIN' : 'DRAW';

    // Group moves into pairs
    const pairedMoves: { turn: number; red?: MoveRecord; blue?: MoveRecord }[] = [];
    for (let i = 0; i < moves.length; i++) {
      const move = moves[i];
      const turnIndex = Math.floor(i / 2);
      if (!pairedMoves[turnIndex]) {
        pairedMoves[turnIndex] = { turn: turnIndex + 1 };
      }
      if (move.side === 'RED') {
        pairedMoves[turnIndex].red = move;
      } else {
        pairedMoves[turnIndex].blue = move;
      }
    }

    const moveLines = pairedMoves.map((p) => {
      let turnStr = `${p.turn}. Đỏ:  ${p.red ? p.red.notation : '...'}`;
      if (p.blue) {
        turnStr += `\n   Xanh: ${p.blue.notation}`;
      }
      return turnStr;
    });

    const fullExport = [
      `[Format "COTULENH-NOTATION"]`,
      `[Version "1.1"]`,
      `[Date "${today}"]`,
      `[Mode "TOTAL_FORCE"]`,
      `[Red "Commander Red"]`,
      `[Blue "Commander Blue"]`,
      `[Result "${resStr}"]`,
      `[Termination "${result.reason}"]`,
      `[FinalScore "Red: ${result.final_scores.RED} - Blue: ${result.final_scores.BLUE}"]`,
      `[Duration "${formatDuration(result.duration_seconds)}"]`,
      ``,
      ...moveLines,
    ].join('\n');

    navigator.clipboard.writeText(fullExport);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const fallenCommanderSide: Side | null =
    result.captured_commander_side ||
    (result.reason === 'COMMANDER_CAPTURED'
      ? isRedWin
        ? 'BLUE'
        : 'RED'
      : null);

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Banner with laurel and winner styling */}
        <div
          className={`${styles.banner} ${
            isRedWin
              ? styles.bannerRed
              : isBlueWin
              ? styles.bannerBlue
              : styles.bannerDraw
          }`}
        >
          <div className={styles.trophyIcon}>
            {isDraw ? '🤝' : '🎖️'}
          </div>
          <h2 className={styles.winnerTitle}>{title}</h2>
          <div className={styles.reasonBadge}>{reasonDesc}</div>
        </div>

        {/* Content body */}
        <div className={styles.body}>
          {/* Spotlight on captured Commander if applicable */}
          {result.reason === 'COMMANDER_CAPTURED' && fallenCommanderSide && (
            <div className={styles.spotlightCard}>
              <div className={styles.spotlightHeader}>
                <span className={styles.spotlightTag}>
                  {t.game.capturedCommanderTitle}
                </span>
              </div>
              <div className={styles.spotlightContent}>
                <div className={styles.avatarWrapper}>
                  <img
                    src={getPieceImageUrl('COMMANDER', fallenCommanderSide)}
                    alt="Fallen Commander"
                    className={styles.fallenAvatar}
                  />
                  <div className={styles.crossedOutBadge}>✕</div>
                </div>
                <div className={styles.spotlightText}>
                  <div className={styles.commanderName}>
                    {lang === 'vi' ? 'Tư lệnh' : 'Commander'}{' '}
                    <span
                      className={
                        fallenCommanderSide === 'RED'
                          ? styles.sideRed
                          : styles.sideBlue
                      }
                    >
                      {fallenCommanderSide === 'RED' ? t.game.redSide : t.game.blueSide}
                    </span>
                  </div>
                  <div className={styles.commanderFate}>
                    {lang === 'vi'
                      ? 'Đã bị bao vây và triệt hạ trên chiến trường!'
                      : 'Eliminated and secured on the battlefield!'}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Tactical Stats Matrix */}
          <div className={styles.statsGrid}>
            <div className={styles.statCard}>
              <span className={styles.statLabel}>{t.game.finalScore}</span>
              <div className={styles.scoreCompare}>
                <span className={styles.scoreRed}>{result.final_scores.RED}</span>
                <span className={styles.scoreVs}>:</span>
                <span className={styles.scoreBlue}>{result.final_scores.BLUE}</span>
              </div>
            </div>

            <div className={styles.statCard}>
              <span className={styles.statLabel}>{t.game.totalTurns}</span>
              <strong className={styles.statValue}>{result.total_turns}</strong>
            </div>

            <div className={styles.statCard}>
              <span className={styles.statLabel}>{t.game.totalMoves}</span>
              <strong className={styles.statValue}>{result.total_moves}</strong>
            </div>

            <div className={styles.statCard}>
              <span className={styles.statLabel}>{t.game.duration}</span>
              <strong className={styles.statValue}>
                {formatDuration(result.duration_seconds)}
              </strong>
            </div>
          </div>
        </div>

        {/* Modal Actions */}
        <div className={styles.actions}>
          <button
            type="button"
            className="btn btn-primary"
            onClick={onNewGame}
          >
            🔄 {t.game.newGame}
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleCopyFullMatch}
            title={lang === 'vi' ? 'Sao chép biên bản chuẩn COTULENH-NOTATION' : 'Copy COTULENH-NOTATION'}
          >
            {copied ? (
              <span style={{ color: '#22c55e' }}>✓ {lang === 'vi' ? 'Đã sao chép biên bản' : 'Copied!'}</span>
            ) : (
              <span>📋 {lang === 'vi' ? 'Sao chép biên bản' : 'Copy Notation'}</span>
            )}
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
            title={t.game.btnReviewBoard}
          >
            👁️ {t.game.btnReviewBoard}
          </button>
        </div>
      </div>
    </div>
  );
};
