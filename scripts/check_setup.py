#!/usr/bin/env python3
"""
Verify ParkSight installation and setup.

Usage:
    python scripts/check_setup.py
"""

import sys
from pathlib import Path

def check_python_version():
    """Check Python version."""
    print("Checking Python version...")
    if sys.version_info < (3, 10):
        print("  ❌ Python 3.10+ required")
        return False
    print(f"  ✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    return True

def check_dependencies():
    """Check required packages."""
    print("\nChecking dependencies...")
    required = [
        'torch',
        'torchvision',
        'segmentation_models_pytorch',
        'datasets',
        'ee',
        'geopandas',
        'rasterio',
        'yaml'
    ]

    missing = []
    for pkg in required:
        try:
            if pkg == 'ee':
                import ee
            elif pkg == 'yaml':
                import yaml
            else:
                __import__(pkg)
            print(f"  ✓ {pkg}")
        except ImportError:
            print(f"  ❌ {pkg} not found")
            missing.append(pkg)

    if missing:
        print(f"\nInstall missing packages:")
        print(f"  pip install -r requirements.txt")
        return False
    return True

def check_cuda():
    """Check CUDA availability."""
    print("\nChecking CUDA...")
    try:
        import torch
        if torch.cuda.is_available():
            print(f"  ✓ CUDA available: {torch.cuda.get_device_name(0)}")
            return True
        else:
            print("  ⚠ CUDA not available (CPU training will be slow)")
            return True
    except Exception as e:
        print(f"  ❌ Error checking CUDA: {e}")
        return False

def check_directories():
    """Check directory structure."""
    print("\nChecking directories...")
    required_dirs = [
        'data',
        'models',
        'outputs',
        'src',
        'scripts',
        'config',
        'frontend'
    ]

    for dir_name in required_dirs:
        dir_path = Path(dir_name)
        if dir_path.exists():
            print(f"  ✓ {dir_name}/")
        else:
            print(f"  ❌ {dir_name}/ missing")
            return False
    return True

def check_config():
    """Check configuration file."""
    print("\nChecking configuration...")
    config_path = Path('config/config.yaml')

    if not config_path.exists():
        print(f"  ❌ config.yaml not found")
        return False

    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print(f"  ✓ config.yaml loaded")

        # Check key sections
        sections = ['paths', 'training', 'model', 'data']
        for section in sections:
            if section in config:
                print(f"  ✓ {section} section found")
            else:
                print(f"  ❌ {section} section missing")
                return False

        return True
    except Exception as e:
        print(f"  ❌ Error loading config: {e}")
        return False

def check_gee():
    """Check Google Earth Engine authentication."""
    print("\nChecking Google Earth Engine...")
    try:
        import ee
        ee.Initialize()
        print("  ✓ GEE authenticated and initialized")
        return True
    except Exception as e:
        print("  ⚠ GEE not authenticated")
        print("  Run: earthengine authenticate")
        return False

def main():
    print("="*60)
    print("ParkSight Setup Verification")
    print("="*60)

    checks = [
        check_python_version(),
        check_dependencies(),
        check_cuda(),
        check_directories(),
        check_config(),
        check_gee()
    ]

    print("\n" + "="*60)
    if all(checks[:5]):  # GEE is optional for some steps
        print("✓ Setup complete! Ready to run pipeline.")
    else:
        print("❌ Setup incomplete. Please fix errors above.")
    print("="*60)

if __name__ == "__main__":
    main()
