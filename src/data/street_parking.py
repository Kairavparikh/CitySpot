"""Fetch street parking data from Atlanta city sources."""

import requests
import json
from typing import Dict, List
from datetime import datetime


def fetch_atlanta_street_parking():
    """
    Fetch street parking zones from Atlanta Open Data.

    Note: This uses Atlanta's open data portal.
    Real-time availability would require ParkMobile API (paid).
    """

    # Atlanta Open Data Portal - Parking Meters
    # https://opendata.atlantaga.gov/
    base_url = "https://services3.arcgis.com/Et5Qeq3gvIjxnEQM/arcgis/rest/services"

    # Example endpoint (you may need to find the actual one)
    endpoint = f"{base_url}/Parking_Meters/FeatureServer/0/query"

    params = {
        'where': '1=1',  # Get all
        'outFields': '*',
        'f': 'geojson',
        'returnGeometry': 'true'
    }

    try:
        response = requests.get(endpoint, params=params)

        if response.status_code == 200:
            data = response.json()
            return process_street_parking(data)
        else:
            print(f"Warning: Could not fetch parking data (status {response.status_code})")
            return None

    except Exception as e:
        print(f"Error fetching street parking: {e}")
        return None


def fetch_parkmobile_availability(zone_id: str, api_key: str = None):
    """
    Fetch real-time availability from ParkMobile API.

    Args:
        zone_id: ParkMobile zone ID
        api_key: ParkMobile API key (requires partnership)

    Returns:
        Real-time availability data

    Note: This is a paid API requiring business partnership.
    For demo, we'll simulate availability.
    """
    if not api_key:
        # Simulate availability for demo
        import random
        return {
            'zone_id': zone_id,
            'total_spaces': random.randint(10, 50),
            'available': random.randint(0, 20),
            'occupied': random.randint(5, 30),
            'rate': f"${random.choice([1, 1.5, 2, 2.5])}/hr",
            'time_limit': random.choice(['2 hours', '3 hours', '4 hours', 'No limit']),
            'last_updated': datetime.now().isoformat()
        }

    # Real ParkMobile API call would go here
    # endpoint = f"https://api.parkmobile.com/v1/zones/{zone_id}/availability"
    # headers = {'Authorization': f'Bearer {api_key}'}
    # response = requests.get(endpoint, headers=headers)
    # return response.json()

    return None


def process_street_parking(geojson_data: Dict) -> Dict:
    """
    Process street parking GeoJSON and add availability estimates.

    Args:
        geojson_data: Raw GeoJSON from city API

    Returns:
        Processed GeoJSON with parking zones
    """
    features = []

    for feature in geojson_data.get('features', []):
        props = feature.get('properties', {})

        # Get real-time availability (simulated for demo)
        zone_id = props.get('ZONE_ID') or props.get('zone_id') or 'unknown'
        availability = fetch_parkmobile_availability(zone_id)

        # Create enhanced feature
        enhanced = {
            'type': 'Feature',
            'geometry': feature['geometry'],
            'properties': {
                'type': 'street_parking',
                'zone_id': zone_id,
                'name': f"Street Parking Zone {zone_id}",
                'address': props.get('LOCATION') or props.get('address') or 'Unknown',
                'total_spaces': availability['total_spaces'],
                'available': availability['available'],
                'occupied': availability['occupied'],
                'occupancy_rate': round(availability['occupied'] / availability['total_spaces'] * 100, 1),
                'hourly_rate': availability['rate'],
                'time_limit': availability['time_limit'],
                'payment_methods': ['ParkMobile', 'Credit Card', 'Coin'],
                'enforcement_hours': '8 AM - 6 PM Mon-Sat',
                'last_updated': availability['last_updated'],
                'source': 'City of Atlanta'
            }
        }
        features.append(enhanced)

    return {
        'type': 'FeatureCollection',
        'features': features
    }


def fetch_openstreetmap_parking():
    """
    Fetch street parking zones from OpenStreetMap (free alternative).

    Returns:
        GeoJSON with OSM parking data
    """
    # Overpass API query for Atlanta street parking
    overpass_url = "http://overpass-api.de/api/interpreter"

    # Atlanta bounding box
    bbox = [33.6490, -84.5880, 33.8490, -84.2880]  # [min_lat, min_lon, max_lat, max_lon]

    query = f"""
    [out:json][timeout:25];
    (
      way["amenity"="parking"]["parking"="street_side"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      way["amenity"="parking"]["parking"="lane"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      way["highway"]["parking:lane"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
    );
    out geom;
    """

    try:
        response = requests.get(overpass_url, params={'data': query})

        if response.status_code == 200:
            data = response.json()
            return convert_osm_to_geojson(data)
        else:
            print(f"Warning: OSM query failed (status {response.status_code})")
            return None

    except Exception as e:
        print(f"Error fetching OSM data: {e}")
        return None


def convert_osm_to_geojson(osm_data: Dict) -> Dict:
    """Convert OSM format to GeoJSON with simulated availability."""
    import random

    features = []

    for element in osm_data.get('elements', []):
        if element['type'] != 'way':
            continue

        # Extract coordinates
        coords = [[node['lon'], node['lat']] for node in element.get('geometry', [])]

        if not coords:
            continue

        # Get tags
        tags = element.get('tags', {})

        # Simulate availability
        total_spaces = random.randint(5, 30)
        available = random.randint(0, total_spaces)

        feature = {
            'type': 'Feature',
            'geometry': {
                'type': 'LineString',
                'coordinates': coords
            },
            'properties': {
                'type': 'street_parking',
                'name': tags.get('name', 'Street Parking'),
                'street': tags.get('highway', 'Unknown Street'),
                'total_spaces': total_spaces,
                'available': available,
                'occupied': total_spaces - available,
                'occupancy_rate': round((total_spaces - available) / total_spaces * 100, 1),
                'hourly_rate': '$2/hr',  # Typical Atlanta rate
                'time_limit': tags.get('parking:maxstay', '2 hours'),
                'payment_methods': ['ParkMobile'],
                'source': 'OpenStreetMap'
            }
        }
        features.append(feature)

    return {
        'type': 'FeatureCollection',
        'features': features
    }
