export interface LatLng {
  lat: number;
  lng: number;
}

/**
 * Validates coordinate bounds.
 * Disallows NaN, out of range coordinates, and strictly disallows (0, 0)
 * to prevent silent fallback to Null Island.
 */
export function isValidCoordinate(lat: number, lng: number): boolean {
  if (typeof lat !== 'number' || typeof lng !== 'number') return false;
  if (isNaN(lat) || isNaN(lng)) return false;
  if (lat < -90 || lat > 90) return false;
  if (lng < -180 || lng > 180) return false;
  // Strictly prevent (0, 0) as valid site location
  if (Math.abs(lat) < 0.000001 && Math.abs(lng) < 0.000001) {
    return false;
  }
  return true;
}

/**
 * Parses WKT string e.g. "POINT(77.594562 12.971598)" or legacy "lat, lng" string.
 * Returns null if string is empty, invalid, or represents (0, 0).
 */
export function parsePointWkt(wkt: string | null | undefined): LatLng | null {
  if (!wkt || typeof wkt !== 'string') return null;
  const trimmed = wkt.trim();
  if (!trimmed) return null;

  // WKT format: POINT(longitude latitude)
  const pointMatch = trimmed.match(/^POINT\s*\(\s*([+-]?\d+(?:\.\d+)?)\s+([+-]?\d+(?:\.\d+)?)\s*\)$/i);
  if (pointMatch) {
    const lng = parseFloat(pointMatch[1]);
    const lat = parseFloat(pointMatch[2]);
    if (!isValidCoordinate(lat, lng)) return null;
    return { lat, lng };
  }

  // Legacy fallback: "latitude, longitude" or "lat,lng"
  const commaMatch = trimmed.match(/^([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)$/);
  if (commaMatch) {
    const lat = parseFloat(commaMatch[1]);
    const lng = parseFloat(commaMatch[2]);
    if (!isValidCoordinate(lat, lng)) return null;
    return { lat, lng };
  }

  return null;
}

/**
 * Formats lat/lng into WKT: POINT(longitude latitude)
 * Follows OGC standard where longitude is the X-coordinate and latitude is the Y-coordinate.
 * Rounded to 6 decimal places (~0.1m precision).
 */
export function formatPointWkt(lat: number, lng: number): string {
  if (!isValidCoordinate(lat, lng)) {
    throw new Error(`Cannot format invalid coordinates: lat=${lat}, lng=${lng}`);
  }
  const formattedLng = Number(lng.toFixed(6));
  const formattedLat = Number(lat.toFixed(6));
  return `POINT(${formattedLng} ${formattedLat})`;
}

/**
 * Formats coordinates for clear human-readable display.
 */
export function formatCoordinatesDisplay(lat: number, lng: number): string {
  const latDir = lat >= 0 ? 'N' : 'S';
  const lngDir = lng >= 0 ? 'E' : 'W';
  return `${Math.abs(lat).toFixed(6)}° ${latDir}, ${Math.abs(lng).toFixed(6)}° ${lngDir}`;
}
