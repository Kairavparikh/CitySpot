#!/bin/bash

# ParkSight - Automated Pipeline Runner
# Runs all steps from training through final visualization

set -e  # Exit on error

echo "============================================================"
echo "ParkSight - Automated Pipeline"
echo "============================================================"

# Activate virtual environment
source venv/bin/activate

# Step 1: Train Model
echo ""
echo "Step 1/4: Training Model (3 epochs)..."
echo "------------------------------------------------------------"
python3 scripts/01_train_model.py
echo "✓ Training complete!"

# Step 2: Download NAIP Tiles
echo ""
echo "Step 2/4: Downloading NAIP Tiles (10 tiles for testing)..."
echo "------------------------------------------------------------"
python3 scripts/02_download_naip.py --max-tiles 10
echo "✓ Download complete!"

# Step 3: Run Inference
echo ""
echo "Step 3/4: Running Inference..."
echo "------------------------------------------------------------"
python3 scripts/03_run_inference.py
echo "✓ Inference complete!"

# Step 4: Generate GeoJSON
echo ""
echo "Step 4/4: Generating GeoJSON..."
echo "------------------------------------------------------------"
python3 scripts/04_generate_geojson.py
echo "✓ GeoJSON generated!"

# Summary
echo ""
echo "============================================================"
echo "Pipeline Complete!"
echo "============================================================"
echo ""
echo "Results:"
echo "  - Model: models/final_model.pth"
echo "  - GeoJSON: outputs/parking_lots.geojson"
echo ""
echo "To view results:"
echo "  cd frontend"
echo "  python3 -m http.server 8000"
echo "  Open: http://localhost:8000"
echo ""
echo "============================================================"
