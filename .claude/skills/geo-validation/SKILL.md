---
name: geo-validation
description: Validate directional claims, walk times, and pedestrian routes using OSM data (Nominatim geocoding + Overpass queries). Fixes hallucinations about east/west/north/south, crossing barriers, and travel times by grounding everything in real coordinates.
---

# Geospatial Validation Skill

Use this skill whenever writing or reviewing content that makes claims about:
- Cardinal directions between real places ("X is north of Y", "walk east to Z")
- Walk, bike, or transit times between locations
- Pedestrian route feasibility (especially near major roads, highways, water)
- Which side of a road, barrier, or landmark a place is on

## When to Trigger

- Any document contains directional language about real-world places
- Walk times are stated or implied
- A route is described that might cross a major road or natural barrier
- Content was written without first looking up coordinates
- A previous version of the content contained a directional error

**Do not rely on training-data geography.** Street-level east/west/north/south claims are frequently wrong. Always derive from coordinates.

---

## Step 1 — Geocode All Locations

Use **Nominatim** (no API key required, 1 req/sec rate limit):

```python
import urllib.request, urllib.parse, json, time, math

def geocode(place: str, region: str = "Seattle, WA") -> tuple[float, float, str] | None:
    params = urllib.parse.urlencode({"q": f"{place}, {region}", "format": "json", "limit": 1})
    req = urllib.request.Request(
        f"https://nominatim.openstreetmap.org/search?{params}",
        headers={"User-Agent": "GeoValidation/1.0 contact@example.com"},
    )
    with urllib.request.urlopen(req, timeout=10) as r:
        results = json.loads(r.read())
    time.sleep(1.1)  # Nominatim policy: max 1 req/sec
    if results:
        return float(results[0]["lat"]), float(results[0]["lon"]), results[0]["display_name"]
    return None
```

**Always geocode both the origin and destination before making any directional claim.**

For named venues (bars, parks, hotels) that Nominatim may not find by address alone, try the venue name first, then fall back to the street address.

---

## Step 2 — Compute Cardinal Direction

```python
def bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """True bearing from A to B, degrees clockwise from north."""
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δλ = math.radians(lon2 - lon1)
    x = math.sin(Δλ) * math.cos(φ2)
    y = math.cos(φ1) * math.sin(φ2) - math.sin(φ1) * math.cos(φ2) * math.cos(Δλ)
    return (math.degrees(math.atan2(x, y)) + 360) % 360

def cardinal(brng: float, precision: str = "simple") -> str:
    """
    precision='simple'  → N / S / E / W
    precision='ordinal' → N / NE / E / SE / S / SW / W / NW
    """
    if precision == "simple":
        dirs = ["N", "E", "S", "W"]
        return dirs[round(brng / 90) % 4]
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[round(brng / 45) % 8]

def haversine_miles(lat1, lon1, lat2, lon2) -> float:
    R = 3958.8
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    dφ = math.radians(lat2 - lat1)
    dλ = math.radians(lon2 - lon1)
    a = math.sin(dφ/2)**2 + math.cos(φ1) * math.cos(φ2) * math.sin(dλ/2)**2
    return R * 2 * math.asin(math.sqrt(a))
```

Use `cardinal(bearing(lat_a, lon_a, lat_b, lon_b))` to verify any "B is east/west of A" claim before writing it. **Do not use longitude comparison alone** — longitude increases eastward, but street grids don't always align with cardinal axes.

---

## Step 3 — Detect Road Barriers Between Two Points

Before stating a walk is feasible, check whether a major road lies between the two points. Query Overpass for high-speed roads in the bounding box:

```python
OVERPASS_URL = "https://overpass-api.de/api/interpreter"

def find_barriers(lat_a, lon_a, lat_b, lon_b) -> list[dict]:
    """
    Returns major roads (motorway, trunk, primary) in the bounding box between A and B.
    These are potential pedestrian barriers requiring crossing analysis.
    """
    s = min(lat_a, lat_b) - 0.002
    n = max(lat_a, lat_b) + 0.002
    w = min(lon_a, lon_b) - 0.003
    e = max(lon_a, lon_b) + 0.003
    query = f"""
[out:json][timeout:25];
way["highway"~"motorway|trunk|primary"]["name"]({s},{w},{n},{e});
out body;
"""
    data = urllib.parse.urlencode({"data": query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data, headers={"User-Agent": "GeoValidation/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        elements = json.loads(r.read())["elements"]
    return [{"name": el["tags"].get("name",""), "highway": el["tags"].get("highway","")} for el in elements]
```

If `find_barriers()` returns results, proceed to Step 4 to find safe crossing points.

---

## Step 4 — Find Pedestrian Crossings on Barrier Roads

