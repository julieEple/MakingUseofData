"""
Fetch park outlines from OpenStreetMap → GeoJSON + Leaflet HTML
===============================================================
Run once locally to generate parks.geojson and map.html

    pip install requests
    python fetch_parks.py
"""

import json
import time
import requests

PARKS = [
    "Parco Civico Villa Ciani",
    "Parco San Michele",
    "Parco del Tassino",
    "Parco Paradiso",
    "Rivetta Tell",
    "SkatePark Lugano",
    "Parco Lambertenghi",
    "Dog Park Tassino",
]

# Bounding box around Lugano
BBOX = "45.9,8.8,46.1,9.1"

# Colors per park (customise as you like)
COLORS = [
    "#2D6A4F", "#52B788", "#74C69D", "#95D5B2",
    "#B7E4C7", "#40916C", "#1B4332", "#081C15"
]


def fetch_park_geometry(name: str) -> dict | None:
    """Fetch way or relation geometry for a named park."""
    query = f"""
[out:json][timeout:20];
(
  way["name"="{name}"]["leisure"]({{bbox}});
  way["name"="{name}"]["leisure"~"park|garden|playground|pitch"]({{bbox}});
  way["name"="{name}"]({{bbox}});
  relation["name"="{name}"]({{bbox}});
);
out geom;
""".replace("{bbox}", BBOX)

    for attempt in range(3):
        resp = requests.post(
            "https://overpass-api.de/api/interpreter",
            data={"data": query},
            headers={"User-Agent": "fetch_parks/1.0 (lugano-park-map)"},
            timeout=30,
        )
        if resp.status_code == 429:
            time.sleep(10 * (attempt + 1))
            continue
        break
    resp.raise_for_status()
    data = resp.json()
    elements = data.get("elements", [])

    if not elements:
        return None

    # Prefer the largest element (most nodes = most detailed outline)
    el = max(elements, key=lambda e: len(e.get("geometry", e.get("members", []))))
    return el


def element_to_geojson(el: dict, name: str, color: str) -> dict | None:
    """Convert an Overpass element to a GeoJSON Feature."""

    if el["type"] == "way":
        coords = [[g["lon"], g["lat"]] for g in el.get("geometry", [])]
        if not coords:
            return None
        # Close the polygon
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        geometry = {"type": "Polygon", "coordinates": [coords]}

    elif el["type"] == "relation":
        # Use the outer members
        rings = []
        for member in el.get("members", []):
            if member.get("role") == "outer" and "geometry" in member:
                coords = [[g["lon"], g["lat"]] for g in member["geometry"]]
                if coords and coords[0] != coords[-1]:
                    coords.append(coords[0])
                rings.append(coords)
        if not rings:
            return None
        geometry = {"type": "MultiPolygon", "coordinates": [[r] for r in rings]}

    else:
        return None

    return {
        "type": "Feature",
        "properties": {"name": name, "color": color},
        "geometry": geometry,
    }


def build_geojson(features: list) -> dict:
    return {"type": "FeatureCollection", "features": features}


def build_html(geojson: dict) -> str:
    geojson_str = json.dumps(geojson, indent=2)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Lugano Parks</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
  <style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{ font-family: sans-serif; }}
    #map {{ width: 100vw; height: 100vh; }}
    .park-label {{
      background: white;
      border: none;
      font-size: 12px;
      font-weight: 500;
      padding: 2px 6px;
      border-radius: 4px;
      box-shadow: 0 1px 4px rgba(0,0,0,0.2);
    }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    const map = L.map('map').setView([46.005, 8.955], 13);

    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19,
    }}).addTo(map);

    const parks = {geojson_str};

    L.geoJSON(parks, {{
      style: function(feature) {{
        return {{
          color: feature.properties.color,
          fillColor: feature.properties.color,
          fillOpacity: 0.35,
          weight: 2,
        }};
      }},
      onEachFeature: function(feature, layer) {{
        const name = feature.properties.name;
        layer.bindTooltip(name, {{
          permanent: true,
          direction: 'center',
          className: 'park-label',
        }});
        layer.bindPopup('<strong>' + name + '</strong>');
      }}
    }}).addTo(map);
  </script>
</body>
</html>"""


def main():
    features = []

    for i, name in enumerate(PARKS):
        print(f"Fetching: {name} …")
        try:
            el = fetch_park_geometry(name)
            if el:
                feature = element_to_geojson(el, name, COLORS[i % len(COLORS)])
                if feature:
                    features.append(feature)
                    print(f"  ✅ Found ({el['type']} id={el['id']})")
                else:
                    print(f"  ⚠️  Could not convert geometry")
            else:
                print(f"  ❌ Not found in OSM — try searching manually at overpass-turbo.eu")
        except Exception as e:
            print(f"  ❌ Error: {e}")
        time.sleep(5)  # be polite to the API

    # Save GeoJSON
    geojson = build_geojson(features)
    with open("parks.geojson", "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2, ensure_ascii=False)
    print(f"\n✅ parks.geojson saved ({len(features)} parks)")

    # Save HTML
    html = build_html(geojson)
    with open("map.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✅ map.html saved — open in browser to preview")
    print("\nTo embed in your existing HTML, copy the <script> block and the GeoJSON into your page.")


if __name__ == "__main__":
    main()