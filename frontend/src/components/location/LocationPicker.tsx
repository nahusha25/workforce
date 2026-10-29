import React, { useEffect, useRef, useState, useCallback } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { Search, MapPin, LocateFixed, RotateCcw, X, AlertTriangle, CheckCircle2 } from 'lucide-react';
import { searchNominatim, type NominatimPlace } from '../../api/nominatim';
import {
  parsePointWkt,
  formatPointWkt,
  type LatLng,
} from '../../utils/geo';
import styles from './LocationPicker.module.css';

export interface LocationPickerProps {
  value?: string | null;
  onChange: (wkt: string | null) => void;
  radiusMeters?: number;
  onRadiusChange?: (radius: number) => void;
  onAddressSelect?: (address: string) => void;
  disabled?: boolean;
  error?: string | null;
  radiusTestId?: string;
  defaultCenter?: [number, number]; // [lat, lng], default Bengaluru
  defaultZoom?: number;
}

const DEFAULT_CENTER: [number, number] = [12.9716, 77.5946]; // Bengaluru
const DEFAULT_ZOOM = 13;

const createMarkerIcon = () => {
  return L.divIcon({
    className: 'custom-map-pin',
    html: `
      <div style="position: relative; width: 32px; height: 38px; transform: translate(-16px, -38px); pointer-events: auto; cursor: grab;">
        <svg viewBox="0 0 24 24" width="32" height="38" style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.35));">
          <path d="M12 0C7.58 0 4 3.58 4 8c0 5.25 7 13 8 14 1-1 8-8.75 8-14 0-4.42-3.58-8-8-8z" fill="#2563eb" stroke="#ffffff" stroke-width="1.5" />
          <circle cx="12" cy="8" r="3.5" fill="#ffffff" />
        </svg>
      </div>
    `,
    iconSize: [32, 38],
    iconAnchor: [16, 38],
  });
};

