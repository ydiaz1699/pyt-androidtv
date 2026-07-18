"""Data models for pyt-androidtv using dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, StrEnum


class DeviceType(IntEnum):
    """Device type enumeration."""

    UNKNOWN = 0
    ANDROID_TV = 1
    FIRE_TV = 2


class State(StrEnum):
    """Device state enumeration."""

    IDLE = "idle"
    OFF = "off"
    PLAYING = "playing"
    PAUSED = "paused"
    STANDBY = "standby"
    STOPPED = "stopped"
    UNAVAILABLE = "unavailable"


class AudioState(StrEnum):
    """Audio playback state."""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass(frozen=True, slots=True)
class DeviceInfo:
    """Immutable device information."""

    manufacturer: str = ""
    model: str = ""
    serial_number: str | None = None
    sw_version: str = ""
    product_id: str = ""
    mac_wifi: str | None = None
    mac_ethernet: str | None = None

    @property
    def android_version(self) -> int | None:
        """Parse the Android version as an integer, or None if not determinable."""
        try:
            return int(self.sw_version.split(".")[0])
        except (ValueError, IndexError):
            return None

    @property
    def is_android_11_plus(self) -> bool:
        """Whether this device runs Android 11 or higher."""
        ver = self.android_version
        return ver is not None and ver >= 11


@dataclass(slots=True)
class DeviceState:
    """Current state of the device."""

    state: State = State.UNAVAILABLE
    current_app: str | None = None
    running_apps: list[str] = field(default_factory=list)
    audio_output_device: str | None = None
    is_volume_muted: bool | None = None
    volume_level: float | None = None
    hdmi_input: str | None = None
    screen_on: bool | None = None
    awake: bool | None = None
    wake_lock_size: int | None = None
    media_session_state: int | None = None

    @property
    def is_on(self) -> bool:
        """Whether the device is on (not off/standby/unavailable)."""
        return self.state not in (State.OFF, State.STANDBY, State.UNAVAILABLE)


@dataclass(frozen=True, slots=True)
class ADBConfig:
    """Configuration for ADB connection."""

    host: str
    port: int = 5555
    adbkey: str = ""
    adb_server_ip: str = ""
    adb_server_port: int = 5037
    auth_timeout_s: float = 10.0
    transport_timeout_s: float = 1.0
    lock_timeout_s: float = 3.0


@dataclass(frozen=True, slots=True)
class StateDetectionRule:
    """A single rule for state detection."""

    state: State | None = None
    use_property: str | None = None
    conditions: dict[str, int | str] = field(default_factory=dict)
