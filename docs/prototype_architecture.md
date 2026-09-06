# SIH26166 Lunar Image Registration: Prototype Architecture

## 1. Executive Summary

The **SIH26166 Scientific Lunar Image Registration System Prototype** demonstrates end-to-end multi-sensor orbital image registration. Designed for high accuracy across lunar terrain challenges (drastic illumination changes, multi-scale resolutions, perspective distortion, crater density variations), the prototype demonstrates the full 12-stage algorithmic registration architecture completely offline without requiring massive real dataset downloads or GPU clusters.

```
                    INPUT
                      │
             ┌────────┴────────┐
             │                 │
       Synthetic Data       Real Data
             │                 │
             └────────┬────────┘
                      ▼
                  ImagePair
                      │
                      ▼
             [STAGE 2] PREPROCESSING (Robust Normalization, CLAHE, Denoising)
                      │
                      ▼
             [STAGE 3] MULTI-SCALE REPRESENTATION (Gaussian Pyramid / GSD Matching)
                      │
                      ▼
             [STAGE 4] FEATURE DETECTION (SIFT / ORB Keypoint & Descriptor Extraction)
                      │
                      ▼
             [STAGE 5] CORRESPONDENCE MATCHING (k-NN / Lowe's Ratio-Test)
                      │
                      ▼
             [STAGE 6] CONFIDENCE FILTERING (Metric-based Quality Score)
                      │
                      ▼
             [STAGE 7] SPATIAL DISTRIBUTION OPTIMIZATION (Uniform Grid Partitioning)
                      │
                      ▼
             [STAGE 8] ROBUST GEOMETRIC ESTIMATION (RANSAC / MAGSAC Homography & Affine)
                      │
                      ▼
             [STAGE 9] SUB-PIXEL REFINEMENT (Local NCC / Gradient Optimization)
                      │
                      ▼
             [STAGE 10] IMAGE WARPING & REGISTRATION (Bilinear Resampling & Rescaling)
                      │
                      ▼
             [STAGE 11] QUANTITATIVE EVALUATION (RMSE, SSIM, PSNR, GT Error Benchmarks)
                      │
             ┌────────┴────────┐
             ▼                 ▼
         Metrics          Visualization
             │                 │
             └────────┬────────┘
                      ▼
             [STAGE 12] EXPERIMENT TRACKING & REPORTING (Local Run Vault & Optional Supabase)
```

## 2. Core Modules and Separation of Concerns

1. **Data Layer (`prototype/data_interface.py`)**:
   - `ImagePair`: Sensor-agnostic raster container holding reference raster, source raster, scientific metadata, and optional ground truth coordinates.
2. **Synthetic Engine (`prototype/synthetic/`)**:
   - Procedural lunar geomorphology generation (craters, rims, ejecta rays, rilles, ridges, Lambertian sun shading) with analytical ground-truth transformation matrices.
3. **Preprocessing (`preprocessing/`)**:
   - Radiometric cleaning, robust percentile normalization, CLAHE local contrast equalization, and multi-scale Gaussian pyramids.
4. **Feature Detection (`features/`)**:
   - Scale-Invariant Feature Transform (SIFT) and ORB feature extractors with automatic fallback.
5. **Matching & Spatial Selection (`matching/`)**:
   - $k$-NN matcher ($k=2$) with Lowe's ratio test, confidence scoring, and $8 \times 8$ grid-based spatial distribution filtering.
6. **Geometry & Subpixel (`geometry/`, `subpixel/`)**:
   - RANSAC and USAC-MAGSAC robust Homography / Affine estimation, coupled with local Normalized Cross-Correlation (NCC) parabolic peak subpixel refinement.
7. **Registration & Evaluation (`registration/`, `evaluation/`)**:
   - Perspective/Affine warping, difference maps, checkerboard continuity maps, and rigorous metrics (RMSE, SSIM, PSNR, Mutual Information, NCC).
8. **Experiment Tracking (`experiments/`)**:
   - Isolated run directories in `experiments/runs/<experiment_id>/` storing manifests, JSON metrics, matrices, logs, and diagnostic figures.
