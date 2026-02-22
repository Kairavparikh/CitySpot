#!/usr/bin/env python3
"""
Train parking segmentation model on ParkSeg12k dataset.

Usage:
    python scripts/01_train_model.py
"""

import sys
from pathlib import Path
import yaml

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.data.parkseg_dataset import get_dataloaders
from src.model.segmentation import ParkingSegmentationModel
from src.model.train import Trainer


def main():
    print("="*70)
    print("ParkSight - Model Training")
    print("="*70)

    # Load config
    config_path = Path("config/config.yaml")
    print(f"\nLoading configuration from {config_path}...")

    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)

    # Create dataloaders
    print("\nLoading ParkSeg12k dataset...")
    train_loader, test_loader = get_dataloaders(config)
    print(f"Train samples: {len(train_loader.dataset)}")
    print(f"Test samples: {len(test_loader.dataset)}")

    # Create model
    print("\nInitializing model...")
    model = ParkingSegmentationModel(config)

    # Count parameters
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Total parameters: {total_params:,}")
    print(f"Trainable parameters: {trainable_params:,}")

    # Create trainer
    trainer = Trainer(config, model, train_loader, test_loader)

    # Train
    best_iou = trainer.train()

    print("\n" + "="*70)
    print(f"Training complete!")
    print(f"Best model saved to: {config['paths']['final_model']}")
    print(f"Best validation IoU: {best_iou:.4f}")
    print("="*70)


if __name__ == "__main__":
    main()
