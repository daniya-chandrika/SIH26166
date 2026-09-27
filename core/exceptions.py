"""
Core System Exceptions and Status Enums for SIH26166.
Enforces strict failure detection and zero-silent-fallback policies (Section 23, Section 45).
"""
from enum import Enum
from typing import Optional, Dict, Any


class RegistrationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    INSUFFICIENT_MATCHES = "INSUFFICIENT_MATCHES"
    POOR_SPATIAL_COVERAGE = "POOR_SPATIAL_COVERAGE"
    HIGH_REPROJECTION_ERROR = "HIGH_REPROJECTION_ERROR"
    NO_GEOGRAPHIC_OVERLAP = "NO_GEOGRAPHIC_OVERLAP"
    LOW_IMAGE_QUALITY = "LOW_IMAGE_QUALITY"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    PROCESSING_ERROR = "PROCESSING_ERROR"
    REGISTRATION_FAILED = "REGISTRATION_FAILED"


class LunarRegistrationError(Exception):
    """Base exception for lunar image registration pipeline."""
    def __init__(self, message: str, status: RegistrationStatus = RegistrationStatus.PROCESSING_ERROR, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.details = details or {}


class ModelUnavailableError(LunarRegistrationError):
    """Raised when a requested learned or specialized model is unavailable, without silent fallback."""
    def __init__(self, model_name: str, missing_dependency: str, details: Optional[Dict[str, Any]] = None):
        msg = f"Requested registration model '{model_name}' is unavailable. Missing dependency or weights: {missing_dependency}"
        super().__init__(msg, status=RegistrationStatus.MODEL_UNAVAILABLE, details=details)
        self.model_name = model_name
        self.missing_dependency = missing_dependency


class InsufficientMatchesError(LunarRegistrationError):
    def __init__(self, match_count: int, required_count: int = 4, details: Optional[Dict[str, Any]] = None):
        msg = f"Insufficient keypoint correspondences found ({match_count} found, minimum {required_count} required)."
        super().__init__(msg, status=RegistrationStatus.INSUFFICIENT_MATCHES, details=details)


class GeographicOverlapError(LunarRegistrationError):
    def __init__(self, overlap_pct: float, threshold_pct: float = 15.0, details: Optional[Dict[str, Any]] = None):
        msg = f"Geographic overlap {overlap_pct:.2f}% is below the required threshold of {threshold_pct:.2f}%."
        super().__init__(msg, status=RegistrationStatus.NO_GEOGRAPHIC_OVERLAP, details=details)


class SpatialDistributionError(LunarRegistrationError):
    def __init__(self, coverage_pct: float, min_coverage_pct: float = 20.0, details: Optional[Dict[str, Any]] = None):
        msg = f"Keypoint spatial coverage {coverage_pct:.1f}% is critically clustered below threshold {min_coverage_pct:.1f}%."
        super().__init__(msg, status=RegistrationStatus.POOR_SPATIAL_COVERAGE, details=details)


class LowImageQualityError(LunarRegistrationError):
    def __init__(self, quality_score: float, reason: str, details: Optional[Dict[str, Any]] = None):
        msg = f"Image quality score ({quality_score:.2f}) failed QA criteria: {reason}"
        super().__init__(msg, status=RegistrationStatus.LOW_IMAGE_QUALITY, details=details)
