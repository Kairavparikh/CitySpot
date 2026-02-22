"""ParkSeg12k dataset loader from Hugging Face."""

import numpy as np
import torch
from torch.utils.data import Dataset
from datasets import load_dataset
from PIL import Image
import albumentations as A
from albumentations.pytorch import ToTensorV2


class ParkSeg12kDataset(Dataset):
    """
    PyTorch Dataset for ParkSeg12k from Hugging Face.

    Dataset: UTEL-UIUC/parkseg12k
    - 12,617 512×512 image-mask pairs
    - 4-channel images (RGB + NIR) or 3-channel (RGB only)
    - Binary segmentation masks
    """

    def __init__(
        self,
        split="train",
        use_nir=True,
        transform=None,
        image_size=512
    ):
        """
        Args:
            split: "train" or "test"
            use_nir: If True, use 4-channel (RGB+NIR), else 3-channel (RGB)
            transform: Albumentations transform pipeline
            image_size: Target image size (default 512)
        """
        self.split = split
        self.use_nir = use_nir
        self.image_size = image_size

        # Load dataset from Hugging Face
        print(f"Loading ParkSeg12k dataset ({split} split)...")
        self.dataset = load_dataset(
            "UTEL-UIUC/parkseg12k",
            split=split
        )
        print(f"Loaded {len(self.dataset)} samples")

        # Setup transforms
        if transform is None:
            self.transform = self._default_transform()
        else:
            self.transform = transform

    def _default_transform(self):
        """Default transform pipeline."""
        if self.split == "train":
            return A.Compose([
                A.HorizontalFlip(p=0.5),
                A.VerticalFlip(p=0.5),
                A.Rotate(limit=15, p=0.5),
                A.Normalize(
                    mean=[0.485, 0.456, 0.406, 0.5] if self.use_nir else [0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225, 0.25] if self.use_nir else [0.229, 0.224, 0.225]
                ),
                ToTensorV2()
            ])
        else:
            return A.Compose([
                A.Normalize(
                    mean=[0.485, 0.456, 0.406, 0.5] if self.use_nir else [0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225, 0.25] if self.use_nir else [0.229, 0.224, 0.225]
                ),
                ToTensorV2()
            ])

    def __len__(self):
        return len(self.dataset)

    def __getitem__(self, idx):
        """
        Returns:
            image: Tensor of shape (C, H, W) where C=4 (RGB+NIR) or 3 (RGB)
            mask: Tensor of shape (H, W) with binary values
        """
        sample = self.dataset[idx]

        # ParkSeg12k has keys: 'rgb', 'nir', 'mask'
        rgb = sample['rgb']
        nir = sample['nir']
        mask = sample['mask']

        # Convert PIL to numpy
        if isinstance(rgb, Image.Image):
            rgb = np.array(rgb)
        if isinstance(nir, Image.Image):
            nir = np.array(nir)
        if isinstance(mask, Image.Image):
            mask = np.array(mask)

        # Build 4-channel image (RGB + NIR)
        if self.use_nir:
            # NIR is grayscale, add channel dimension if needed
            if len(nir.shape) == 2:
                nir = nir[..., np.newaxis]
            # Concatenate RGB + NIR
            image = np.concatenate([rgb, nir], axis=-1)  # Shape: (H, W, 4)
        else:
            # Use only RGB
            image = rgb  # Shape: (H, W, 3)

        # Ensure mask is 2D binary
        if len(mask.shape) == 3:
            mask = mask[..., 0]  # Take first channel if multi-channel
        mask = (mask > 0).astype(np.float32)  # Binarize

        # Apply transformations
        transformed = self.transform(image=image, mask=mask)
        image = transformed["image"]
        mask = transformed["mask"]

        # Ensure mask is (H, W) not (1, H, W)
        if isinstance(mask, torch.Tensor) and mask.dim() == 3:
            mask = mask.squeeze(0)

        return image, mask


def get_dataloaders(config):
    """
    Create train and test dataloaders.

    Args:
        config: Config dict with training parameters

    Returns:
        train_loader, test_loader
    """
    train_dataset = ParkSeg12kDataset(
        split="train",
        use_nir=config["data"]["use_nir"],
        image_size=config["data"]["image_size"]
    )

    test_dataset = ParkSeg12kDataset(
        split="test",
        use_nir=config["data"]["use_nir"],
        image_size=config["data"]["image_size"]
    )

    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=config["training"]["batch_size"],
        shuffle=True,
        num_workers=config["training"]["num_workers"],
        pin_memory=True
    )

    test_loader = torch.utils.data.DataLoader(
        test_dataset,
        batch_size=config["training"]["batch_size"],
        shuffle=False,
        num_workers=config["training"]["num_workers"],
        pin_memory=True
    )

    return train_loader, test_loader
