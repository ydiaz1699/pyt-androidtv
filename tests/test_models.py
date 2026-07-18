"""Tests for pyt-androidtv data models."""

from __future__ import annotations

import pytest

from pyt_androidtv.models import ADBConfig, DeviceInfo, DeviceState, DeviceType, State


class TestDeviceInfo:
    """Tests for the DeviceInfo model."""

    def test_default_values(self) -> None:
        """DeviceInfo should have sensible defaults."""
        info = DeviceInfo()
        assert info.manufacturer == ""
        assert info.model == ""
        assert info.serial_number is None
        assert info.sw_version == ""
        assert info.product_id == ""
        assert info.mac_wifi is None
        assert info.mac_ethernet is None

    def test_android_version_parsing_simple(self) -> None:
        """android_version should parse a simple version string."""
        info = DeviceInfo(sw_version="12")
        assert info.android_version == 12

    def test_android_version_parsing_dotted(self) -> None:
        """android_version should parse a dotted version string (major only)."""
        info = DeviceInfo(sw_version="13.0.1")
        assert info.android_version == 13

    def test_android_version_parsing_empty(self) -> None:
        """android_version should return None for empty sw_version."""
        info = DeviceInfo(sw_version="")
        assert info.android_version is None

    def test_android_version_parsing_invalid(self) -> None:
        """android_version should return None for non-numeric sw_version."""
        info = DeviceInfo(sw_version="unknown")
        assert info.android_version is None

    def test_is_android_11_plus_true(self) -> None:
        """is_android_11_plus should be True for version >= 11."""
        assert DeviceInfo(sw_version="11").is_android_11_plus is True
        assert DeviceInfo(sw_version="12").is_android_11_plus is True
        assert DeviceInfo(sw_version="14").is_android_11_plus is True

    def test_is_android_11_plus_false(self) -> None:
        """is_android_11_plus should be False for version < 11."""
        assert DeviceInfo(sw_version="10").is_android_11_plus is False
        assert DeviceInfo(sw_version="9").is_android_11_plus is False
        assert DeviceInfo(sw_version="7").is_android_11_plus is False

    def test_is_android_11_plus_none(self) -> None:
        """is_android_11_plus should be False when version cannot be determined."""
        assert DeviceInfo(sw_version="").is_android_11_plus is False
        assert DeviceInfo(sw_version="unknown").is_android_11_plus is False

    def test_immutability(self) -> None:
        """DeviceInfo should be immutable (frozen dataclass)."""
        info = DeviceInfo(manufacturer="Google", model="Chromecast")
        with pytest.raises(AttributeError):
            info.manufacturer = "Other"  # type: ignore[misc]

    def test_equality(self) -> None:
        """Two DeviceInfo with same values should be equal."""
        info1 = DeviceInfo(manufacturer="Google", model="Chromecast", sw_version="12")
        info2 = DeviceInfo(manufacturer="Google", model="Chromecast", sw_version="12")
        assert info1 == info2

    def test_full_construction(self) -> None:
        """DeviceInfo should accept all fields."""
        info = DeviceInfo(
            manufacturer="Amazon",
            model="Fire TV Stick",
            serial_number="ABC123",
            sw_version="9",
            product_id="mantis",
            mac_wifi="aa:bb:cc:dd:ee:ff",
            mac_ethernet="11:22:33:44:55:66",
        )
        assert info.manufacturer == "Amazon"
        assert info.model == "Fire TV Stick"
        assert info.serial_number == "ABC123"
        assert info.sw_version == "9"
        assert info.product_id == "mantis"
        assert info.mac_wifi == "aa:bb:cc:dd:ee:ff"
        assert info.mac_ethernet == "11:22:33:44:55:66"