```python
def find_crossings_on_road(road_name: str, lat_a, lon_a, lat_b, lon_b) -> list[dict]:
    """
    Find signalized pedestrian crossings on a named road between two bounding points.
    Returns crossings sorted south-to-north by latitude.
    """
    s = min(lat_a, lat_b) - 0.005
    n = max(lat_a, lat_b) + 0.005
    w = min(lon_a, lon_b) - 0.008
    e = max(lon_a, lon_b) + 0.008

    # First: get way node IDs for the named road
    way_query = f"""
[out:json][timeout:25];
way["name"="{road_name}"]["highway"]({s},{w},{n},{e});
out body;
>;
out skel qt;
"""
    data = urllib.parse.urlencode({"data": way_query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data, headers={"User-Agent": "GeoValidation/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        result = json.loads(r.read())

    road_node_ids = set()
    for el in result["elements"]:
        if el["type"] == "way":
            road_node_ids.update(el.get("nodes", []))

    # Second: get all crossing nodes in area, filter to those on the road
    cross_query = f"""
[out:json][timeout:25];
(
  node["highway"="crossing"]({s},{w},{n},{e});
  node["highway"="traffic_signals"]({s},{w},{n},{e});
);
out body;
"""
    data = urllib.parse.urlencode({"data": cross_query}).encode()
    req = urllib.request.Request(OVERPASS_URL, data=data, headers={"User-Agent": "GeoValidation/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        nodes = json.loads(r.read())["elements"]

    crossings = []
    seen_lats = set()
    for node in nodes:
        if node["id"] not in road_node_ids:
            continue
        lat = round(node["lat"], 4)
        if lat in seen_lats:
            continue
        seen_lats.add(lat)
        tags = node.get("tags", {})
        crossings.append({
            "lat": node["lat"],
            "lon": node["lon"],
            "type": tags.get("crossing", tags.get("highway", "")),
            "signals": tags.get("crossing", "") == "traffic_signals" or tags.get("button_operated") == "yes",
        })

    return sorted(crossings, key=lambda c: c["lat"])
```

---

## Step 5 — Compute Realistic Walk Time

Straight-line distance understates real walk time when barriers exist. Apply:

```python
def walk_time_minutes(
    lat_a, lon_a, lat_b, lon_b,
    barrier_detour_miles: float = 0.0,
    pace_min_per_mile: float = 20,
) -> int:
    """
    pace_min_per_mile: 20 = city walk (with lights), 15 = brisk, 25 = leisurely
    barrier_detour_miles: extra distance to reach a crossing and backtrack
    """
    straight = haversine_miles(lat_a, lon_a, lat_b, lon_b)
    city_factor = 1.2  # grid detour vs. straight line
    total = (straight * city_factor + barrier_detour_miles) * pace_min_per_mile
    return round(total)
```

**Barrier detour estimation:**
- Pedestrian must walk to nearest crossing, cross, then walk back toward destination
- Estimate: `distance_to_nearest_crossing + crossing_width (~0.05 mi)`
- If no signalized crossing exists within 0.5 miles of the direct path: **do not state a walk time** — state "not recommended on foot; use rideshare or bus"

---

## Step 6 — Local OSM Subset (for Offline / High-Volume Use)

When running many queries or Overpass times out repeatedly, download a regional PBF:

```bash
# Install osmium-tool
brew install osmium-tool

# Download Washington State extract from Geofabrik (~300MB)
curl -O https://download.geofabrik.de/north-america/us/washington-latest.osm.pbf

# Extract just the Seattle area bounding box (lat 47.48-47.78, lon -122.46 to -122.22)
osmium extract \
  --bbox -122.46,47.48,-122.22,47.78 \
  washington-latest.osm.pbf \
  -o seattle.osm.pbf

# Convert to GeoJSON for Python use
osmium export seattle.osm.pbf -o seattle.geojson

# Query locally instead of Overpass — eliminates timeouts
```

For Python queries against a local PBF, install `pyrosm`:
```bash
uv add pyrosm   # or pip install pyrosm
```

```python
from pyrosm import OSM
osm = OSM("seattle.osm.pbf")
roads = osm.get_network("driving")  # or "walking", "cycling"
pois = osm.get_pois(custom_filter={"tourism": ["hotel", "motel"]})
```

Cache the downloaded PBF in the project directory. Geofabrik updates daily; re-download when data feels stale (> 2 weeks old for active urban areas).

---

## Validation Checklist

Before finalizing any content with directional or routing claims:

- [ ] All named locations geocoded via Nominatim — lat/lon confirmed, not assumed
- [ ] Cardinal direction derived from `bearing()` — not from memory or intuition
- [ ] Walk time uses haversine + city_factor (1.2), not straight-line
- [ ] Major road barriers checked via `find_barriers()`
- [ ] If barrier found: crossing locations confirmed via `find_crossings_on_road()`
- [ ] If no crossings within 0.5 mi of route: walking flagged as not recommended
- [ ] "Walk X min" claims account for detour to crossing, not just destination distance
- [ ] No directional phrases written before coordinates are in hand

---

## Common Failure Modes to Watch For

| Claim | Why it fails | Fix |
|---|---|---|
| "walk east to X" | Longitude alone doesn't determine east/west — use bearing() | Geocode both points, compute cardinal |
| "X is a 10-min walk" | Ignores barriers, grid detour factor, and crossing detours | Use walk_time_minutes() with barrier check |
| "cross Aurora at the light" | Assumes crossings exist — may be a mile gap | Query find_crossings_on_road() first |
| "Gas Works Park is west of Y" | Named parks are hard to intuit — their centroid may surprise you | Always geocode the park itself |
| "walk along the waterfront to X" | Waterways, fences, and grade changes break apparent routes | Query for barriers, not just distance |
