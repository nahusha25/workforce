/**
 * Returns YYYY-MM-DD formatted string using local browser date (not UTC).
 * This ensures that users near midnight in positive/negative UTC offset zones
 * always have their current local calendar day selected by default.
 */
export function getLocalISODate(d: Date = new Date()): string {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

const ISO_DATE_REGEX = /^\d{4}-\d{2}-\d{2}$/;

/**
 * Validates whether a string is a valid YYYY-MM-DD calendar date.
 */
export function isValidISODate(val: string | null | undefined): boolean {
  if (!val || !ISO_DATE_REGEX.test(val)) {
    return false;
  }
  const [y, m, d] = val.split('-').map(Number);
  const parsed = new Date(y, m - 1, d);
  return (
    parsed.getFullYear() === y &&
    parsed.getMonth() === m - 1 &&
    parsed.getDate() === d
  );
}
