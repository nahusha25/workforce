import { render, screen, fireEvent, waitFor, cleanup, act } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import L from 'leaflet';
import { LocationPicker } from './LocationPicker';
import * as nominatimApi from '../../api/nominatim';

vi.mock('../../api/nominatim', () => ({
  searchNominatim: vi.fn(),
}));

const mockNominatimPlaces: nominatimApi.NominatimPlace[] = [
  {
    place_id: 101,
    lat: '12.971598',
    lon: '77.594562',
    display_name: 'Cubbon Park, MG Road, Bengaluru, Karnataka, 560001, India',
    name: 'Cubbon Park',
  },
  {
    place_id: 102,
    lat: '13.082680',
    lon: '80.270718',
    display_name: 'Chennai Central, Station Road, Chennai, Tamil Nadu, 600003, India',
    name: 'Chennai Central',
  },
];

describe('LocationPicker component', () => {
  let capturedMap: L.Map | null = null;
  let capturedMarker: L.Marker | null = null;
  let origMap: any;
  let origMarker: any;

  beforeEach(() => {
    vi.clearAllMocks();
    capturedMap = null;
    capturedMarker = null;

    origMap = L.map;
    origMarker = L.marker;

    vi.spyOn(L, 'map').mockImplementation((...args: any[]) => {
      const instance = (origMap as any)(...args);
      capturedMap = instance;
      return instance;
    });

    vi.spyOn(L, 'marker').mockImplementation((...args: any[]) => {
      const instance = (origMarker as any)(...args);
      capturedMarker = instance;
      return instance;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    cleanup();
  });

  it('renders search input, map container, and unselected state without fallback to (0,0)', () => {
    const onChange = vi.fn();
    render(<LocationPicker value={null} onChange={onChange} radiusMeters={100} />);

    expect(screen.getByTestId('location-search-input')).toBeInTheDocument();
    expect(screen.getByTestId('location-map-container')).toBeInTheDocument();
    expect(screen.getByTestId('location-unselected-warning')).toHaveTextContent(
      'No location selected. Click map or search above.'
    );
    expect(screen.queryByTestId('location-lat-display')).not.toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });

  it('restores saved marker coordinates and radius correctly in edit mode', () => {
    const onChange = vi.fn();
    render(
      <LocationPicker
        value="POINT(77.594562 12.971598)"
        onChange={onChange}
        radiusMeters={200}
      />
    );

    // Coordinates readout should display parsed lat and lng
    expect(screen.getByTestId('location-lat-display')).toHaveTextContent('Lat: 12.971598');
    expect(screen.getByTestId('location-lng-display')).toHaveTextContent('Lng: 77.594562');
    expect(screen.getByText('Geofence Pin Set')).toBeInTheDocument();

    // Radius input should reflect 200m
    const radiusInput = screen.getByTestId('location-radius-input') as HTMLInputElement;
    expect(radiusInput.value).toBe('200');
  });

  it('searches address via Nominatim autocomplete and updates coordinates on selection', async () => {
    vi.mocked(nominatimApi.searchNominatim).mockResolvedValue(mockNominatimPlaces);

    const onChange = vi.fn();
    const onAddressSelect = vi.fn();

    render(
      <LocationPicker
        value={null}
        onChange={onChange}
        onAddressSelect={onAddressSelect}
        radiusMeters={100}
      />
    );

    const searchInput = screen.getByTestId('location-search-input');
    fireEvent.change(searchInput, { target: { value: 'Cubbon Park' } });

    // Wait for debounce and search results
    await waitFor(
      () => {
        expect(nominatimApi.searchNominatim).toHaveBeenCalledWith('Cubbon Park', expect.any(Object));
      },
      { timeout: 1500 }
    );

    await waitFor(() => {
      expect(screen.getByTestId('location-search-results')).toBeInTheDocument();
      expect(screen.getByText('Cubbon Park')).toBeInTheDocument();
    });

    // Select the first suggestion
    fireEvent.click(screen.getByTestId('location-search-item-0'));

    // Verify coordinate update & callbacks
    await waitFor(() => {
      expect(onChange).toHaveBeenCalledWith('POINT(77.594562 12.971598)');
      expect(onAddressSelect).toHaveBeenCalledWith(mockNominatimPlaces[0].display_name);
    });

    expect(screen.getByTestId('location-lat-display')).toHaveTextContent('Lat: 12.971598');
    expect(screen.getByTestId('location-lng-display')).toHaveTextContent('Lng: 77.594562');
  });

  it('updates coordinates on manual map click', async () => {
    const onChange = vi.fn();
    render(<LocationPicker value={null} onChange={onChange} radiusMeters={100} />);

    expect(capturedMap).not.toBeNull();

    // Simulate clicking on the Leaflet map
    act(() => {
      capturedMap?.fire('click', {
        latlng: L.latLng(12.9352, 77.6245),
      });
    });

    expect(onChange).toHaveBeenCalledWith('POINT(77.6245 12.9352)');
    expect(screen.getByTestId('location-lat-display')).toHaveTextContent('Lat: 12.935200');
    expect(screen.getByTestId('location-lng-display')).toHaveTextContent('Lng: 77.624500');
  });

  it('updates coordinates when marker is dragged and dropped', async () => {
    const onChange = vi.fn();
    render(
      <LocationPicker
        value="POINT(77.594562 12.971598)"
        onChange={onChange}
        radiusMeters={100}
      />
    );

    expect(capturedMarker).not.toBeNull();

    // Drag marker to a new position
    act(() => {
      capturedMarker?.setLatLng([12.9400, 77.6100]);
      capturedMarker?.fire('dragend');
    });

    expect(onChange).toHaveBeenCalledWith('POINT(77.61 12.94)');
    expect(screen.getByTestId('location-lat-display')).toHaveTextContent('Lat: 12.940000');
    expect(screen.getByTestId('location-lng-display')).toHaveTextContent('Lng: 77.610000');
  });

  it('updates radius immediately via input and preset pills', () => {
    const onChange = vi.fn();
    const onRadiusChange = vi.fn();

    render(
      <LocationPicker
        value="POINT(77.594562 12.971598)"
        onChange={onChange}
        radiusMeters={100}
        onRadiusChange={onRadiusChange}
      />
    );

    const radiusInput = screen.getByTestId('location-radius-input') as HTMLInputElement;
    expect(radiusInput.value).toBe('100');

    // Change radius to 250m via input
    fireEvent.change(radiusInput, { target: { value: '250' } });
    expect(onRadiusChange).toHaveBeenCalledWith(250);

    // Click 500m preset pill
    const preset500 = screen.getByTestId('location-radius-preset-500');
    fireEvent.click(preset500);
    expect(onRadiusChange).toHaveBeenCalledWith(500);
    expect(radiusInput.value).toBe('500');
  });

  it('clears pin and coordinates when Clear Pin button is clicked', () => {
    const onChange = vi.fn();
    render(
      <LocationPicker
        value="POINT(77.594562 12.971598)"
        onChange={onChange}
        radiusMeters={100}
      />
    );

    expect(screen.getByTestId('location-lat-display')).toBeInTheDocument();

    const clearBtn = screen.getByTestId('location-clear-btn');
    fireEvent.click(clearBtn);

    expect(onChange).toHaveBeenCalledWith(null);
    expect(screen.getByTestId('location-unselected-warning')).toBeInTheDocument();
  });

  it('displays user-friendly message when Nominatim search encounters network error', async () => {
    vi.mocked(nominatimApi.searchNominatim).mockRejectedValue(new Error('Network error'));

    render(<LocationPicker value={null} onChange={vi.fn()} radiusMeters={100} />);

    const searchInput = screen.getByTestId('location-search-input');
    fireEvent.change(searchInput, { target: { value: 'Test Location' } });

    await waitFor(
      () => {
        expect(screen.getByTestId('location-search-error')).toHaveTextContent(
          'Could not reach search service. You can select directly on the map.'
        );
      },
      { timeout: 1500 }
    );
  });
});
