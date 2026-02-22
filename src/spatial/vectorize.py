"""Convert prediction masks to GeoJSON polygons."""

import numpy as np
import geopandas as gpd
from shapely.geometry import shape, mapping
from rasterio import features
from rasterio.crs import CRS
import pandas as pd

from ..inference.postprocess import estimate_parking_spots, categorize_lot_size


def mask_to_geojson(mask, transform, crs, config, prob_map=None):
    """
    Convert binary mask to GeoJSON polygons.

    Args:
        mask: Binary mask (H, W) as numpy array
        transform: Rasterio affine transform (pixel → lat/lon)
        crs: Coordinate reference system
        config: Configuration dictionary
        prob_map: Probability map (H, W) for confidence estimation

    Returns:
        GeoDataFrame with parking lot polygons and attributes
    """
    # Extract polygon shapes from mask
    shapes_gen = features.shapes(
        mask.astype(np.int16),
        mask=(mask > 0),
        transform=transform
    )

    polygons = []
    confidences = []

    for geom, value in shapes_gen:
        if value == 1:  # Parking lot pixels
            # Convert to shapely geometry
            poly = shape(geom)

            # Simplify geometry to reduce file size
            tolerance = config["vectorization"]["simplify_tolerance"] / 111000  # meters to degrees
            poly = poly.simplify(tolerance, preserve_topology=True)

            # Skip invalid or very small polygons
            if not poly.is_valid or poly.area < 1e-10:
                continue

            polygons.append(poly)

            # Calculate average confidence if prob_map provided
            if prob_map is not None:
                # Get pixel coordinates for this polygon
                # (This is approximate - for exact, would need to rasterize polygon)
                confidence = float(np.mean(prob_map[mask > 0]))
                confidences.append(confidence)
            else:
                confidences.append(0.8)  # Default confidence

    if not polygons:
        # Return empty GeoDataFrame
        return gpd.GeoDataFrame(columns=['geometry', 'area_m2', 'num_spots', 'confidence', 'size_category'])

    # Create GeoDataFrame
    gdf = gpd.GeoDataFrame({'geometry': polygons}, crs=crs)

    # Calculate area in square meters
    # Convert to Web Mercator (EPSG:3857) for area calculation
    gdf_projected = gdf.to_crs(epsg=3857)
    areas_m2 = gdf_projected.geometry.area

    # Add attributes
    gdf['area_m2'] = areas_m2
    gdf['num_spots'] = [
        estimate_parking_spots(area, config["vectorization"]["spot_area_m2"])
        for area in areas_m2
    ]
    gdf['confidence'] = confidences
    gdf['size_category'] = [
        categorize_lot_size(spots, config)
        for spots in gdf['num_spots']
    ]

    # Convert back to WGS84 (EPSG:4326) for GeoJSON
    gdf = gdf.to_crs(epsg=4326)

    # Add centroid coordinates
    gdf['center_lon'] = gdf.geometry.centroid.x
    gdf['center_lat'] = gdf.geometry.centroid.y

    return gdf


def merge_geojsons(gdf_list):
    """
    Merge multiple GeoDataFrames into one.

    Args:
        gdf_list: List of GeoDataFrames

    Returns:
        Merged GeoDataFrame
    """
    if not gdf_list:
        return gpd.GeoDataFrame(columns=['geometry', 'area_m2', 'num_spots', 'confidence', 'size_category'])

    # Filter out empty GeoDataFrames
    gdf_list = [gdf for gdf in gdf_list if not gdf.empty]

    if not gdf_list:
        return gpd.GeoDataFrame(columns=['geometry', 'area_m2', 'num_spots', 'confidence', 'size_category'])

    # Concatenate all GeoDataFrames
    merged = gpd.GeoDataFrame(pd.concat(gdf_list, ignore_index=True))

    # Remove duplicates based on geometry overlap
    # (This is a simple approach; for production, would use spatial joins)
    merged = merged.drop_duplicates(subset=['center_lon', 'center_lat'])

    # Reset index
    merged = merged.reset_index(drop=True)

    # Add unique IDs
    merged['lot_id'] = range(len(merged))

    return merged


def save_geojson(gdf, output_path):
    """
    Save GeoDataFrame to GeoJSON file.

    Args:
        gdf: GeoDataFrame
        output_path: Output file path
    """
    # Ensure numeric columns are properly typed
    gdf['area_m2'] = gdf['area_m2'].astype(float)
    gdf['num_spots'] = gdf['num_spots'].astype(int)
    gdf['confidence'] = gdf['confidence'].astype(float)

    # Save to GeoJSON
    gdf.to_file(output_path, driver='GeoJSON')
    print(f"Saved GeoJSON with {len(gdf)} parking lots to {output_path}")
