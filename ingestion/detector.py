"""
Automatic sensor and format detector for lunar orbital products.
Analyzes filenames, archive structures, XML/PDS labels, ENVI headers, and GeoTIFF tags
to identify sensor modalities: OHRC, TMC-2, IIRS, and LROC NAC.
"""
import re
from pathlib import Path
from typing import Optional, Tuple, Dict, Any, List
from ingestion.models import SensorType


class LunarSensorDetector:
    """
    Intelligent rule-based and label-parsing detector for lunar imagery.
    """

    # Keyword patterns in filenames and paths
    SENSOR_PATTERNS = {
        SensorType.OHRC: [
            r"ch2_ohr", r"ch2.*ohrc", r"ohrc", r"_ohr_", r"ohr_ncp", r"ohr_raw"
        ],
        SensorType.TMC_2: [
            r"ch2_tmc", r"ch2.*tmc2", r"tmc-2", r"tmc2", r"_tmc_", r"tmc_anc", r"tmc_raw"
        ],
        SensorType.IIRS: [
            r"ch2_iir", r"ch2.*iirs", r"iirs", r"_iir_", r"iir_raw", r"iir_spc"
        ],
        SensorType.LROC: [
            r"nac_lro", r"lroc", r"lro.*nac", r"lro.*wac", r"m1[0-9]{8}[re]k?", r"m[0-9]{9}[re]"
        ]
    }

    # Label text patterns
    LABEL_PATTERNS = {
        SensorType.OHRC: [
            r"ORBITER\s+HIGH\s+RESOLUTION\s+CAMERA",
            r"INSTRUMENT_NAME\s*=\s*\"?OHRC\"?",
            r"INSTRUMENT_ID\s*=\s*\"?OHRC\"?",
            r"<instrument_id>OHRC</instrument_id>",
            r"<instrument_name>.*OHRC.*</instrument_name>"
        ],
        SensorType.TMC_2: [
            r"TERRAIN\s+MAPPING\s+CAMERA",
            r"INSTRUMENT_NAME\s*=\s*\"?TMC-?2?\"?",
            r"INSTRUMENT_ID\s*=\s*\"?TMC-?2?\"?",
            r"<instrument_id>TMC-?2?</instrument_id>",
            r"<instrument_name>.*Terrain\s+Mapping.*</instrument_name>"
        ],
        SensorType.IIRS: [
            r"IMAGING\s+INFRARED\s+SPECTROMETER",
            r"INSTRUMENT_NAME\s*=\s*\"?IIRS\"?",
            r"INSTRUMENT_ID\s*=\s*\"?IIRS\"?",
            r"<instrument_id>IIRS</instrument_id>",
            r"<instrument_name>.*Imaging\s+Infrared.*</instrument_name>"
        ],
        SensorType.LROC: [
            r"LUNAR\s+RECONNAISSANCE\s+ORBITER\s+CAMERA",
            r"INSTRUMENT_NAME\s*=\s*\"?LROC\"?",
            r"INSTRUMENT_ID\s*=\s*\"?LROC\"?",
            r"INSTRUMENT_ID\s*=\s*\"?NACL?R?\"?",
            r"<instrument_id>LROC.*</instrument_id>",
            r"<instrument_name>.*Lunar\s+Reconnaissance\s+Orbiter\s+Camera.*</instrument_name>"
        ]
    }

    @classmethod
    def detect_from_filename(cls, filename: str) -> Optional[Tuple[SensorType, float]]:
        """
        Detect sensor from file or archive name.
        Returns: (SensorType, confidence [0.0 - 1.0]) or None
        """
        clean_name = Path(filename).name.lower()
        for sensor, patterns in cls.SENSOR_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, clean_name):
                    return sensor, 0.85
        return None

    @classmethod
    def detect_from_label_content(cls, content: str) -> Optional[Tuple[SensorType, float]]:
        """
        Detect sensor by scanning text content of PDS3 LBL, PDS4 XML, or ENVI HDR.
        Returns: (SensorType, confidence [0.0 - 1.0]) or None
        """
        for sensor, patterns in cls.LABEL_PATTERNS.items():
            for pat in patterns:
                if re.search(pat, content, re.IGNORECASE):
                    return sensor, 0.99
        return None

    @classmethod
    def detect_sensor(
        cls,
        file_path_or_name: str | Path,
        label_content: Optional[str] = None,
        extracted_files: Optional[List[str | Path]] = None
    ) -> Tuple[SensorType, float, str]:
        """
        Comprehensive multi-stage sensor detection.
        Returns: (SensorType, confidence, detection_reason)
        """
        # 1. Inspect label content if provided
        if label_content:
            res = cls.detect_from_label_content(label_content)
            if res:
                sensor, conf = res
                return sensor, conf, f"Detected from metadata label tag matching '{sensor.value}'"

        # 2. Inspect extracted files list
        if extracted_files:
            for f in extracted_files:
                p = Path(f)
                res = cls.detect_from_filename(p.name)
                if res:
                    sensor, conf = res
                    return sensor, conf, f"Detected from member file name: '{p.name}'"

                # Check if it's a label file
                if p.suffix.lower() in [".xml", ".lbl", ".pds", ".hdr"] and p.is_file():
                    try:
                        text = p.read_text(encoding="utf-8", errors="ignore")[:50000]
                        label_res = cls.detect_from_label_content(text)
                        if label_res:
                            sensor, conf = label_res
                            return sensor, conf, f"Detected from label file '{p.name}'"
                    except Exception:
                        pass

        # 3. Inspect main filename
        name_res = cls.detect_from_filename(str(file_path_or_name))
        if name_res:
            sensor, conf = name_res
            return sensor, conf, f"Detected from primary product filename: '{Path(file_path_or_name).name}'"

        # 4. Fallback: Check if file itself exists and can be read as a label
        p_main = Path(file_path_or_name)
        if p_main.is_file() and p_main.suffix.lower() in [".xml", ".lbl", ".pds", ".hdr", ".txt"]:
            try:
                text = p_main.read_text(encoding="utf-8", errors="ignore")[:50000]
                label_res = cls.detect_from_label_content(text)
                if label_res:
                    sensor, conf = label_res
                    return sensor, conf, f"Detected from label content in '{p_main.name}'"
            except Exception:
                pass

        # Default fallback
        return SensorType.OHRC, 0.50, "Default fallback to OHRC (Auto-detect inconclusive)"
