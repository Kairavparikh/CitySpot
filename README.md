# ParkSight

**AI-Powered Parking Detection System for Atlanta**

ParkSight uses deep learning and satellite imagery to detect and map parking infrastructure across Atlanta, combining AI-detected surface lots with real-time garage data and street parking information.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.14-blue.svg)
![PyTorch](https://img.shields.io/badge/PyTorch-2.0-red.svg)

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [System Architecture](#system-architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Results](#results)
- [Data Sources](#data-sources)
- [Model Details](#model-details)
- [API Integration](#api-integration)
- [Future Improvements](#future-improvements)
- [License](#license)

---

## Overview

ParkSight is a comprehensive parking detection system built for a 36-hour hackathon that:

1. **Trains a deep learning model** to detect parking lots from satellite imagery
2. **Downloads 1,012 NAIP tiles** covering metropolitan Atlanta
3. **Runs inference** to identify 1,931 surface parking lots
4. **Integrates real data** from Google Places API (garages) and OpenStreetMap (street parking)
5. **Visualizes everything** in an interactive dark-themed web interface

**Total Parking Inventory Detected:**
- 🅿️ 1,931 surface parking lots (AI-detected)
- 🏢 11 parking garages (Google Places)
- 🛣️ 56 street parking zones (OpenStreetMap)
- **517,826 estimated parking spaces**

---

## Features

### AI-Powered Detection
- DeepLabV3+ semantic segmentation model with ResNet34 encoder
- 70.7% IoU accuracy on parking lot detection
- 4-channel input (RGB + Near-Infrared from NAIP imagery)
- Trained on 12,617 images from ParkSeg12k dataset

### Comprehensive Data Integration
- **Surface Lots**: Satellite-based AI detection with size classification
- **Parking Garages**: Real ratings, pricing, hours from Google Places API
- **Street Parking**: Zone-based availability with estimated occupancy patterns

### Interactive Frontend
- 🗺️ Three view modes: Map, Heatmap, Analytics
- 💼 AI Business Advisor chatbot for site selection
- 📍 Current location tracking with one-click positioning
- 🎨 Dark theme with smooth animations
- 🔍 Advanced filtering (size, confidence, search)
- 📊 Analytics dashboard with Chart.js visualizations
- 🎯 Layer toggles for different parking types
- 📱 Responsive design

### Spatial Analysis
- 6.0 square miles of coverage
- GeoJSON format for easy integration
- Accurate spot estimation based on lot area
- Geographic coordinate tracking

---

## Tech Stack

### Deep Learning
- **PyTorch 2.x** - Deep learning framework
- **torchvision** - DeepLabV3+ architecture
- **scikit-image** - Image processing and postprocessing
- **Apple MPS** - GPU acceleration for M-series chips

### Geospatial
- **Google Earth Engine** - NAIP satellite imagery download
- **GeoPandas** - Spatial data processing
- **Shapely** - Geometric operations
- **Rasterio** - Geospatial raster I/O

### Data Sources
- **USDA NAIP** - 1-meter resolution satellite imagery
- **Google Places API** - Parking garage information
- **OpenStreetMap Overpass API** - Street parking zones
- **Hugging Face** - ParkSeg12k training dataset

### Frontend
- **Leaflet.js** - Interactive mapping
- **Chart.js** - Data visualizations
- **CARTO Dark Matter** - Base map tiles
- Vanilla JavaScript, HTML5, CSS3

### Other
- **Python 3.14** - Core language
- **YAML** - Configuration management
- **Pandas** - Data manipulation

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     PARKSIGHT PIPELINE                      │
└─────────────────────────────────────────────────────────────┘

1. TRAINING PHASE
   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
   │ ParkSeg12k   │─────▶│ DeepLabV3+   │─────▶│ Trained Model│
   │ Dataset      │      │ Training     │      │ (70.7% IoU)  │
   │ (12,617 imgs)│      │ (5 epochs)   │      │              │
   └──────────────┘      └──────────────┘      └──────────────┘

2. INFERENCE PHASE
   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
   │ NAIP Tiles   │─────▶│ Inference    │─────▶│ Predictions  │
   │ (1,012 tiles)│      │ Engine       │      │ (masks)      │
   └──────────────┘      └──────────────┘      └──────────────┘

3. VECTORIZATION
   ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
   │ Binary Masks │─────▶│ Polygon      │─────▶│ GeoJSON      │
   │              │      │ Conversion   │      │ (1,931 lots) │
   └──────────────┘      └──────────────┘      └──────────────┘

4. DATA ENRICHMENT
   ┌──────────────┐      ┌──────────────┐
   │ Google Places│─────▶│              │
   │ API (garages)│      │   Combined   │
   ├──────────────┤      │   GeoJSON    │
   │ OpenStreetMap│─────▶│              │
   │ (street park)│      │              │
   └──────────────┘      └──────────────┘

5. VISUALIZATION
   ┌──────────────┐      ┌──────────────┐
   │ GeoJSON Data │─────▶│ Interactive  │
   │              │      │ Web Frontend │
   └──────────────┘      └──────────────┘
```

---

## Installation

### Prerequisites

- Python 3.14+
- Git
- Google Cloud Account (for Earth Engine & Places API)
- 10GB+ free disk space

### Step 1: Clone Repository

```bash
git clone https://github.com/yourusername/parksight.git
cd parksight
```

### Step 2: Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Google Earth Engine Setup

1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable Earth Engine API
3. Authenticate:

```bash
earthengine authenticate
```

4. Set your project ID:

```bash
export GEE_PROJECT='your-project-id'
```

### Step 5: Google Places API Setup (Optional)

1. Enable Places API in Google Cloud Console
2. Create an API key
3. Set up billing (required, but has free tier)

### Step 6: Configure Settings

Edit `config/config.yaml` to customize:
- Training parameters
- Region boundaries
- Model architecture settings

---

## Usage

### Quick Start (Using Pre-trained Model)

If you have the trained model file:

```bash
# 1. Download NAIP tiles (20-30 minutes)
python3 scripts/02_download_naip.py

# 2. Run inference (2-3 minutes)
python3 scripts/03_run_inference.py

# 3. Generate GeoJSON (5 seconds)
python3 scripts/04_generate_geojson.py

# 4. Launch frontend
cd frontend
python3 -m http.server 8000
# Visit: http://localhost:8000
```

### Full Pipeline (Training from Scratch)

```bash
# 1. Train model (8-9 hours)
python3 scripts/01_train_model.py

# 2. Download NAIP tiles (20-30 minutes)
python3 scripts/02_download_naip.py

# 3. Run inference (2-3 minutes)
python3 scripts/03_run_inference.py

# 4. Generate GeoJSON (5 seconds)
python3 scripts/04_generate_geojson.py

# 5. Fetch parking garages (with API key)
python3 scripts/05_fetch_garages.py --api-key YOUR_KEY --radius 15000

# 6. Fetch street parking
python3 scripts/06_fetch_street_parking.py

# 7. Launch frontend
cd frontend
python3 -m http.server 8000
# Visit: http://localhost:8000
```

### Individual Components

**Train only:**
```bash
python3 scripts/01_train_model.py
```

**Download satellite imagery:**
```bash
python3 scripts/02_download_naip.py
```

**Run inference:**
```bash
python3 scripts/03_run_inference.py
```

**Generate vector data:**
```bash
python3 scripts/04_generate_geojson.py
```

**Fetch garage data:**
```bash
python3 scripts/05_fetch_garages.py --api-key YOUR_KEY --radius 15000
```

**Fetch street parking:**
```bash
python3 scripts/06_fetch_street_parking.py
```

---

## Project Structure

```
parksight/
│
├── config/
│   └── config.yaml              # Configuration settings
│
├── src/
│   ├── data/
│   │   ├── dataset.py           # ParkSeg12k dataset loader
│   │   ├── naip_downloader.py   # Earth Engine NAIP fetcher
│   │   ├── google_places.py     # Places API integration
│   │   └── street_parking.py    # OpenStreetMap fetcher
│   │
│   ├── models/
│   │   └── deeplabv3plus.py     # Model architecture
│   │
│   ├── training/
│   │   └── trainer.py           # Training loop & validation
│   │
│   ├── inference/
│   │   ├── predictor.py         # Inference engine
│   │   └── postprocess.py       # Mask cleaning & refinement
│   │
│   └── spatial/
│       └── vectorize.py         # Raster → vector conversion
│
├── scripts/
│   ├── 01_train_model.py        # Training script
│   ├── 02_download_naip.py      # Download satellite tiles
│   ├── 03_run_inference.py      # Run detection
│   ├── 04_generate_geojson.py   # Create vector outputs
│   ├── 05_fetch_garages.py      # Get garage data
│   └── 06_fetch_street_parking.py  # Get street parking
│
├── frontend/
│   ├── index.html               # Main webpage
│   ├── app.js                   # Application logic
│   └── styles.css               # Styling
│
├── models/
│   └── final_model.pth          # Trained model weights (not in git)
│
├── outputs/
│   ├── parking_lots.geojson     # AI-detected surface lots
│   ├── parking_garages.geojson  # Garage locations
│   └── street_parking.geojson   # Street parking zones
│
├── data/
│   ├── naip_tiles/              # Downloaded satellite imagery
│   ├── metadata.csv             # Tile metadata
│   └── dataset/                 # ParkSeg12k dataset (not in git)
│
├── requirements.txt             # Python dependencies
├── .gitignore                   # Git ignore rules
└── README.md                    # This file
```

---

## Results

### Model Performance

**Training Results:**
```
Epoch 1: Train IoU: 59.5% → Val IoU: 60.9%
Epoch 2: Train IoU: 66.2% → Val IoU: 69.5%
Epoch 3: Train IoU: 68.4% → Val IoU: 70.5%
Epoch 4: Train IoU: 69.6% → Val IoU: 70.1%
Epoch 5: Train IoU: 70.5% → Val IoU: 70.7% ✓ Best
```

**Final Metrics:**
- Validation IoU: **70.7%**
- Training Time: ~9.5 hours (Apple M-series)
- Model Size: ~180MB
- Parameters: 22.4 million

### Detection Results

**Coverage:**
- Total area scanned: 6.0 square miles
- Tiles processed: 1,012
- Processing time: 2:23 minutes

**Parking Lots Detected:**
- Total lots: 1,931
- Small lots (<50 spots): 1,316
- Medium lots (50-200 spots): 161
- Large lots (200+ spots): 454
- Total estimated spaces: 517,826

**Additional Data:**
- Parking garages: 11 (with ratings & pricing)
- Street parking zones: 56 (with estimated availability)

### Size Distribution

| Category | Count | Percentage | Est. Spaces |
|----------|-------|------------|-------------|
| Small    | 1,316 | 68.2%      | ~39,480     |
| Medium   | 161   | 8.3%       | ~20,125     |
| Large    | 454   | 23.5%      | ~458,221    |

---

## Data Sources

### NAIP Imagery (USDA)
- **Source**: Google Earth Engine
- **Resolution**: 1 meter/pixel
- **Bands**: RGB + Near-Infrared (NIR)
- **Coverage**: Metropolitan Atlanta
- **Year**: Latest available (2019-2021)
- **License**: Public domain

### ParkSeg12k Dataset (Hugging Face)
- **Source**: `srikantamehta/ParkSeg12k`
- **Images**: 12,617 annotated parking lots
- **Resolution**: 512×512 pixels
- **Format**: RGB + NIR GeoTIFF
- **Annotations**: Binary masks
- **License**: CC BY 4.0

### Google Places API
- **Data**: Parking garage locations, ratings, reviews, pricing
- **Garages found**: 11 in Atlanta metro
- **Fields**: Name, address, phone, hours, website, price level
- **Cost**: Free tier (up to certain limits)

### OpenStreetMap
- **Source**: Overpass API
- **Data**: Street parking zones
- **Zones found**: 56 in Atlanta
- **License**: ODbL

---

## Model Details

### Architecture: DeepLabV3+

**Encoder:** ResNet34 (pretrained on ImageNet)
- Input: 512×512×4 (RGB + NIR)
- Backbone: ResNet34 with dilated convolutions
- Output stride: 16

**ASPP Module:** Atrous Spatial Pyramid Pooling
- Multiple dilation rates: [1, 6, 12, 18]
- Captures multi-scale context
- 256 output channels

**Decoder:**
- Low-level feature fusion
- 4× upsampling
- Output: 512×512×1 (binary mask)

**Loss Function:**
- Combination of Dice Loss + Binary Cross-Entropy
- Optimized for imbalanced segmentation

**Optimizer:**
- AdamW with weight decay
- Learning rate: 1e-4
- Cosine annealing scheduler

### Training Configuration

```yaml
model:
  architecture: deeplabv3plus
  encoder: resnet34
  num_classes: 1
  input_channels: 4

training:
  epochs: 5
  batch_size: 8
  learning_rate: 0.0001
  weight_decay: 0.01
  num_workers: 4

data:
  image_size: 512
  augmentation: true
```

### Postprocessing

1. **Thresholding**: Probabilities > 0.5 → parking lot
2. **Small object removal**: Remove blobs < 50 pixels
3. **Hole filling**: Fill gaps < 30 pixels
4. **Morphological closing**: Smooth boundaries
5. **Spot estimation**: 30 m² per space (accounts for driving lanes, aisles, landscaping)

---

## API Integration

### Google Places API

**Setup:**
1. Enable Places API in Google Cloud Console
2. Create API key
3. Set up billing (required)

**Usage:**
```bash
python3 scripts/05_fetch_garages.py \
  --api-key YOUR_API_KEY \
  --radius 15000
```

**Rate Limits:**
- Free tier: Limited requests/day
- Pagination: Max 60 results (3 pages × 20)

### Google Earth Engine

**Setup:**
1. Create Google Cloud project
2. Enable Earth Engine API
3. Authenticate: `earthengine authenticate`
4. Set project: `export GEE_PROJECT='project-id'`

**Usage:**
```python
from src.data.naip_downloader import download_naip_tiles
download_naip_tiles(region_bounds, output_dir)
```

### OpenStreetMap Overpass API

**No authentication required**

**Usage:**
```bash
python3 scripts/06_fetch_street_parking.py
```

---

## Business Advisor Chatbot

ParkSight includes an AI-powered business advisor that helps entrepreneurs find optimal retail locations based on parking availability and neighborhood intelligence.

### Features

- **Interactive Chat Interface**: Floating button for easy access
- **Pre-built Queries**: Quick suggestions for common business types
- **Contextual Responses**: Answers based on parking data analysis
- **Smart Recommendations**: Combines parking metrics with location insights

### Supported Business Types

- ☕ Coffee Shops & Cafes
- 👗 Boutiques & Retail Stores
- 🍕 Restaurants & Food Service
- 🏋️ Gyms & Fitness Centers
- 💼 Professional Services

### How It Works

1. Click the "Business Advisor" button (bottom-right)
2. Ask about opening a business or use quick suggestions
3. Receive location recommendations based on:
   - Parking availability (# of spots nearby)
   - Average occupancy rates
   - Parking pricing
   - Neighborhood demographics

### Future Enhancements

- Integration with Claude/OpenAI API for dynamic responses
- Real-time parking availability correlation
- Demographic data from Census API
- Competitive analysis (similar businesses nearby)
- Interactive map highlighting (click to show recommended areas)

---

## Future Improvements

### Model Enhancements
- [ ] Train on larger dataset for better accuracy
- [ ] Add temporal analysis (track changes over time)
- [ ] Detect parking lot occupancy from satellite imagery
- [ ] Multi-city support (expand beyond Atlanta)
- [ ] Fine-tune on Atlanta-specific imagery

### Data Integration
- [ ] Real-time availability via ParkMobile API (paid)
- [ ] City of Atlanta Open Data Portal integration
- [ ] Traffic data correlation
- [ ] EV charging station detection
- [ ] Accessibility features (handicap spots)

### Frontend Features
- [ ] Mobile app (React Native)
- [ ] Turn-by-turn navigation to parking
- [ ] Price comparison tool
- [ ] Booking integration
- [ ] User reviews and ratings
- [ ] Predictive availability (ML-based)

### Technical Improvements
- [ ] Model quantization for faster inference
- [ ] Cloud deployment (AWS/GCP)
- [ ] REST API for programmatic access
- [ ] Caching layer for faster loads
- [ ] Real-time updates via WebSockets

---

## Performance Notes

### Hardware Recommendations

**Minimum:**
- 8GB RAM
- 4-core CPU
- 20GB disk space

**Recommended:**
- 16GB+ RAM
- Apple M-series (MPS) or NVIDIA GPU
- 50GB disk space
- SSD for faster I/O

### Timing Benchmarks (Apple M1 Pro)

| Task | Duration | Speed |
|------|----------|-------|
| Model Training | 9.5 hours | ~5.9s/batch |
| NAIP Download | 25 minutes | ~40 tiles/min |
| Inference | 2.5 minutes | ~7 tiles/s |
| Vectorization | 5 seconds | ~200 tiles/s |
| Total Pipeline | ~10 hours | - |

---

## Troubleshooting

### Common Issues

**"ModuleNotFoundError: No module named 'yaml'"**
```bash
pip install pyyaml
```

**"Google Earth Engine authentication failed"**
```bash
earthengine authenticate
export GEE_PROJECT='your-project-id'
```

**"Google Places API REQUEST_DENIED"**
- Enable Places API in Google Cloud Console
- Set up billing account
- Check API key restrictions

**"CUDA/MPS not available"**
- Model will fallback to CPU (slower)
- For Mac: Ensure macOS 12.3+ for MPS support
- For Linux/Windows: Install CUDA-compatible PyTorch

**"Frontend shows nothing"**
- If running from root: Visit `http://localhost:8000/frontend/`
- Or run server from `frontend/` directory

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Acknowledgments

- **ParkSeg12k Dataset**: Srikant Mehta (Hugging Face)
- **NAIP Imagery**: USDA Farm Service Agency
- **DeepLabV3+ Architecture**: Google Research
- **OpenStreetMap**: Community contributors
- **Libraries**: PyTorch, GeoPandas, Leaflet.js, Chart.js
- **Hackathon**: Built during Hackalytics 2026

---

## Contact

**Project Link**: [https://github.com/yourusername/parksight](https://github.com/yourusername/parksight)

---

**Built with ❤️ for smarter cities**
