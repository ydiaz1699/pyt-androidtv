"""Base TV module - shared logic for Android TV and Fire TV."""

from .base import BaseTV
from .state import StateDetectionEngine

__all__ = ["BaseTV", "StateDetectionEngine"]
