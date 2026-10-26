import React, { useRef, useEffect } from 'react';
import { MoveRecord } from '../../types';
import { Language } from '../../i18n';
import styles from './MoveHistory.module.css';

interface MoveHistoryProps {
  moves: MoveRecord[];
  lang: Language;
}

export const MoveHistory: React.FC<MoveHistoryProps> = ({ moves, lang }) => {
  const listRef = useRef<HTMLDivElement>(null);

  // Group moves into pairs (Turn: Red move, Blue move)
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

  const [copied, setCopied] = React.useState(false);

  // Auto-scroll to bottom on new move
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [moves.length]);

  const handleCopyNotation = () => {
    if (pairedMoves.length === 0) return;
    const lines = pairedMoves.map((p) => {
      let turnStr = `${p.turn}. Đỏ:  ${p.red ? p.red.notation : '...'}`;
      if (p.blue) {
        turnStr += `\n   Xanh: ${p.blue.notation}`;
      }
      return turnStr;
    });
    navigator.clipboard.writeText(lines.join('\n'));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
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
              <span style={{ color: '#22c55e' }}>✓ {lang === 'vi' ? 'Đã sao chép' : 'Copied!'}</span>
            ) : (
              <span>📋 {lang === 'vi' ? 'Sao chép' : 'Copy'}</span>
            )}
          </button>
        )}
      </div>

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
              <div className={styles.moveCell}>
                <span className={styles.sideBadgeRed}>Đỏ</span>
                <span className={styles.moveRed}>
                  {pair.red ? pair.red.notation : '—'}
                </span>
              </div>
              <div className={styles.moveCell}>
                <span className={styles.sideBadgeBlue}>Xanh</span>
                <span className={styles.moveBlue}>
                  {pair.blue ? pair.blue.notation : '—'}
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
