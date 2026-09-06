"""
Geometric Transformation Model Definitions for SIH26166.
"""
from enum import Enum


class GeometricModelType(str, Enum):
    AFFINE = "AFFINE"
    HOMOGRAPHY = "HOMOGRAPHY"
    RIGID = "RIGID"

    @classmethod
    def from_string(cls, name: str) -> "GeometricModelType":
        clean = name.upper().strip()
        if clean in ["AFFINE", "AFF"]:
            return cls.AFFINE
        elif clean in ["HOMOGRAPHY", "HOMO", "PERSPECTIVE"]:
            return cls.HOMOGRAPHY
        elif clean in ["RIGID", "EUCLIDEAN"]:
            return cls.RIGID
        else:
            raise ValueError(f"Unsupported geometric model '{name}'. Choose AFFINE or HOMOGRAPHY.")
