import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import '@testing-library/jest-dom/vitest';
import { MemoryRouter } from 'react-router-dom';
import { SitesPage } from './SitesPage';
import { AuthContext } from '../context/AuthContext';
import * as masterDataApi from '../api/masterData';
import * as nominatimApi from '../api/nominatim';
import type { SystemRole } from '../types/auth';

vi.mock('../api/nominatim', () => ({
  searchNominatim: vi.fn(),
}));

vi.mock('../api/masterData', async (importOriginal) => {
  const actual = await importOriginal<typeof import('../api/masterData')>();
  return {
    ...actual,
    getSitesApi: vi.fn(),
    getProjectsApi: vi.fn(),
    createSiteApi: vi.fn(),
    deleteSiteApi: vi.fn(),
    updateSiteApi: vi.fn(),
  };
});

const mockProjects = [
  { id: 'proj-1', name: 'Metro Line Extension', client_id: 'client-1', status: 'Active' },
];

const mockSites = [
  {
    id: 'site-1',
    name: 'Central Junction Site',
    project_id: 'proj-1',
    address: '123 Main Street',
    location: null,
    permitted_radius_m: 100,
    is_active: true,
  },
  {
    id: 'site-2',
    name: 'North Depot Site',
    project_id: 'proj-1',
    address: '456 North Ave',
    location: null,
    permitted_radius_m: 50,
    is_active: false,
  },
];

