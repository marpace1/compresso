# Compresso

Professional-grade local image compression desktop application. Analyzes each image, predicts optimal settings, and compresses to the target size — all offline, all private.

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-blue?style=flat-square&logo=python" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/PySide6-6.6+-green?style=flat-square" alt="PySide6 6.6+">
  <img src="https://img.shields.io/badge/License-MIT-gray?style=flat-square" alt="MIT License">
</p>

---

## Features

### Core Compression

- **Smart Image Analysis** — Inspects noise level, texture complexity, edge density, sharpness, entropy, and color distribution in under 500 ms. Uses these metrics to recommend the best format and quality settings automatically.
- **Dual Linked Sliders** — Compression % and Quality % sliders are intelligently coupled through a prediction model. Moving one slider adjusts the other to keep the output balanced.
- **Live Predictions** — As you move any slider, the prediction panel instantly estimates output file size, compression ratio, visual quality score, expected SSIM, expected PSNR, and processing time — all before you hit Compress.
- **Target File Size** — Set an exact target (e.g. 500 KB, 2 MB, 0.5 GB) and Compresso binary-searches the optimal quality parameter to hit it. Works with every supported image type, not just JPEG.

### Multi-Format Support

| Input Formats | Output Formats |
|---|---|
| PNG, JPEG, BMP, TIFF, GIF, HEIC, AVIF, WebP | JPEG, PNG, WebP, AVIF |

- **JPEG** — PIL with optional MozJPEG (`cjpeg`) for better compression at the same quality.
- **PNG** — PIL optimize + compress levels, with optional oxipng for smaller lossless output.
- **WebP** — Lossy encoding via PIL with configurable method (0-6).
- **AVIF** — Next-gen format via `pillow-avif-plugin` for superior quality-to-size ratio.

### Target Size per Image Type

| Source Format | Strategy |
|---|---|
| JPEG / WebP / AVIF | Binary-search over quality (1–95) with early stopping |
| PNG | Palette reduction (256/128/64 colors), grayscale conversion, compression levels 0–9. Falls back to lossy WebP if lossless can't reach the target. |
| BMP / TIFF / GIF / Other | Converts to WebP and binary-searches quality |

### UI / UX

- **Before / After Comparison** — Draggable divider slider to visually compare original and compressed side by side.
- **Difference Heatmap** — Grayscale diff visualization with gamma amplification to highlight subtle compression artifacts.
- **Zoom Controls** — 100%, 200%, 400% zoom plus mouse-wheel zoom for pixel-level inspection.
- **Batch Mode** — Load an entire folder of images and compress them all in one go with the same settings.
- **Monochrome Dark Theme** — Minimal grayscale palette, Inter font, clean card-based layout.
- **Scrollable Layout** — The entire UI stays accessible when the window is resized smaller.
- **Metadata Stripping** — Optionally remove EXIF, GPS, ICC profiles, and thumbnails.

### Architecture

- **Non-blocking UI** — All analysis, compression, and batch operations run in `QThreadPool` background threads. The UI never freezes.
- **Layered Design** — Four clear layers: Models (dataclasses), Core (engines), Workers (threads), UI (PySide6 widgets).
- **Type-Safe Data Flow** — Every piece of data is a frozen `@dataclass(slots=True)`. No dicts passed around.

---

## Project Structure

```
compresso/
├── main.py                      # Application entry point
├── run.sh                       # One-command launch script (creates venv automatically)
├── requirements.txt             # Python dependencies
├── .gitignore
├── README.md
│
├── models/
│   ├── __init__.py
│   └── data_models.py           # ImageInfo, AnalysisResult, CompressionSettings,
│                                # CompressionPrediction, CompressionResult, BatchItem
│
├── core/
│   ├── __init__.py
│   ├── analyzer.py              # Image analysis engine (noise, texture, edges, entropy)
│   ├── predictor.py             # Compression prediction from analysis metrics
│   ├── compressor.py            # Multi-backend compression (JPEG/WebP/PNG/AVIF)
│   │                            #   + target-size binary search for all formats
│   ├── optimizer.py             # SSIM-targeted quality optimization
│   ├── metrics.py               # SSIM, PSNR, MS-SSIM calculation
│   └── metadata.py              # EXIF / ICC / GPS metadata handling
│
├── workers/
│   ├── __init__.py
│   ├── analysis_worker.py       # Background analysis (QRunnable)
│   ├── compression_worker.py    # Background compression + target-size worker
│   └── batch_worker.py          # Background batch processing
│
├── ui/
│   ├── __init__.py
│   ├── main_window.py           # Main window: layout, connections, file handling
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── drop_zone.py         # Drag-and-drop file / folder accept widget
│   │   ├── image_info_panel.py  # Displays file name, dimensions, size, format, bit depth
│   │   ├── smart_sliders.py     # Dual linked sliders + presets + target size input
│   │   ├── prediction_panel.py  # Live compression prediction display
│   │   ├── difficulty_meter.py  # Visual bar: Easy / Medium / Hard / Very Hard
│   │   ├── comparison_view.py   # Before/after canvas + zoom + heatmap toggle
│   │   └── stats_panel.py       # Post-compression results (size, ratio, SSIM, PSNR)
│   └── dialogs/
│       ├── __init__.py
│       └── batch_dialog.py      # Batch processing dialog with progress table
│
├── themes/
│   ├── __init__.py
│   └── dark_theme.py            # Class-based QSS dark theme (pure grayscale palette)
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py               # File size formatting, path utils, math, easing
│   └── logger.py                # Logging configuration
│
└── output/                      # Default output directory (gitignored)
```

