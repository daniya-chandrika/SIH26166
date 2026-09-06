"""
Spatial Distribution Optimization for SIH26166.
Enforces uniform spatial coverage of keypoint correspondences across the lunar scene,
preventing match clustering in single prominent craters or high-contrast ridges.
"""
from dataclasses import dataclass
from typing import Tuple, Dict, Any, List, Optional
import numpy as np


@dataclass
class SpatialSelectionResult:
    source_points: np.ndarray
    reference_points: np.ndarray
    confidence: np.ndarray
    occupied_cells: int
    total_cells: int
    spatial_coverage_percentage: float
    grid_rows: int
    grid_cols: int
    cell_distribution: Dict[Tuple[int, int], int]


class SpatialDistributionFilter:
    """
    Partitions reference image into a 2D grid and selects top correspondences per cell.
    """

    def __init__(
        self,
        grid_rows: int = 8,
        grid_cols: int = 8,
        max_matches_per_cell: int = 6
    ):
        self.grid_rows = grid_rows
        self.grid_cols = grid_cols
        self.max_matches_per_cell = max_matches_per_cell

    def spatially_uniform_selection(
        self,
        src_points: np.ndarray,
        ref_points: np.ndarray,
        confidence: np.ndarray,
        image_width: int = 512,
        image_height: int = 512,
        grid_rows: Optional[int] = None,
        grid_cols: Optional[int] = None,
        max_matches_per_cell: Optional[int] = None
    ) -> SpatialSelectionResult:
        """
        Partition correspondences into grid bins and select highest-confidence points per bin.
        """
        rows = grid_rows or self.grid_rows
        cols = grid_cols or self.grid_cols
        max_per_cell = max_matches_per_cell or self.max_matches_per_cell
        total_cells = rows * cols

        num_pts = len(ref_points)
        if num_pts == 0:
            return SpatialSelectionResult(
                source_points=np.empty((0, 2), dtype=np.float32),
                reference_points=np.empty((0, 2), dtype=np.float32),
                confidence=np.empty((0,), dtype=np.float32),
                occupied_cells=0,
                total_cells=total_cells,
                spatial_coverage_percentage=0.0,
                grid_rows=rows,
                grid_cols=cols,
                cell_distribution={}
            )

        # Compute cell indices for each reference point
        cell_w = max(1.0, float(image_width) / float(cols))
        cell_h = max(1.0, float(image_height) / float(rows))

        col_indices = np.clip((ref_points[:, 0] / cell_w).astype(int), 0, cols - 1)
        row_indices = np.clip((ref_points[:, 1] / cell_h).astype(int), 0, rows - 1)

        # Group point indices by cell
        cell_bins: Dict[Tuple[int, int], List[int]] = {}
        for idx in range(num_pts):
            cell_key = (int(row_indices[idx]), int(col_indices[idx]))
            if cell_key not in cell_bins:
                cell_bins[cell_key] = []
            cell_bins[cell_key].append(idx)

        # Select top-confidence matches per cell
        selected_indices: List[int] = []
        cell_dist: Dict[Tuple[int, int], int] = {}

        for cell_key, indices in cell_bins.items():
            if len(indices) <= max_per_cell:
                selected = indices
            else:
                # Sort indices descending by confidence
                sorted_idx = sorted(indices, key=lambda i: confidence[i], reverse=True)
                selected = sorted_idx[:max_per_cell]

            selected_indices.extend(selected)
            cell_dist[cell_key] = len(selected)

        # Sort selected indices to maintain consistency
        selected_indices = sorted(selected_indices)

        selected_src = src_points[selected_indices]
        selected_ref = ref_points[selected_indices]
        selected_conf = confidence[selected_indices]

        occupied = len(cell_dist)
        coverage_pct = (float(occupied) / float(total_cells)) * 100.0

        return SpatialSelectionResult(
            source_points=selected_src,
            reference_points=selected_ref,
            confidence=selected_conf,
            occupied_cells=occupied,
            total_cells=total_cells,
            spatial_coverage_percentage=float(coverage_pct),
            grid_rows=rows,
            grid_cols=cols,
            cell_distribution=cell_dist
        )
