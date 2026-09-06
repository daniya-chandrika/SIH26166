"""
Synthetic Scenario Definitions for SIH26166.
Implements the 8 standard benchmark scenarios simulating real lunar orbital image variations.
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from prototype.synthetic.transformations import GeometricParams, RadiometricParams


@dataclass
class ScenarioDefinition:
    name: str
    description: str
    geo_params: GeometricParams
    radio_params: RadiometricParams


SCENARIOS: Dict[str, ScenarioDefinition] = {
    "illumination": ScenarioDefinition(
        name="illumination",
        description="Illumination angle shift, solar gradient variation, and dynamic range changes",
        geo_params=GeometricParams(
            rotation_deg=0.0,
            scale=1.0,
            translation_x=0.0,
            translation_y=0.0
        ),
        radio_params=RadiometricParams(
            illumination_gradient_strength=0.35,
            illumination_gradient_angle_deg=135.0,
            gamma=1.25,
            contrast_scale=0.85,
            gaussian_noise_std=0.015
        )
    ),

    "scale": ScenarioDefinition(
        name="scale",
        description="Moderate scale variation (1.25x) simulating GSD difference with translation",
        geo_params=GeometricParams(
            rotation_deg=0.0,
            scale=1.25,
            translation_x=12.0,
            translation_y=-8.0
        ),
        radio_params=RadiometricParams(
            contrast_scale=1.0,
            gaussian_noise_std=0.01
        )
    ),

    "rotation_translation": ScenarioDefinition(
        name="rotation_translation",
        description="Orbital spacecraft track rotation (25 deg) and ground track shift (dx, dy)",
        geo_params=GeometricParams(
            rotation_deg=25.0,
            scale=1.0,
            translation_x=18.0,
            translation_y=-14.0
        ),
        radio_params=RadiometricParams(
            contrast_scale=0.95,
            gaussian_noise_std=0.01
        )
    ),

    "viewpoint": ScenarioDefinition(
        name="viewpoint",
        description="Off-nadir viewpoint and perspective homography tilt",
        geo_params=GeometricParams(
            rotation_deg=8.0,
            scale=1.05,
            translation_x=10.0,
            translation_y=5.0,
            perspective_x=0.0003,
            perspective_y=0.0002
        ),
        radio_params=RadiometricParams(
            contrast_scale=0.95,
            gaussian_noise_std=0.012
        )
    ),

    "scale_illumination": ScenarioDefinition(
        name="scale_illumination",
        description="Combined scale difference (1.20x) and solar illumination angle variation",
        geo_params=GeometricParams(
            rotation_deg=0.0,
            scale=1.20,
            translation_x=15.0,
            translation_y=10.0
        ),
        radio_params=RadiometricParams(
            illumination_gradient_strength=0.30,
            illumination_gradient_angle_deg=45.0,
            gamma=1.2,
            gaussian_noise_std=0.015
        )
    ),

    "viewpoint_illumination": ScenarioDefinition(
        name="viewpoint_illumination",
        description="Off-nadir perspective tilt combined with steep solar shadowing and gamma shift",
        geo_params=GeometricParams(
            rotation_deg=12.0,
            scale=1.08,
            translation_x=-15.0,
            translation_y=12.0,
            perspective_x=-0.00025,
            perspective_y=0.0003
        ),
        radio_params=RadiometricParams(
            illumination_gradient_strength=0.40,
            illumination_gradient_angle_deg=210.0,
            gamma=1.3,
            gaussian_noise_std=0.02
        )
    ),

    "strong_scale": ScenarioDefinition(
        name="strong_scale",
        description="Strong multi-sensor GSD difference (1.45x) simulating high-to-medium resolution",
        geo_params=GeometricParams(
            rotation_deg=10.0,
            scale=1.45,
            translation_x=-20.0,
            translation_y=15.0
        ),
        radio_params=RadiometricParams(
            contrast_scale=0.9,
            gaussian_noise_std=0.015,
            blur_sigma=0.5
        )
    ),

    "combined": ScenarioDefinition(
        name="combined",
        description="Full challenge: rotation (18 deg), scale (1.18x), perspective tilt, illumination gradient, noise, and mild blur",
        geo_params=GeometricParams(
            rotation_deg=18.0,
            scale=1.18,
            translation_x=16.0,
            translation_y=-12.0,
            shear_x=0.02,
            perspective_x=0.0002,
            perspective_y=-0.00015
        ),
        radio_params=RadiometricParams(
            illumination_gradient_strength=0.30,
            illumination_gradient_angle_deg=120.0,
            gamma=1.15,
            contrast_scale=0.92,
            gaussian_noise_std=0.018,
            blur_sigma=0.6
        )
    ),
}


class SyntheticScenarioManager:
    """
    Manages access and parameterization of synthetic benchmark scenarios.
    """

    @staticmethod
    def get_scenario(name: str) -> ScenarioDefinition:
        clean_name = name.lower().strip()
        if clean_name not in SCENARIOS:
            available = ", ".join(SCENARIOS.keys())
            raise ValueError(f"Unknown scenario '{name}'. Available scenarios: {available}")
        return SCENARIOS[clean_name]

    @staticmethod
    def list_scenarios() -> Dict[str, str]:
        return {k: v.description for k, v in SCENARIOS.items()}
