"""Android TV device implementation."""

from __future__ import annotations

import logging
from typing import Any

from ..adb.server import ADBServerConnection
from ..adb.tcp import ADBConnection
from ..basetv.base import BaseTV
from ..constants import CMD_TURN_OFF_ANDROIDTV, CMD_TURN_ON_ANDROIDTV, CommandRegistry
from ..models import ADBConfig, DeviceState, DeviceType, State

_LOGGER = logging.getLogger(__name__)


class AndroidTV(BaseTV):
    """Represent an Android TV device.

    Parameters
    ----------
    config : ADBConfig
        The ADB connection configuration.
    state_detection_rules : dict or None
        Custom state detection rules.

    """

    DEVICE_TYPE: str = "androidtv"

    def __init__(
        self,
        config: ADBConfig,
        state_detection_rules: dict[str, list[Any]] | None = None,
    ) -> None:
        if config.adb_server_ip:
            adb: ADBConnection | ADBServerConnection = ADBServerConnection(
                host=config.host,
                port=config.port,
                adb_server_ip=config.adb_server_ip,
                adb_server_port=config.adb_server_port,
                lock_timeout_s=config.lock_timeout_s,
            )
        else:
            adb = ADBConnection(
                host=config.host,
                port=config.port,
                adbkey=config.adbkey,
                lock_timeout_s=config.lock_timeout_s,
            )

        super().__init__(adb=adb, config=config, state_detection_rules=state_detection_rules)

    async def update(self, *, get_running_apps: bool = True, lazy: bool = True) -> DeviceState:
        """Update the device state.

        Parameters
        ----------
        get_running_apps : bool
            Whether to retrieve the running apps list.
        lazy : bool
            If True, skip some queries when the device is off.

        Returns
        -------
        DeviceState
            The current device state.

        """
        if not self.available:
            return DeviceState(state=State.UNAVAILABLE)

        # Get screen state, awake, and wake lock size
        screen_on, awake, wake_lock_size = await self.screen_on_awake_wake_lock_size()

        # If the screen is off, the device is off/standby
        if screen_on is None:
            return DeviceState(state=State.UNAVAILABLE)

        if not screen_on:
            state = DeviceState(
                state=State.OFF,
                screen_on=False,
                awake=awake,
                wake_lock_size=wake_lock_size,
            )
            return state

        if not awake:
            state = DeviceState(
                state=State.STANDBY,
                screen_on=True,
                awake=False,
                wake_lock_size=wake_lock_size,
            )
            return state

        # Device is on - get more information
        current_app, media_session_state = await self.current_app_media_session_state()

        # Get audio state
        audio_state_val = await self.audio_state()

        # Get running apps
        running_apps_list: list[str] = []
        if get_running_apps:
            apps = await self.running_apps()
            running_apps_list = apps if apps else []

        # Get HDMI input
        hdmi_input = await self.get_hdmi_input()

        # Get volume properties
        volume_props = await self.stream_music_properties()

        # Determine the state
        detected_state = self._determine_state(
            current_app=current_app,
            media_session_state=media_session_state,
            wake_lock_size=wake_lock_size,
            audio_state=audio_state_val,
        )

        return DeviceState(
            state=detected_state,
            current_app=current_app,
            running_apps=running_apps_list,
            audio_output_device=volume_props.get("audio_output_device"),
            is_volume_muted=volume_props.get("is_volume_muted"),
            volume_level=volume_props.get("volume_level"),
            hdmi_input=hdmi_input,
            screen_on=screen_on,
            awake=awake,
            wake_lock_size=wake_lock_size,
            media_session_state=media_session_state,
        )

    def _determine_state(
        self,
        *,
        current_app: str | None,
        media_session_state: int | None,
        wake_lock_size: int | None,
        audio_state: str | None,
    ) -> State:
        """Determine the device state using the state engine and fallbacks.

        Parameters
        ----------
        current_app : str or None
            The current foreground app.
        media_session_state : int or None
            The media session state.
        wake_lock_size : int or None
            The wake lock size.
        audio_state : str or None
            The audio state.

        Returns
        -------
        State
            The determined state.

        """
        # Try the state detection engine first
        state = self._state_engine.detect_state(
            current_app=current_app,
            media_session_state=media_session_state,
            wake_lock_size=wake_lock_size,
            audio_state=audio_state,
        )
        if state is not None:
            return state

        # Fallback: use media session state
        if media_session_state == 2:
            return State.PAUSED
        if media_session_state == 3:
            return State.PLAYING

        # Fallback: use audio state
        if audio_state == "paused":
            return State.PAUSED
        if audio_state == "playing":
            return State.PLAYING

        # Default to idle
        return State.IDLE

    async def turn_on(self) -> None:
        """Turn on the Android TV device."""
        await self._adb.shell(CMD_TURN_ON_ANDROIDTV)

    async def turn_off(self) -> None:
        """Turn off the Android TV device."""
        await self._adb.shell(CMD_TURN_OFF_ANDROIDTV)

    async def get_properties_dict(self) -> dict[str, Any]:
        """Get a dictionary of all device properties.

        Returns
        -------
        dict
            A dictionary containing device info and current state.

        """
        device_info = await self.get_device_properties()
        state = await self.update()

        return {
            "device_type": DeviceType.ANDROID_TV,
            "manufacturer": device_info.manufacturer,
            "model": device_info.model,
            "serial_number": device_info.serial_number,
            "sw_version": device_info.sw_version,
            "product_id": device_info.product_id,
            "mac_wifi": device_info.mac_wifi,
            "mac_ethernet": device_info.mac_ethernet,
            "state": state.state,
            "current_app": state.current_app,
            "running_apps": state.running_apps,
            "hdmi_input": state.hdmi_input,
            "volume_level": state.volume_level,
            "is_volume_muted": state.is_volume_muted,
        }
