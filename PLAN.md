# ParkSight: Satellite-Based Parking Detection System
## 36-Hour Hackathon Plan

**CRITICAL FACTS:**
- ParkSeg12k is a DATASET (12,617 image-mask pairs), NOT a pretrained model
- We must TRAIN DeepLabV3+ with ResNet34 ImageNet backbone on ParkSeg12k
- Dataset available on Hugging Face: `UTEL-UIUC/parkseg12k`
- Images are already 512×512 with NIR channel available (matches NAIP)
- Timeline: 36 hours (not 4 weeks)
- Scope: Midtown/Buckhead/Airport corridor only (not all Atlanta)

---

## 1. Hackathon-Scoped Project Structure

```
ParkSight/
│
├── data/
│   ├── naip_tiles/                   # Raw NAIP imagery from GEE (scoped area)
│   ├── processed/                    # Preprocessed Atlanta tiles for inference
│   └── metadata.csv                  # Tile coordinates, timestamps
│
├── models/
│   ├── checkpoints/                  # Training checkpoints (best model)
│   └── final_model.pth               # Trained model for deployment
│
├── outputs/
│   ├── predictions/                  # Prediction masks (NumPy arrays)
│   └── parking_lots.geojson          # Final vectorized parking polygons
│
├── src/
│   ├── data/
│   │   ├── __init__.py
│   │   ├── parkseg_dataset.py        # Load ParkSeg12k from Hugging Face
│   │   └── naip_downloader.py        # Fetch NAIP tiles via GEE for Atlanta
│   │
│   ├── model/
│   │   ├── __init__.py
│   │   ├── segmentation.py           # DeepLabV3+ with ResNet34 backbone
│   │   └── train.py                  # Training loop on ParkSeg12k
│   │
│   ├── inference/
│   │   ├── __init__.py
│   │   ├── predictor.py              # Run inference on Atlanta tiles
│   │   └── postprocess.py            # Clean masks, remove noise
│   │
│   └── spatial/
│       ├── __init__.py
│       └── vectorize.py              # Convert masks → GeoJSON polygons
│
├── frontend/
│   ├── index.html                    # Main UI (dark theme map interface)
│   ├── app.js                        # Map logic, filters, stats
│   ├── styles.css                    # Dark theme styling
│   └── api.js                        # Load GeoJSON, compute stats
│
├── scripts/
│   ├── 01_train_model.py             # Train on ParkSeg12k dataset
│   ├── 02_download_naip.py           # Fetch Atlanta NAIP tiles
│   ├── 03_run_inference.py           # Predict on all tiles
│   └── 04_generate_geojson.py        # Vectorize and export
│
├── config/
│   ├── config.yaml                   # Hyperparameters, paths
│   └── atlanta_roi.geojson           # Scoped region of interest
│
├── requirements.txt                  # Python dependencies
├── README.md                         # Setup & reproduction
└── PLAN.md                           # This file
```

**REMOVED (not needed for hackathon):**
- tests/ — no time for testing
- notebooks/ — documentation only
- Streamlit dashboard — building custom web UI instead
- aggregator.py — stats computed client-side from GeoJSON

---

## 2. 36-Hour Critical Path

### Timeline & Phases

