"""
Evaluation Reporting and Formatting for SIH26166.
Generates human-readable terminal summaries, structured JSON, and scientific audit reports.
"""
from typing import Dict, Any, Optional
import json
from pathlib import Path

from evaluation.metrics import FullEvaluationReport


class EvaluationReporter:
    """
    Renders clean, informative console reports and exports metric dictionaries.
    """

    @staticmethod
    def render_console_report(
        report: FullEvaluationReport,
        scenario_name: str = "combined",
        detector_name: str = "SIFT",
        matcher_name: str = "BFMatcher",
        geometry_name: str = "Homography/RANSAC",
        subpixel_name: str = "Local correlation refinement",
        run_output_dir: Optional[str] = None
    ) -> str:
        lines = []
        lines.append("----------------------------------------------------")
        lines.append("SIH26166 LUNAR IMAGE REGISTRATION PROTOTYPE")
        lines.append("----------------------------------------------------")
        lines.append("")
        lines.append("Input:")
        lines.append("Synthetic lunar terrain")
        lines.append("")
        lines.append("Scenario:")
        lines.append(f"{scenario_name}")
        lines.append("")
        lines.append("Feature detector:")
        lines.append(f"{detector_name}")
        lines.append("")
        lines.append("Matcher:")
        lines.append(f"{matcher_name}")
        lines.append("")
        lines.append("Geometry:")
        lines.append(f"{geometry_name}")
        lines.append("")
        lines.append("Subpixel:")
        lines.append(f"{subpixel_name}")
        lines.append("")
        lines.append("----------------------------------------------------")
        lines.append("RESULTS")
        lines.append("----------------------------------------------------")
        lines.append(f"Initial keypoints:      Ref={report.initial_keypoints_ref} | Src={report.initial_keypoints_src}")
        lines.append(f"Candidate matches:      {report.candidate_matches}")
        lines.append(f"Filtered matches:       {report.filtered_matches}")
        lines.append(f"Inliers:                {report.inliers_count}")
        lines.append(f"Inlier ratio:           {report.inlier_ratio:.2%}")
        lines.append(f"Spatial coverage:       {report.spatial_coverage_percentage:.1f}% ({report.occupied_grid_cells}/{report.total_grid_cells} cells)")
        lines.append(f"Reprojection RMSE:      {report.reprojection_rmse_px:.3f} px")
        lines.append(f"Image RMSE:             {report.rmse:.4f}")
        lines.append(f"Image MAE:              {report.mae:.4f}")
        lines.append(f"SSIM:                   {report.ssim:.4f}")
        lines.append(f"PSNR:                   {report.psnr_db:.2f} dB")
        lines.append(f"Mutual Information:     {report.mutual_information:.4f}")
        lines.append(f"Normalized Cross-Corr:  {report.normalized_cross_correlation:.4f}")
        lines.append(f"Subpixel Mean Disp:     {report.subpixel_mean_displacement_px:.3f} px (conv: {report.subpixel_convergence_rate:.1%})")

        if report.ground_truth_metrics:
            gt = report.ground_truth_metrics
            lines.append("")
            lines.append("GROUND TRUTH VERIFICATION (Synthetic Benchmark):")
            lines.append(f"  Translation Error:    {gt.get('translation_error_px', 0.0):.3f} px")
            lines.append(f"  Rotation Error:       {gt.get('rotation_error_deg', 0.0):.3f} deg")
            lines.append(f"  Scale Error:          {gt.get('scale_error', 0.0):.4f}")
            lines.append(f"  Corner Reproj RMSE:   {gt.get('corner_reprojection_rmse_px', 0.0):.3f} px")
            lines.append(f"  Matrix Frobenius Diff:{gt.get('matrix_frobenius_norm_diff', 0.0):.4f}")

        lines.append("")
        lines.append(f"Registration status:    {report.registration_status}")
        if report.failure_reason:
            lines.append(f"Failure Reason:         {report.failure_reason}")

        if run_output_dir:
            lines.append("")
            lines.append("----------------------------------------------------")
            lines.append("OUTPUT FILES")
            lines.append("----------------------------------------------------")
            lines.append(f"Run Directory:          {run_output_dir}")
            lines.append(f"Visualizations:         {run_output_dir}/visualizations/")
            lines.append(f"Registered Output:      {run_output_dir}/registered/")
            lines.append(f"Metrics & Logs:         {run_output_dir}/metrics.json & logs.txt")

        lines.append("")
        lines.append("----------------------------------------------------")
        lines.append("IMPORTANT:")
        lines.append("This is a synthetic benchmark.")
        lines.append("It does not represent final performance")
        lines.append("on Chandrayaan-2/LROC scientific imagery.")
        lines.append("----------------------------------------------------")

        return "\n".join(lines)

    @staticmethod
    def export_json(report: FullEvaluationReport, output_path: Path) -> None:
        """Save report dictionary to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2)
