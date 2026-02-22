"""Parking lot segmentation model using DeepLabV3+ with ResNet34."""

import torch
import torch.nn as nn
import torch.nn.functional as F
import segmentation_models_pytorch as smp


class ParkingSegmentationModel(nn.Module):
    """
    DeepLabV3+ with ResNet34 backbone for parking lot segmentation.

    Uses ImageNet-pretrained encoder and trains on ParkSeg12k dataset.
    """

    def __init__(self, config):
        """
        Args:
            config: Config dict with model parameters
        """
        super().__init__()

        self.config = config
        model_cfg = config["model"]

        # Create DeepLabV3+ model
        self.model = smp.DeepLabV3Plus(
            encoder_name=model_cfg["encoder"],
            encoder_weights=model_cfg["encoder_weights"],
            in_channels=model_cfg["in_channels"],
            classes=model_cfg["classes"],
            activation=model_cfg["activation"]
        )

    def forward(self, x):
        """
        Forward pass.

        Args:
            x: Input tensor of shape (B, C, H, W)

        Returns:
            Predictions of shape (B, 1, H, W) with sigmoid activation
        """
        return self.model(x)

    def predict(self, x, threshold=0.5):
        """
        Make binary predictions.

        Args:
            x: Input tensor
            threshold: Probability threshold for binary classification

        Returns:
            Binary mask (B, 1, H, W)
        """
        with torch.no_grad():
            probs = self.forward(x)
            return (probs > threshold).float()


class DiceBCELoss(nn.Module):
    """
    Combined Dice Loss and Binary Cross-Entropy Loss.

    This is a common loss for segmentation tasks that balances:
    - Dice: Handles class imbalance well
    - BCE: Provides per-pixel supervision
    """

    def __init__(self, dice_weight=0.5, bce_weight=0.5, smooth=1e-6):
        """
        Args:
            dice_weight: Weight for Dice loss component
            bce_weight: Weight for BCE loss component
            smooth: Smoothing factor to avoid division by zero
        """
        super().__init__()
        self.dice_weight = dice_weight
        self.bce_weight = bce_weight
        self.smooth = smooth
        self.bce = nn.BCELoss()

    def dice_loss(self, pred, target):
        """
        Calculate Dice loss.

        Args:
            pred: Predictions (B, 1, H, W)
            target: Ground truth (B, 1, H, W)

        Returns:
            Dice loss value
        """
        pred = pred.contiguous().view(-1)
        target = target.contiguous().view(-1)

        intersection = (pred * target).sum()
        dice_score = (2. * intersection + self.smooth) / (
            pred.sum() + target.sum() + self.smooth
        )

        return 1 - dice_score

    def forward(self, pred, target):
        """
        Calculate combined loss.

        Args:
            pred: Predictions (B, 1, H, W)
            target: Ground truth (B, H, W) or (B, 1, H, W)

        Returns:
            Combined loss value
        """
        # Ensure target has same shape as pred
        if target.dim() == 3:
            target = target.unsqueeze(1)

        # Calculate both losses
        dice = self.dice_loss(pred, target)
        bce = self.bce(pred, target)

        # Weighted combination
        return self.dice_weight * dice + self.bce_weight * bce


def calculate_iou(pred, target, threshold=0.5):
    """
    Calculate Intersection over Union (IoU) metric.

    Args:
        pred: Predictions (B, 1, H, W)
        target: Ground truth (B, H, W) or (B, 1, H, W)
        threshold: Threshold for binarizing predictions

    Returns:
        Mean IoU across batch
    """
    with torch.no_grad():
        # Binarize predictions
        pred_binary = (pred > threshold).float()

        # Ensure target has same shape
        if target.dim() == 3:
            target = target.unsqueeze(1)

        # Flatten
        pred_binary = pred_binary.contiguous().view(-1)
        target = target.contiguous().view(-1)

        # Calculate IoU
        intersection = (pred_binary * target).sum()
        union = pred_binary.sum() + target.sum() - intersection

        iou = (intersection + 1e-6) / (union + 1e-6)

        return iou.item()
