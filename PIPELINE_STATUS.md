# ParkSight Pipeline Status

## Current Status

### ✅ Step 1: Model Training (IN PROGRESS)
**Status:** Running in background
**Progress:** Epoch 1/3, processing batches
**Metrics:**
- Loss: Decreasing (0.6653 → 0.5089)
- IoU: Increasing (0.0813 → 0.4058)

**Estimated completion:** ~5 hours from start

**Location:** Training output being saved to `models/checkpoints/`

---

## Next Steps (Run After Training Completes)

### Step 2: Download NAIP Tiles

```bash
cd /Users/kairavparikh/Hackalytics
source venv/bin/activate
python3 scripts/02_download_naip.py --max-tiles 10
```

**Time:** ~20-30 minutes (for 10 tiles)
**Output:** `data/naip_tiles/` and `data/metadata.csv`

**Note:** This requires Google Earth Engine authentication:
```bash
earthengine authenticate
```

---

### Step 3: Run Inference

```bash
python3 scripts/03_run_inference.py
```

**Time:** ~5-10 minutes
**Output:** `outputs/predictions/` (prediction masks)

---

### Step 4: Generate GeoJSON

```bash
python3 scripts/04_generate_geojson.py
```

**Time:** ~2-5 minutes
**Output:** `outputs/parking_lots.geojson`

---

### Step 5: View Results

```bash
cd frontend
python3 -m http.server 8000
```

Then open: http://localhost:8000

---

## Checking Training Progress

To monitor training progress:

```bash
# View recent output
tail -50 /tmp/training_output.log  # If you redirected output

# Or check for saved checkpoints
ls -lh models/checkpoints/

# Final model will be at:
ls -lh models/final_model.pth
```

---

## If Training Fails

If training crashes or you stop it early:

1. **Use the demo data** - already working:
   ```bash
   cd frontend
   python3 -m http.server 8000
   ```

2. **Or restart training** with full 30 epochs:
   - Edit `config/config.yaml`: set `epochs: 30`
   - Run: `python3 scripts/01_train_model.py`

---

## Current Configuration

- **Epochs:** 3 (quick test)
- **Batch size:** 8
- **Device:** CPU (Mac)
- **Dataset:** 11,355 training samples, 1,262 test samples

---

## Errors Fixed

1. ✅ Removed `verbose=True` from scheduler (not supported in PyTorch 2.10)
2. ✅ Removed `trust_remote_code=True` from dataset loader (deprecated)
3. ✅ Fixed dataset loading - ParkSeg12k has keys: `rgb`, `nir`, `mask`

---

## What's Happening Now

The model is learning to segment parking lots from satellite imagery:
- Input: 512×512 images with RGB + NIR channels
- Output: Binary mask (parking = white, background = black)
- Learning rate: 0.0003
- Optimization: AdamW
- Loss: Dice Loss + Binary Cross-Entropy

The IoU (Intersection over Union) metric shows how well predictions match ground truth:
- 0.0 = No overlap (terrible)
- 0.5 = Decent
- 0.7+ = Good
- 0.9+ = Excellent

Current IoU of ~0.40 is reasonable for early training!

---

## Next Update

Training will complete in ~5 hours. When done:
1. Check for `models/final_model.pth`
2. Run steps 2-5 above
3. View results in the frontend!
