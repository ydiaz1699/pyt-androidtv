"""pyt-androidtv: Modern Python library for Android TV / Fire TV control via ADB."""

from __future__ import annotations

from .androidtv.androidtv import AndroidTV
from .exceptions import (
    ADBConnectionError,
    DeviceNotAvailableError,
    LockNotAcquiredError,
    PytAndroidTVError,
)
from .firetv.firetv import FireTV
from .models import DeviceInfo, DeviceState

__version__ = "1.0.0"
__all__ = [
    "AndroidTV",
    "FireTV",
    "DeviceInfo",
    "DeviceState",
    "PytAndroidTVError",
    "ADBConnectionError",
    "DeviceNotAvailableError",
    "LockNotAcquiredError",
]
