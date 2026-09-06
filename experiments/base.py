"""
Experiment Tracking Interface.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional


class ExperimentTrackerBase(ABC):
    """
    Abstract interface for experiment tracking and benchmark runs.
    """

    @abstractmethod
    def start_run(self, experiment_name: str, config: Dict[str, Any]) -> str:
        """Start a new experiment run and return run_id."""
        pass

    @abstractmethod
    def log_metrics(self, run_id: str, metrics: Dict[str, float]) -> None:
        """Log quantitative evaluation metrics for run."""
        pass

    @abstractmethod
    def end_run(self, run_id: str, status: str = "COMPLETED") -> None:
        """Mark run as completed."""
        pass
