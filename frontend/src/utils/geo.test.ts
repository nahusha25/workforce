import { describe, it, expect } from 'vitest';
import {
  parsePointWkt,
  formatPointWkt,
  isValidCoordinate,
  formatCoordinatesDisplay,
} from './geo';

describe('geo utils', () => {
  describe('isValidCoordinate', () => {
    it('returns true for valid coordinates', () => {
      expect(isValidCoordinate(12.971598, 77.594562)).toBe(true);
      expect(isValidCoordinate(-33.8688, 151.2093)).toBe(true);
      expect(isValidCoordinate(0.0001, 0.0001)).toBe(true);
    });

    it('returns false for (0, 0) coordinates to prevent silent fallback', () => {
      expect(isValidCoordinate(0, 0)).toBe(false);
      expect(isValidCoordinate(0.0, 0.0)).toBe(false);
    });

    it('returns false for out-of-range coordinates', () => {
      expect(isValidCoordinate(91, 77)).toBe(false);
      expect(isValidCoordinate(-91, 77)).toBe(false);
      expect(isValidCoordinate(12, 181)).toBe(false);
      expect(isValidCoordinate(12, -181)).toBe(false);
      expect(isValidCoordinate(NaN, 77)).toBe(false);
      expect(isValidCoordinate(12, NaN)).toBe(false);
    });
  });

  describe('parsePointWkt', () => {
    it('correctly parses WKT POINT with longitude first and latitude second', () => {
      const parsed = parsePointWkt('POINT(77.594562 12.971598)');
      expect(parsed).toEqual({
        lng: 77.594562,
        lat: 12.971598,
      });
    });

    it('correctly parses WKT POINT with lowercase and extra whitespace', () => {
      const parsed = parsePointWkt('  point (  77.594562   12.971598  ) ');
      expect(parsed).toEqual({
        lng: 77.594562,
        lat: 12.971598,
      });
    });

    it('parses legacy lat, lng format as fallback', () => {
      const parsed = parsePointWkt('12.971598, 77.594562');
      expect(parsed).toEqual({
        lat: 12.971598,
        lng: 77.594562,
      });
    });

    it('returns null and rejects POINT(0 0)', () => {
      expect(parsePointWkt('POINT(0 0)')).toBeNull();
      expect(parsePointWkt('POINT(0.0 0.0)')).toBeNull();
      expect(parsePointWkt('0, 0')).toBeNull();
    });

    it('returns null for null, undefined, empty, or invalid strings', () => {
      expect(parsePointWkt(null)).toBeNull();
      expect(parsePointWkt(undefined)).toBeNull();
      expect(parsePointWkt('')).toBeNull();
      expect(parsePointWkt('   ')).toBeNull();
      expect(parsePointWkt('not a coordinate')).toBeNull();
      expect(parsePointWkt('POINT(abc def)')).toBeNull();
    });
  });

  describe('formatPointWkt', () => {
    it('formats coordinates into standard POINT(longitude latitude)', () => {
      expect(formatPointWkt(12.971598, 77.594562)).toBe('POINT(77.594562 12.971598)');
    });

    it('throws error when attempting to format (0, 0)', () => {
      expect(() => formatPointWkt(0, 0)).toThrow('Cannot format invalid coordinates');
    });

    it('throws error for invalid coordinates', () => {
      expect(() => formatPointWkt(100, 200)).toThrow('Cannot format invalid coordinates');
    });
  });

  describe('formatCoordinatesDisplay', () => {
    it('formats coordinates with cardinal directions', () => {
      expect(formatCoordinatesDisplay(12.971598, 77.594562)).toBe('12.971598° N, 77.594562° E');
      expect(formatCoordinatesDisplay(-33.8688, -70.6693)).toBe('33.868800° S, 70.669300° W');
    });
  });
});
