"""
Synthetic Dataset Engine for SIH26166.
Generates procedural lunar terrain patterns with ground-truth transformations.
"""
from prototype.synthetic.generator import SyntheticTerrainGenerator
from prototype.synthetic.transformations import TransformationEngine
from prototype.synthetic.scenarios import SyntheticScenarioManager, SCENARIOS
from prototype.synthetic.ground_truth import GroundTruthTransform
from prototype.synthetic.dataset import SyntheticDatasetGenerator

__all__ = [
    "SyntheticTerrainGenerator",
    "TransformationEngine",
    "SyntheticScenarioManager",
    "SCENARIOS",
    "GroundTruthTransform",
    "SyntheticDatasetGenerator",
]
