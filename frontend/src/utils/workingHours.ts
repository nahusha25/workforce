/**
 * Formats decimal working hours into a readable, rounded duration string.
 *
 * Rules:
 * - Converts decimal hours to total minutes and rounds to the nearest whole minute.
 * - 0 hours -> "0 min"
 * - Sub-hour durations -> "X min" (e.g., 0.5h -> "30 min", 0.75h -> "45 min")
 * - Exact hours -> "1 hr" or "X hrs" (e.g., 1h -> "1 hr", 5h -> "5 hrs")
 * - Mixed hours and minutes -> "1 hr Y min" or "X hrs Y min" (e.g., 5.5h -> "5 hrs 30 min", 7.25h -> "7 hrs 15 min")
 * - null, undefined, empty, invalid (NaN/Infinity), or negative values -> fallback (default '—')
 *
 * @param hours Decimal hours as number or string
 * @param fallback String to display when input is null, undefined, invalid, or negative
 */
export function formatWorkingHours(
  hours: number | string | null | undefined,
  fallback: string = '—'
): string {
  if (
    hours === null ||
    hours === undefined ||
    (typeof hours === 'string' && hours.trim() === '')
  ) {
    return fallback;
  }

  const num = typeof hours === 'number' ? hours : Number(hours);
  if (isNaN(num) || !isFinite(num) || num < 0) {
    return fallback;
  }

  const totalMinutes = Math.round(num * 60);

  if (totalMinutes === 0) {
    return '0 min';
  }

  const h = Math.floor(totalMinutes / 60);
  const m = totalMinutes % 60;

  if (h === 0) {
    return `${m} min`;
  }

  const hourLabel = h === 1 ? '1 hr' : `${h} hrs`;

  if (m === 0) {
    return hourLabel;
  }

  return `${hourLabel} ${m} min`;
}