```
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: MODEL TRAINING (Hours 0-12) — PARALLEL TRACK A             │
└─────────────────────────────────────────────────────────────────────┘
  1. Load ParkSeg12k dataset from Hugging Face (UTEL-UIUC/parkseg12k)
  2. Initialize DeepLabV3+ with ResNet34 ImageNet backbone
  3. Train on 12,617 image-mask pairs (90/10 split)
     - Input: 512×512×4 (RGB + NIR) NAIP-like imagery
     - Output: 512×512 binary masks (parking lot segmentation)
     - Loss: Dice Loss + Binary Cross-Entropy
     - Optimizer: AdamW, LR: 3e-4, batch size: 16
     - Epochs: 20-30 (early stopping on validation mIoU)
  4. Save best checkpoint → models/final_model.pth
  5. Target: mIoU > 0.75 on ParkSeg12k test set

┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 2: ATLANTA DATA ACQUISITION (Hours 0-8) — PARALLEL TRACK B    │
└─────────────────────────────────────────────────────────────────────┘
  6. Define scoped ROI: Midtown + Buckhead + Airport corridor
     - ~50 km² instead of full 350 km² Atlanta metro
     - Bounding box: config/atlanta_roi.geojson
  7. Query Google Earth Engine for NAIP imagery
     - Collection: "USDA/NAIP/DOQQ"
     - Bands: R, G, B, N (4-channel to match ParkSeg12k)
     - Resolution: 1m/pixel
     - Years: 2019-2021 (most recent complete coverage)
  8. Split ROI into 512×512m tiles (~200 tiles for scoped area)
  9. Export tiles as GeoTIFF → data/naip_tiles/
  10. Log tile coordinates → data/metadata.csv

┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 3: INFERENCE (Hours 12-20)                                    │
└─────────────────────────────────────────────────────────────────────┘
  11. Load trained model from models/final_model.pth
  12. Preprocess Atlanta tiles:
      - Resize to 512×512 pixels
      - Normalize (ImageNet stats)
      - Convert to PyTorch tensors
  13. Batch predict on all ~200 tiles (GPU: ~5min total)
  14. Apply postprocessing to masks:
      - Remove blobs < 20 pixels (~20 m²)
      - Fill holes < 10 pixels
      - Morphological closing (kernel=3)
  15. Save prediction masks → outputs/predictions/

┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 4: VECTORIZATION & GEOJSON EXPORT (Hours 20-24)               │
└─────────────────────────────────────────────────────────────────────┘
  16. For each prediction mask:
      - Load corresponding tile coordinates from metadata.csv
      - Convert raster mask → shapely polygons
      - Transform pixel coords → lat/lon (EPSG:4326)
  17. Compute per-polygon attributes:
      - area_m2: Polygon area in square meters
      - num_spots: Estimate (area_m2 / 12.5) # standard spot = 2.5m × 5m
      - confidence: Mean prediction probability in polygon
      - size_category: "small" (<50 spots), "medium" (50-200), "large" (>200)
  18. Merge all polygons into single GeoDataFrame
  19. Export → outputs/parking_lots.geojson

┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 5: WEB UI DEVELOPMENT (Hours 8-28) — PARALLEL TRACK C         │
└─────────────────────────────────────────────────────────────────────┘
  20. Build dark-themed map interface:
      - Leaflet.js map with CARTO Dark basemap
      - Load parking_lots.geojson as overlay
      - Color polygons by size: blue (small), orange (medium), red (large)
  21. Implement left sidebar:
      - Aggregate stats: total lots, estimated spots, coverage area, avg size
      - Confidence meter (average across all detections)
      - Filters: lot size toggles, confidence slider
      - Search box (filter by neighborhood/address)
  22. Wire filters to map:
      - Update visible polygons on filter change
      - Recompute stats for filtered subset
  23. Add interactions:
      - Click polygon → show popup (lot details)
      - Zoom to bounds on search
  24. Deploy: frontend/ directory with index.html + assets

┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 6: VALIDATION & POLISH (Hours 28-36)                          │
└─────────────────────────────────────────────────────────────────────┘
  25. Spot-check predictions against satellite imagery
  26. Cross-reference with OpenStreetMap parking lot data (if available)
  27. Fix any obvious false positives (e.g., rooftops, roads)
  28. Optimize GeoJSON size (simplify geometries if >1MB)
  29. Prep demo: screenshots, talking points, video walkthrough
  30. Final deployment test: ensure UI loads parking_lots.geojson correctly
```

---

## 3. Dependencies (Hackathon-Scoped)

```
# Machine Learning
torch==2.1.2
torchvision==0.16.2
segmentation-models-pytorch==0.3.3   # DeepLabV3+ with ResNet34
datasets==2.16.1                     # Hugging Face dataset loader

# Geospatial
earthengine-api==0.1.389
geopandas==0.14.1
rasterio==1.3.9
shapely==2.0.2

# Image Processing
opencv-python==4.8.1
scikit-image==0.22.0
pillow==10.1.0

# Utilities
numpy==1.24.3
pandas==2.1.3
pyyaml==6.0.1
tqdm==4.66.1
```

### System Requirements
- Python 3.10+
- CUDA 11.8+ (GPU required for training)
- 16GB RAM minimum
- ~20GB storage (scoped Atlanta area + model checkpoints)

### Quick Setup
```bash
pip install -r requirements.txt
earthengine authenticate
python -c "from datasets import load_dataset; load_dataset('UTEL-UIUC/parkseg12k')"  # Pre-cache dataset
```

---

## 4. 36-Hour Build Order

### Hours 0-2: Setup & Config
1. `requirements.txt` → install all dependencies
2. `config/config.yaml` → hyperparameters, paths
3. `config/atlanta_roi.geojson` → scoped bounding box (Midtown/Buckhead/Airport)
4. Authenticate GEE, verify GPU access

### Hours 2-8: Parallel Work — Data + Model Training Start
**Track A (Training):**
5. `src/data/parkseg_dataset.py` → Hugging Face dataset loader
6. `src/model/segmentation.py` → DeepLabV3+ with ResNet34
7. `src/model/train.py` → training loop
8. `scripts/01_train_model.py` → kick off training (runs overnight)

**Track B (Data Acquisition):**
9. `src/data/naip_downloader.py` → GEE tile export for Atlanta ROI
10. `scripts/02_download_naip.py` → download ~200 tiles (background job)

