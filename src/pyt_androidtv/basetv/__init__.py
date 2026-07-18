"""Módulo Base TV - lógica compartida para Android TV y Fire TV."""

from .base import BaseTV
from .state import StateDetectionEngine

__all__ = ["BaseTV", "StateDetectionEngine"]
