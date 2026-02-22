#!/usr/bin/env python3
"""
Generate demo GeoJSON data for testing the frontend.

This creates fake parking lot data around Atlanta so you can test
the web interface without running the full pipeline.

Usage:
    python scripts/generate_demo_data.py
"""

import json
import random
from pathlib import Path

def generate_random_polygon(center_lat, center_lon, size_category):
    """Generate a random rectangular polygon."""
    # Size ranges in degrees (approximate)
    if size_category == "small":
        width = random.uniform(0.0005, 0.001)
        height = random.uniform(0.0005, 0.001)
    elif size_category == "medium":
        width = random.uniform(0.001, 0.002)
        height = random.uniform(0.001, 0.002)
    else:  # large
        width = random.uniform(0.002, 0.004)
        height = random.uniform(0.002, 0.004)

    # Create rectangular coordinates
    half_w = width / 2
    half_h = height / 2

    return [
        [
            [center_lon - half_w, center_lat - half_h],
            [center_lon + half_w, center_lat - half_h],
            [center_lon + half_w, center_lat + half_h],
            [center_lon - half_w, center_lat + half_h],
            [center_lon - half_w, center_lat - half_h]
        ]
    ]

def calculate_area(coords):
    """Estimate area in m² from lat/lon coordinates."""
    # Simple approximation using bounding box
    lons = [p[0] for p in coords[0]]
    lats = [p[1] for p in coords[0]]

    width_deg = max(lons) - min(lons)
    height_deg = max(lats) - min(lats)

    # At ~34°N: 1° lon ≈ 90km, 1° lat ≈ 111km
    width_m = width_deg * 90000
    height_m = height_deg * 111000

    return width_m * height_m

def generate_demo_data(num_lots=10):
    """Generate demo parking lot data."""
    # Atlanta center
    center_lat = 33.7490
    center_lon = -84.3880

    # Distribute lots around Atlanta
    features = []
    size_categories = ["small", "medium", "large"]

    for i in range(num_lots):
        # Random position within ~10km of center
        lat = center_lat + random.uniform(-0.09, 0.09)
        lon = center_lon + random.uniform(-0.11, 0.11)

        # Random size category
        size_category = random.choice(size_categories)

        # Generate polygon
        coords = generate_random_polygon(lat, lon, size_category)

        # Calculate area
        area_m2 = calculate_area(coords)

        # Estimate spots (standard spot = 12.5 m²)
        num_spots = int(area_m2 / 12.5)

        # Random confidence
        confidence = random.uniform(0.7, 0.95)

        feature = {
            "type": "Feature",
            "properties": {
                "lot_id": i,
                "area_m2": area_m2,
                "num_spots": num_spots,
                "confidence": confidence,
                "size_category": size_category,
                "center_lon": lon,
                "center_lat": lat
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": coords
            }
        }

        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    return geojson

def main():
    print("="*60)
    print("Generating Demo Data")
    print("="*60)

    # Generate demo data
    num_lots = 10
    print(f"\nGenerating {num_lots} demo parking lots...")
    demo_data = generate_demo_data(num_lots)

    # Save to outputs directory
    output_path = Path("outputs/parking_lots.geojson")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(demo_data, f, indent=2)

    print(f"✓ Saved to {output_path}")

    # Print stats
    total_spots = sum(f['properties']['num_spots'] for f in demo_data['features'])
    total_area = sum(f['properties']['area_m2'] for f in demo_data['features'])

    print(f"\nDemo Data Statistics:")
    print(f"  Total lots: {len(demo_data['features'])}")
    print(f"  Total spots: {total_spots}")
    print(f"  Total area: {total_area:.2f} m²")

    print("\n" + "="*60)
    print("Demo data generated!")
    print("Launch the frontend to view:")
    print("  cd frontend")
    print("  python -m http.server 8000")
    print("  Open http://localhost:8000")
    print("="*60)

if __name__ == "__main__":
    main()