### Hours 8-14: Model Training + UI Prototyping
**Track A (Training cont.):**
- Monitor training progress (target: mIoU > 0.75)
- Save best checkpoint

**Track C (Frontend):**
11. `frontend/index.html` → basic map layout
12. `frontend/styles.css` → dark theme matching mockup
13. `frontend/app.js` → Leaflet map initialization

### Hours 14-20: Inference Pipeline
14. `src/inference/predictor.py` → load model, batch prediction
15. `src/inference/postprocess.py` → clean masks
16. `scripts/03_run_inference.py` → run on all Atlanta tiles

### Hours 20-24: Vectorization & GeoJSON
17. `src/spatial/vectorize.py` → mask → polygons with attributes
18. `scripts/04_generate_geojson.py` → create parking_lots.geojson

### Hours 24-28: UI Integration
19. `frontend/api.js` → load GeoJSON, compute aggregate stats
20. Wire filters (size categories, confidence slider, search)
21. Add polygon click interactions, legends

### Hours 28-34: Validation & Debugging
22. Spot-check predictions vs satellite imagery
23. Fix false positives (tune postprocessing thresholds)
24. Optimize GeoJSON (simplify geometries if needed)

### Hours 34-36: Demo Prep
25. Test full pipeline end-to-end
26. Screenshots, video walkthrough
27. Prepare presentation talking points

---

## 5. Module Interfaces

### `gee_downloader.py`
```python
def download_naip_tiles(
    bounds: gpd.GeoDataFrame,  # Polygon boundary
    output_dir: Path,          # Where to save GeoTIFFs
    year_range: tuple[int, int] = (2021, 2023),
    resolution: int = 1        # meters/pixel
) -> pd.DataFrame:             # Returns manifest of downloaded tiles
    """Fetches NAIP imagery from Google Earth Engine."""
```

### `image_processor.py`
```python
def preprocess_tile(
    geotiff_path: Path,
    target_size: tuple[int, int] = (512, 512),
    normalize: bool = True
) -> np.ndarray:  # Shape: (C, H, W), dtype: float32
    """Loads and preprocesses a single GeoTIFF tile."""
```

### `segmentation_model.py`
```python
class ParkingSegmentationModel(nn.Module):
    def __init__(self, encoder: str = "resnet50", weights: Path = None):
        """Initializes U-Net with pretrained encoder."""

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Input: (B, 3, 512, 512) → Output: (B, 1, 512, 512)"""
```

### `predictor.py`
```python
def predict_tile(
    model: nn.Module,
    image: np.ndarray,     # (C, H, W)
    threshold: float = 0.5
) -> np.ndarray:           # (H, W), binary mask
    """Runs inference on a single tile."""

def batch_predict(
    model: nn.Module,
    tile_dir: Path,
    output_dir: Path,
    batch_size: int = 8
) -> None:
    """Processes all tiles in directory."""
```

### `postprocessing.py`
```python
def clean_mask(
    mask: np.ndarray,       # Binary mask (H, W)
    min_area_m2: float = 15,
    fill_holes_m2: float = 5,
    resolution_m: float = 1.0
) -> np.ndarray:            # Cleaned binary mask
    """Removes noise and fills holes."""
```

### `vectorizer.py`
```python
def mask_to_geojson(
    mask: np.ndarray,       # Binary mask
    transform: Affine,      # Rasterio transform (pixel → lat/lon)
    crs: str = "EPSG:4326"
) -> gpd.GeoDataFrame:      # Polygons with geometry + area
    """Converts prediction mask to GeoJSON polygons."""
```

### `aggregator.py`
```python
def aggregate_by_grid(
    parking_gdf: gpd.GeoDataFrame,
    grid_size_m: int = 1000
) -> gpd.GeoDataFrame:      # Grid cells with spot counts
    """Counts parking spots per grid cell."""
```

### `map_builder.py`
```python
def create_interactive_map(
    parking_geojson: Path,
    output_html: Path,
    basemap: str = "OpenStreetMap"
) -> None:
    """Generates Folium map with parking overlays."""
```

---

## 6. Risks & Mitigation Strategies

### Data Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| **GEE rate limits** | Download stalls after 100 tiles | Implement exponential backoff, split downloads across days |
| **Cloud cover in NAIP** | Missing data for some tiles | Pre-filter by cloud score, fallback to older imagery |
| **Tile boundary artifacts** | Parking lots cut off at edges | Use 10% overlap between tiles, merge predictions |
| **Large dataset size** | 100GB+ storage needed | Stream processing, delete raw tiles after preprocessing |

### Model Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| **ParkSeg12k domain shift** | Poor performance on Atlanta | Fine-tune on 50-100 manually labeled Atlanta tiles |
| **Small parking lots missed** | Undercount in urban areas | Lower detection threshold, use smaller tile size |
| **False positives (roads)** | Overcount | Train on negative examples, post-filter by shape (parking = rectangular) |
| **GPU memory limits** | Can't process large tiles | Reduce batch size, use gradient checkpointing |

