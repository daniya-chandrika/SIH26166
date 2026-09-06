"""
Sensor Configuration and Specification Profiles for SIH26166.
Maintains authentic mission parameters for Chandrayaan-2 and LRO instruments.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class SensorConfig:
    name: str
    mission: str
    agency: str
    sensor_type: str
    nominal_gsd_m: float
    gsd_range_m: List[float]
    nominal_bands: int
    bit_depth: int
    metadata_standard: str
    description: str


SENSOR_PROFILES: Dict[str, SensorConfig] = {
    "OHRC": SensorConfig(
        name="OHRC",
        mission="Chandrayaan-2",
        agency="ISRO",
        sensor_type="Optical Panchromatic",
        nominal_gsd_m=0.25,
        gsd_range_m=[0.25, 0.32],
        nominal_bands=1,
        bit_depth=12,
        metadata_standard="PDS4",
        description="Orbital High Resolution Camera providing sub-meter lunar surface imagery from 100km orbit."
    ),
    "TMC-2": SensorConfig(
        name="TMC-2",
        mission="Chandrayaan-2",
        agency="ISRO",
        sensor_type="Stereo Triplet Panchromatic",
        nominal_gsd_m=5.0,
        gsd_range_m=[5.0, 5.0],
        nominal_bands=1,
        bit_depth=10,
        metadata_standard="PDS4",
        description="Terrain Mapping Camera-2 stereo triplets for high-resolution 3D DEMs and orthomosaics."
    ),
    "IIRS": SensorConfig(
        name="IIRS",
        mission="Chandrayaan-2",
        agency="ISRO",
        sensor_type="Hyperspectral Spectrometer",
        nominal_gsd_m=80.0,
        gsd_range_m=[80.0, 100.0],
        nominal_bands=256,
        bit_depth=14,
        metadata_standard="PDS4",
        description="Imaging Infrared Spectrometer for 0.8-5.0um mineralogical mapping and water/hydroxyl absorption."
    ),
    "LROC": SensorConfig(
        name="LROC",
        mission="Lunar Reconnaissance Orbiter",
        agency="NASA",
        sensor_type="Optical Narrow Angle Camera",
        nominal_gsd_m=0.50,
        gsd_range_m=[0.50, 2.0],
        nominal_bands=1,
        bit_depth=12,
        metadata_standard="PDS3/PDS4",
        description="Lunar Reconnaissance Orbiter Camera (NAC) high-resolution reference imagery and DTMs."
    )
}


def get_sensor_config(sensor_name: str) -> SensorConfig:
    """Retrieve verified sensor profile."""
    clean_name = sensor_name.upper().strip()
    if clean_name not in SENSOR_PROFILES:
        raise ValueError(f"Unknown sensor '{sensor_name}'. Supported sensors: {list(SENSOR_PROFILES.keys())}")
    return SENSOR_PROFILES[clean_name]
