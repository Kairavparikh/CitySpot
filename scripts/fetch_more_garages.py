#!/usr/bin/env python3
"""
Fetch Atlanta parking garages from OpenStreetMap via Overpass API.
Merges with existing parking_garages.geojson and re-ingests into Actian VectorAI DB.
"""

import json
import sys
import time
import requests
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent.parent / "outputs" / "parking_garages.geojson"
OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# Bounding box covers greater Atlanta metro area
ATLANTA_BBOX = "33.60,-84.55,33.90,-84.20"


def fetch_osm_garages():
    """Query Overpass for all parking structures in Atlanta."""
    query = f"""
    [out:json][timeout:60];
    (
      node["amenity"="parking"]["parking"="multi-storey"]({ATLANTA_BBOX});
      way["amenity"="parking"]["parking"="multi-storey"]({ATLANTA_BBOX});
      relation["amenity"="parking"]["parking"="multi-storey"]({ATLANTA_BBOX});
      node["amenity"="parking"]["parking"="underground"]({ATLANTA_BBOX});
      way["amenity"="parking"]["parking"="underground"]({ATLANTA_BBOX});
      node["amenity"="parking_garage"]({ATLANTA_BBOX});
      way["amenity"="parking_garage"]({ATLANTA_BBOX});
      node["building"="parking"]({ATLANTA_BBOX});
      way["building"="parking"]({ATLANTA_BBOX});
      node["building"="garage"]({ATLANTA_BBOX});
      way["building"="garage"]({ATLANTA_BBOX});
    );
    out center tags;
    """

    print("Querying Overpass API for Atlanta parking structures...")
    try:
        resp = requests.post(OVERPASS_URL, data={"data": query}, timeout=60)
        resp.raise_for_status()
        return resp.json().get("elements", [])
    except requests.exceptions.Timeout:
        print("Overpass timed out, trying backup server...")
        try:
            resp = requests.post(
                "https://overpass.kumi.systems/api/interpreter",
                data={"data": query},
                timeout=60,
            )
            resp.raise_for_status()
            return resp.json().get("elements", [])
        except Exception as e:
            print(f"Backup server failed: {e}")
            return []
    except Exception as e:
        print(f"Overpass error: {e}")
        return []


def elements_to_features(elements):
    """Convert OSM elements to GeoJSON features."""
    features = []
    seen_names = set()

    for el in elements:
        tags = el.get("tags", {})

        # Get coordinates
        if el["type"] == "node":
            lat, lon = el.get("lat"), el.get("lon")
        elif el["type"] in ("way", "relation"):
            center = el.get("center", {})
            lat, lon = center.get("lat"), center.get("lon")
        else:
            continue

        if not lat or not lon:
            continue

        name = tags.get("name") or tags.get("operator") or f"Parking Structure ({lat:.4f},{lon:.4f})"

        # Deduplicate by name+coords
        key = f"{name}_{round(lat,3)}_{round(lon,3)}"
        if key in seen_names:
            continue
        seen_names.add(key)

        capacity = tags.get("capacity")
        try:
            capacity = int(capacity)
        except (TypeError, ValueError):
            capacity = None

        parking_type = tags.get("parking", "")
        if parking_type == "underground":
            structure_type = "underground"
        else:
            structure_type = "garage"

        levels = tags.get("building:levels") or tags.get("levels")
        try:
            levels = int(levels)
        except (TypeError, ValueError):
            levels = None

        feature = {
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
            "properties": {
                "type": structure_type,
                "name": name,
                "source": "OpenStreetMap",
                "address": tags.get("addr:full") or (
                    f"{tags.get('addr:housenumber','')} {tags.get('addr:street','')}".strip()
                ) or None,
                "capacity": capacity,
                "levels": levels,
                "operator": tags.get("operator"),
                "fee": tags.get("fee"),
                "opening_hours": tags.get("opening_hours"),
                "osm_id": el.get("id"),
                "osm_type": el["type"],
                "price_level": 2,
                "estimated_hourly": "$2–4/hr",
                "estimated_daily": "$15–25/day",
            },
        }
        features.append(feature)

    return features


def load_existing():
    """Load existing garages geojson."""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            data = json.load(f)
        return data.get("features", [])
    return []


def merge_features(existing, new_features):
    """Merge new features, avoiding duplicates by name+coords."""
    existing_keys = set()
    for feat in existing:
        coords = feat["geometry"]["coordinates"]
        name = feat["properties"].get("name", "")
        key = f"{name}_{round(coords[1],3)}_{round(coords[0],3)}"
        existing_keys.add(key)

    added = 0
    for feat in new_features:
        coords = feat["geometry"]["coordinates"]
        name = feat["properties"].get("name", "")
        key = f"{name}_{round(coords[1],3)}_{round(coords[0],3)}"
        if key not in existing_keys:
            existing.append(feat)
            existing_keys.add(key)
            added += 1

    return existing, added


