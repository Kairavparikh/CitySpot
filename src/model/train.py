"""Training loop for parking segmentation model."""

import torch
import torch.optim as optim
from pathlib import Path
from tqdm import tqdm
import yaml

from .segmentation import ParkingSegmentationModel, DiceBCELoss, calculate_iou


class Trainer:
    """Trainer class for parking segmentation model."""

    def __init__(self, config, model, train_loader, test_loader):
        """
        Args:
            config: Configuration dictionary
            model: ParkingSegmentationModel instance
            train_loader: Training data loader
            test_loader: Test/validation data loader
        """
        self.config = config
        self.model = model
        self.train_loader = train_loader
        self.test_loader = test_loader

        # Setup device
        self.device = torch.device(config["training"]["device"]
                                   if torch.cuda.is_available()
                                   else "cpu")
        self.model.to(self.device)
        print(f"Using device: {self.device}")

        # Loss and optimizer
        self.criterion = DiceBCELoss()
        self.optimizer = optim.AdamW(
            self.model.parameters(),
            lr=config["training"]["learning_rate"]
        )

        # Learning rate scheduler
        self.scheduler = optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer,
            mode='max',
            factor=0.5,
            patience=3
        )

        # Tracking
        self.best_iou = 0.0
        self.epochs_without_improvement = 0
        self.train_losses = []
        self.val_ious = []

    def train_epoch(self, epoch):
        """Train for one epoch."""
        self.model.train()
        total_loss = 0.0
        total_iou = 0.0

        pbar = tqdm(self.train_loader, desc=f"Epoch {epoch+1} [Train]")
        for batch_idx, (images, masks) in enumerate(pbar):
            # Move to device
            images = images.to(self.device)
            masks = masks.to(self.device)

            # Forward pass
            self.optimizer.zero_grad()
            outputs = self.model(images)

            # Calculate loss
            loss = self.criterion(outputs, masks)

            # Backward pass
            loss.backward()
            self.optimizer.step()

            # Metrics
            iou = calculate_iou(outputs, masks)
            total_loss += loss.item()
            total_iou += iou

            # Update progress bar
            pbar.set_postfix({
                'loss': f"{loss.item():.4f}",
                'iou': f"{iou:.4f}"
            })

        avg_loss = total_loss / len(self.train_loader)
        avg_iou = total_iou / len(self.train_loader)

        return avg_loss, avg_iou

    def validate(self):
        """Validate on test set."""
        self.model.eval()
        total_loss = 0.0
        total_iou = 0.0

        with torch.no_grad():
            pbar = tqdm(self.test_loader, desc="Validation")
            for images, masks in pbar:
                # Move to device
                images = images.to(self.device)
                masks = masks.to(self.device)

                # Forward pass
                outputs = self.model(images)

                # Calculate metrics
                loss = self.criterion(outputs, masks)
                iou = calculate_iou(outputs, masks)

                total_loss += loss.item()
                total_iou += iou

                pbar.set_postfix({
                    'val_loss': f"{loss.item():.4f}",
                    'val_iou': f"{iou:.4f}"
                })

        avg_loss = total_loss / len(self.test_loader)
        avg_iou = total_iou / len(self.test_loader)

        return avg_loss, avg_iou

    def save_checkpoint(self, epoch, iou, is_best=False):
        """Save model checkpoint."""
        checkpoint_dir = Path(self.config["paths"]["checkpoints"])
        checkpoint_dir.mkdir(parents=True, exist_ok=True)

        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'iou': iou,
            'config': self.config
        }

        # Save regular checkpoint
        checkpoint_path = checkpoint_dir / f"checkpoint_epoch_{epoch+1}.pth"
        torch.save(checkpoint, checkpoint_path)

        # Save best model
        if is_best:
            best_path = Path(self.config["paths"]["final_model"])
            best_path.parent.mkdir(parents=True, exist_ok=True)
            torch.save(checkpoint, best_path)
            print(f"✓ Saved best model (IoU: {iou:.4f}) to {best_path}")

    def train(self):
        """Full training loop."""
        print("\n" + "="*60)
        print("Starting Training")
        print("="*60)

        num_epochs = self.config["training"]["epochs"]
        patience = self.config["training"]["early_stopping_patience"]

        for epoch in range(num_epochs):
            print(f"\nEpoch {epoch+1}/{num_epochs}")
            print("-" * 60)

            # Train
            train_loss, train_iou = self.train_epoch(epoch)
            self.train_losses.append(train_loss)

            # Validate
            val_loss, val_iou = self.validate()
            self.val_ious.append(val_iou)

            print(f"\nEpoch {epoch+1} Summary:")
            print(f"  Train Loss: {train_loss:.4f} | Train IoU: {train_iou:.4f}")
            print(f"  Val Loss:   {val_loss:.4f} | Val IoU:   {val_iou:.4f}")

            # Learning rate scheduler step
            self.scheduler.step(val_iou)

            # Check for improvement
            is_best = val_iou > self.best_iou
            if is_best:
                self.best_iou = val_iou
                self.epochs_without_improvement = 0
            else:
                self.epochs_without_improvement += 1

            # Save checkpoint
            self.save_checkpoint(epoch, val_iou, is_best)

            # Early stopping
            if self.epochs_without_improvement >= patience:
                print(f"\n⚠ Early stopping triggered after {epoch+1} epochs")
                print(f"  No improvement for {patience} epochs")
                break

        print("\n" + "="*60)
        print("Training Complete!")
        print(f"Best Validation IoU: {self.best_iou:.4f}")
        print("="*60 + "\n")

        return self.best_iou


def load_config(config_path="config/config.yaml"):
    """Load configuration from YAML file."""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config
