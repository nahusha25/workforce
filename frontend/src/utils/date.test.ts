import { describe, it, expect } from 'vitest';
import { getLocalISODate, isValidISODate } from './date';

describe('date utils', () => {
  describe('getLocalISODate', () => {
    it('formats a date to YYYY-MM-DD using local calendar values', () => {
      const d = new Date(2026, 8, 25); // Sept 25, 2026
      expect(getLocalISODate(d)).toBe('2026-09-25');
    });

    it('formats single-digit months and days with leading zeros', () => {
      const d = new Date(2026, 0, 5); // Jan 5, 2026
      expect(getLocalISODate(d)).toBe('2026-01-05');
    });
  });

  describe('isValidISODate', () => {
    it('returns true for valid YYYY-MM-DD dates', () => {
      expect(isValidISODate('2026-09-25')).toBe(true);
      expect(isValidISODate('2026-02-28')).toBe(true);
    });

    it('returns false for invalid date formats or invalid calendar dates', () => {
      expect(isValidISODate('2026-9-25')).toBe(false);
      expect(isValidISODate('invalid')).toBe(false);
      expect(isValidISODate('')).toBe(false);
      expect(isValidISODate(null)).toBe(false);
      expect(isValidISODate(undefined)).toBe(false);
      expect(isValidISODate('2026-02-31')).toBe(false);
    });
  });
});
