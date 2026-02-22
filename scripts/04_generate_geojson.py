#!/usr/bin/env python3
"""
Generate GeoJSON from prediction masks.

Usage:
    python scripts/04_generate_geojson.py
"""

import sys
from pathlib import Path
import yaml
import numpy as np
from tqdm import tqdm

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.spatial.vectorize import mask_to_geojson, merge_geojsons, save_geojson
from rasterio.crs import CRS
from rasterio.transform import Affine


def main():
    print("="*70)
    print("ParkSight - GeoJSON Generation")
    print("="*70)

    # Load config
    config_path = Path("config/config.yaml")
    print(f"\nLoading configuration from {config_path}...")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Get all prediction masks
    predictions_dir = Path(config['paths']['predictions'])
    mask_files = list(predictions_dir.glob("*_mask.npy"))

    print(f"\nFound {len(mask_files)} prediction masks")

    # Convert each mask to GeoJSON
    gdfs = []

    for mask_file in tqdm(mask_files, desc="Vectorizing masks"):
        try:
            # Load mask data
            mask_data = np.load(mask_file, allow_pickle=True).item()
            mask = mask_data['mask']
            prob = mask_data['prob']
            transform = mask_data['transform']
            crs = CRS.from_string(mask_data['crs'])

            # Convert to GeoJSON
            gdf = mask_to_geojson(mask, transform, crs, config, prob_map=prob)

            if not gdf.empty:
                gdfs.append(gdf)

        except Exception as e:
            print(f"\nError processing {mask_file}: {e}")
            continue

    # Merge all GeoDataFrames
    print("\nMerging GeoDataFrames...")
    merged_gdf = merge_geojsons(gdfs)

    print(f"Total parking lots detected: {len(merged_gdf)}")
    print(f"Total estimated spots: {merged_gdf['num_spots'].sum()}")

    # Calculate coverage statistics
    total_area_m2 = merged_gdf['area_m2'].sum()
    total_area_mi2 = total_area_m2 / 2.59e6  # m² to mi²

    print(f"Total coverage area: {total_area_m2:.2f} m² ({total_area_mi2:.4f} mi²)")
    print(f"Average lot size: {merged_gdf['area_m2'].mean():.2f} m²")

    # Size distribution
    print("\nSize distribution:")
    print(merged_gdf['size_category'].value_counts())

    # Save to GeoJSON
    output_path = Path(config['paths']['geojson'])
    print(f"\nSaving to {output_path}...")
    save_geojson(merged_gdf, output_path)

    print("\n" + "="*70)
    print(f"GeoJSON generation complete!")
    print(f"Output: {output_path}")
    print("="*70)


if __name__ == "__main__":
    main()
