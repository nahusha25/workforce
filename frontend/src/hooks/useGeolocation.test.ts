import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useGeolocation } from './useGeolocation';

// Mock geolocation
const mockGeolocation = {
  getCurrentPosition: vi.fn(),
};

Object.defineProperty(globalThis.navigator, 'geolocation', {
  value: mockGeolocation,
  configurable: true,
});

describe('useGeolocation', () => {
  beforeEach(() => {
    mockGeolocation.getCurrentPosition.mockReset();
  });

  it('should have correct initial state', () => {
    const { result } = renderHook(() => useGeolocation());
    expect(result.current.location).toBeNull();
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(typeof result.current.getLocation).toBe('function');
  });

  it('should set error if geolocation is not supported', () => {
    const originalGeolocation = globalThis.navigator.geolocation;
    Object.defineProperty(globalThis.navigator, 'geolocation', {
      value: undefined,
      configurable: true,
    });

    const { result } = renderHook(() => useGeolocation());

    act(() => {
      result.current.getLocation();
    });

    expect(result.current.error).toBe('Geolocation is not supported by your browser');
    expect(result.current.loading).toBe(false);

    // Restore
    Object.defineProperty(globalThis.navigator, 'geolocation', {
      value: originalGeolocation,
      configurable: true,
    });
  });

  it('should acquire successful location', () => {
    mockGeolocation.getCurrentPosition.mockImplementationOnce((successCallback) => {
      successCallback({
        coords: {
          latitude: 40.7128,
          longitude: -74.0060,
        },
      });
    });

    const { result } = renderHook(() => useGeolocation());

    act(() => {
      result.current.getLocation();
    });

    // It should trigger loading (synchronously inside act before callback if it wasn't mocked synchronously, 
    // but here the callback is immediate, so loading should be false immediately after success)
    expect(mockGeolocation.getCurrentPosition).toHaveBeenCalled();
    expect(result.current.loading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(result.current.location).toEqual({
      latitude: 40.7128,
      longitude: -74.0060,
    });
  });

  it('should handle PERMISSION_DENIED', () => {
    mockGeolocation.getCurrentPosition.mockImplementationOnce((_, errorCallback) => {
      errorCallback({
        code: 1, // PERMISSION_DENIED
        PERMISSION_DENIED: 1,
        POSITION_UNAVAILABLE: 2,
        TIMEOUT: 3,
      });
    });

    const { result } = renderHook(() => useGeolocation());

    act(() => {
      result.current.getLocation();
    });

    expect(result.current.location).toBeNull();
    expect(result.current.error).toBe('Location permission denied');
    expect(result.current.loading).toBe(false);
  });

  it('should handle POSITION_UNAVAILABLE', () => {
    mockGeolocation.getCurrentPosition.mockImplementationOnce((_, errorCallback) => {
      errorCallback({
        code: 2, // POSITION_UNAVAILABLE
        PERMISSION_DENIED: 1,
        POSITION_UNAVAILABLE: 2,
        TIMEOUT: 3,
      });
    });

    const { result } = renderHook(() => useGeolocation());

    act(() => {
      result.current.getLocation();
    });

    expect(result.current.error).toBe('Location information is unavailable');
  });

  it('should handle TIMEOUT', () => {
    mockGeolocation.getCurrentPosition.mockImplementationOnce((_, errorCallback) => {
      errorCallback({
        code: 3, // TIMEOUT
        PERMISSION_DENIED: 1,
        POSITION_UNAVAILABLE: 2,
        TIMEOUT: 3,
      });
    });

    const { result } = renderHook(() => useGeolocation());

    act(() => {
      result.current.getLocation();
    });

    expect(result.current.error).toBe('The request to get user location timed out');
  });

  it('should clear stale error on re-trigger', () => {
    let callCount = 0;
    mockGeolocation.getCurrentPosition.mockImplementation((successCallback, errorCallback) => {
      callCount++;
      if (callCount === 1) {
        // First call fails
        errorCallback({
          code: 1,
          PERMISSION_DENIED: 1,
        });
      } else {
        // Second call succeeds
        successCallback({
          coords: { latitude: 10, longitude: 20 },
        });
      }
    });

    const { result } = renderHook(() => useGeolocation());

    // First call
    act(() => {
      result.current.getLocation();
    });
    expect(result.current.error).toBe('Location permission denied');

    // Second call
    act(() => {
      result.current.getLocation();
    });
    expect(result.current.error).toBeNull();
    expect(result.current.location).toEqual({ latitude: 10, longitude: 20 });
  });

  it('should verify loading state', () => {
    let successCallbackRef: any;
    mockGeolocation.getCurrentPosition.mockImplementationOnce((successCallback) => {
      successCallbackRef = successCallback;
    });

    const { result } = renderHook(() => useGeolocation());

    act(() => {
      result.current.getLocation();
    });

    // After calling getLocation but before the callback fires, loading should be true
    expect(result.current.loading).toBe(true);

    // Now fire the callback
    act(() => {
      successCallbackRef({
        coords: { latitude: 50, longitude: 50 },
      });
    });

    // Loading should be false again
    expect(result.current.loading).toBe(false);
    expect(result.current.location).toEqual({ latitude: 50, longitude: 50 });
  });
});
