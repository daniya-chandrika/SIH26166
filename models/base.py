"""
Deep Learning Model Interfaces.
[Placeholder for future SuperPoint, LightGlue, and LoFTR neural network backends]
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class LunarRegistrationModelBase(ABC):
    """
    Abstract base class for neural registration architectures.
    """

    @abstractmethod
    def load_weights(self, checkpoint_path: str) -> None:
        """Load trained neural model weights."""
        pass

    @abstractmethod
    def forward(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """Perform neural inference pass."""
        pass
