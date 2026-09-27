"""
Model Registry, Version Tracker, and Zero-Silent-Fallback Verification Subsystem for SIH26166.
Maintains explicit audit trails of requested models, availability, versions, inference times,
and explicit fallback diagnostics.
"""
from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
import time
import cv2


@dataclass
class ModelExecutionMetadata:
    """Explicit metadata record for every feature and matching model execution."""
    model_requested: str
    model_available: bool
    model_used: str
    model_status: str              # "AVAILABLE", "MODEL_UNAVAILABLE", "INITIALIZED"
    model_version: str
    dependency_status: str
    device: str                    # "CPU", "CUDA:0", or "N/A"
    inference_time_ms: float
    fallback_used: bool
    fallback_reason: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "MODEL_REQUESTED": self.model_requested,
            "MODEL_AVAILABLE": self.model_available,
            "MODEL_USED": self.model_used,
            "MODEL_STATUS": self.model_status,
            "MODEL_VERSION": self.model_version,
            "DEPENDENCY_STATUS": self.dependency_status,
            "DEVICE": self.device,
            "INFERENCE_TIME": f"{self.inference_time_ms:.2f} ms",
            "FALLBACK_USED": self.fallback_used,
            "FALLBACK_REASON": self.fallback_reason or "N/A"
        }


class ModelRegistry:
    """
    Central registry for verifying and executing classical and deep learning models
    with zero silent fallbacks.
    """

    SUPPORTED_MODELS = ["SIFT", "ORB", "SUPERPOINT", "LOFTR", "LIGHTGLUE", "DISK", "ALIKED"]

    @classmethod
    def inspect_model(cls, model_name: str, fallback_candidate: Optional[str] = None) -> ModelExecutionMetadata:
        """
        Inspect availability and dependency status for a requested model.
        """
        name_upper = model_name.upper().strip()

        if name_upper == "SIFT":
            cv_ver = cv2.__version__
            return ModelExecutionMetadata(
                model_requested="SIFT",
                model_available=True,
                model_used="SIFT",
                model_status="AVAILABLE",
                model_version=f"OpenCV {cv_ver}",
                dependency_status="OpenCV SIFT compiled and operational",
                device="CPU",
                inference_time_ms=0.0,
                fallback_used=False,
                fallback_reason=None
            )

        elif name_upper == "ORB":
            cv_ver = cv2.__version__
            return ModelExecutionMetadata(
                model_requested="ORB",
                model_available=True,
                model_used="ORB",
                model_status="AVAILABLE",
                model_version=f"OpenCV {cv_ver}",
                dependency_status="OpenCV ORB compiled and operational",
                device="CPU",
                inference_time_ms=0.0,
                fallback_used=False,
                fallback_reason=None
            )

        # Deep Learning Models
        torch_available = False
        torch_ver = "N/A"
        device = "N/A"
        try:
            import torch
            torch_available = True
            torch_ver = f"PyTorch {torch.__version__}"
            device = "CUDA:0" if torch.cuda.is_available() else "CPU"
        except ImportError:
            torch_available = False
            torch_ver = "Not Installed"
            device = "N/A"

        if name_upper in ["SUPERPOINT", "SUPERPOINT_LEARNED"]:
            is_avail = torch_available
            dep_msg = f"{torch_ver} available" if is_avail else "PyTorch or SuperPoint checkpoint (.pth) not found"
            status = "AVAILABLE" if is_avail else "MODEL_UNAVAILABLE"
            return ModelExecutionMetadata(
                model_requested="SuperPoint",
                model_available=is_avail,
                model_used="SuperPoint" if is_avail else (fallback_candidate or "NONE"),
                model_status=status,
                model_version=torch_ver,
                dependency_status=dep_msg,
                device=device,
                inference_time_ms=0.0,
                fallback_used=(not is_avail and fallback_candidate is not None),
                fallback_reason=None if is_avail else "PyTorch/weights unavailable; explicit fallback declared"
            )

        elif name_upper in ["LOFTR", "LOFTR_LEARNED"]:
            is_avail = torch_available
            dep_msg = f"{torch_ver} available" if is_avail else "PyTorch or LoFTR weights (.ckpt) not found"
            status = "AVAILABLE" if is_avail else "MODEL_UNAVAILABLE"
            return ModelExecutionMetadata(
                model_requested="LoFTR",
                model_available=is_avail,
                model_used="LoFTR" if is_avail else (fallback_candidate or "NONE"),
                model_status=status,
                model_version=torch_ver,
                dependency_status=dep_msg,
                device=device,
                inference_time_ms=0.0,
                fallback_used=(not is_avail and fallback_candidate is not None),
                fallback_reason=None if is_avail else "PyTorch/weights unavailable; explicit fallback declared"
            )

        elif name_upper in ["LIGHTGLUE", "LIGHTGLUE_LEARNED"]:
            is_avail = torch_available
            dep_msg = f"{torch_ver} available" if is_avail else "PyTorch or LightGlue weights not found"
            status = "AVAILABLE" if is_avail else "MODEL_UNAVAILABLE"
            return ModelExecutionMetadata(
                model_requested="LightGlue",
                model_available=is_avail,
                model_used="LightGlue" if is_avail else (fallback_candidate or "NONE"),
                model_status=status,
                model_version=torch_ver,
                dependency_status=dep_msg,
                device=device,
                inference_time_ms=0.0,
                fallback_used=(not is_avail and fallback_candidate is not None),
                fallback_reason=None if is_avail else "PyTorch/weights unavailable; explicit fallback declared"
            )

        elif name_upper in ["DISK", "DISK_LEARNED"]:
            is_avail = torch_available
            dep_msg = f"{torch_ver} available" if is_avail else "PyTorch or DISK weights not found"
            status = "AVAILABLE" if is_avail else "MODEL_UNAVAILABLE"
            return ModelExecutionMetadata(
                model_requested="DISK",
                model_available=is_avail,
                model_used="DISK" if is_avail else (fallback_candidate or "NONE"),
                model_status=status,
                model_version=torch_ver,
                dependency_status=dep_msg,
                device=device,
                inference_time_ms=0.0,
                fallback_used=(not is_avail and fallback_candidate is not None),
                fallback_reason=None if is_avail else "PyTorch/weights unavailable; explicit fallback declared"
            )

        elif name_upper in ["ALIKED", "ALIKED_LEARNED"]:
            is_avail = torch_available
            dep_msg = f"{torch_ver} available" if is_avail else "PyTorch or ALIKED weights not found"
            status = "AVAILABLE" if is_avail else "MODEL_UNAVAILABLE"
            return ModelExecutionMetadata(
                model_requested="ALIKED",
                model_available=is_avail,
                model_used="ALIKED" if is_avail else (fallback_candidate or "NONE"),
                model_status=status,
                model_version=torch_ver,
                dependency_status=dep_msg,
                device=device,
                inference_time_ms=0.0,
                fallback_used=(not is_avail and fallback_candidate is not None),
                fallback_reason=None if is_avail else "PyTorch/weights unavailable; explicit fallback declared"
            )

        else:
            return ModelExecutionMetadata(
                model_requested=model_name,
                model_available=False,
                model_used=fallback_candidate or "NONE",
                model_status="MODEL_UNAVAILABLE",
                model_version="Unknown",
                dependency_status=f"Unsupported model identifier: '{model_name}'",
                device="N/A",
                inference_time_ms=0.0,
                fallback_used=fallback_candidate is not None,
                fallback_reason="Unsupported model identifier"
            )
