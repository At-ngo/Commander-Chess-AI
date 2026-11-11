import React, { useRef, useEffect } from 'react';
import { MoveRecord } from '../../types';
import { Language, translations } from '../../i18n';
import { formatMoveRecordsForRecordInput } from '../../utils/recordAnalyzer';
import styles from './MoveHistory.module.css';

interface MoveHistoryProps {
  moves: MoveRecord[];
  lang: Language;
  activeSnapshotIndex?: number;
  totalSnapshots?: number;
  onNavigateSnapshot?: (snapshotIndex: number | null) => void;
}

export const MoveHistory: React.FC<MoveHistoryProps> = ({
  moves,
  lang,
  activeSnapshotIndex,
  totalSnapshots,
  onNavigateSnapshot,
}) => {
  const listRef = useRef<HTMLDivElement>(null);
  const t = translations[lang];

  // Group moves cleanly by round without overwriting consecutive same-side compound moves
  const pairedMoves: { turn: number; red?: MoveRecord; blue?: MoveRecord }[] = [];
  for (const move of moves) {
    const lastRow = pairedMoves[pairedMoves.length - 1];
    if (move.side === 'RED') {
      if (!lastRow || lastRow.red || lastRow.blue) {
        pairedMoves.push({ turn: pairedMoves.length + 1, red: move });
      } else {
        lastRow.red = move;
      }
    } else {
      if (!lastRow || lastRow.blue) {
        pairedMoves.push({ turn: pairedMoves.length + 1, blue: move });
      } else {
        lastRow.blue = move;
      }
    }
  }

  const [copied, setCopied] = React.useState(false);

  const maxIdx = Math.max(0, (totalSnapshots ?? moves.length + 1) - 1);
  const currentIdx = activeSnapshotIndex ?? maxIdx;

  // Auto-scroll to bottom on new move only when viewing the live tail
  useEffect(() => {
    if (listRef.current && currentIdx >= maxIdx) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [moves.length, currentIdx, maxIdx]);

  const isSoloSplitMove = (move?: MoveRecord): boolean =>
    Boolean(
      move &&
        (move.action?.action_type === 'MOVE' ||
          move.action?.action_type === 'CAPTURE_REPLACE') &&
        move.action?.carry_cargo === false &&
        !/\{[^}]*carry(?:_cargo)?\s*=/i.test(move.notation || '')
    );

  const formatCopyNotation = (move: MoveRecord) => {
    const base = (move.notation || '').trim();
    if (isSoloSplitMove(move)) {
      return `${base} {carry=0}`;
    }
    return base;
  };

  const handleCopyNotation = () => {
    if (moves.length === 0) return;
    navigator.clipboard.writeText(formatMoveRecordsForRecordInput(moves));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatNotation = (notation?: string) => {
    if (!notation) return '—';
    if (notation.includes('> **') && notation.includes('**')) {
      const parts = notation.split(/(> \*\*[^*]+\*\*)/g);
      return parts.map((part, idx) => {
        if (part.startsWith('> **') && part.endsWith('**')) {
          const sym = part.slice(4, -2);
          return (
            <span key={idx} style={{ color: 'var(--gold-primary)', fontWeight: 800 }}>
              {`> `}★{sym}
            </span>
          );
        }
        return part;
      });
    }
    return notation;
  };

  const renderMoveCell = (move: MoveRecord | undefined, side: 'RED' | 'BLUE') => {
    const isRed = side === 'RED';
    const isActive = move && currentIdx === move.move_number;
    const clickable = Boolean(move && onNavigateSnapshot);
    const soloSuffix = isSoloSplitMove(move) ? ' {carry=0}' : '';

    const handleClick = () => {
      if (!move || !onNavigateSnapshot) return;
      onNavigateSnapshot(move.move_number >= maxIdx ? null : move.move_number);
    };

    return (
      <button
        type="button"
        disabled={!clickable}
        onClick={handleClick}
        className={`${styles.moveCell} ${clickable ? styles.moveCellClickable : ''} ${
          isActive ? styles.moveCellActive : ''
        }`}
        title={move ? formatCopyNotation(move) : ''}
      >
        <span className={isRed ? styles.sideBadgeRed : styles.sideBadgeBlue}>
          {isRed ? (lang === 'vi' ? 'Đỏ: ' : 'Red: ') : lang === 'vi' ? 'Xanh: ' : 'Blue: '}
        </span>
        <span className={isRed ? styles.moveRed : styles.moveBlue}>
          {formatNotation(move?.notation)}
          {soloSuffix}
        </span>
      </button>
    );
  };

  return (
    <div className={`tactical-panel ${styles.container}`}>
      <div className={styles.header}>
        <span className={styles.title}>
          {lang === 'vi' ? 'Biên bản tác chiến' : 'Action Log'}
        </span>
        {moves.length > 0 && (
          <button
            type="button"
            className={styles.copyBtn}
            onClick={handleCopyNotation}
            title={lang === 'vi' ? 'Sao chép biên bản tác chiến' : 'Copy Move Notation'}
          >
            {copied ? (
              <span style={{ color: '#22c55e' }}>✓ {lang === 'vi' ? 'Đã chép' : 'Copied!'}</span>
            ) : (
              <span>📋 {lang === 'vi' ? 'Sao chép' : 'Copy'}</span>
            )}
          </button>
        )}
      </div>

      {onNavigateSnapshot && maxIdx > 0 && (
        <div className={styles.miniNavBar}>
          <button
            type="button"
            className={styles.miniNavBtn}
            disabled={currentIdx <= 0}
            onClick={() => onNavigateSnapshot(0)}
            title={t.game.navFirst}
          >
            ⏮
          </button>
          <button
            type="button"
            className={styles.miniNavBtn}
            disabled={currentIdx <= 0}
            onClick={() => onNavigateSnapshot(Math.max(0, currentIdx - 1))}
            title={t.game.navPrev}
          >
            ◀
          </button>
          <span className={styles.miniNavCounter}>
            {currentIdx}/{maxIdx}
          </span>
          <button
            type="button"
            className={styles.miniNavBtn}
            disabled={currentIdx >= maxIdx}
            onClick={() =>
              onNavigateSnapshot(currentIdx + 1 >= maxIdx ? null : currentIdx + 1)
            }
            title={t.game.navNext}
          >
            ▶
          </button>
          <button
            type="button"
            className={styles.miniNavBtn}
            disabled={currentIdx >= maxIdx}
            onClick={() => onNavigateSnapshot(null)}
            title={t.game.navLast}
          >
            ⏭
          </button>
        </div>
      )}

      <div className={styles.list} ref={listRef}>
        {pairedMoves.length === 0 ? (
          <div className={styles.emptyState}>
            {lang === 'vi'
              ? 'Chưa có nước đi nào. Chọn quân cờ và click điểm đến để đi thử.'
              : 'No moves recorded yet. Select a piece and click a target to test.'}
          </div>
        ) : (
          pairedMoves.map((pair) => (
            <div key={`turn-${pair.turn}`} className={styles.row}>
              <span className={styles.turnNum}>{pair.turn}.</span>
              {renderMoveCell(pair.red, 'RED')}
              {renderMoveCell(pair.blue, 'BLUE')}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
