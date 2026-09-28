import React from 'react';
import styles from './LoadingSpinner.module.css';

export interface LoadingSpinnerProps {
  label?: string;
  fullScreen?: boolean;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  label = 'Loading...',
  fullScreen = false,
}) => {
  const containerClass = fullScreen ? styles.fullScreen : styles.inline;

  return (
    <div className={containerClass} role="status">
      <div className={styles.spinner} />
      {label && <span className={styles.label}>{label}</span>}
    </div>
  );
};
