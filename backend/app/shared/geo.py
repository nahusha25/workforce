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


def parse_location_to_lat_lng(location) -> tuple[float | None, float | None]:
    """
    Safely extracts (latitude, longitude) as floats from various location formats:
    - GeoAlchemy2 WKBElement (as loaded from PostGIS geography columns)
    - Raw WKB bytes or memoryview
    - OGC WKT strings such as 'POINT(longitude latitude)'

    Guarantees:
    - Returns (None, None) if location is missing, empty, malformed, or (0, 0).
    - Never substitutes default or fake coordinates.
    - Accurately respects WKT/WKB axis order (X = longitude, Y = latitude).
    """
    if location is None:
        return None, None

    import struct

    wkb_bytes = None
    if hasattr(location, "data") and isinstance(location.data, (bytes, bytearray, memoryview)):
        wkb_bytes = bytes(location.data)
    elif isinstance(location, (bytes, bytearray, memoryview)):
        wkb_bytes = bytes(location)
    elif isinstance(location, str) and not location.strip().upper().startswith("POINT"):
        trimmed = location.strip()
        if len(trimmed) >= 42:
            try:
                wkb_bytes = bytes.fromhex(trimmed)
            except ValueError:
                wkb_bytes = None

    if wkb_bytes and len(wkb_bytes) >= 21:
        try:
            byte_order = "<" if wkb_bytes[0] == 1 else ">"
            geom_type = struct.unpack(f"{byte_order}I", wkb_bytes[1:5])[0]
            offset = 5
            # EWKB flag: 0x20000000 indicates 4-byte SRID prefix
            if geom_type & 0x20000000:
                offset += 4
                geom_type &= ~0x20000000

            if geom_type == 1:  # Point
                x, y = struct.unpack(f"{byte_order}dd", wkb_bytes[offset : offset + 16])
                # Strictly guard against (0, 0)
                if abs(x) < 1e-6 and abs(y) < 1e-6:
                    return None, None
                if -90.0 <= y <= 90.0 and -180.0 <= x <= 180.0:
                    return round(float(y), 7), round(float(x), 7)
        except Exception:
            pass

    # 2. Handle OGC WKT string (e.g., 'POINT(77.50956 12.96629)')
    if isinstance(location, str):
        trimmed = location.strip()
        if trimmed.upper().startswith("POINT") and "(" in trimmed and ")" in trimmed:
            try:
                content = trimmed[trimmed.index("(") + 1 : trimmed.rindex(")")].strip()
                parts = content.split()
                if len(parts) >= 2:
                    lng = float(parts[0])
                    lat = float(parts[1])
                    # Strictly guard against (0, 0)
                    if abs(lat) < 1e-6 and abs(lng) < 1e-6:
                        return None, None
                    if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
                        return round(lat, 7), round(lng, 7)
            except Exception:
                pass

    return None, None

