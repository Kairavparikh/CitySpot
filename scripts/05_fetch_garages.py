#!/usr/bin/env python3
"""
Fetch Atlanta parking garages from Google Places API with full details
including reviews, ratings, hours, and pricing.
Merges with existing OSM garage data and saves to outputs/parking_garages.geojson.

Usage:
    python scripts/05_fetch_garages.py --api-key YOUR_KEY
    # or set GOOGLE_MAPS_API_KEY in .env
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.google_places import fetch_parking_garages, estimate_pricing

OUTPUT_FILE = Path('outputs/parking_garages.geojson')

# Multiple search centers to cover greater Atlanta
SEARCH_CENTERS = [
    (33.7490, -84.3880, 'Downtown/Midtown Atlanta'),
    (33.8490, -84.3670, 'Buckhead'),
    (33.7748, -84.2963, 'Decatur'),
    (33.7750, -84.3970, 'Georgia Tech'),
]


def load_osm_garages():
    """Load existing OSM garages from GeoJSON (preserve them)."""
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE) as f:
            data = json.load(f)
        osm = [f for f in data.get('features', [])
               if f['properties'].get('source') == 'OpenStreetMap']
        print(f"Preserved {len(osm)} existing OSM garages")
        return osm
    return []


def main():
    parser = argparse.ArgumentParser(description='Fetch parking garage data from Google Places')
    parser.add_argument('--api-key', type=str, default=None,
                        help='Google Places API key (or set GOOGLE_MAPS_API_KEY env var)')
    parser.add_argument('--radius', type=int, default=5000,
                        help='Search radius per center in meters (default: 5000)')
    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.environ.get('GOOGLE_MAPS_API_KEY')
    if not api_key:
        # Try loading from .env
        env_path = Path(__file__).parent.parent / '.env'
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith('GOOGLE_MAPS_API_KEY='):
                    api_key = line.split('=', 1)[1].strip()
                    break

    if not api_key:
        print("ERROR: No Google Maps API key found.")
        print("Either:")
        print("  1. Pass it: python scripts/05_fetch_garages.py --api-key YOUR_KEY")
        print("  2. Add to .env: GOOGLE_MAPS_API_KEY=your_key_here")
        sys.exit(1)

    print("=" * 60)
    print("ParkSight — Google Places Garage Fetcher (with Reviews)")
    print("=" * 60)

    # 1. Preserve existing OSM garages
    osm_features = load_osm_garages()

    # 2. Fetch Google Places data from multiple centers
    all_google_features = []
    seen_place_ids = set()

    for lat, lon, area_name in SEARCH_CENTERS:
        print(f"\nSearching {area_name}...")
        try:
            result = fetch_parking_garages(lat, lon, radius=args.radius, api_key=api_key)
            new_features = result.get('features', [])

            added = 0
            for feat in new_features:
                pid = feat['properties'].get('place_id')
                if pid and pid not in seen_place_ids:
                    seen_place_ids.add(pid)

                    # Add estimated pricing
                    price_level = feat['properties'].get('price_level') or 2
                    feat['properties']['price_level'] = price_level
                    pricing = estimate_pricing(price_level)
                    feat['properties']['estimated_hourly'] = pricing['hourly']
                    feat['properties']['estimated_daily'] = pricing['daily']
                    feat['properties']['price_description'] = pricing['description']

                    all_google_features.append(feat)
                    added += 1

            print(f"  Added {added} new garages (total: {len(all_google_features)})")
            time.sleep(1)

        except Exception as e:
            print(f"  Warning: Error fetching {area_name}: {e}")

    print(f"\nTotal Google Places garages: {len(all_google_features)}")

    # Stats
    with_reviews = sum(1 for f in all_google_features if f['properties'].get('reviews'))
    rated = [f for f in all_google_features if f['properties'].get('rating')]
    if rated:
        avg_rating = sum(f['properties']['rating'] for f in rated) / len(rated)
        total_reviews = sum(f['properties'].get('total_ratings', 0) for f in all_google_features)
        print(f"Garages with review snippets: {with_reviews}")
        print(f"Average rating: {avg_rating:.1f}/5.0")
        print(f"Total reviews across all garages: {total_reviews:,}")

    # 3. Merge OSM + Google Places
    merged = osm_features + all_google_features
    print(f"\nMerged: {len(merged)} total ({len(osm_features)} OSM + {len(all_google_features)} Google Places)")

    # 4. Save
    OUTPUT_FILE.parent.mkdir(exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': merged}, f, indent=2)

    print(f"\nSaved to {OUTPUT_FILE}")
    print("\nTop rated garages:")
    sorted_g = sorted(rated, key=lambda x: x['properties']['rating'], reverse=True)[:5]
    for i, feat in enumerate(sorted_g, 1):
        p = feat['properties']
        reviews = p.get('reviews', [])
        print(f"  {i}. {p['name']} — {p['rating']}/5.0 "
              f"({p.get('total_ratings', 0)} reviews, {len(reviews)} snippets)")

    print("\nDone! Reload the frontend to see updated markers with ratings and reviews.")


if __name__ == '__main__':
    main()
