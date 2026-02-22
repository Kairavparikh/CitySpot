"""Inference predictor for parking lot detection."""

import torch
import numpy as np
from pathlib import Path
from tqdm import tqdm
import rasterio
from PIL import Image
import albumentations as A
from albumentations.pytorch import ToTensorV2

from ..model.segmentation import ParkingSegmentationModel


class ParkingPredictor:
    """Predictor for running inference on NAIP tiles."""

    def __init__(self, model_path, config, device=None):
        """
        Args:
            model_path: Path to trained model checkpoint
            config: Configuration dictionary
            device: torch.device (auto-detects if None)
        """
        self.config = config
        self.device = device or torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        # Load model
        print(f"Loading model from {model_path}...")
        checkpoint = torch.load(model_path, map_location=self.device)

        self.model = ParkingSegmentationModel(config)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval()

        print(f"Model loaded successfully on {self.device}")
        print(f"Model IoU: {checkpoint.get('iou', 'N/A')}")

        # Setup transform
        self.transform = A.Compose([
            A.Normalize(
                mean=[0.485, 0.456, 0.406, 0.5] if config["data"]["use_nir"] else [0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225, 0.25] if config["data"]["use_nir"] else [0.229, 0.224, 0.225]
            ),
            ToTensorV2()
        ])

        self.threshold = config["inference"]["threshold"]

    def load_tile(self, tile_path):
        """
        Load and preprocess a NAIP tile.

        Args:
            tile_path: Path to GeoTIFF file

        Returns:
            tensor: Preprocessed image tensor (1, C, H, W)
            transform: Rasterio transform for georeferencing
            crs: Coordinate reference system
        """
        # Read GeoTIFF
        with rasterio.open(tile_path) as src:
            # Read all bands (R, G, B, NIR)
            image = src.read()  # Shape: (C, H, W)
            transform = src.transform
            crs = src.crs

            # Transpose to (H, W, C)
            image = np.transpose(image, (1, 2, 0))

            # Normalize to [0, 255] if needed
            if image.max() > 255:
                image = (image / image.max() * 255).astype(np.uint8)

        # Resize if needed
        target_size = self.config["data"]["image_size"]
        if image.shape[:2] != (target_size, target_size):
            image = np.array(Image.fromarray(image).resize(
                (target_size, target_size),
                Image.BILINEAR
            ))

        # Apply transform
        transformed = self.transform(image=image)
        tensor = transformed["image"].unsqueeze(0)  # Add batch dimension

        return tensor, transform, crs

    def predict_tile(self, tile_path):
        """
        Predict parking lots for a single tile.

        Args:
            tile_path: Path to GeoTIFF file

        Returns:
            mask: Binary mask (H, W) as numpy array
            prob: Probability map (H, W) as numpy array
            transform: Rasterio transform
            crs: Coordinate reference system
        """
        with torch.no_grad():
            # Load tile
            tensor, transform, crs = self.load_tile(tile_path)
            tensor = tensor.to(self.device)

            # Predict
            output = self.model(tensor)  # Shape: (1, 1, H, W)

            # Convert to numpy
            prob = output.squeeze().cpu().numpy()  # Shape: (H, W)
            mask = (prob > self.threshold).astype(np.uint8)

        return mask, prob, transform, crs

    def predict_batch(self, tile_paths, output_dir):
        """
        Predict on a batch of tiles.

        Args:
            tile_paths: List of paths to GeoTIFF files
            output_dir: Directory to save prediction masks

        Returns:
            List of (tile_path, mask_path, transform, crs) tuples
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []

        for tile_path in tqdm(tile_paths, desc="Running inference"):
            try:
                # Predict
                mask, prob, transform, crs = self.predict_tile(tile_path)

                # Save mask
                tile_name = Path(tile_path).stem
                mask_path = output_dir / f"{tile_name}_mask.npy"
                np.save(mask_path, {
                    'mask': mask,
                    'prob': prob,
                    'transform': transform,
                    'crs': str(crs)
                }, allow_pickle=True)

                results.append({
                    'tile_path': str(tile_path),
                    'mask_path': str(mask_path),
                    'transform': transform,
                    'crs': crs
                })

            except Exception as e:
                print(f"Error processing {tile_path}: {e}")
                continue

        print(f"\nInference complete: {len(results)}/{len(tile_paths)} tiles processed")
        return results
