# SIH26166 12-Stage Registration Pipeline Specification

## Stage Breakdown

| Stage | Name | Description | Output |
|---|---|---|---|
| **[1/12]** | **Synthetic / Input Dataset** | Generates or loads paired reference and source images with ground-truth transformations. | `ImagePair` |
| **[2/12]** | **Preprocessing** | Robust 1%-99% percentile normalization, NaN/Inf handling, CLAHE enhancement, unsharp masking. | Normalized float32 & enhanced uint8 rasters |
| **[3/12]** | **Multi-scale** | Builds 3-level Gaussian image pyramid for coarse-to-fine registration. | `List[np.ndarray]` |
| **[4/12]** | **Feature Detection** | SIFT/ORB keypoint and visual descriptor extraction. | `KeypointsData` |
| **[5/12]** | **Correspondence Matching** | Nearest-neighbor matching with Lowe's ratio test filter ($d_1/d_2 \le 0.80$). | `MatchResult` |
| **[6/12]** | **Confidence Filtering** | Physically-grounded quality scoring: $c = (1 - d_1/d_2) \cdot \exp(-d_1 / \sigma)$. | Quality filtered matches |
| **[7/12]** | **Spatial Distribution** | $8 \times 8$ uniform grid selection to prevent feature clustering in single craters. | Spatially uniform match set + coverage % |
| **[8/12]** | **Geometry Estimation** | Robust RANSAC / USAC_MAGSAC Homography or Affine matrix estimation. | $3 \times 3$ Transformation matrix + Inlier mask |
| **[9/12]** | **Sub-pixel Refinement** | Local NCC template matching with 2D parabolic peak interpolation. | Refined coordinates + displacement stats |
| **[10/12]** | **Registration** | Inverse projective warping into reference coordinate grid. | Warped registered image |
| **[11/12]** | **Evaluation** | Computes pixel RMSE, MAE, SSIM, PSNR, Mutual Information, and ground truth error. | `FullEvaluationReport` |
| **[12/12]** | **Reporting & Tracking** | Visualizations, JSON metrics, and logs written to `experiments/runs/<exp_id>/`. | Run archive & terminal report |

## Execution Example

```powershell
py -3 -m cli.dataset_cli prototype run --scenario combined --seed 42
```