def build_garage_rag_text(features):
    """Build descriptive text chunks for RAG ingestion."""
    chunks = []

    # Overall summary
    total = len(features)
    garages = [f for f in features if f["properties"]["type"] == "garage"]
    underground = [f for f in features if f["properties"]["type"] == "underground"]
    with_capacity = [f for f in features if f["properties"].get("capacity")]
    total_capacity = sum(f["properties"]["capacity"] for f in with_capacity)

    chunks.append({
        "text": (
            f"Atlanta has {total} known parking structures including {len(garages)} above-ground "
            f"parking garages and {len(underground)} underground parking facilities. "
            f"Of these, {len(with_capacity)} have known capacity data totaling {total_capacity:,} spaces. "
            f"Parking garages are distributed across Downtown, Midtown, Buckhead, Decatur, "
            f"Georgia Tech campus, Emory University, and surrounding neighborhoods."
        ),
        "source": "osm_garages_summary",
        "chunk_id": 0,
    })

    # Group by neighborhood/area
    areas = {
        "Downtown Atlanta": (33.748, -84.391, 0.015),
        "Midtown Atlanta": (33.784, -84.383, 0.018),
        "Buckhead": (33.849, -84.378, 0.020),
        "Old Fourth Ward": (33.762, -84.368, 0.015),
        "Decatur": (33.774, -84.296, 0.015),
        "Georgia Tech": (33.775, -84.397, 0.012),
        "Emory / Druid Hills": (33.793, -84.325, 0.018),
        "Midtown South / West End": (33.736, -84.412, 0.020),
    }

    for area_name, (clat, clon, radius) in areas.items():
        nearby = [
            f for f in features
            if abs(f["geometry"]["coordinates"][1] - clat) < radius
            and abs(f["geometry"]["coordinates"][0] - clon) < radius
        ]
        if not nearby:
            continue

        names = [f["properties"]["name"] for f in nearby[:8]]
        capacities = [f["properties"]["capacity"] for f in nearby if f["properties"].get("capacity")]
        total_cap = sum(capacities) if capacities else None

        text = (
            f"{area_name} has {len(nearby)} parking structures: {', '.join(names[:6])}. "
        )
        if total_cap:
            text += f"Total known capacity in {area_name}: {total_cap:,} spaces. "
        text += (
            f"Typical rates: $2–5/hr for surface lots, $3–8/hr for garages. "
            f"Most structures offer daily max rates of $15–30."
        )

        chunks.append({
            "text": text,
            "source": f"osm_garages_{area_name.lower().replace(' ', '_').replace('/', '_')}",
            "chunk_id": 0,
        })

    return chunks


def reingest_garages(chunks):
    """Add garage chunks to Actian VectorAI DB."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from cortex import CortexClient

    COLLECTION = "parksight_knowledge"
    HOST = "localhost:50051"

    print("\nLoading embedding model...")
    model = SentenceTransformer("all-MiniLM-L6-v2")

    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} garage knowledge chunks...")
    embeddings = model.encode(texts, show_progress_bar=True)
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings_norm = (embeddings / norms).tolist()

    with CortexClient(HOST) as client:
        # Find current max ID
        count = client.count(COLLECTION)
        start_id = count  # append after existing docs

        ids = list(range(start_id, start_id + len(chunks)))
        payloads = [{"text": c["text"], "source": c["source"], "chunk_id": c["chunk_id"]} for c in chunks]

        print(f"Inserting {len(chunks)} chunks (IDs {start_id}–{ids[-1]})...")
        client.batch_upsert(COLLECTION, ids=ids, vectors=embeddings_norm, payloads=payloads)

        new_count = client.count(COLLECTION)
        print(f"[OK] Collection now has {new_count} total documents")


def main():
    print("=" * 60)
    print("Atlanta Parking Garage Fetcher (OpenStreetMap)")
    print("=" * 60)

    # 1. Fetch from OSM
    elements = fetch_osm_garages()
    print(f"Got {len(elements)} raw OSM elements")

    if not elements:
        print("No data from OSM. Check your internet connection.")
        sys.exit(1)

    new_features = elements_to_features(elements)
    print(f"Parsed {len(new_features)} unique garage features")

    # 2. Merge with existing
    existing = load_existing()
    print(f"Existing garages in file: {len(existing)}")
    merged, added = merge_features(existing, new_features)
    print(f"Added {added} new garages (total: {len(merged)})")

    # 3. Save updated GeoJSON
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, "w") as f:
        json.dump({"type": "FeatureCollection", "features": merged}, f, indent=2)
    print(f"Saved {len(merged)} garages to {OUTPUT_FILE}")

    # 4. Build RAG chunks and re-ingest
    print("\nBuilding RAG knowledge chunks...")
    chunks = build_garage_rag_text(merged)
    print(f"Created {len(chunks)} knowledge chunks")

    reingest_garages(chunks)

    print("\n" + "=" * 60)
    print(f"Done! {len(merged)} garages now in GeoJSON + Actian DB")
    print("=" * 60)


if __name__ == "__main__":
    main()
