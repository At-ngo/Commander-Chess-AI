import React from 'react';
import { Language, translations } from '../../i18n';
import styles from './Header.module.css';

interface HeaderProps {
  currentLang: Language;
  onLanguageChange: (lang: Language) => void;
  activeTab: string;
  onTabChange: (tab: string) => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentLang,
  onLanguageChange,
  activeTab,
  onTabChange,
}) => {
  const t = translations[currentLang];

  return (
    <header className={styles.header}>
      <div className={styles.container}>
        {/* Brand Logo & Name */}
        <div
          className={styles.brand}
          onClick={() => onTabChange('home')}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') onTabChange('home');
          }}
          title={t.nav.home}
        >
          <div className={styles.brandIcon}>⋆</div>
          <div className={styles.brandText}>
            <span className={styles.brandTitle}>
              {t.appName}
            </span>
            <span className={styles.brandSubtitle}>
              {t.appSubtitle}
            </span>
          </div>
        </div>

        {/* Navigation & Language Selector */}
        <nav className={styles.nav}>
          <ul className={styles.navLinks}>
            <li>
              <button
                className={`${styles.navLink} ${
                  activeTab === 'home' ? styles.navLinkActive : ''
                }`}
                onClick={() => onTabChange('home')}
              >
                {t.nav.home}
              </button>
            </li>
            <li>
              <button
                className={`${styles.navLink} ${
                  activeTab === 'play' ? styles.navLinkActive : ''
                }`}
                onClick={() => onTabChange('play')}
              >
                {t.nav.play}
              </button>
            </li>
            <li>
              <button
                className={`${styles.navLink} ${
                  activeTab === 'aiVsAi' ? styles.navLinkActive : ''
                }`}
                onClick={() => onTabChange('aiVsAi')}
              >
                {t.nav.aiVsAi}
              </button>
            </li>
            <li>
              <button
                className={`${styles.navLink} ${
                  activeTab === 'replays' ? styles.navLinkActive : ''
                }`}
                onClick={() => onTabChange('replays')}
              >
                {t.nav.replays}
              </button>
            </li>
            <li>
              <button
                className={`${styles.navLink} ${
                  activeTab === 'stats' ? styles.navLinkActive : ''
                }`}
                onClick={() => onTabChange('stats')}
              >
                {t.nav.stats}
              </button>
            </li>
            <li>
              <button
                className={`${styles.navLink} ${
                  activeTab === 'rules' ? styles.navLinkActive : ''
                }`}
                onClick={() => onTabChange('rules')}
              >
                {t.nav.rules}
              </button>
            </li>
          </ul>

          {/* Top-Right Language Selector */}
          <div className={styles.langSelector}>
            <button
              className={`${styles.langBtn} ${
                currentLang === 'vi' ? styles.langBtnActive : ''
              }`}
              onClick={() => onLanguageChange('vi')}
              title="Tiếng Việt"
            >
              VI
            </button>
            <button
              className={`${styles.langBtn} ${
                currentLang === 'en' ? styles.langBtnActive : ''
              }`}
              onClick={() => onLanguageChange('en')}
              title="English"
            >
              EN
            </button>
          </div>
        </nav>
      </div>
    </header>
  );
};
