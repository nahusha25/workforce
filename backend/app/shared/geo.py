import math

EARTH_RADIUS_METRES = 6371000.0

def validate_coordinates(lat: float, lng: float) -> None:
    """Validates that GPS coordinates are within standard ranges."""
    if not isinstance(lat, (int, float)) or not isinstance(lng, (int, float)):
        raise ValueError("Latitude and longitude must be numbers.")
    if not -90.0 <= lat <= 90.0:
        raise ValueError("Latitude must be between -90 and 90.")
    if not -180.0 <= lng <= 180.0:
        raise ValueError("Longitude must be between -180 and 180.")

def calculate_distance_metres(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Calculates the geographical distance in metres between two GPS coordinates
    using the Haversine formula.
    """
    validate_coordinates(lat1, lng1)
    validate_coordinates(lat2, lng2)

    # Convert degrees to radians
    lat1_rad = math.radians(lat1)
    lng1_rad = math.radians(lng1)
    lat2_rad = math.radians(lat2)
    lng2_rad = math.radians(lng2)

    # Haversine formula
    dlon = lng2_rad - lng1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.asin(math.sqrt(a))
    
    return EARTH_RADIUS_METRES * c

def is_within_geofence(
    emp_lat: float,
    emp_lng: float,
    site_lat: float,
    site_lng: float,
    radius_metres: float
) -> bool:
    """
    Determines if an employee is within the specified radius of a site.
    Returns True if distance <= radius_metres, else False.
    """
    if not isinstance(radius_metres, (int, float)):
        raise ValueError("Radius must be a number.")
    if radius_metres < 0:
        raise ValueError("Radius must be non-negative.")
        
    distance = calculate_distance_metres(emp_lat, emp_lng, site_lat, site_lng)
    
    return distance <= radius_metres
