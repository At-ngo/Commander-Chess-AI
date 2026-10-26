import React from 'react';
import { Language, translations } from '../../i18n';
import styles from './ConfirmModal.module.css';

interface ConfirmModalProps {
  isOpen: boolean;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  isDanger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
  lang: Language;
}

export const ConfirmModal: React.FC<ConfirmModalProps> = ({
  isOpen,
  title,
  description,
  confirmLabel,
  cancelLabel,
  isDanger = false,
  onConfirm,
  onCancel,
  lang,
}) => {
  const t = translations[lang];

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onCancel} role="dialog" aria-modal="true">
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.icon}>{isDanger ? '⚠️' : 'ℹ️'}</div>
          <h3 className={styles.title}>{title}</h3>
        </div>

        <div className={styles.body}>
          <p className={styles.description}>{description}</p>
        </div>

        <div className={styles.actions}>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={onCancel}
          >
            {cancelLabel || t.game.confirmCancel}
          </button>
          <button
            type="button"
            className={`btn ${isDanger ? 'btn-primary' : 'btn-primary'}`}
            style={isDanger ? { background: 'var(--team-red)', borderColor: 'var(--team-red)', color: '#ffffff' } : {}}
            onClick={onConfirm}
          >
            {confirmLabel || t.game.confirmYes}
          </button>
        </div>
      </div>
    </div>
  );
};
