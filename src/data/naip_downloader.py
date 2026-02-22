"""NAIP imagery downloader using Google Earth Engine."""

import ee
import geojson
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import time


def authenticate_gee():
    """Authenticate and initialize Google Earth Engine."""
    import os

    # Try to get project from environment or use a default
    project = os.environ.get('GOOGLE_CLOUD_PROJECT') or os.environ.get('GEE_PROJECT')

    if not project:
        # Try to auto-detect project from gcloud config
        try:
            import subprocess
            result = subprocess.run(
                ['gcloud', 'config', 'get-value', 'project'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                project = result.stdout.strip()
                print(f"Auto-detected project: {project}")
        except:
            pass

    # If still no project, try without it first (works for some setups)
    if not project:
        try:
            ee.Initialize()
            print("GEE initialized successfully")
            return
        except:
            pass

        # Last resort: provide clear instructions
        print("\n" + "="*60)
        print("ERROR: Google Cloud project required for Earth Engine")
        print("="*60)
        print("\nQuick fix (2 minutes):")
        print("1. Go to: https://console.cloud.google.com/")
        print("2. Create a new project (any name, e.g., 'parksight')")
        print("3. Copy the Project ID")
        print("4. Run: export GEE_PROJECT='your-project-id'")
        print("5. Re-run this script")
        print("\nAlternatively, use demo data:")
        print("  cd frontend && python3 -m http.server 8000")
        print("="*60 + "\n")
        raise Exception("GEE project required. See instructions above.")

    # Initialize with project
    try:
        ee.Initialize(project=project)
        print(f"GEE initialized successfully with project: {project}")
    except Exception as e:
        print(f"Error initializing GEE: {e}")
        raise


def load_roi(roi_path):
    """
    Load region of interest from GeoJSON file.

    Args:
        roi_path: Path to GeoJSON file

    Returns:
        ee.Geometry
    """
    with open(roi_path, 'r') as f:
        data = geojson.load(f)

    coords = data['features'][0]['geometry']['coordinates'][0]
    return ee.Geometry.Polygon(coords)


def create_tile_grid(roi, tile_size_m=512):
    """
    Create a grid of tiles covering the ROI.

    Args:
        roi: ee.Geometry of the region of interest
        tile_size_m: Size of each tile in meters

    Returns:
        List of ee.Geometry tiles with metadata
    """
    bounds = roi.bounds().getInfo()['coordinates'][0]

    # Extract min/max lat/lon
    lons = [coord[0] for coord in bounds]
    lats = [coord[1] for coord in bounds]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    # Approximate degrees per meter (rough estimate)
    # At ~34°N latitude: 1° lon ≈ 90km, 1° lat ≈ 111km
    deg_per_m_lon = 1 / 90000
    deg_per_m_lat = 1 / 111000

    tile_deg_lon = tile_size_m * deg_per_m_lon
    tile_deg_lat = tile_size_m * deg_per_m_lat

    tiles = []
    tile_id = 0

    lat = min_lat
    while lat < max_lat:
        lon = min_lon
        while lon < max_lon:
            # Create tile polygon
            tile_coords = [
                [lon, lat],
                [lon + tile_deg_lon, lat],
                [lon + tile_deg_lon, lat + tile_deg_lat],
                [lon, lat + tile_deg_lat],
                [lon, lat]
            ]
            tile_geom = ee.Geometry.Polygon([tile_coords])

            # Check if tile intersects ROI
            if tile_geom.intersects(roi).getInfo():
                tiles.append({
                    'id': tile_id,
                    'geometry': tile_geom,
                    'center_lon': lon + tile_deg_lon / 2,
                    'center_lat': lat + tile_deg_lat / 2,
                    'bounds': [lon, lat, lon + tile_deg_lon, lat + tile_deg_lat]
                })
                tile_id += 1

            lon += tile_deg_lon
        lat += tile_deg_lat

    print(f"Created {len(tiles)} tiles covering ROI")
    return tiles


def download_naip_tile(tile, output_dir, config):
    """
    Download NAIP imagery for a single tile.

    Args:
        tile: Dictionary with tile geometry and metadata
        output_dir: Directory to save GeoTIFF
        config: Config dictionary

    Returns:
        Success status and file path
    """
    try:
        # Query NAIP collection
        naip = (ee.ImageCollection('USDA/NAIP/DOQQ')
                .filterBounds(tile['geometry'])
                .filterDate(f"{min(config['gee']['years'])}-01-01",
                          f"{max(config['gee']['years'])}-12-31")
                .select(config['gee']['bands'])
                .sort('system:time_start', False))  # Most recent first

        # Get the most recent image
        image = naip.first()

        if image is None:
            print(f"Warning: No NAIP imagery found for tile {tile['id']}")
            return False, None

        # Clip to tile bounds
        image = image.clip(tile['geometry'])

        # Export parameters
        output_path = Path(output_dir) / f"tile_{tile['id']:04d}.tif"

        # Get download URL
        # Note: For large-scale downloads, use Export.image.toDrive()
        # For hackathon, we'll use getDownloadUrl for small tiles
        url = image.getDownloadURL({
            'region': tile['geometry'],
            'scale': config['gee']['resolution'],
            'format': 'GEO_TIFF',
            'bands': config['gee']['bands']
        })

        # Download using requests (you'll need to add this)
        import requests
        response = requests.get(url, stream=True)

        with open(output_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        return True, str(output_path)

    except Exception as e:
        print(f"Error downloading tile {tile['id']}: {e}")
        return False, None


def download_all_tiles(roi_path, output_dir, config, max_tiles=None):
    """
    Download all NAIP tiles for the ROI.

    Args:
        roi_path: Path to ROI GeoJSON
        output_dir: Directory to save tiles
        config: Config dictionary
        max_tiles: Maximum number of tiles to download (for testing)

    Returns:
        DataFrame with tile metadata
    """
    authenticate_gee()

    # Load ROI
    roi = load_roi(roi_path)

    # Create tile grid
    tiles = create_tile_grid(roi, config['gee']['tile_size_m'])

    if max_tiles:
        tiles = tiles[:max_tiles]
        print(f"Limited to {max_tiles} tiles for testing")

    # Create output directory
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Download tiles
    metadata = []
    successful = 0

    for tile in tqdm(tiles, desc="Downloading tiles"):
        success, filepath = download_naip_tile(tile, output_dir, config)

        metadata.append({
            'tile_id': tile['id'],
            'center_lon': tile['center_lon'],
            'center_lat': tile['center_lat'],
            'bounds': str(tile['bounds']),
            'filepath': filepath,
            'success': success
        })

        if success:
            successful += 1

        # Rate limiting to avoid GEE quota issues
        time.sleep(0.5)

    print(f"\nDownload complete: {successful}/{len(tiles)} tiles successful")

    # Save metadata
    df = pd.DataFrame(metadata)
    metadata_path = Path(config['paths']['metadata'])
    metadata_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(metadata_path, index=False)
    print(f"Metadata saved to {metadata_path}")

    return df