### Spatial Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| **Coordinate misalignment** | Polygons don't match satellite imagery | Validate CRS consistency, use rasterio transforms |
| **Overlapping polygons** | Double-counting | Use spatial union before counting |
| **Invalid geometries** | GeoJSON export fails | Apply `.buffer(0)` to fix topology errors |

### Deployment Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| **HTML map too large** | Browser crashes (10K+ polygons) | Cluster points at low zoom, simplify geometries |
| **Slow inference** | 48+ hours for full Atlanta | Use GPU batching, parallelize across tiles |
| **Reproducibility issues** | Results change across runs | Fix random seeds, version all dependencies |

---

## 7. 4-Person Hackathon Strategy

### Team Roles (36-Hour Sprint)

#### **Person 1: ML Engineer**
**Hours 0-12:** Train model on ParkSeg12k
- Setup training pipeline
- Monitor convergence
- Save best checkpoint (target: mIoU > 0.75)

**Hours 12-20:** Run inference on Atlanta tiles
- Load trained model
- Batch predict on ~200 tiles
- Apply postprocessing

**Hours 20-28:** Validate predictions
- Spot-check against satellite imagery
- Tune postprocessing thresholds

#### **Person 2: Data Engineer**
**Hours 0-8:** Download Atlanta NAIP tiles
- Define scoped ROI (Midtown/Buckhead/Airport)
- Setup GEE export (~200 tiles)
- Monitor downloads

**Hours 8-20:** Preprocessing pipeline
- Normalize tiles (ImageNet stats)
- Create metadata CSV with coordinates
- Feed tiles to inference pipeline

**Hours 20-24:** Vectorization
- Convert masks → GeoJSON polygons
- Compute per-lot attributes (area, spots, confidence)

#### **Person 3: Frontend Developer**
**Hours 0-12:** UI scaffolding
- Setup Leaflet map (CARTO Dark basemap)
- Implement dark theme CSS (match mockup)
- Build sidebar layout (stats, filters)

**Hours 12-24:** Interactivity & logic
- Load GeoJSON, render polygons (colored by size)
- Wire filters (size toggles, confidence slider, search)
- Compute aggregate stats dynamically

**Hours 24-34:** Polish & testing
- Add polygon click popups
- Optimize for performance (large GeoJSON)
- Cross-browser testing

#### **Person 4: Integrator / QA**
**Hours 0-8:** Config & setup
- Create atlanta_roi.geojson
- Setup config.yaml
- Document reproduction steps

**Hours 8-20:** Pipeline orchestration
- Write scripts (01-04)
- Monitor all parallel jobs
- Debug blockers

**Hours 20-34:** End-to-end validation
- Test full pipeline
- Verify GeoJSON → UI flow
- Prepare demo materials

### Critical Dependencies
1. **ParkSeg12k training → Inference** (P1 → P1, hours 12+)
2. **NAIP download → Inference** (P2 → P1, hours 8+)
3. **Predictions → Vectorization** (P1 → P2, hours 20+)
4. **GeoJSON → UI integration** (P2 → P3, hours 24+)

### Fully Parallelizable (Hours 0-12)
- P1: Model training
- P2: Data download
- P3: UI development (use mock GeoJSON)
- P4: Config & documentation

---

## 8. Success Metrics

### Quantitative Goals
- **Coverage:** 95%+ of Atlanta metro area processed
- **Accuracy:** IoU > 0.7 on validation set
- **Completeness:** <5% missing tiles due to cloud cover
- **Performance:** Inference <1 minute per tile (GPU)

### Deliverables Checklist
- [ ] Interactive map showing all detected parking lots
- [ ] GeoJSON file with parking polygons (downloadable)
- [ ] Statistics CSV (counts per neighborhood)
- [ ] Model evaluation report (metrics, sample predictions)
- [ ] README with reproduction instructions

---

## 9. Next Steps After Approval

1. **Setup:** Create conda environment, authenticate GEE, clone ParkSeg12k
2. **Kickoff Meeting:** Assign team roles, share GitHub repo
3. **Iteration 1:** Build data download + sample preprocessing (validate data quality)
4. **Iteration 2:** Test pretrained model on 10 tiles (decide if fine-tuning needed)
5. **Iteration 3:** Full inference pipeline on 100 tiles (measure performance)
6. **Iteration 4:** Vectorization + map prototype (validate output format)
7. **Iteration 5:** Full Atlanta run + final map (production deployment)

---

**Total Timeline:** 36 hours
**Compute:** GPU required for training (~8-12 hours), GEE free tier sufficient
**Deliverables:** Trained segmentation model + Interactive web map + GeoJSON dataset

