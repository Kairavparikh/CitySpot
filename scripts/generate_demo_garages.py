#!/usr/bin/env python3
"""Generate demo parking garage data for testing."""

import json
import random

# Atlanta garage locations (real places for realism)
demo_garages = [
    {"name": "Peachtree Center Parking", "lat": 33.7590, "lon": -84.3880},
    {"name": "CNN Center Parking Deck", "lat": 33.7580, "lon": -84.3950},
    {"name": "State Farm Arena Garage", "lat": 33.7573, "lon": -84.3963},
    {"name": "Mercedes-Benz Stadium Parking", "lat": 33.7553, "lon": -84.4006},
    {"name": "Georgia World Congress Center Deck", "lat": 33.7598, "lon": -84.3978},
    {"name": "Lenox Square Parking", "lat": 33.8470, "lon": -84.3619},
    {"name": "Phipps Plaza Garage", "lat": 33.8456, "lon": -84.3615},
    {"name": "Ponce City Market Parking", "lat": 33.7722, "lon": -84.3650},
    {"name": "Colony Square Garage", "lat": 33.7916, "lon": -84.3863},
    {"name": "Atlantic Station Deck", "lat": 33.7925, "lon": -84.3981},
    {"name": "Tech Square Parking", "lat": 33.7756, "lon": -84.3963},
    {"name": "Centennial Olympic Park Garage", "lat": 33.7631, "lon": -84.3939},
    {"name": "Georgia Aquarium Parking", "lat": 33.7634, "lon": -84.3951},
    {"name": "World of Coca-Cola Deck", "lat": 33.7628, "lon": -84.3927},
    {"name": "Fox Theatre Parking", "lat": 33.7726, "lon": -84.3853},
]

features = []

for i, garage in enumerate(demo_garages):
    # Generate realistic mock data
    rating = round(random.uniform(3.5, 4.9), 1)
    total_ratings = random.randint(100, 2000)
    price_level = random.randint(1, 4)

    # Price estimates based on level
    pricing = {
        1: {"hourly": "$2-4", "daily": "$10-15", "desc": "Inexpensive"},
        2: {"hourly": "$4-7", "daily": "$15-25", "desc": "Moderate"},
        3: {"hourly": "$7-12", "daily": "$25-35", "desc": "Expensive"},
        4: {"hourly": "$12-20", "daily": "$35-50", "desc": "Very Expensive"}
    }[price_level]

    feature = {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [garage["lon"], garage["lat"]]
        },
        "properties": {
            "type": "garage",
            "name": garage["name"],
            "rating": rating,
            "total_ratings": total_ratings,
            "price_level": price_level,
            "estimated_hourly": pricing["hourly"],
            "estimated_daily": pricing["daily"],
            "price_description": pricing["desc"],
            "address": f"{random.randint(100, 999)} Peachtree St NE, Atlanta, GA",
            "phone": f"(404) {random.randint(100, 999)}-{random.randint(1000, 9999)}",
            "source": "Demo Data"
        }
    }
    features.append(feature)

geojson = {
    "type": "FeatureCollection",
    "features": features
}

# Save to file
import os
os.makedirs('outputs', exist_ok=True)

with open('outputs/parking_garages.geojson', 'w') as f:
    json.dump(geojson, f, indent=2)

print("="*70)
print(f"✓ Generated {len(features)} demo parking garages")
print("✓ Saved to outputs/parking_garages.geojson")
print("="*70)
print()
print("Summary:")
print(f"  - Total garages: {len(features)}")
avg_rating = sum(f['properties']['rating'] for f in features) / len(features)
print(f"  - Average rating: {avg_rating:.1f}/5.0")
print()
print("🎯 This is DEMO data for testing.")
print("   Run scripts/05_fetch_garages.py with your API key for real data.")
print()
