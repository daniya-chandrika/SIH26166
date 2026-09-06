"""
Synthetic Dataset Generator for SIH26166.
Produces standard ImagePair instances with procedural terrain and ground-truth transformations.
"""
from typing import Optional, Dict, Any
import numpy as np

from prototype.data_interface import ImagePair
from prototype.synthetic.generator import SyntheticTerrainGenerator
from prototype.synthetic.transformations import TransformationEngine
from prototype.synthetic.scenarios import SyntheticScenarioManager, ScenarioDefinition


class SyntheticDatasetGenerator:
    """
    Generates deterministic, parameterized synthetic lunar image pairs for registration benchmarking.
    """

    def __init__(self, default_seed: int = 42):
        self.default_seed = default_seed

    def generate_pair(
        self,
        scenario_name: str = "combined",
        width: int = 512,
        height: int = 512,
        seed: Optional[int] = None,
        dtype=np.float32
    ) -> ImagePair:
        """
        Generate paired reference and source images according to the designated scenario.
        """
        active_seed = seed if seed is not None else self.default_seed

        # 1. Retrieve Scenario
        scenario = SyntheticScenarioManager.get_scenario(scenario_name)

        # 2. Procedural Reference Terrain Generation
        terrain_gen = SyntheticTerrainGenerator(seed=active_seed)
        ref_image = terrain_gen.generate(
            width=width,
            height=height,
            sun_azimuth_deg=45.0,
            sun_elevation_deg=30.0,
            dtype=dtype
        )

        # 3. Apply Paired Transformations
        engine = TransformationEngine(seed=active_seed + 100)
        source_image, H_gt = engine.transform(
            reference_image=ref_image,
            geo_params=scenario.geo_params,
            radio_params=scenario.radio_params
        )

        # 4. Package Metadata
        metadata: Dict[str, Any] = {
            "dataset_type": "SYNTHETIC_PROCEDURAL",
            "scenario": scenario.name,
            "scenario_description": scenario.description,
            "seed": active_seed,
            "width": width,
            "height": height,
            "simulated_sensor_gsd_m": 1.0,
            "is_synthetic_benchmark": True,
            "sun_azimuth_deg": 45.0,
            "sun_elevation_deg": 30.0,
        }

        ground_truth_details: Dict[str, Any] = {
            "rotation_deg": scenario.geo_params.rotation_deg,
            "scale": scenario.geo_params.scale,
            "translation_x": scenario.geo_params.translation_x,
            "translation_y": scenario.geo_params.translation_y,
            "shear_x": scenario.geo_params.shear_x,
            "shear_y": scenario.geo_params.shear_y,
            "perspective_x": scenario.geo_params.perspective_x,
            "perspective_y": scenario.geo_params.perspective_y,
            "illumination_gradient_strength": scenario.radio_params.illumination_gradient_strength,
            "gaussian_noise_std": scenario.radio_params.gaussian_noise_std,
            "blur_sigma": scenario.radio_params.blur_sigma,
        }

        return ImagePair(
            reference=ref_image,
            source=source_image,
            metadata=metadata,
            ground_truth_transform=H_gt,
            ground_truth_details=ground_truth_details,
            scenario_name=scenario.name,
            seed=active_seed,
            name=f"synthetic_{scenario.name}_seed{active_seed}"
        )
