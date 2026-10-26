import React from 'react';
import { Language, translations } from '../../i18n';
import styles from './Home.module.css';

interface HomeProps {
  lang: Language;
  onNavigate: (tab: string) => void;
}

export const Home: React.FC<HomeProps> = ({ lang, onNavigate }) => {
  const t = translations[lang];

  return (
    <div className={styles.homeContainer}>
      {/* 1. Hero Introduction Section */}
      <section className={styles.heroSection}>
        <div className={styles.heroContent}>
          <div className={styles.heroBadge}>{t.home.heroBadge}</div>
          <h1 className={styles.heroTitle}>{t.home.heroTitle}</h1>
          <h2 className={styles.heroSubtitle}>{t.home.heroSubtitle}</h2>
          <p className={styles.heroDesc}>{t.home.heroDesc}</p>

          <div className={styles.heroActions}>
            <button
              type="button"
              className="btn btn-primary"
              style={{ padding: '0.8rem 1.6rem', fontSize: '1rem' }}
              onClick={() => onNavigate('play')}
            >
              <span>{t.home.btnPlayNow}</span>
              <span>→</span>
            </button>
            <button
              type="button"
              className="btn btn-secondary"
              style={{ padding: '0.8rem 1.4rem' }}
              onClick={() => onNavigate('rules')}
            >
              {t.home.btnViewRules}
            </button>
          </div>
        </div>

        {/* Visual Showcase: Key tactical pieces */}
        <div className={styles.heroVisual}>
          <div className={styles.showcaseGrid}>
            <div className={styles.showcaseCard}>
              <img
                src="/assets/pieces/red/TL_red.png"
                alt="Tư lệnh"
                className={styles.showcaseImg}
              />
              <span className={styles.showcaseLabel}>
                {lang === 'vi' ? 'Tư lệnh' : 'Commander'}
              </span>
            </div>
            <div className={styles.showcaseCard}>
              <img
                src="/assets/pieces/blue/K_blue.png"
                alt="Không quân"
                className={styles.showcaseImg}
              />
              <span className={styles.showcaseLabel}>
                {lang === 'vi' ? 'Không quân' : 'Aircraft'}
              </span>
            </div>
            <div className={styles.showcaseCard}>
              <img
                src="/assets/pieces/red/H_red.png"
                alt="Hải quân"
                className={styles.showcaseImg}
              />
              <span className={styles.showcaseLabel}>
                {lang === 'vi' ? 'Hải quân' : 'Navy'}
              </span>
            </div>
            <div className={styles.showcaseCard}>
              <img
                src="/assets/pieces/blue/T_blue.png"
                alt="Xe tăng"
                className={styles.showcaseImg}
              />
              <span className={styles.showcaseLabel}>
                {lang === 'vi' ? 'Xe tăng' : 'Tank'}
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* 2. Operational Action Hub (Large Functional Buttons) */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>{t.home.modesTitle}</h2>
        </div>

        <div className={styles.modesGrid}>
          {/* Card 1: Play vs AI (Primary Active) */}
          <div
            className={`${styles.modeCard} ${styles.modeCardPrimary}`}
            onClick={() => onNavigate('play')}
            role="button"
            tabIndex={0}
          >
            <div>
              <div className={styles.modeTop}>
                <div className={styles.modeIconBadge}>⋆</div>
                <span className="badge">{t.home.statusReady}</span>
              </div>
              <h3 className={styles.modeTitle}>{t.home.playAiTitle}</h3>
              <p className={styles.modeDesc}>{t.home.playAiDesc}</p>
            </div>
            <div className={styles.modeActionHint}>
              <span>{lang === 'vi' ? 'Bắt đầu ván đấu' : 'Launch Match'}</span>
              <span>→</span>
            </div>
          </div>

          {/* Card 2: Human vs Human (Local Hotseat) */}
          <div
            className={styles.modeCard}
            onClick={() => onNavigate('play')}
            role="button"
            tabIndex={0}
          >
            <div>
              <div className={styles.modeTop}>
                <div className={styles.modeIconBadge}>⚔</div>
                <span className="badge">{t.home.statusReady}</span>
              </div>
              <h3 className={styles.modeTitle}>{t.home.playHumanTitle}</h3>
              <p className={styles.modeDesc}>{t.home.playHumanDesc}</p>
            </div>
            <div className={styles.modeActionHint}>
              <span>{lang === 'vi' ? 'Vào bàn cờ đôi' : 'Enter Hotseat'}</span>
              <span>→</span>
            </div>
          </div>

          {/* Card 3: AI vs AI Spectator */}
          <div
            className={`${styles.modeCard} ${styles.modeCardDisabled}`}
            onClick={() => onNavigate('aiVsAi')}
            role="button"
            tabIndex={0}
          >
            <div>
              <div className={styles.modeTop}>
                <div className={styles.modeIconBadge}>◈</div>
                <span className="badge">{t.home.statusDev}</span>
              </div>
              <h3 className={styles.modeTitle}>{t.home.aiVsAiTitle}</h3>
              <p className={styles.modeDesc}>{t.home.aiVsAiDesc}</p>
            </div>
            <div className={styles.modeActionHint} style={{ color: 'var(--text-secondary)' }}>
              <span>{lang === 'vi' ? 'Xem cấu hình' : 'View Config'}</span>
              <span>→</span>
            </div>
          </div>

          {/* Card 4: Rules & Guide */}
          <div
            className={styles.modeCard}
            onClick={() => onNavigate('rules')}
            role="button"
            tabIndex={0}
          >
            <div>
              <div className={styles.modeTop}>
                <div className={styles.modeIconBadge}>📖</div>
                <span className="badge">{t.home.statusReady}</span>
              </div>
              <h3 className={styles.modeTitle}>{t.home.rulesTitle}</h3>
              <p className={styles.modeDesc}>{t.home.rulesDesc}</p>
            </div>
            <div className={styles.modeActionHint}>
              <span>{lang === 'vi' ? 'Tra cứu luật' : 'Study Tactics'}</span>
              <span>→</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. Tactical Pillars Section */}
      <section style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <div className={styles.sectionHeader}>
          <h2 className={styles.sectionTitle}>{t.home.pillarsTitle}</h2>
        </div>

        <div className={styles.pillarsGrid}>
          <div className={styles.pillarCard}>
            <div className={styles.pillarHeader}>
              <div className={styles.pillarNumber}>1</div>
              <h3 className={styles.pillarTitle}>{t.home.pillar1Title}</h3>
            </div>
            <p className={styles.pillarDesc}>{t.home.pillar1Desc}</p>
          </div>

          <div className={styles.pillarCard}>
            <div className={styles.pillarHeader}>
              <div className={styles.pillarNumber}>2</div>
              <h3 className={styles.pillarTitle}>{t.home.pillar2Title}</h3>
            </div>
            <p className={styles.pillarDesc}>{t.home.pillar2Desc}</p>
          </div>

          <div className={styles.pillarCard}>
            <div className={styles.pillarHeader}>
              <div className={styles.pillarNumber}>3</div>
              <h3 className={styles.pillarTitle}>{t.home.pillar3Title}</h3>
            </div>
            <p className={styles.pillarDesc}>{t.home.pillar3Desc}</p>
          </div>
        </div>
      </section>
    </div>
  );
};