export const LocationPicker: React.FC<LocationPickerProps> = ({
  value,
  onChange,
  radiusMeters = 100,
  onRadiusChange,
  onAddressSelect,
  disabled = false,
  error = null,
  radiusTestId = 'location-radius-input',
  defaultCenter = DEFAULT_CENTER,
  defaultZoom = DEFAULT_ZOOM,
}) => {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);
  const circleRef = useRef<L.Circle | null>(null);

  // Active coordinates
  const parsedValue = parsePointWkt(value);
  const [selectedCoords, setSelectedCoords] = useState<LatLng | null>(parsedValue);

  // Address search state
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [searchResults, setSearchResults] = useState<NominatimPlace[]>([]);
  const [showDropdown, setShowDropdown] = useState<boolean>(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const searchAbortRef = useRef<AbortController | null>(null);
  const searchTimeoutRef = useRef<any>(null);

  // Radius state
  const [currentRadius, setCurrentRadius] = useState<number>(radiusMeters);

  // Keep latest callback and prop references
  const onChangeRef = useRef(onChange);
  onChangeRef.current = onChange;
  const disabledRef = useRef(disabled);
  disabledRef.current = disabled;
  const radiusRef = useRef(currentRadius);
  radiusRef.current = currentRadius;
  const onAddressSelectRef = useRef(onAddressSelect);
  onAddressSelectRef.current = onAddressSelect;

  // Sync radius prop only when prop actually changes
  const prevRadiusMetersRef = useRef(radiusMeters);
  useEffect(() => {
    if (prevRadiusMetersRef.current !== radiusMeters) {
      prevRadiusMetersRef.current = radiusMeters;
      setCurrentRadius(radiusMeters);
      if (circleRef.current) {
        circleRef.current.setRadius(radiusMeters);
      }
    }
  }, [radiusMeters]);

  // Layer update helper
  const updateMapLayers = useCallback((lat: number, lng: number, radius: number) => {
    const map = mapInstanceRef.current;
    if (!map) return;

    // Update or create Marker
    if (markerRef.current) {
      markerRef.current.setLatLng([lat, lng]);
    } else {
      const marker = L.marker([lat, lng], {
        icon: createMarkerIcon(),
        draggable: !disabledRef.current,
      }).addTo(map);

      marker.on('dragend', () => {
        const newLatLng = marker.getLatLng();
        handlePositionChange(newLatLng.lat, newLatLng.lng);
      });

      markerRef.current = marker;
    }

    // Update or create Circle
    if (circleRef.current) {
      circleRef.current.setLatLng([lat, lng]);
      circleRef.current.setRadius(radius);
    } else {
      const circle = L.circle([lat, lng], {
        radius,
        color: '#2563eb',
        fillColor: '#3b82f6',
        fillOpacity: 0.2,
        weight: 2,
      }).addTo(map);
      circleRef.current = circle;
    }
  }, []);

  const removeMapLayers = useCallback(() => {
    if (markerRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(markerRef.current);
      markerRef.current = null;
    }
    if (circleRef.current && mapInstanceRef.current) {
      mapInstanceRef.current.removeLayer(circleRef.current);
      circleRef.current = null;
    }
  }, []);

  const handlePositionChange = useCallback((lat: number, lng: number) => {
    const coords = { lat, lng };
    setSelectedCoords(coords);
    updateMapLayers(lat, lng, radiusRef.current);
    const wkt = formatPointWkt(lat, lng);
    onChangeRef.current(wkt);
  }, [updateMapLayers]);

  // Sync external value changes (e.g. edit mode or reset)
  useEffect(() => {
    const coords = parsePointWkt(value);
    setSelectedCoords(coords);

    if (mapInstanceRef.current) {
      if (coords) {
        updateMapLayers(coords.lat, coords.lng, radiusRef.current);
        mapInstanceRef.current.setView([coords.lat, coords.lng], 16);
      } else {
        removeMapLayers();
      }
    }
  }, [value, updateMapLayers, removeMapLayers]);

  // Initialize Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapInstanceRef.current) return;

    const initialCoords = parsedValue;
    const center = initialCoords ? [initialCoords.lat, initialCoords.lng] as [number, number] : defaultCenter;
    const zoom = initialCoords ? 16 : defaultZoom;

    // Clean any prior Leaflet ID in container
    if ((mapContainerRef.current as any)._leaflet_id) {
      (mapContainerRef.current as any)._leaflet_id = null;
    }

    const map = L.map(mapContainerRef.current, {
      center,
      zoom,
      zoomControl: true,
    });

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">OpenStreetMap</a> contributors',
      maxZoom: 19,
    }).addTo(map);

    // Map Click Listener
    map.on('click', (e: L.LeafletMouseEvent) => {
      if (disabledRef.current) return;
      handlePositionChange(e.latlng.lat, e.latlng.lng);
    });

    mapInstanceRef.current = map;

    // If initial value exists, render layers
    if (initialCoords) {
      updateMapLayers(initialCoords.lat, initialCoords.lng, radiusRef.current);
    }

    return () => {
      map.remove();
      mapInstanceRef.current = null;
      markerRef.current = null;
      circleRef.current = null;
    };
  }, [defaultCenter, defaultZoom, handlePositionChange, parsedValue, updateMapLayers]);

  // Update marker draggable property when disabled changes
  useEffect(() => {
    if (markerRef.current) {
      if (disabled) {
        markerRef.current.dragging?.disable();
      } else {
        markerRef.current.dragging?.enable();
      }
    }
  }, [disabled]);

  // Debounced Nominatim address search
  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const query = e.target.value;
    setSearchQuery(query);
    setSearchError(null);

    if (searchTimeoutRef.current) {
      clearTimeout(searchTimeoutRef.current);
    }
    if (searchAbortRef.current) {
      searchAbortRef.current.abort();
    }

    if (!query.trim() || query.trim().length < 2) {
      setSearchResults([]);
      setShowDropdown(false);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);
    searchTimeoutRef.current = setTimeout(async () => {
      const controller = new AbortController();
      searchAbortRef.current = controller;
      try {
        const results = await searchNominatim(query, controller.signal);
        setSearchResults(results);
        setShowDropdown(results.length > 0);
        if (results.length === 0) {
          setSearchError('No matching places found.');
        }
      } catch (err: any) {
        if (err.name !== 'AbortError') {
          setSearchError('Could not reach search service. You can select directly on the map.');
          setShowDropdown(false);
        }
      } finally {
        setIsSearching(false);
      }
    }, 400); // 400ms debounce per Nominatim policy
  };

  const handleSelectSuggestion = (place: NominatimPlace) => {
    const lat = parseFloat(place.lat);
    const lng = parseFloat(place.lon);
    if (isNaN(lat) || isNaN(lng)) return;

    setSearchQuery(place.display_name);
    setShowDropdown(false);
    setSearchResults([]);

    if (mapInstanceRef.current) {
      mapInstanceRef.current.setView([lat, lng], 16, { animate: true });
    }

    handlePositionChange(lat, lng);

    if (onAddressSelect) {
      onAddressSelect(place.display_name);
    }
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    setSearchResults([]);
    setShowDropdown(false);
    setSearchError(null);
  };

  const handleRadiusChange = (newRadius: number) => {
    if (isNaN(newRadius) || newRadius < 0) return;
    setCurrentRadius(newRadius);
    if (circleRef.current) {
      circleRef.current.setRadius(newRadius);
    }
    if (onRadiusChange) {
      onRadiusChange(newRadius);
    }
  };

  const handleUseCurrentLocation = () => {
    if (!navigator.geolocation) {
      setSearchError('Geolocation is not supported by your browser.');
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        const { latitude, longitude } = pos.coords;
        if (mapInstanceRef.current) {
          mapInstanceRef.current.setView([latitude, longitude], 16, { animate: true });
        }
        handlePositionChange(latitude, longitude);
      },
      (err) => {
        setSearchError(`Geolocation error: ${err.message}`);
      },
      { enableHighAccuracy: true, timeout: 8000 }
    );
  };

  const handleClearLocation = () => {
    removeMapLayers();
    setSelectedCoords(null);
    setSearchQuery('');
    onChange(null);
  };

  return (
    <div className={styles.container} data-testid="location-picker">
      {/* 1. Address Search Autocomplete */}
      <div className={styles.searchSection}>
        <div className={styles.searchInputWrapper}>
          <span className={styles.searchIcon}>
            <Search size={18} />
          </span>
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search address, area, landmark or place"
            value={searchQuery}
            onChange={handleSearchChange}
            onFocus={() => {
              if (searchResults.length > 0) setShowDropdown(true);
            }}
            disabled={disabled}
            data-testid="location-search-input"
            autoComplete="off"
          />
          {isSearching && (
            <div className={styles.searchSpinner} data-testid="location-search-loading" />
          )}
          {!isSearching && searchQuery && (
            <button
              type="button"
              className={styles.clearSearchBtn}
              onClick={handleClearSearch}
              title="Clear search"
              data-testid="location-clear-search-btn"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* Search Results Dropdown */}
        {showDropdown && searchResults.length > 0 && (
          <ul className={styles.suggestionsDropdown} data-testid="location-search-results">
            {searchResults.map((place, idx) => {
              const parts = place.display_name.split(',');
              const primary = parts[0]?.trim();
              const secondary = parts.slice(1).join(',').trim();
              return (
                <li
                  key={place.place_id || idx}
                  className={styles.suggestionItem}
                  onClick={() => handleSelectSuggestion(place)}
                  data-testid={`location-search-item-${idx}`}
                >
                  <span className={styles.suggestionTitle}>{primary}</span>
                  {secondary && <span className={styles.suggestionAddress}>{secondary}</span>}
                </li>
              );
            })}
            <li className={styles.attributionFooter}>
              OpenStreetMap Nominatim
            </li>
          </ul>
        )}

        {searchError && (
          <div className={styles.errorBanner} data-testid="location-search-error">
            {searchError}
          </div>
        )}
      </div>

      {/* 2. Leaflet Map Container */}
      <div className={styles.mapWrapper}>
        <div
          ref={mapContainerRef}
          className={styles.mapContainer}
          data-testid="location-map-container"
        />

        {/* Floating Map Controls */}
        <div className={styles.mapOverlayControls}>
          <button
            type="button"
            className={styles.mapBtn}
            onClick={handleUseCurrentLocation}
            title="Locate my position"
            disabled={disabled}
            data-testid="location-my-location-btn"
          >
            <LocateFixed size={14} />
            <span>My Location</span>
          </button>
          {selectedCoords && (
            <button
              type="button"
              className={styles.mapBtn}
              onClick={handleClearLocation}
              title="Clear marker"
              disabled={disabled}
              data-testid="location-clear-btn"
            >
              <RotateCcw size={14} />
              <span>Clear Pin</span>
            </button>
          )}
        </div>

        {!selectedCoords && (
          <div className={styles.mapHintBadge}>
            <MapPin size={14} />
            <span>Click map or search above to drop pin</span>
          </div>
        )}
      </div>

      {/* 3. Coordinates & Radius Controls Panel */}
      <div className={styles.detailsPanel}>
        <div className={styles.coordBox}>
          <span className={styles.panelLabel}>Selected Coordinates</span>
          {selectedCoords ? (
            <div className={styles.coordValues}>
              <span className={styles.activeCoordSuccess}>
                <CheckCircle2 size={16} />
                <span>Geofence Pin Set</span>
              </span>
              <span className={styles.coordTag} data-testid="location-lat-display">
                Lat: {selectedCoords.lat.toFixed(6)}
              </span>
              <span className={styles.coordTag} data-testid="location-lng-display">
                Lng: {selectedCoords.lng.toFixed(6)}
              </span>
            </div>
          ) : (
            <div className={styles.noCoordWarning} data-testid="location-unselected-warning">
              <AlertTriangle size={16} />
              <span>No location selected. Click map or search above.</span>
            </div>
          )}
        </div>

        <div className={styles.radiusBox}>
          <span className={styles.panelLabel}>Permitted Radius (Geofence)</span>
          <div className={styles.radiusControls}>
            <input
              type="number"
              min="10"
              max="5000"
              step="10"
              className={styles.radiusInput}
              value={currentRadius}
              onChange={(e) => handleRadiusChange(parseFloat(e.target.value) || 0)}
              disabled={disabled}
              data-testid={radiusTestId}
            />
            <span style={{ fontSize: 'var(--font-size-sm)', color: 'var(--color-neutral-700)' }}>
              meters
            </span>

            <div className={styles.presetButtons}>
              {[50, 100, 200, 500].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  className={`${styles.presetBtn} ${currentRadius === preset ? styles.presetBtnActive : ''}`}
                  onClick={() => handleRadiusChange(preset)}
                  disabled={disabled}
                  data-testid={`location-radius-preset-${preset}`}
                >
                  {preset}m
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {error && (
        <div className={styles.errorBanner} data-testid="location-error-message">
          {error}
        </div>
      )}
    </div>
  );
};
