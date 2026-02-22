# ParkSight - Quick Start Guide

## Immediate Testing (No Pipeline Required)

We've generated demo data so you can test the frontend immediately!

```bash
cd frontend
python3 -m http.server 8000
```

Then open http://localhost:8000 in your browser.

You should see:
- Interactive map with 10 demo parking lots
- Stats showing total lots, estimated spots, coverage area
- Working filters (size, confidence, search)
- Clickable parking lot polygons with details

## Next Steps for Hackathon

### Option 1: Quick Demo (5 minutes)
Already done! The demo data is loaded. Use this to:
- Test the UI
- Understand the data structure
- Present the concept

### Option 2: Small-Scale Test (2-3 hours)
Train on a subset and test on a small area:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Train model (limited epochs for testing)
# Edit config/config.yaml and set epochs: 5
python3 scripts/01_train_model.py

# 3. Download ~10 NAIP tiles
python3 scripts/02_download_naip.py --max-tiles 10

# 4. Run inference
python3 scripts/03_run_inference.py

# 5. Generate GeoJSON
python3 scripts/04_generate_geojson.py

# 6. View results
cd frontend && python3 -m http.server 8000
```

### Option 3: Full Pipeline (24+ hours)
For production-quality results:

```bash
# 1. Install and authenticate
pip install -r requirements.txt
earthengine authenticate

# 2. Train model (8-12 hours on GPU)
python3 scripts/01_train_model.py

# 3. Download all Atlanta tiles (1-2 hours)
python3 scripts/02_download_naip.py

# 4. Run inference (15-30 minutes)
python3 scripts/03_run_inference.py

# 5. Generate GeoJSON (5 minutes)
python3 scripts/04_generate_geojson.py

# 6. Launch frontend
cd frontend && python3 -m http.server 8000
```

## Verifying Setup

```bash
python3 scripts/check_setup.py
```

This checks:
- Python version (3.10+)
- Required packages
- CUDA availability
- Directory structure
- Configuration files
- GEE authentication

## Troubleshooting

### Dependencies Not Installing
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

### CUDA Not Available
Edit `config/config.yaml`:
```yaml
training:
  device: "cpu"  # Change from "cuda" to "cpu"
```

Note: CPU training will be ~10x slower.

### GEE Authentication Failed
```bash
earthengine authenticate
```
Follow the browser prompts and copy the authorization code.

### Frontend Not Loading Data
Check that GeoJSON exists:
```bash
ls -lh outputs/parking_lots.geojson
```

If missing, run:
```bash
python3 scripts/generate_demo_data.py  # For demo data
# OR
python3 scripts/04_generate_geojson.py  # For real data
```

## Customization

### Change Atlanta Coverage Area
Edit `config/atlanta_roi.geojson` to define your region of interest.

### Adjust Model Confidence Threshold
Edit `config/config.yaml`:
```yaml
inference:
  threshold: 0.5  # Lower = more detections, higher = fewer false positives
```

### Change Lot Size Categories
Edit `config/config.yaml`:
```yaml
vectorization:
  size_categories:
    small: 50   # < 50 spots
    medium: 200 # 50-200 spots
    # large: > 200 spots
```

## Presentation Tips

1. **Start with the demo**: Show the working UI with demo data
2. **Explain the pipeline**: Walk through the 4-step process
3. **Show the model**: Explain DeepLabV3+ and ParkSeg12k dataset
4. **Highlight features**: Filters, stats, interactive map
5. **Discuss applications**: Urban planning, parking optimization, EV charging placement

## Key Metrics to Present

- **Dataset**: 12,617 training samples from ParkSeg12k
- **Model**: DeepLabV3+ with ResNet34 (ImageNet pretrained)
- **Target Accuracy**: mIoU > 0.75
- **Coverage**: Scoped to ~50 km² (Midtown/Buckhead/Airport)
- **Resolution**: 1 meter/pixel NAIP imagery
- **Channels**: 4-channel (RGB + NIR) for better vegetation/parking separation

## What's Working Right Now

✅ Complete project structure
✅ Model architecture implemented
✅ Training pipeline ready
✅ NAIP downloader configured
✅ Inference and postprocessing
✅ GeoJSON vectorization
✅ Interactive web interface
✅ Demo data for testing

## What Needs Running

⏳ Model training (8-12 hours on GPU)
⏳ NAIP tile download (1-2 hours)
⏳ Inference on real tiles (15-30 minutes)

For the hackathon: Use the demo data to present the concept, then run the pipeline in parallel to show real results later!

---

Good luck! 🚀
