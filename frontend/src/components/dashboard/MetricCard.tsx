import React from 'react';
import styles from './MetricCard.module.css';

export interface MetricCardProps {
  title: string;
  value?: string | number | null;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: {
    direction: 'up' | 'down' | 'neutral';
    text: string;
  };
  isLoading?: boolean;
  isError?: boolean;
  onClick?: () => void;
  testId?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  isLoading = false,
  isError = false,
  onClick,
  testId,
}) => {
  const cardClasses = [
    styles.card,
    onClick ? styles.clickable : '',
  ]
    .filter(Boolean)
    .join(' ');

  if (isLoading) {
    return (
      <div className={styles.card} data-testid={testId || 'metric-card-loading'}>
        <div className={styles.header}>
          <div className={`${styles.skeleton} ${styles.skeletonTitle}`} />
          {icon && <div className={styles.iconWrapper}>{icon}</div>}
        </div>
        <div className={styles.content}>
          <div className={`${styles.skeleton} ${styles.skeletonValue}`} />
          <div className={`${styles.skeleton} ${styles.skeletonSubtitle}`} />
        </div>
      </div>
    );
  }

  const trendClass =
    trend?.direction === 'up'
      ? styles.trendUp
      : trend?.direction === 'down'
      ? styles.trendDown
      : styles.trendNeutral;

  return (
    <div
      className={cardClasses}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                onClick();
              }
            }
          : undefined
      }
      data-testid={testId || `metric-card-${title.toLowerCase().replace(/\s+/g, '-')}`}
    >
      <div className={styles.header}>
        <h3 className={styles.title}>{title}</h3>
        {icon && <div className={styles.iconWrapper}>{icon}</div>}
      </div>

      <div className={styles.content}>
        {isError ? (
          <div className={styles.errorBanner}>Failed to load metric</div>
        ) : (
          <div className={styles.value}>
            {value !== undefined && value !== null ? value : '-'}
          </div>
        )}

        {(subtitle || trend) && (
          <div className={styles.footer}>
            {trend && (
              <span className={`${styles.trend} ${trendClass}`}>
                {trend.direction === 'up' && '↑ '}
                {trend.direction === 'down' && '↓ '}
                {trend.text}
              </span>
            )}
            {subtitle && <span className={styles.subtitle}>{subtitle}</span>}
          </div>
        )}
      </div>
    </div>
  );
};
