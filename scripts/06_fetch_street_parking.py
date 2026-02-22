#!/usr/bin/env python3
"""Fetch street parking data from OpenStreetMap."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data.street_parking import fetch_openstreetmap_parking
import json


def main():
    print("="*70)
    print("ParkSight - Street Parking Data Fetcher")
    print("="*70)
    print()

    print("Fetching street parking zones from OpenStreetMap...")
    print("(This includes simulated real-time availability)")
    print()

    # Fetch street parking data
    data = fetch_openstreetmap_parking()

    if not data or not data.get('features'):
        print("No street parking data found.")
        print()
        print("Note: OSM street parking data depends on volunteer mapping.")
        print("For production, consider:")
        print("  - City of Atlanta Open Data Portal")
        print("  - ParkMobile API (paid)")
        print("  - Manual zone mapping")
        return

    # Save to file
    output_path = 'outputs/street_parking.geojson'
    os.makedirs('outputs', exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    print("="*70)
    print(f"✓ Saved {len(data['features'])} street parking zones")
    print(f"✓ Location: {output_path}")
    print("="*70)
    print()

    # Summary
    total_spaces = sum(f['properties']['total_spaces'] for f in data['features'])
    total_available = sum(f['properties']['available'] for f in data['features'])
    avg_occupancy = sum(f['properties']['occupancy_rate'] for f in data['features']) / len(data['features'])

    print("Summary:")
    print(f"  - Street parking zones: {len(data['features'])}")
    print(f"  - Total spaces: {total_spaces}")
    print(f"  - Currently available: {total_available}")
    print(f"  - Average occupancy: {avg_occupancy:.1f}%")
    print()
    print("💡 Real-time availability is simulated for demo.")
    print("   In production, integrate with ParkMobile or city APIs.")


if __name__ == '__main__':
    main()
