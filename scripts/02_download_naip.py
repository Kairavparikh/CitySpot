#!/usr/bin/env python3
"""
Download NAIP tiles for Atlanta region.

Usage:
    python scripts/02_download_naip.py [--max-tiles N]
"""

import sys
from pathlib import Path
import yaml
import argparse

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.naip_downloader import download_all_tiles


def main():
    parser = argparse.ArgumentParser(description="Download NAIP tiles for Atlanta")
    parser.add_argument(
        '--max-tiles',
        type=int,
        default=None,
        help='Maximum number of tiles to download (for testing)'
    )
    args = parser.parse_args()

    print("="*70)
    print("ParkSight - NAIP Data Download")
    print("="*70)

    # Load config
    config_path = Path("config/config.yaml")
    print(f"\nLoading configuration from {config_path}...")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Setup paths
    roi_path = Path(config['paths']['roi'])
    output_dir = Path(config['paths']['naip_tiles'])

    print(f"\nROI: {roi_path}")
    print(f"Output directory: {output_dir}")

    if args.max_tiles:
        print(f"Max tiles: {args.max_tiles} (testing mode)")

    # Download tiles
    print("\nStarting download...")
    metadata = download_all_tiles(
        roi_path,
        output_dir,
        config,
        max_tiles=args.max_tiles
    )

    print("\n" + "="*70)
    print(f"Download complete!")
    print(f"Tiles downloaded: {metadata['success'].sum()}")
    print(f"Metadata saved to: {config['paths']['metadata']}")
    print("="*70)


if __name__ == "__main__":
    main()
