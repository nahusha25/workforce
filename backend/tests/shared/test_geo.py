import pytest
from app.shared.geo import calculate_distance_metres, is_within_geofence, validate_coordinates

def test_identical_coordinates():
    lat = 12.9716
    lng = 77.5946
    distance = calculate_distance_metres(lat, lng, lat, lng)
    assert distance == 0.0

def test_known_distance_accuracy():
    # Example coordinates:
    # Paris, France (approx)
    lat1, lng1 = 48.8566, 2.3522
    # London, UK (approx)
    lat2, lng2 = 51.5074, -0.1278
    
    distance = calculate_distance_metres(lat1, lng1, lat2, lng2)
    # Distance between Paris and London is approx 343.5 km.
    # Haversine distance for these specific coords with R=6371km is ~343556 m.
    assert 343550 <= distance <= 343560
    
def test_short_distance():
    # 1 degree of latitude is approx 111.32 km.
    # 0.0001 degree of latitude is approx 11.1 metres.
    lat1, lng1 = 12.0000, 77.0000
    lat2, lng2 = 12.0001, 77.0000
    
    distance = calculate_distance_metres(lat1, lng1, lat2, lng2)
    # Haversine distance with R=6371km should be approx 11.119 m.
    assert 11.10 <= distance <= 11.13

def test_validation_invalid_latitude():
    with pytest.raises(ValueError, match="Latitude must be between -90 and 90."):
        calculate_distance_metres(91.0, 77.0, 12.0, 77.0)
        
    with pytest.raises(ValueError, match="Latitude must be between -90 and 90."):
        calculate_distance_metres(12.0, 77.0, -90.1, 77.0)

def test_validation_invalid_longitude():
    with pytest.raises(ValueError, match="Longitude must be between -180 and 180."):
        calculate_distance_metres(12.0, 180.1, 12.0, 77.0)

    with pytest.raises(ValueError, match="Longitude must be between -180 and 180."):
        calculate_distance_metres(12.0, 77.0, 12.0, -181.0)

def test_validation_non_numeric():
    with pytest.raises(ValueError, match="Latitude and longitude must be numbers."):
        calculate_distance_metres("12.0", 77.0, 12.0, 77.0)

def test_is_within_geofence_exact_boundary():
    # Distance is approx 11.12 m
    lat1, lng1 = 12.0000, 77.0000
    lat2, lng2 = 12.0001, 77.0000
    
    distance = calculate_distance_metres(lat1, lng1, lat2, lng2)
    
    assert is_within_geofence(lat1, lng1, lat2, lng2, distance) == True
    
def test_is_within_geofence_inside():
    # Distance is approx 11.12 m
    lat1, lng1 = 12.0000, 77.0000
    lat2, lng2 = 12.0001, 77.0000
    
    # Radius is 20m, clearly inside
    assert is_within_geofence(lat1, lng1, lat2, lng2, 20.0) == True

def test_is_within_geofence_outside():
    # Distance is approx 11.12 m
    lat1, lng1 = 12.0000, 77.0000
    lat2, lng2 = 12.0001, 77.0000
    
    # Radius is 10m, just outside
    assert is_within_geofence(lat1, lng1, lat2, lng2, 10.0) == False

def test_is_within_geofence_clearly_outside():
    lat1, lng1 = 48.8566, 2.3522 # Paris
    lat2, lng2 = 51.5074, -0.1278 # London
    
    # Distance is ~343km
    # Radius is 100m, clearly outside
    assert is_within_geofence(lat1, lng1, lat2, lng2, 100.0) == False

def test_is_within_geofence_zero_radius():
    lat1, lng1 = 12.9716, 77.5946
    
    # Distance is 0, Radius is 0 -> True
    assert is_within_geofence(lat1, lng1, lat1, lng1, 0.0) == True
    
    lat2, lng2 = 12.9717, 77.5946
    # Distance > 0, Radius is 0 -> False
    assert is_within_geofence(lat1, lng1, lat2, lng2, 0.0) == False

def test_is_within_geofence_invalid_radius():
    with pytest.raises(ValueError, match="Radius must be non-negative."):
        is_within_geofence(12.0, 77.0, 12.0, 77.0, -10.0)
        
    with pytest.raises(ValueError, match="Radius must be a number."):
        is_within_geofence(12.0, 77.0, 12.0, 77.0, "100")
