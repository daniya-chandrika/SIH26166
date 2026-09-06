# SIH26166 Quantitative Registration Evaluation

## 1. Metrics Overview

All metrics in SIH26166 are mathematically computed from genuine raster arrays and coordinate transformations without synthetic fabrication or hard-coded assumptions.

### Radiometric & Image Similarity Metrics
- **RMSE (Root Mean Square Error)**:
  $$\text{RMSE} = \sqrt{\frac{1}{|\Omega|} \sum_{(x,y) \in \Omega} (I_{\text{ref}}(x,y) - I_{\text{reg}}(x,y))^2}$$
  Computed over the valid overlap region $\Omega$.
- **MAE (Mean Absolute Error)**: Average absolute intensity deviation.
- **SSIM (Structural Similarity Index)**: Measures structural pattern correlation independent of uniform brightness/contrast shifts.
- **PSNR (Peak Signal-to-Noise Ratio)**: Expressed in dB ($10 \log_{10} \frac{\text{MAX}^2}{\text{MSE}}$).
- **Mutual Information**: Information-theoretic alignment measure $I(X; Y) = H(X) + H(Y) - H(X, Y)$.
- **Normalized Cross-Correlation (NCC)**: Pearson linear correlation coefficient between overlapping pixels.

### Geometric & Correspondence Quality Metrics
- **Inlier Count & Ratio**: Number and percentage of correspondences that fit the geometric transformation within RANSAC reprojection threshold.
- **Spatial Coverage Percentage**: Percentage of $8 \times 8$ grid cells occupied by valid inlier correspondences.
- **Reprojection RMSE**: Root mean square error of mapped inlier coordinates:
  $$\text{RMSE}_{\text{reproj}} = \sqrt{\frac{1}{K} \sum_{i=1}^K \| p_{\text{ref}, i} - \hat{H} p_{\text{src}, i} \|^2}$$

### Ground Truth Error Decomposition (Synthetic Benchmarks)
- **Translation Error**: $\|\mathbf{t}_{\text{est}} - \mathbf{t}_{\text{gt}}\|_2$ (pixels).
- **Rotation Error**: $|\theta_{\text{est}} - \theta_{\text{gt}}|$ (degrees).
- **Scale Error**: $|s_{\text{est}} - s_{\text{gt}}|$.
- **Corner Reprojection RMSE**: Average pixel error when mapping image 4 corners with $H_{\text{est}}$ vs $H_{\text{gt}}$.
- **Matrix Frobenius Difference**: $\| \hat{H}_{\text{est}} - \hat{H}_{\text{gt}} \|_F$.