---

## Installation

### Prerequisites

- **Python 3.12+**
- A desktop environment (Linux, macOS, or Windows with GUI support)

### Quick Start

```bash
# Clone the repo
git clone https://github.com/<your-username>/compresso.git
cd compresso

# Option 1: One-command launch (creates venv, installs deps, runs app)
chmod +x run.sh
./run.sh

# Option 2: Manual setup
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

### Optional: External Tools

Compresso auto-detects these tools at runtime. If found, they are used instead of the pure-PIL fallback for better compression at equal quality.

| Tool | Format | Install (Ubuntu/Debian) | Install (macOS) |
|---|---|---|---|
| **MozJPEG** (`cjpeg`) | JPEG | `sudo apt install libjpeg-turbo-progs` | `brew install mozjpeg` |
| **oxipng** | PNG | `sudo apt install oxipng` | `brew install oxipng` |

These are completely optional. Compresso works perfectly without them.

---

## Usage

### Single Image

1. **Drag and drop** an image onto the window, or use **File > Open Image** (Ctrl+O)
2. Compresso analyzes the image and sets recommended sliders
3. Adjust **Compression %**, **Quality %**, output format, or pick a preset
4. Watch the prediction panel update in real time
5. Click **Compress** (or use a preset)
6. Compare original vs. compressed with the before/after slider
7. Toggle **Heatmap** to see exactly where compression artifacts appear
8. Click **Save As** to export the result

### Target File Size

1. Load an image as above
2. In the **Target Size** section, enter a number and pick the unit (KB / MB / GB)
3. Click **Compress to Target**
4. Compresso runs a binary search across quality levels to land as close to the target as possible
5. The output format is chosen automatically based on the source format

### Batch Mode

1. Click **Batch Mode** or drag a folder onto the window
2. Add or remove images from the queue
3. Configure output settings and output folder
4. Click **Start Batch** to process all images

### Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+O` | Open image |
| `Ctrl+S` | Save compressed image |
| `Ctrl+B` | Open batch mode |
| `Ctrl+R` | Reset everything |
| `Ctrl+Q` | Quit |

---

## Compression Pipeline

```
Load Image
    │
    ▼
Analysis (background thread)
    ├── Noise level (Laplacian stddev)
    ├── Texture complexity (LBP uniformity)
    ├── Edge density (Canny + dilation)
    ├── Sharpness (Laplacian variance)
    ├── Entropy (histogram)
    ├── Color distribution
    ├── Metadata size
    └── Already-compressed detection
    │
    ▼
Prediction (instant, main thread)
    ├── Estimated output size
    ├── Compression ratio
    ├── Visual quality score
    ├── Expected SSIM / PSNR
    └── Processing time estimate
    │
    ▼
Compression (background thread)
    ├── Format-specific encoder (JPEG/WebP/PNG/AVIF)
    ├── Optional external tool (MozJPEG / oxipng)
    └── Metadata stripping (if enabled)
    │
    ▼
Metrics (post-compression)
    ├── Actual SSIM
    ├── Actual PSNR
    ├── File size comparison
    └── Space saved
```

---

## Tech Stack

| Component | Technology |
|---|---|
| GUI Framework | PySide6 (Qt 6) |
| Image I/O | Pillow, pillow-heif, pillow-avif-plugin |
| Image Analysis | OpenCV (cv2), scikit-image, NumPy, SciPy |
| Compression Backends | PIL libjpeg, MozJPEG (optional), oxipng (optional) |
| Threading | QThreadPool + QRunnable |
| Quality Metrics | SSIM, PSNR, MS-SSIM (scikit-image) |
| Styling | QSS (class-based theme system) |

---

## License

MIT