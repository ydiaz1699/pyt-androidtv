"""Módulo de diagnósticos del dispositivo.

Inspirado en AndroidForensics (https://github.com/DouglasFreshHabian/AndroidForensics).
"""

from .system import SystemDiagnostics
from .network import NetworkDiagnostics
from .apps import AppDiagnostics
from .report import DeviceDiagnostics, DiagnosticReport

__all__ = [
    "DeviceDiagnostics",
    "DiagnosticReport",
    "SystemDiagnostics",
    "NetworkDiagnostics",
    "AppDiagnostics",
]
