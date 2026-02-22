"""Postprocessing for prediction masks."""

import numpy as np
from scipy import ndimage
from skimage.morphology import remove_small_objects, remove_small_holes, binary_closing


def postprocess_mask(mask, config):
    """
    Clean up prediction mask by removing noise and filling holes.

    Args:
        mask: Binary mask (H, W) as numpy array
        config: Configuration dictionary

    Returns:
        Cleaned binary mask (H, W)
    """
    pp_config = config["postprocessing"]

    # Convert to boolean
    mask_bool = mask.astype(bool)

    # Remove small objects (noise)
    min_size = pp_config["min_area_pixels"]
    if min_size > 0:
        mask_bool = remove_small_objects(mask_bool, min_size=min_size)

    # Fill small holes
    hole_size = pp_config["fill_holes_pixels"]
    if hole_size > 0:
        mask_bool = remove_small_holes(mask_bool, area_threshold=hole_size)

    # Morphological closing (smooth edges, connect nearby components)
    kernel_size = pp_config["morphology_kernel_size"]
    if kernel_size > 0:
        mask_bool = binary_closing(
            mask_bool,
            footprint=np.ones((kernel_size, kernel_size))
        )

    return mask_bool.astype(np.uint8)


def estimate_parking_spots(area_m2, spot_area_m2=12.5):
    """
    Estimate number of parking spots from parking lot area.

    Args:
        area_m2: Parking lot area in square meters
        spot_area_m2: Average area per parking spot (default: 12.5 m² = 2.5m × 5m)

    Returns:
        Estimated number of spots
    """
    return int(area_m2 / spot_area_m2)


def categorize_lot_size(num_spots, config):
    """
    Categorize parking lot by size.

    Args:
        num_spots: Number of parking spots
        config: Configuration dictionary

    Returns:
        "small", "medium", or "large"
    """
    categories = config["vectorization"]["size_categories"]

    if num_spots < categories["small"]:
        return "small"
    elif num_spots < categories["medium"]:
        return "medium"
    else:
        return "large"
