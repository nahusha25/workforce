import { useCallback, useEffect, useState } from 'react';

export function useCountdown(initialSeconds: number = 300) {
  const [secondsLeft, setSecondsLeft] = useState<number>(initialSeconds);
  const [isActive, setIsActive] = useState<boolean>(false);

  useEffect(() => {
    let interval: number | undefined;
    if (isActive && secondsLeft > 0) {
      interval = window.setInterval(() => {
        setSecondsLeft((prev) => prev - 1);
      }, 1000);
    } else if (secondsLeft === 0) {
      setIsActive(false);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isActive, secondsLeft]);

  const startTimer = useCallback((seconds?: number) => {
    setSecondsLeft(seconds !== undefined ? seconds : initialSeconds);
    setIsActive(true);
  }, [initialSeconds]);

  const resetTimer = useCallback(() => {
    setSecondsLeft(initialSeconds);
    setIsActive(true);
  }, [initialSeconds]);

  const stopTimer = useCallback(() => {
    setIsActive(false);
  }, []);

  const minutes = Math.floor(secondsLeft / 60);
  const seconds = secondsLeft % 60;
  const formattedTime = `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;

  return {
    secondsLeft,
    isExpired: secondsLeft === 0,
    isActive,
    formattedTime,
    startTimer,
    resetTimer,
    stopTimer,
  };
}
