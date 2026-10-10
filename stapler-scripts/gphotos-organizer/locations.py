from __future__ import annotations

from typing import Dict, Optional
from models import LocationInfo

DEFAULT_LOCATIONS: Dict[str, LocationInfo] = {
    "seattle": LocationInfo(name="Seattle, WA", lat=47.6062, lon=-122.3321),
    "boston": LocationInfo(name="Boston, MA", lat=42.3601, lon=-71.0589),
    "las vegas": LocationInfo(name="Las Vegas, NV", lat=36.1699, lon=-115.1398),
    "vegas": LocationInfo(name="Las Vegas, NV", lat=36.1699, lon=-115.1398),
    "fullerton": LocationInfo(name="Fullerton, CA", lat=33.8704, lon=-117.9242),
    "new orleans": LocationInfo(name="New Orleans, LA", lat=29.9511, lon=-90.0715),
    "neworleans": LocationInfo(name="New Orleans, LA", lat=29.9511, lon=-90.0715),
    "iowa": LocationInfo(name="Ames, IA", lat=42.0308, lon=-93.6319),
    "ames": LocationInfo(name="Ames, IA", lat=42.0308, lon=-93.6319),
    "ames, ia": LocationInfo(name="Ames, IA", lat=42.0308, lon=-93.6319),
    "daleside": LocationInfo(name="Hawthorne, CA", lat=33.9167, lon=-118.3333),
    "hawthorne": LocationInfo(name="Hawthorne, CA", lat=33.9167, lon=-118.3333),
    "maria regina": LocationInfo(name="Gardena, CA", lat=33.8883, lon=-118.3089),
    "gardena": LocationInfo(name="Gardena, CA", lat=33.8883, lon=-118.3089),
    "el camino": LocationInfo(name="Torrance, CA", lat=33.8767, lon=-118.3308),
    "torrance": LocationInfo(name="Torrance, CA", lat=33.8767, lon=-118.3308),
    "sbu": LocationInfo(name="Stony Brook, NY", lat=40.9123, lon=-73.1234),
    "stony brook": LocationInfo(name="Stony Brook, NY", lat=40.9123, lon=-73.1234),
    "carnivle cruise": LocationInfo(name="Caribbean Sea", lat=25.0000, lon=-71.0000),
    "carnival cruise": LocationInfo(name="Caribbean Sea", lat=25.0000, lon=-71.0000),
}


def find_location_in_string(text: str, custom_locations: Optional[Dict[str, LocationInfo]] = None) -> Optional[LocationInfo]:
    lookup = {**DEFAULT_LOCATIONS, **(custom_locations or {})}
    lower_text = text.lower()
    
    for key, loc in lookup.items():
        if key in lower_text:
            return loc
            
    return None
