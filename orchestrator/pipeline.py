"""
Pipeline Controller and Stage Orchestrator.
Orchestrates INGESTION -> METADATA -> QUALITY stages and produces manifests and reports.
"""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

from ingestion.models import SensorType, IngestionResult
from ingestion.extractor import ArchiveExtractor
from ingestion.inspector import ArchiveInspector
from metadata.models import LunarProductMetadata
from metadata.extractor import MetadataExtractor
from quality.models import QualityReportItem, QualityStatus
from quality.checkers import RasterQualityChecker
from quality.reporter import QualityReporter
from reports.manifest import ManifestGenerator
from orchestrator.logger import PipelineLogger


@dataclass
class PipelineExecutionSummary:
    success: bool
    ingestion_results: List[IngestionResult] = field(default_factory=list)
    products_metadata: List[LunarProductMetadata] = field(default_factory=list)
    quality_items: List[QualityReportItem] = field(default_factory=list)
    manifest_report: Dict[str, Any] = field(default_factory=dict)
    quality_report: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class LunarPipelineOrchestrator:
    """
    Main controller for the Lunar Image Registration Foundation Pipeline.
    """

    def __init__(
        self,
        raw_dir: str | Path = "./data/raw",
        extracted_dir: str | Path = "./data/extracted",
        reports_dir: str | Path = "./reports",
        max_nodata_percent: float = 50.0,
        max_saturation_percent: float = 15.0
    ):
        self.raw_dir = Path(raw_dir).resolve()
        self.extracted_dir = Path(extracted_dir).resolve()
        self.reports_dir = Path(reports_dir).resolve()

        self.extractor = ArchiveExtractor(raw_store_dir=self.raw_dir, extracted_store_dir=self.extracted_dir)
        self.inspector = ArchiveInspector()
        self.metadata_extractor = MetadataExtractor()
        self.quality_checker = RasterQualityChecker(
            max_nodata_percent=max_nodata_percent,
            max_saturation_percent=max_saturation_percent
        )
        self.quality_reporter = QualityReporter(output_dir=self.reports_dir)
        self.manifest_generator = ManifestGenerator(output_dir=self.reports_dir)
        self.logger = PipelineLogger()

    def run(self, sensor_archives: Dict[SensorType, str | Path]) -> PipelineExecutionSummary:
        """
        Execute the 3 foundational stages: INGESTION, METADATA, QUALITY.
        """
        self.logger.header("SIH26166 Scientific Lunar Pipeline Orchestrator")
        summary = PipelineExecutionSummary(success=True)
        total_stages = 3

        # =========================================================================
        # STAGE 1: DATA INGESTION
        # =========================================================================
        self.logger.stage_start(1, total_stages, "Data Ingestion & Integrity Validation")
        ingestion_success = True

        for sensor, zip_path in sensor_archives.items():
            path = Path(zip_path).resolve()
            try:
                self.logger.info(f"Processing {sensor.value} product archive: {path.name}")
                val_result, extract_dir = self.extractor.extract(path, sensor=sensor, preserve_in_raw=True)
                ing_result = self.inspector.inspect(
                    extract_dir=extract_dir,
                    sensor=sensor,
                    archive_path=path,
                    archive_sha256=val_result.sha256_hash
                )
                summary.ingestion_results.append(ing_result)
                self.logger.info(
                    f"  [OK] {sensor.value}: SHA256={val_result.sha256_hash[:12]}... "
                    f"({len(ing_result.files)} files, {len(ing_result.scientific_images)} rasters)"
                )
            except Exception as e:
                ingestion_success = False
                err_msg = f"Failed to ingest {sensor.value} archive '{path}': {str(e)}"
                summary.errors.append(err_msg)
                self.logger.error(err_msg)

        if not summary.ingestion_results or not ingestion_success:
            self.logger.stage_result(1, total_stages, "Ingestion", "FAILED", f"{len(summary.ingestion_results)} archives processed with errors")
            summary.success = False
            return summary

        self.logger.stage_result(
            1, total_stages, "Ingestion", "SUCCESS",
            f"{len(summary.ingestion_results)} archives validated, {sum(len(r.files) for r in summary.ingestion_results)} files indexed"
        )

        # =========================================================================
        # STAGE 2: METADATA EXTRACTION
        # =========================================================================
        self.logger.stage_start(2, total_stages, "Scientific Metadata Extraction")
        metadata_success = True

        for ing_result in summary.ingestion_results:
            try:
                extracted_metas = self.metadata_extractor.extract_from_ingestion(ing_result)
                summary.products_metadata.extend(extracted_metas)
                for meta in extracted_metas:
                    self.logger.info(
                        f"  [OK] [{meta.sensor}] Product: {meta.product_id} | "
                        f"Dims: {meta.width}x{meta.height}x{meta.number_of_bands} | "
                        f"GSD: {meta.spatial_resolution}m | Format: {meta.format}"
                    )
            except Exception as e:
                metadata_success = False
                err_msg = f"Error extracting metadata for {ing_result.sensor.value}: {str(e)}"
                summary.errors.append(err_msg)
                self.logger.error(err_msg)

        if not summary.products_metadata or not metadata_success:
            self.logger.stage_result(2, total_stages, "Metadata", "FAILED", "Metadata extraction encountered critical errors")
            summary.success = False
            return summary

        self.logger.stage_result(
            2, total_stages, "Metadata", "SUCCESS",
            f"{len(summary.products_metadata)} scientific products parsed (0 synthetic values)"
        )

        # Generate dataset manifest
        summary.manifest_report = self.manifest_generator.generate_manifest(
            ingestion_results=summary.ingestion_results,
            products_metadata=summary.products_metadata
        )

        # =========================================================================
        # STAGE 3: QUALITY ASSURANCE & CONTROL
        # =========================================================================
        self.logger.stage_start(3, total_stages, "Scientific Quality Control")
        has_warnings = False
        has_failures = False

        for meta in summary.products_metadata:
            try:
                q_item = self.quality_checker.evaluate(meta)
                summary.quality_items.append(q_item)

                if q_item.status == QualityStatus.FAIL:
                    has_failures = True
                    self.logger.error(f"  [FAIL] [{q_item.sensor}]: {q_item.product_id} - {'; '.join(q_item.issues)}")
                elif q_item.status == QualityStatus.WARNING:
                    has_warnings = True
                    self.logger.warning(f"  [WARN] [{q_item.sensor}]: {q_item.product_id} (Score: {q_item.quality_score:.2f}) - {'; '.join(q_item.issues)}")
                else:
                    self.logger.info(f"  [PASS] [{q_item.sensor}]: {q_item.product_id} (Score: {q_item.quality_score:.2f})")
            except Exception as e:
                has_failures = True
                err_msg = f"Error in quality check for {meta.product_id}: {str(e)}"
                summary.errors.append(err_msg)
                self.logger.error(err_msg)

        # Generate quality report
        summary.quality_report = self.quality_reporter.generate_report(summary.quality_items)

        if has_failures:
            self.logger.stage_result(3, total_stages, "Quality", "FAIL", f"{len(summary.quality_items)} products evaluated, critical failures detected")
            summary.success = False
        elif has_warnings:
            self.logger.stage_result(3, total_stages, "Quality", "WARNING", f"{len(summary.quality_items)} products evaluated, non-critical warnings noted")
        else:
            self.logger.stage_result(3, total_stages, "Quality", "SUCCESS", f"{len(summary.quality_items)} products evaluated, all passed")

        # =========================================================================
        # SUMMARY & COMPLETION
        # =========================================================================
        self.logger.header("Pipeline Foundation Complete")
        self.logger.info(f"Manifest exported: {self.reports_dir / 'dataset_manifest.json'} & .csv")
        self.logger.info(f"Quality report exported: {self.reports_dir / 'quality_report.json'} & .csv")
        self.logger.info("Pipeline stopped after Stage 3 (Foundation complete). Subsequent stages ready via interfaces.\n")

        return summary
