import { useState, useCallback } from 'react';

export interface LocationData {
  latitude: number;
  longitude: number;
}

export interface UseGeolocationReturn {
  location: LocationData | null;
  error: string | null;
  loading: boolean;
  getLocation: () => void;
}

export function useGeolocation(): UseGeolocationReturn {
  const [location, setLocation] = useState<LocationData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const getLocation = useCallback(() => {
    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
        });
        setError(null);
        setLoading(false);
      },
      (geoError) => {
        let errorMessage = 'An unknown error occurred';
        switch (geoError.code) {
          case geoError.PERMISSION_DENIED:
            errorMessage = 'Location permission denied';
            break;
          case geoError.POSITION_UNAVAILABLE:
            errorMessage = 'Location information is unavailable';
            break;
          case geoError.TIMEOUT:
            errorMessage = 'The request to get user location timed out';
            break;
        }
        setError(errorMessage);
        setLoading(false);
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  }, []);

  return { location, error, loading, getLocation };
}
