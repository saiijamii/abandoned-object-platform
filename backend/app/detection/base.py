from abc import ABC, abstractmethod
from typing import Any

from .types import Detection


class Detector(ABC):
    @abstractmethod
    def detect(self, frame: Any) -> list[Detection]:
        """Return normalized detections for one image."""
