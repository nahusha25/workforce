import { describe, it, expect } from 'vitest';
import { formatWorkingHours } from './workingHours';

describe('formatWorkingHours', () => {
  describe('zero hours', () => {
    it('formats 0 hours as "0 min"', () => {
      expect(formatWorkingHours(0)).toBe('0 min');
      expect(formatWorkingHours(0.0)).toBe('0 min');
      expect(formatWorkingHours('0')).toBe('0 min');
      expect(formatWorkingHours('0.0')).toBe('0 min');
    });

    it('formats negligible fractions rounding to 0 as "0 min"', () => {
      // 0.005h = 0.3 min -> rounds to 0 min
      expect(formatWorkingHours(0.005)).toBe('0 min');
    });
  });

  describe('minute-only (< 1 hr)', () => {
    it('formats 0.5 hours as "30 min"', () => {
      expect(formatWorkingHours(0.5)).toBe('30 min');
      expect(formatWorkingHours('0.5')).toBe('30 min');
    });

    it('formats 0.75 hours as "45 min"', () => {
      expect(formatWorkingHours(0.75)).toBe('45 min');
      expect(formatWorkingHours('0.75')).toBe('45 min');
    });

    it('formats 0.25 hours as "15 min"', () => {
      expect(formatWorkingHours(0.25)).toBe('15 min');
    });

    it('formats 1 minute (0.01667 hours) as "1 min"', () => {
      expect(formatWorkingHours(1 / 60)).toBe('1 min');
    });
  });

  describe('exact hours (no remaining minutes)', () => {
    it('formats 1 hour with singular "1 hr"', () => {
      expect(formatWorkingHours(1)).toBe('1 hr');
      expect(formatWorkingHours(1.0)).toBe('1 hr');
      expect(formatWorkingHours('1')).toBe('1 hr');
    });

    it('formats integer hours > 1 with plural "hrs"', () => {
      expect(formatWorkingHours(2)).toBe('2 hrs');
      expect(formatWorkingHours(5)).toBe('5 hrs');
      expect(formatWorkingHours(8)).toBe('8 hrs');
      expect(formatWorkingHours(24)).toBe('24 hrs');
      expect(formatWorkingHours('5')).toBe('5 hrs');
    });
  });

  describe('mixed hours and minutes', () => {
    it('formats 1 hour with minutes using singular "1 hr Y min"', () => {
      expect(formatWorkingHours(1.5)).toBe('1 hr 30 min');
      expect(formatWorkingHours(1.25)).toBe('1 hr 15 min');
      expect(formatWorkingHours(1.75)).toBe('1 hr 45 min');
      expect(formatWorkingHours('1.5')).toBe('1 hr 30 min');
    });

    it('formats multiple hours with minutes using plural "X hrs Y min"', () => {
      expect(formatWorkingHours(5.5)).toBe('5 hrs 30 min');
      expect(formatWorkingHours(7.25)).toBe('7 hrs 15 min');
      expect(formatWorkingHours(8.5)).toBe('8 hrs 30 min');
      expect(formatWorkingHours(9.75)).toBe('9 hrs 45 min');
      expect(formatWorkingHours('5.5')).toBe('5 hrs 30 min');
      expect(formatWorkingHours('7.25')).toBe('7 hrs 15 min');
    });
  });

  describe('floating-point rounding and noise suppression', () => {
    it('rounds real-world fractional working hours cleanly', () => {
      // Verification page issue example: 0.49683332583333334h (29.81 min) -> 30 min
      expect(formatWorkingHours(0.49683332583333334)).toBe('30 min');
    });

    it('rounds values close to the next whole hour up to the hour', () => {
      // 0.999h = 59.94 min -> 60 min -> 1 hr
      expect(formatWorkingHours(0.999)).toBe('1 hr');
      // 1.999h = 119.94 min -> 120 min -> 2 hrs
      expect(formatWorkingHours(1.999)).toBe('2 hrs');
      // 5.999h -> 6 hrs
      expect(formatWorkingHours(5.999)).toBe('6 hrs');
    });

    it('rounds values close to the whole hour with fractional noise down to exact hour', () => {
      // 1.001h = 60.06 min -> 60 min -> 1 hr
      expect(formatWorkingHours(1.001)).toBe('1 hr');
      // 8.0000000001h -> 8 hrs
      expect(formatWorkingHours(8.0000000001)).toBe('8 hrs');
    });

    it('rounds fractional minutes to the nearest whole minute', () => {
      // 5.503h = 330.18 min -> 330 min -> 5 hrs 30 min
      expect(formatWorkingHours(5.503)).toBe('5 hrs 30 min');
      // 2.08333h = 124.9998 min -> 125 min -> 2 hrs 5 min
      expect(formatWorkingHours(2.08333)).toBe('2 hrs 5 min');
    });
  });

  describe('null, undefined, invalid, and negative inputs', () => {
    it('returns default fallback "—" for null and undefined', () => {
      expect(formatWorkingHours(null)).toBe('—');
      expect(formatWorkingHours(undefined)).toBe('—');
    });

    it('supports custom fallback string for tables and reports', () => {
      expect(formatWorkingHours(null, '-')).toBe('-');
      expect(formatWorkingHours(undefined, 'N/A')).toBe('N/A');
      expect(formatWorkingHours('', '-')).toBe('-');
    });

    it('returns fallback for empty string or whitespace', () => {
      expect(formatWorkingHours('')).toBe('—');
      expect(formatWorkingHours('   ')).toBe('—');
    });

    it('returns fallback for non-numeric and NaN values', () => {
      expect(formatWorkingHours('invalid')).toBe('—');
      expect(formatWorkingHours('abc')).toBe('—');
      expect(formatWorkingHours(NaN)).toBe('—');
    });

    it('returns fallback for Infinity and -Infinity', () => {
      expect(formatWorkingHours(Infinity)).toBe('—');
      expect(formatWorkingHours(-Infinity)).toBe('—');
    });

    it('returns fallback for negative values', () => {
      expect(formatWorkingHours(-1)).toBe('—');
      expect(formatWorkingHours(-5.5)).toBe('—');
      expect(formatWorkingHours('-0.5')).toBe('—');
      expect(formatWorkingHours(-10, '-')).toBe('-');
    });
  });
});
