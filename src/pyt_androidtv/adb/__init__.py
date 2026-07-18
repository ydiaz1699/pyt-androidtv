"""Módulo de gestión de conexiones ADB."""

from .base import ADBInterface
from .tcp import ADBConnection

__all__ = ["ADBInterface", "ADBConnection"]
