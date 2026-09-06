"""
Full 12-Stage Scientific Lunar Image Registration Prototype Orchestrator for SIH26166.
Orchestrates:
[1/12] Synthetic Dataset
[2/12] Preprocessing
[3/12] Multi-scale Representation
[4/12] Feature Detection
[5/12] Correspondence Matching
[6/12] Confidence Filtering
[7/12] Spatial Selection
[8/12] Geometry Estimation
[9/12] Sub-pixel Refinement
[10/12] Registration
[11/12] Evaluation
[12/12] Reporting
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, Any, List
import io
import time
import numpy as np

from prototype.data_interface import ImagePair
from prototype.synthetic.dataset import SyntheticDatasetGenerator
from prototype.synthetic.ground_truth import GroundTruthTransform
from preprocessing.pipeline import PreprocessingPipeline, PreprocessingConfig
from features.detector import SIFTFeatureDetector, ORBFeatureDetector, AutoFeatureDetector
from matching.matcher import DescriptorMatcher
from matching.confidence import ConfidenceFilter
from matching.spatial_filter import SpatialDistributionFilter
from geometry.models import GeometricModelType
from geometry.estimator import RobustGeometricEstimator
from subpixel.refinement import SubpixelRefiner
from registration.pipeline import RegistrationPipeline
from evaluation.metrics import RegistrationMetricsCalculator, FullEvaluationReport
from evaluation.reporter import EvaluationReporter
from evaluation.visualization import RegistrationVisualizer
from experiments.tracker import ExperimentTracker


@dataclass
class PrototypePipelineConfig:
    scenario: str = "combined"
    seed: int = 42
    image_width: int = 512
    image_height: int = 512
    detector: str = "SIFT"  # SIFT or ORB
    geometric_model: str = "HOMOGRAPHY"  # HOMOGRAPHY or AFFINE
    ransac_threshold: float = 3.0
    min_confidence: float = 0.10
    grid_rows: int = 8
    grid_cols: int = 8
    max_matches_per_cell: int = 6
    subpixel_patch_size: int = 15
    save_images: bool = True
    output_dir: str = "./experiments/runs"


class PrototypeRegistrationOrchestrator:
    """
    Unified controller executing all 12 stages of lunar image registration.
    """

    def __init__(self, config: Optional[PrototypePipelineConfig] = None):
        self.config = config or PrototypePipelineConfig()
        self.tracker = ExperimentTracker(base_dir=self.config.output_dir)

    def run(self, input_pair: Optional[ImagePair] = None) -> FullEvaluationReport:
        """
        Execute 12-stage registration pipeline.
        If input_pair is None, synthesizes data on the fly according to scenario & seed.
        """
        experiment_id = self.tracker.generate_experiment_id(self.config.scenario)
        run_dir = self.tracker.create_run_directory(experiment_id)
        log_buffer = io.StringIO()

        def log_msg(msg: str):
            print(msg)
            log_buffer.write(msg + "\n")

        log_msg("====================================================")
        log_msg("SIH26166 REGISTRATION PROTOTYPE")
        log_msg("====================================================")

        total_stages = 12
        failed_stage = None
        failure_reason = None

        # -------------------------------------------------------------
        # STAGE 1: Synthetic Dataset Generation / Input Loading
        # -------------------------------------------------------------
        try:
            if input_pair is not None:
                pair = input_pair
                log_msg(f"[1/{total_stages}] Input Dataset ............ SUCCESS ({pair.name})")
            else:
                gen = SyntheticDatasetGenerator(default_seed=self.config.seed)
                pair = gen.generate_pair(
                    scenario_name=self.config.scenario,
                    width=self.config.image_width,
                    height=self.config.image_height,
                    seed=self.config.seed
                )
                log_msg(f"[1/{total_stages}] Synthetic Dataset ........ SUCCESS ({pair.scenario_name}, seed={pair.seed})")
        except Exception as e:
            log_msg(f"[1/{total_stages}] Synthetic Dataset ........ FAILED ({str(e)})")
            return self._build_failure_report("Synthetic Dataset", str(e))

        # -------------------------------------------------------------
        # STAGE 2: Preprocessing
        # -------------------------------------------------------------
        try:
            prep_cfg = PreprocessingConfig(
                normalize=True,
                apply_clahe=True,
                apply_unsharp=True,
                multiscale=True,
                pyramid_levels=3
            )
            preprocessor = PreprocessingPipeline(config=prep_cfg)
            preprocessed = preprocessor.process(pair)
            log_msg(f"[2/{total_stages}] Preprocessing ........... SUCCESS")
        except Exception as e:
            log_msg(f"[2/{total_stages}] Preprocessing ........... FAILED ({str(e)})")
            return self._build_failure_report("Preprocessing", str(e))

        # -------------------------------------------------------------
        # STAGE 3: Multi-scale Representation
        # -------------------------------------------------------------
        try:
            pyr_len = len(preprocessed.reference_pyramid)
            if pyr_len < 1:
                raise ValueError("Pyramid generation produced 0 levels.")
            log_msg(f"[3/{total_stages}] Multi-scale ............. SUCCESS ({pyr_len} levels)")
        except Exception as e:
            log_msg(f"[3/{total_stages}] Multi-scale ............. FAILED ({str(e)})")
            return self._build_failure_report("Multi-scale", str(e))

        # -------------------------------------------------------------
        # STAGE 4: Feature Detection
        # -------------------------------------------------------------
        try:
            if self.config.detector.upper() == "ORB":
                detector = ORBFeatureDetector(nfeatures=2000)
            else:
                detector = SIFTFeatureDetector(nfeatures=2000)

            feats_ref = detector.extract_features(preprocessed.reference_enhanced_uint8)
            feats_src = detector.extract_features(preprocessed.source_enhanced_uint8)

            n_ref = len(feats_ref.keypoints)
            n_src = len(feats_src.keypoints)

            if n_ref < 4 or n_src < 4:
                raise ValueError(f"Insufficient keypoints detected (Ref: {n_ref}, Src: {n_src}).")

            log_msg(f"[4/{total_stages}] Feature Detection ....... SUCCESS (Ref={n_ref}, Src={n_src})")
        except Exception as e:
            log_msg(f"[4/{total_stages}] Feature Detection ....... FAILED ({str(e)})")
            return self._build_failure_report("Feature Detection", str(e))

        # -------------------------------------------------------------
        # STAGE 5: Correspondence Matching
        # -------------------------------------------------------------
        try:
            matcher = DescriptorMatcher(ratio_threshold=0.80)
            raw_match_result = matcher.match(
                features_src=feats_src,
                features_ref=feats_ref,
                min_confidence=0.0
            )
            raw_count = raw_match_result.filtered_match_count
            if raw_count < 4:
                raise ValueError(f"Insufficient raw matches found: {raw_count}")
            log_msg(f"[5/{total_stages}] Matching ................ SUCCESS ({raw_count} matches)")
        except Exception as e:
            log_msg(f"[5/{total_stages}] Matching ................ FAILED ({str(e)})")
            return self._build_failure_report("Matching", str(e))

        # -------------------------------------------------------------
        # STAGE 6: Confidence Filtering
        # -------------------------------------------------------------
        try:
            conf_src, conf_ref, conf_scores = ConfidenceFilter.filter_by_confidence(
                src_points=raw_match_result.source_points,
                ref_points=raw_match_result.reference_points,
                confidence_scores=raw_match_result.confidence,
                min_confidence=self.config.min_confidence
            )
            filtered_count = len(conf_scores)
            if filtered_count < 4:
                raise ValueError(f"Too few matches passed confidence filter: {filtered_count}")
            log_msg(f"[6/{total_stages}] Confidence Filtering .... SUCCESS ({filtered_count} matches)")
        except Exception as e:
            log_msg(f"[6/{total_stages}] Confidence Filtering .... FAILED ({str(e)})")
            return self._build_failure_report("Confidence Filtering", str(e))

        # -------------------------------------------------------------
        # STAGE 7: Spatial Distribution Optimization
        # -------------------------------------------------------------
        try:
            spatial_filter = SpatialDistributionFilter(
                grid_rows=self.config.grid_rows,
                grid_cols=self.config.grid_cols,
                max_matches_per_cell=self.config.max_matches_per_cell
            )
            spatial_result = spatial_filter.spatially_uniform_selection(
                src_points=conf_src,
                ref_points=conf_ref,
                confidence=conf_scores,
                image_width=pair.reference.shape[1],
                image_height=pair.reference.shape[0]
            )
            log_msg(
                f"[7/{total_stages}] Spatial Selection ....... SUCCESS "
                f"({len(spatial_result.reference_points)} pts, {spatial_result.spatial_coverage_percentage:.1f}% coverage)"
            )
        except Exception as e:
            log_msg(f"[7/{total_stages}] Spatial Selection ....... FAILED ({str(e)})")
            return self._build_failure_report("Spatial Selection", str(e))

        # -------------------------------------------------------------
        # STAGE 8: Robust Geometric Estimation
        # -------------------------------------------------------------
        try:
            geo_model = GeometricModelType.from_string(self.config.geometric_model)
            estimator = RobustGeometricEstimator(
                model_type=geo_model,
                min_inliers_required=6,
                max_reprojection_error_pixels=self.config.ransac_threshold
            )
            transform_result = estimator.estimate_transformation(
                src_points=spatial_result.source_points,
                dst_points=spatial_result.reference_points
            )
            if transform_result.matrix is None:
                raise ValueError(f"Geometry estimation failed: {transform_result.estimator}")
            log_msg(
                f"[8/{total_stages}] Geometry Estimation ..... SUCCESS "
                f"({transform_result.inliers_count}/{len(spatial_result.source_points)} inliers, "
                f"RMSE={transform_result.residual_rmse:.2f}px)"
            )
        except Exception as e:
            log_msg(f"[8/{total_stages}] Geometry Estimation ..... FAILED ({str(e)})")
            return self._build_failure_report("Geometry Estimation", str(e))

        # -------------------------------------------------------------
        # STAGE 9: Sub-pixel Refinement
        # -------------------------------------------------------------
        try:
            subpixel_refiner = SubpixelRefiner(patch_size=self.config.subpixel_patch_size)
            # Refine inlier correspondences
            inlier_mask = transform_result.inliers_mask
            sub_res = subpixel_refiner.refine(
                src_image=preprocessed.source_normalized,
                ref_image=preprocessed.reference_normalized,
                src_points=spatial_result.source_points[inlier_mask],
                ref_points=spatial_result.reference_points[inlier_mask]
            )
            log_msg(
                f"[9/{total_stages}] Sub-pixel Refinement .... SUCCESS "
                f"(disp={sub_res.displacement_norm_mean:.2f}px, conv={sub_res.convergence_rate:.1%})"
            )
        except Exception as e:
            log_msg(f"[9/{total_stages}] Sub-pixel Refinement .... FAILED ({str(e)})")
            return self._build_failure_report("Sub-pixel Refinement", str(e))

        # -------------------------------------------------------------
        # STAGE 10: Registration & Warping
        # -------------------------------------------------------------
        try:
            registrar = RegistrationPipeline()
            reg_output = registrar.register(
                source_image=preprocessed.source_normalized,
                reference_image=preprocessed.reference_normalized,
                transformation=transform_result
            )
            log_msg(f"[10/{total_stages}] Registration ........... SUCCESS")
        except Exception as e:
            log_msg(f"[10/{total_stages}] Registration ........... FAILED ({str(e)})")
            return self._build_failure_report("Registration", str(e))

        # -------------------------------------------------------------
        # STAGE 11: Evaluation & Metrics Benchmark
        # -------------------------------------------------------------
        try:
            metrics_calc = RegistrationMetricsCalculator()
            eval_metrics = metrics_calc.evaluate(
                registered_image=reg_output.registered_image,
                reference_image=preprocessed.reference_normalized
            )

            # Ground truth comparison if synthetic
            gt_metrics_dict = None
            if pair.ground_truth_transform is not None:
                gt_checker = GroundTruthTransform(pair.ground_truth_transform, pair.ground_truth_details)
                gt_comp = gt_checker.compare(
                    transform_result.matrix,
                    image_width=pair.reference.shape[1],
                    image_height=pair.reference.shape[0]
                )
                gt_metrics_dict = gt_comp.to_dict()

            full_report = FullEvaluationReport(
                rmse=eval_metrics.rmse_pixels,
                mae=eval_metrics.mae_pixels,
                ssim=eval_metrics.ssim,
                psnr_db=eval_metrics.psnr_db,
                mutual_information=eval_metrics.mutual_information,
                normalized_cross_correlation=eval_metrics.normalized_cross_correlation,
                initial_keypoints_ref=n_ref,
                initial_keypoints_src=n_src,
                candidate_matches=raw_count,
                filtered_matches=len(spatial_result.reference_points),
                inliers_count=transform_result.inliers_count,
                inlier_ratio=transform_result.inlier_ratio,
                spatial_coverage_percentage=spatial_result.spatial_coverage_percentage,
                occupied_grid_cells=spatial_result.occupied_cells,
                total_grid_cells=spatial_result.total_cells,
                reprojection_rmse_px=transform_result.residual_rmse,
                geometric_model=transform_result.transformation_type,
                estimator=transform_result.estimator,
                subpixel_mean_displacement_px=sub_res.displacement_norm_mean,
                subpixel_convergence_rate=sub_res.convergence_rate,
                ground_truth_metrics=gt_metrics_dict,
                registration_status="SUCCESS"
            )
            log_msg(f"[11/{total_stages}] Evaluation ............. SUCCESS (RMSE={full_report.rmse:.4f}, SSIM={full_report.ssim:.3f})")
        except Exception as e:
            log_msg(f"[11/{total_stages}] Evaluation ............. FAILED ({str(e)})")
            return self._build_failure_report("Evaluation", str(e))

        # -------------------------------------------------------------
        # STAGE 12: Reporting, Visualization & Experiment Archiving
        # -------------------------------------------------------------
        try:
            # 1. Generate Visualizations
            vis_paths = RegistrationVisualizer.generate_all_visualizations(
                ref_img=preprocessed.reference_normalized,
                src_img=preprocessed.source_normalized,
                reg_img=reg_output.registered_image,
                diff_map=reg_output.difference_map,
                ref_pts=spatial_result.reference_points,
                src_pts=spatial_result.source_points,
                inliers_mask=transform_result.inliers_mask,
                report=full_report,
                output_dir=run_dir / "visualizations"
            )

            # 2. Save Artifacts in Run Directory
            config_dict = {
                "experiment_id": experiment_id,
                "scenario": self.config.scenario,
                "seed": self.config.seed,
                "image_width": self.config.image_width,
                "image_height": self.config.image_height,
                "detector": self.config.detector,
                "model": self.config.geometric_model,
                "ransac_threshold": self.config.ransac_threshold,
                "grid": f"{self.config.grid_rows}x{self.config.grid_cols}"
            }

            transform_dict = {
                "model": transform_result.transformation_type,
                "matrix": transform_result.matrix.tolist() if transform_result.matrix is not None else None,
                "inliers_count": transform_result.inliers_count,
                "inlier_ratio": transform_result.inlier_ratio,
                "reprojection_rmse": transform_result.residual_rmse,
                "estimator": transform_result.estimator
            }

            matches_dict = {
                "raw_matches": raw_count,
                "confidence_filtered": filtered_count,
                "spatial_selected": len(spatial_result.reference_points),
                "inliers": transform_result.inliers_count,
                "occupied_cells": spatial_result.occupied_cells,
                "total_cells": spatial_result.total_cells,
                "coverage_pct": spatial_result.spatial_coverage_percentage
            }

            # 3. Render and Save Summary
            summary_text = EvaluationReporter.render_console_report(
                report=full_report,
                scenario_name=self.config.scenario,
                detector_name=self.config.detector,
                matcher_name=matcher.name,
                geometry_name=f"{transform_result.transformation_type}/{transform_result.estimator}",
                subpixel_name="Local correlation refinement",
                run_output_dir=str(run_dir)
            )

            self.tracker.save_run_artifacts(
                run_dir=run_dir,
                config_data=config_dict,
                metrics_data=full_report.to_dict(),
                transform_data=transform_dict,
                ground_truth_data=pair.ground_truth_details,
                matches_data=matches_dict,
                log_text=log_buffer.getvalue(),
                ref_image=preprocessed.reference_normalized,
                src_image=preprocessed.source_normalized,
                reg_image=reg_output.registered_image,
                diff_image=reg_output.difference_map
            )

            log_msg(f"[12/{total_stages}] Reporting .............. SUCCESS")

            # Final Summary Banner
            log_msg("\n====================================================")
            log_msg("FINAL RESULT\n")
            log_msg(f"Registration: {full_report.registration_status}\n")
            log_msg(f"Matches:          {full_report.candidate_matches}")
            log_msg(f"Inliers:          {full_report.inliers_count}")
            log_msg(f"Inlier Ratio:     {full_report.inlier_ratio:.2%}")
            log_msg(f"Spatial Coverage: {full_report.spatial_coverage_percentage:.1f}%")
            log_msg(f"RMSE:             {full_report.rmse:.4f}")
            if full_report.ground_truth_metrics:
                gt = full_report.ground_truth_metrics
                log_msg(f"Transformation Error: Translation={gt.get('translation_error_px', 0.0):.2f}px, Rotation={gt.get('rotation_error_deg', 0.0):.2f}deg")
            log_msg(f"\nOutput:\n{run_dir}\n")

            return full_report

        except Exception as e:
            log_msg(f"[12/{total_stages}] Reporting .............. FAILED ({str(e)})")
            return self._build_failure_report("Reporting", str(e))

    def _build_failure_report(self, stage_name: str, reason: str) -> FullEvaluationReport:
        return FullEvaluationReport(
            rmse=999.0,
            mae=999.0,
            ssim=0.0,
            psnr_db=0.0,
            mutual_information=0.0,
            normalized_cross_correlation=0.0,
            initial_keypoints_ref=0,
            initial_keypoints_src=0,
            candidate_matches=0,
            filtered_matches=0,
            inliers_count=0,
            inlier_ratio=0.0,
            spatial_coverage_percentage=0.0,
            occupied_grid_cells=0,
            total_grid_cells=64,
            reprojection_rmse_px=999.0,
            geometric_model="NONE",
            estimator="FAILED",
            subpixel_mean_displacement_px=0.0,
            subpixel_convergence_rate=0.0,
            ground_truth_metrics=None,
            registration_status="REGISTRATION_FAILED",
            failure_reason=f"Failed at Stage [{stage_name}]: {reason}"
        )
