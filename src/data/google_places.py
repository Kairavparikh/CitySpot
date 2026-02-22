"""Fetch parking garage data from Google Places API."""

import requests
import json
from typing import Dict, List


def fetch_parking_garages(center_lat: float, center_lon: float,
                          radius: int = 10000, api_key: str = None) -> Dict:
    """
    Fetch parking garages from Google Places API.

    Args:
        center_lat: Center latitude
        center_lon: Center longitude
        radius: Search radius in meters (max 50000)
        api_key: Google Places API key

    Returns:
        GeoJSON FeatureCollection with parking garage data
    """
    if not api_key:
        raise ValueError("Google Places API key is required")

    base_url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

    # Search parameters
    params = {
        'location': f"{center_lat},{center_lon}",
        'radius': radius,
        'type': 'parking',
        'key': api_key
    }

    print(f"Searching for parking garages within {radius/1000}km of Atlanta...")

    features = []
    next_page_token = None
    page_count = 0
    max_pages = 3  # Get up to 60 results (20 per page)

    while page_count < max_pages:
        # Add pagetoken if we have one
        if next_page_token:
            params['pagetoken'] = next_page_token
            import time
            time.sleep(2)  # Required delay between pagination requests

        # Make request
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        data = response.json()

        if data['status'] not in ['OK', 'ZERO_RESULTS']:
            print(f"Warning: API returned status {data['status']}")
            break

        # Process results from this page
        for place in data.get('results', []):
            # Get additional details
            details = get_place_details(place['place_id'], api_key)

            # Determine if it's a garage (vs surface lot)
            name = place.get('name', '').lower()
            types = place.get('types', [])

            # More lenient filtering - include various parking types
            is_garage = any([
                'garage' in name,
                'deck' in name,
                'structure' in name,
                'multi' in name,
                'underground' in name,
                'parking_garage' in types,
                'parking' in name and ('center' in name or 'plaza' in name or 'building' in name)
            ])

            if not is_garage:
                continue  # Skip surface lots (we detect those with AI)

            # Use rating from details if available (details call is more accurate)
            final_rating = details.get('rating_detail') or place.get('rating')
            final_total_ratings = details.get('total_ratings_detail') or place.get('user_ratings_total', 0)

            feature = {
                'type': 'Feature',
                'geometry': {
                    'type': 'Point',
                    'coordinates': [
                        place['geometry']['location']['lng'],
                        place['geometry']['location']['lat']
                    ]
                },
                'properties': {
                    'type': 'garage',
                    'name': place.get('name'),
                    'rating': final_rating,
                    'total_ratings': final_total_ratings,
                    'price_level': place.get('price_level'),
                    'address': place.get('vicinity'),
                    'place_id': place['place_id'],
                    'source': 'Google Places',
                    **details  # Add extra details (phone, hours, website, reviews, etc.)
                }
            }
            features.append(feature)

        # Check if there are more pages
        next_page_token = data.get('next_page_token')
        page_count += 1

        if not next_page_token:
            break  # No more pages

    print(f"Found {len(features)} parking garages (searched {page_count} pages)")

    return {
        'type': 'FeatureCollection',
        'features': features
    }


def get_place_details(place_id: str, api_key: str) -> Dict:
    """
    Get detailed information for a specific place.

    Args:
        place_id: Google Place ID
        api_key: Google Places API key

    Returns:
        Dictionary with additional details
    """
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"

    params = {
        'place_id': place_id,
        'fields': 'formatted_phone_number,opening_hours,website,price_level,reviews,rating,user_ratings_total',
        'key': api_key
    }

    try:
        response = requests.get(details_url, params=params)
        response.raise_for_status()
        data = response.json()

        if data['status'] == 'OK':
            result = data.get('result', {})

            # Extract opening hours
            hours = None
            if 'opening_hours' in result:
                hours = result['opening_hours'].get('weekday_text', [])

            # Extract reviews (up to 5 from API)
            reviews = []
            for r in result.get('reviews', []):
                reviews.append({
                    'author_name': r.get('author_name', 'Anonymous'),
                    'rating': r.get('rating', 0),
                    'text': r.get('text', ''),
                    'relative_time': r.get('relative_time_description', ''),
                    'time': r.get('time', 0),
                })

            return {
                'phone': result.get('formatted_phone_number'),
                'hours': hours,
                'website': result.get('website'),
                'price_level_detail': result.get('price_level'),
                'reviews': reviews,
                'rating_detail': result.get('rating'),
                'total_ratings_detail': result.get('user_ratings_total'),
            }
    except Exception as e:
        print(f"Warning: Could not fetch details for {place_id}: {e}")

    return {}


def estimate_pricing(price_level: int) -> Dict[str, str]:
    """
    Estimate parking rates based on Google's price level.

    Args:
        price_level: Google's price level (0-4)

    Returns:
        Dictionary with estimated rates
    """
    pricing_map = {
        0: {'hourly': '$1-2', 'daily': '$5-10', 'description': 'Very Inexpensive'},
        1: {'hourly': '$3-5', 'daily': '$10-15', 'description': 'Inexpensive'},
        2: {'hourly': '$5-8', 'daily': '$15-25', 'description': 'Moderate'},
        3: {'hourly': '$8-12', 'daily': '$25-35', 'description': 'Expensive'},
        4: {'hourly': '$12+', 'daily': '$35+', 'description': 'Very Expensive'}
    }

    return pricing_map.get(price_level, pricing_map[2])
