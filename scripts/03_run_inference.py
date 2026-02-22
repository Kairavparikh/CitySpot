#!/usr/bin/env python3
"""
Run inference on Atlanta NAIP tiles.

Usage:
    python scripts/03_run_inference.py
"""

import sys
from pathlib import Path
import yaml
import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.inference.predictor import ParkingPredictor
from src.inference.postprocess import postprocess_mask
import numpy as np


def main():
    print("="*70)
    print("ParkSight - Inference")
    print("="*70)

    # Load config
    config_path = Path("config/config.yaml")
    print(f"\nLoading configuration from {config_path}...")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Load metadata
    metadata_path = Path(config['paths']['metadata'])
    print(f"Loading metadata from {metadata_path}...")
    metadata = pd.read_csv(metadata_path)

    # Filter successful downloads
    successful_tiles = metadata[metadata['success'] == True]
    tile_paths = successful_tiles['filepath'].tolist()

    print(f"\nFound {len(tile_paths)} tiles to process")

    # Load model
    model_path = Path(config['paths']['final_model'])
    print(f"Loading model from {model_path}...")

    predictor = ParkingPredictor(model_path, config)

    # Run inference
    print("\nRunning inference...")
    results = predictor.predict_batch(tile_paths, config['paths']['predictions'])

    # Postprocess masks
    print("\nPostprocessing masks...")
    for result in results:
        # Load mask
        mask_data = np.load(result['mask_path'], allow_pickle=True).item()
        mask = mask_data['mask']

        # Postprocess
        cleaned_mask = postprocess_mask(mask, config)

        # Update saved mask
        mask_data['mask'] = cleaned_mask
        np.save(result['mask_path'], mask_data, allow_pickle=True)

    print("\n" + "="*70)
    print(f"Inference complete!")
    print(f"Processed {len(results)} tiles")
    print(f"Predictions saved to: {config['paths']['predictions']}")
    print("="*70)


if __name__ == "__main__":
    main()