const renderSitesPage = (role: SystemRole = 'administrator') => {
  return render(
    <AuthContext.Provider
      value={{
        user: {
          id: 'u-1',
          user_id: 'u-1',
          employee_code: 'ADM-01',
          mobile_id: '+919999999999',
          name: 'Admin User',
          system_role: role,
          trade_roles: [],
          active_sites: [],
          is_active: true,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
        role,
        accessToken: 'token',
        isAuthenticated: true,
        isLoading: false,
        error: null,
        requestOtp: vi.fn(),
        verifyOtp: vi.fn(),
        logout: vi.fn(),
        clearError: vi.fn(),
      }}
    >
      <MemoryRouter>
        <SitesPage />
      </MemoryRouter>
    </AuthContext.Provider>
  );
};

describe('SitesPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders site cards and shows delete button for administrators', async () => {
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);

    renderSitesPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Central Junction Site')).toBeInTheDocument();
      expect(screen.getByText('North Depot Site')).toBeInTheDocument();
    });

    expect(screen.getByTestId('delete-site-site-1')).toBeInTheDocument();
    expect(screen.getByTestId('delete-site-site-2')).toBeInTheDocument();
  });

  it('allows administrator to delete a site with confirmation modal', async () => {
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);
    vi.mocked(masterDataApi.deleteSiteApi).mockResolvedValue({ status: 'success', message: 'Site deleted' });

    renderSitesPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Central Junction Site')).toBeInTheDocument();
    });

    // Click delete
    fireEvent.click(screen.getByTestId('delete-site-site-1'));
    expect(screen.getByTestId('confirm-delete-modal')).toBeInTheDocument();
    expect(screen.getByText(/Are you sure you want to permanently delete site/)).toBeInTheDocument();

    // Cancel
    fireEvent.click(screen.getByTestId('cancel-delete-btn'));
    expect(screen.queryByTestId('confirm-delete-modal')).not.toBeInTheDocument();
    expect(masterDataApi.deleteSiteApi).not.toHaveBeenCalled();

    // Confirm delete
    fireEvent.click(screen.getByTestId('delete-site-site-1'));
    fireEvent.click(screen.getByTestId('confirm-delete-btn'));

    await waitFor(() => {
      expect(masterDataApi.deleteSiteApi).toHaveBeenCalledWith('site-1');
    });

    await waitFor(() => {
      expect(screen.getByTestId('success-banner')).toBeInTheDocument();
    });
  });

  it('allows administrator to edit an existing site', async () => {
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);
    vi.mocked(masterDataApi.updateSiteApi).mockResolvedValue({
      ...mockSites[0],
      name: 'Central Junction Site Enhanced',
      permitted_radius_m: 150,
    });

    renderSitesPage('administrator');

    await waitFor(() => {
      expect(screen.getByTestId('edit-site-site-1')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('edit-site-site-1'));

    expect(screen.getByText('Edit Construction Site')).toBeInTheDocument();
    expect(screen.getByDisplayValue('Central Junction Site')).toBeInTheDocument();

    fireEvent.change(screen.getByTestId('site-name-input'), {
      target: { value: 'Central Junction Site Enhanced' },
    });
    fireEvent.change(screen.getByTestId('site-radius-input'), {
      target: { value: '150' },
    });

    fireEvent.click(screen.getByTestId('save-site-btn'));

    await waitFor(() => {
      expect(masterDataApi.updateSiteApi).toHaveBeenCalledWith('site-1', {
        name: 'Central Junction Site Enhanced',
        project_id: 'proj-1',
        address: '123 Main Street',
        location: null,
        permitted_radius_m: 150,
        is_active: true,
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Site "Central Junction Site Enhanced" updated successfully!/i)).toBeInTheDocument();
    });
  });

  it('hides edit and delete buttons when viewed by non-administrator role', async () => {
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);

    renderSitesPage('director');

    await waitFor(() => {
      expect(screen.getByText('Central Junction Site')).toBeInTheDocument();
    });

    expect(screen.queryByTestId('edit-site-site-1')).not.toBeInTheDocument();
    expect(screen.queryByTestId('delete-site-site-1')).not.toBeInTheDocument();
  });

  it('creates a new site with address autocomplete search and saves in POINT(longitude latitude) format', async () => {
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);
    vi.mocked(masterDataApi.createSiteApi).mockResolvedValue({
      id: 'site-3',
      name: 'MG Road Metro Station',
      project_id: 'proj-1',
      address: 'Cubbon Park, MG Road, Bengaluru',
      location: 'POINT(77.594562 12.971598)',
      permitted_radius_m: 200,
      is_active: true,
    });
    vi.mocked(nominatimApi.searchNominatim).mockResolvedValue([
      {
        place_id: 201,
        lat: '12.971598',
        lon: '77.594562',
        display_name: 'Cubbon Park, MG Road, Bengaluru, Karnataka, 560001, India',
      },
    ]);

    renderSitesPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Central Junction Site')).toBeInTheDocument();
    });

    // Open add site form
    fireEvent.click(screen.getByTestId('add-site-btn'));
    expect(screen.getByText('Register New Construction Site')).toBeInTheDocument();

    // Fill name
    fireEvent.change(screen.getByTestId('site-name-input'), {
      target: { value: 'MG Road Metro Station' },
    });

    // Use Nominatim search in LocationPicker
    const searchInput = screen.getByTestId('location-search-input');
    fireEvent.change(searchInput, { target: { value: 'Cubbon Park' } });

    await waitFor(() => {
      expect(screen.getByTestId('location-search-item-0')).toBeInTheDocument();
    });

    // Click search item
    fireEvent.click(screen.getByTestId('location-search-item-0'));

    // Verify address auto-fill and coordinate readout
    await waitFor(() => {
      expect(screen.getByTestId('location-lat-display')).toHaveTextContent('Lat: 12.971598');
      expect(screen.getByTestId('location-lng-display')).toHaveTextContent('Lng: 77.594562');
    });

    // Change radius to 200m
    fireEvent.change(screen.getByTestId('site-radius-input'), {
      target: { value: '200' },
    });

    // Submit form
    fireEvent.click(screen.getByTestId('save-site-btn'));

    await waitFor(() => {
      expect(masterDataApi.createSiteApi).toHaveBeenCalledWith({
        name: 'MG Road Metro Station',
        project_id: 'proj-1',
        address: 'Cubbon Park, MG Road, Bengaluru, Karnataka, 560001, India',
        location: 'POINT(77.594562 12.971598)',
        permitted_radius_m: 200,
        is_active: true,
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Site "MG Road Metro Station" created successfully!/i)).toBeInTheDocument();
    });
  });

  it('restores saved marker coordinates and radius correctly in edit mode', async () => {
    const siteWithLocation = [
      {
        id: 'site-loc-1',
        name: 'Geofenced Site',
        project_id: 'proj-1',
        address: 'MG Road',
        location: 'POINT(77.594562 12.971598)',
        permitted_radius_m: 250,
        is_active: true,
      },
    ];

    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(siteWithLocation);
    vi.mocked(masterDataApi.updateSiteApi).mockResolvedValue({
      ...siteWithLocation[0],
      permitted_radius_m: 300,
    });

    renderSitesPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Geofenced Site')).toBeInTheDocument();
    });

    // Click edit
    fireEvent.click(screen.getByTestId('edit-site-site-loc-1'));

    expect(screen.getByText('Edit Construction Site')).toBeInTheDocument();

    // Verify restored coordinates in LocationPicker
    expect(screen.getByTestId('location-lat-display')).toHaveTextContent('Lat: 12.971598');
    expect(screen.getByTestId('location-lng-display')).toHaveTextContent('Lng: 77.594562');

    // Verify restored radius
    const radiusInput = screen.getByTestId('site-radius-input') as HTMLInputElement;
    expect(radiusInput.value).toBe('250');

    // Update radius via preset pill
    fireEvent.click(screen.getByTestId('location-radius-preset-500'));
    expect(radiusInput.value).toBe('500');

    // Save update
    fireEvent.click(screen.getByTestId('save-site-btn'));

    await waitFor(() => {
      expect(masterDataApi.updateSiteApi).toHaveBeenCalledWith('site-loc-1', {
        name: 'Geofenced Site',
        project_id: 'proj-1',
        address: 'MG Road',
        location: 'POINT(77.594562 12.971598)',
        permitted_radius_m: 500,
        is_active: true,
      });
    });
  });

  it('requires a valid location for sites intended for GPS attendance and blocks submission without location', async () => {
    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(mockSites);

    renderSitesPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('Central Junction Site')).toBeInTheDocument();
    });

    // Open add site form
    fireEvent.click(screen.getByTestId('add-site-btn'));

    // Fill name but omit location
    fireEvent.change(screen.getByTestId('site-name-input'), {
      target: { value: 'Site Missing GPS' },
    });

    // Save with GPS attendance required
    fireEvent.click(screen.getByTestId('save-site-btn'));

    // Should show validation error
    await waitFor(() => {
      expect(screen.getByText(/Please select a valid site location on the map for GPS geofenced attendance/i)).toBeInTheDocument();
    });
    expect(masterDataApi.createSiteApi).not.toHaveBeenCalled();
  });

  it('displays formatted location coordinates on site cards', async () => {
    const sitesWithCoords = [
      {
        id: 'site-coord-1',
        name: 'South Gate Tower',
        project_id: 'proj-1',
        address: 'Outer Ring Road',
        location: 'POINT(77.594562 12.971598)',
        permitted_radius_m: 100,
        is_active: true,
      },
    ];

    vi.mocked(masterDataApi.getProjectsApi).mockResolvedValue(mockProjects);
    vi.mocked(masterDataApi.getSitesApi).mockResolvedValue(sitesWithCoords);

    renderSitesPage('administrator');

    await waitFor(() => {
      expect(screen.getByText('South Gate Tower')).toBeInTheDocument();
    });

    // Should display human-readable coordinates
    expect(screen.getByText(/12.971598° N, 77.594562° E/)).toBeInTheDocument();
    expect(screen.getByText(/Geofence Radius:/)).toBeInTheDocument();
    expect(screen.getByText(/100 m/)).toBeInTheDocument();
  });
});