class TestDeviceState:
    """Tests for the DeviceState model."""

    def test_default_state_is_unavailable(self) -> None:
        """Default DeviceState should be UNAVAILABLE."""
        state = DeviceState()
        assert state.state == State.UNAVAILABLE

    def test_is_on_for_idle(self) -> None:
        """is_on should be True for IDLE state."""
        state = DeviceState(state=State.IDLE)
        assert state.is_on is True

    def test_is_on_for_playing(self) -> None:
        """is_on should be True for PLAYING state."""
        state = DeviceState(state=State.PLAYING)
        assert state.is_on is True

    def test_is_on_for_paused(self) -> None:
        """is_on should be True for PAUSED state."""
        state = DeviceState(state=State.PAUSED)
        assert state.is_on is True

    def test_is_on_for_off(self) -> None:
        """is_on should be False for OFF state."""
        state = DeviceState(state=State.OFF)
        assert state.is_on is False

    def test_is_on_for_standby(self) -> None:
        """is_on should be False for STANDBY state."""
        state = DeviceState(state=State.STANDBY)
        assert state.is_on is False

    def test_is_on_for_unavailable(self) -> None:
        """is_on should be False for UNAVAILABLE state."""
        state = DeviceState(state=State.UNAVAILABLE)
        assert state.is_on is False

    def test_is_on_for_stopped(self) -> None:
        """is_on should be True for STOPPED state."""
        state = DeviceState(state=State.STOPPED)
        assert state.is_on is True

    def test_defaults(self) -> None:
        """DeviceState should have proper defaults."""
        state = DeviceState()
        assert state.current_app is None
        assert state.running_apps == []
        assert state.audio_output_device is None
        assert state.is_volume_muted is None
        assert state.volume_level is None
        assert state.hdmi_input is None
        assert state.screen_on is None
        assert state.awake is None
        assert state.wake_lock_size is None
        assert state.media_session_state is None

    def test_mutable(self) -> None:
        """DeviceState should be mutable (non-frozen)."""
        state = DeviceState()
        state.state = State.PLAYING
        state.current_app = "com.example.app"
        assert state.state == State.PLAYING
        assert state.current_app == "com.example.app"


class TestStateEnum:
    """Tests for the State enum."""

    def test_state_values(self) -> None:
        """State enum should have the expected string values."""
        assert State.IDLE == "idle"
        assert State.OFF == "off"
        assert State.PLAYING == "playing"
        assert State.PAUSED == "paused"
        assert State.STANDBY == "standby"
        assert State.STOPPED == "stopped"
        assert State.UNAVAILABLE == "unavailable"

    def test_state_is_str(self) -> None:
        """State values should be usable as strings."""
        assert f"Device is {State.PLAYING}" == "Device is playing"

    def test_state_comparison(self) -> None:
        """State should support string comparison."""
        assert State.IDLE == "idle"
        assert State.PLAYING != "paused"


class TestDeviceType:
    """Tests for the DeviceType enum."""

    def test_device_type_values(self) -> None:
        """DeviceType enum should have the expected int values."""
        assert DeviceType.UNKNOWN == 0
        assert DeviceType.ANDROID_TV == 1
        assert DeviceType.FIRE_TV == 2


class TestADBConfig:
    """Tests for the ADBConfig model."""

    def test_defaults(self) -> None:
        """ADBConfig should have sensible defaults."""
        config = ADBConfig(host="192.168.1.100")
        assert config.host == "192.168.1.100"
        assert config.port == 5555
        assert config.adbkey == ""
        assert config.adb_server_ip == ""
        assert config.adb_server_port == 5037
        assert config.auth_timeout_s == 10.0
        assert config.transport_timeout_s == 1.0
        assert config.lock_timeout_s == 3.0

    def test_custom_values(self) -> None:
        """ADBConfig should accept custom values."""
        config = ADBConfig(
            host="10.0.0.5",
            port=5556,
            adbkey="/home/user/.android/adbkey",
            adb_server_ip="192.168.1.1",
            adb_server_port=5038,
            auth_timeout_s=20.0,
            transport_timeout_s=2.0,
            lock_timeout_s=5.0,
        )
        assert config.host == "10.0.0.5"
        assert config.port == 5556
        assert config.adbkey == "/home/user/.android/adbkey"
        assert config.adb_server_ip == "192.168.1.1"
        assert config.adb_server_port == 5038
        assert config.auth_timeout_s == 20.0
        assert config.transport_timeout_s == 2.0
        assert config.lock_timeout_s == 5.0

    def test_immutability(self) -> None:
        """ADBConfig should be immutable."""
        config = ADBConfig(host="192.168.1.100")
        with pytest.raises(AttributeError):
            config.host = "10.0.0.1"  # type: ignore[misc]
