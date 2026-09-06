"""
Unified Scientific Metadata Extraction Engine.
Coordinates PDS4, PDS3, GeoTIFF, and ENVI parsers to generate standardized lunar metadata.
"""
from pathlib import Path
from typing import List, Optional, Dict, Any

from ingestion.models import IngestionResult, ExtractedFileInfo, FileCategory, SensorType
from metadata.models import LunarProductMetadata
from metadata.parsers.pds4_parser import PDS4Parser
from metadata.parsers.pds3_parser import PDS3Parser
from metadata.parsers.geotiff_parser import GeoTIFFParser
from metadata.parsers.envi_parser import ENVIParser


class MetadataExtractor:
    """
    Extracts and merges metadata from scientific image files and their accompanying labels.
    """

    def __init__(self):
        self.pds4_parser = PDS4Parser()
        self.pds3_parser = PDS3Parser()
        self.geotiff_parser = GeoTIFFParser()
        self.envi_parser = ENVIParser()

    def extract_from_ingestion(self, ingestion_result: IngestionResult) -> List[LunarProductMetadata]:
        """
        Extract metadata records for all scientific products discovered in an ingestion result.
        """
        products: List[LunarProductMetadata] = []
        scientific_images = ingestion_result.scientific_images
        metadata_files = ingestion_result.metadata_files

        # Group metadata files by stem (list per stem to allow both .hdr and .xml)
        meta_by_stem: Dict[str, List[ExtractedFileInfo]] = {}
        for m in metadata_files:
            stem = Path(m.filename).stem.lower()
            meta_by_stem.setdefault(stem, []).append(m)

        # If there are scientific images, extract for each image
        if scientific_images:
            for sci_img in scientific_images:
                img_path = Path(sci_img.absolute_path)
                stem_lower = img_path.stem.lower()

                # Base metadata from raster
                if img_path.suffix.lower() in [".tif", ".tiff"]:
                    meta = self.geotiff_parser.parse(img_path)
                else:
                    meta = LunarProductMetadata(
                        image_id=img_path.stem,
                        product_id=img_path.stem,
                        filename=img_path.name,
                        file_path=str(img_path),
                        format=img_path.suffix.upper().replace(".", "")
                    )
                meta.file_path = str(img_path)
                meta.filename = img_path.name

                # Look for matching metadata labels
                matching_labels = meta_by_stem.get(stem_lower, [])
                if not matching_labels and metadata_files:
                    matching_labels = metadata_files

                # Parse and merge all associated labels
                for label_info in matching_labels:
                    label_path = Path(label_info.absolute_path)
                    label_meta = self._parse_label(label_path)
                    self._merge_metadata(meta, label_meta)

                # Ensure sensor tag from user ingestion is authoritative
                meta.sensor = ingestion_result.sensor.value
                if not meta.mission:
                    meta.mission = "Chandrayaan-2" if meta.sensor in ["OHRC", "TMC-2", "IIRS"] else "LRO"

                products.append(meta)

        # If no scientific image files found directly but metadata labels exist
        elif metadata_files:
            for meta_file in metadata_files:
                label_path = Path(meta_file.absolute_path)
                meta = self._parse_label(label_path)
                meta.sensor = ingestion_result.sensor.value
                if not meta.mission:
                    meta.mission = "Chandrayaan-2" if meta.sensor in ["OHRC", "TMC-2", "IIRS"] else "LRO"
                products.append(meta)

        return products

    def _parse_label(self, label_path: Path) -> LunarProductMetadata:
        ext = label_path.suffix.lower()
        if ext == ".xml":
            return self.pds4_parser.parse(label_path)
        elif ext in [".lbl", ".pds"]:
            return self.pds3_parser.parse(label_path)
        elif ext == ".hdr":
            return self.envi_parser.parse(label_path)
        else:
            return LunarProductMetadata(
                source_label_file=str(label_path),
                format=ext.upper().replace(".", "")
            )

    def _merge_metadata(self, primary: LunarProductMetadata, supplementary: LunarProductMetadata) -> None:
        """
        Merge supplementary label metadata into primary raster metadata.
        Authoritative label metadata takes precedence for geodetic coordinates, temporal parameters, and angles.
        """
        if supplementary.product_id and (not primary.product_id or primary.product_id == primary.image_id):
            primary.product_id = supplementary.product_id
        if supplementary.product_level:
            primary.product_level = supplementary.product_level
        if supplementary.mission:
            primary.mission = supplementary.mission

        # Temporal
        if supplementary.acquisition_date:
            primary.acquisition_date = supplementary.acquisition_date
        if supplementary.acquisition_time:
            primary.acquisition_time = supplementary.acquisition_time
        if supplementary.start_time_utc:
            primary.start_time_utc = supplementary.start_time_utc
        if supplementary.stop_time_utc:
            primary.stop_time_utc = supplementary.stop_time_utc

        # Geometry & Resolution
        if supplementary.spatial_resolution is not None and primary.spatial_resolution is None:
            primary.spatial_resolution = supplementary.spatial_resolution
        if supplementary.width is not None and primary.width is None:
            primary.width = supplementary.width
        if supplementary.height is not None and primary.height is None:
            primary.height = supplementary.height
        if supplementary.bit_depth is not None and primary.bit_depth is None:
            primary.bit_depth = supplementary.bit_depth
        if supplementary.number_of_bands is not None and (primary.number_of_bands is None or primary.number_of_bands == 1):
            if supplementary.number_of_bands > 1:
                primary.number_of_bands = supplementary.number_of_bands

        # Coordinates (Ground-truth geodetic coordinates from PDS labels)
        if supplementary.latitude is not None:
            primary.latitude = supplementary.latitude
        if supplementary.longitude is not None:
            primary.longitude = supplementary.longitude
        if supplementary.bounding_box is not None:
            primary.bounding_box = supplementary.bounding_box
        if supplementary.footprint is not None:
            primary.footprint = supplementary.footprint
            primary.footprint_geojson = supplementary.footprint_geojson

        # Photometric Angles
        if supplementary.sun_elevation is not None:
            primary.sun_elevation = supplementary.sun_elevation
        if supplementary.sun_azimuth is not None:
            primary.sun_azimuth = supplementary.sun_azimuth
        if supplementary.incidence_angle is not None:
            primary.incidence_angle = supplementary.incidence_angle
        if supplementary.emission_angle is not None:
            primary.emission_angle = supplementary.emission_angle
        if supplementary.phase_angle is not None:
            primary.phase_angle = supplementary.phase_angle
        if supplementary.look_angle is not None:
            primary.look_angle = supplementary.look_angle

        # Georeferencing
        if supplementary.projection and not primary.projection:
            primary.projection = supplementary.projection
        if supplementary.crs and not primary.crs:
            primary.crs = supplementary.crs
        if supplementary.datum and not primary.datum:
            primary.datum = supplementary.datum

        if not primary.source_label_file:
            primary.source_label_file = supplementary.source_label_file
        else:
            primary.source_label_file += f", {supplementary.source_label_file}"
