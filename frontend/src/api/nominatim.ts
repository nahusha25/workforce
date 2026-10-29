export interface NominatimPlace {
  place_id: number;
  lat: string;
  lon: string;
  display_name: string;
  name?: string;
  type?: string;
  importance?: number;
  address?: {
    road?: string;
    suburb?: string;
    city?: string;
    state?: string;
    postcode?: string;
    country?: string;
    [key: string]: string | undefined;
  };
}

/**
 * Searches OpenStreetMap Nominatim API for places/addresses matching the query.
 * Following OSM Nominatim Usage Policy:
 * - 1 query per second max (debounced in UI)
 * - Limit results to 5
 * - Include address details
 */
export async function searchNominatim(
  query: string,
  signal?: AbortSignal
): Promise<NominatimPlace[]> {
  const trimmed = query.trim();
  if (!trimmed || trimmed.length < 2) return [];

  const url = `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(
    trimmed
  )}&addressdetails=1&limit=5`;

  const response = await fetch(url, {
    signal,
    headers: {
      Accept: 'application/json',
      'Accept-Language': 'en',
    },
  });

  if (!response.ok) {
    throw new Error(`Nominatim search failed with status ${response.status}`);
  }

  return response.json();
}
