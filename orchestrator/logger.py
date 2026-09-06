"""
Scientific Pipeline Logger with formatted stage progress output.
Compatible with standard ASCII and all Windows console code pages.
"""
import logging
import sys
from typing import Optional


class PipelineLogger:
    """
    Formatted terminal logger for lunar pipeline execution.
    """

    def __init__(self, name: str = "LunarPipeline"):
        self.logger = logging.getLogger(name)
        if not self.logger.handlers:
            self.logger.setLevel(logging.INFO)
            handler = logging.StreamHandler(sys.stdout)
            formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)

    def header(self, title: str) -> None:
        print("\n" + "=" * 70)
        print(f" {title.upper()}")
        print("=" * 70)

    def stage_start(self, step: int, total_steps: int, stage_name: str) -> None:
        print(f"\n[{step}/{total_steps}] {stage_name.upper()} Starting...")

    def stage_result(self, step: int, total_steps: int, stage_name: str, status: str, details: str = "") -> None:
        dots = "." * max(2, (24 - len(stage_name)))
        status_formatted = status.upper()
        msg = f"[{step}/{total_steps}] {stage_name} {dots} {status_formatted}"
        if details:
            msg += f" ({details})"
        print(msg)

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def warning(self, msg: str) -> None:
        self.logger.warning(msg)

    def error(self, msg: str) -> None:
        self.logger.error(msg)
