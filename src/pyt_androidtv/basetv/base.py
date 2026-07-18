"""Base TV class with shared logic for Android TV and Fire TV."""

from __future__ import annotations

import logging
import re
from typing import Any

from .. import constants
from ..adb.base import ADBInterface
from ..constants import CommandRegistry
from ..exceptions import DeviceNotAvailableError
from ..models import ADBConfig, AudioState, DeviceInfo, DeviceState, State
from .state import StateDetectionEngine

_LOGGER = logging.getLogger(__name__)


class BaseTV:
    """Base class for Android TV and Fire TV devices.

    Provides shared functionality for device communication, state detection,
    and media control via ADB.

    Parameters
    ----------
    adb : ADBInterface
        The ADB connection handler.
    config : ADBConfig
        The ADB configuration.
    state_detection_rules : dict or None
        Custom state detection rules.

    """

    DEVICE_TYPE: str = "base"

    def __init__(
        self,
        adb: ADBInterface,
        config: ADBConfig,
        state_detection_rules: dict[str, list[Any]] | None = None,
    ) -> None:
        self._adb = adb
        self._config = config
        self._device_info: DeviceInfo = DeviceInfo()
        self._installed_apps: list[str] = []
        self._max_volume: float | None = None
        self._state_engine = StateDetectionEngine(state_detection_rules)

    # ======================================================================= #
    #                         Context Manager                                  #
    # ======================================================================= #

    async def __aenter__(self) -> BaseTV:
        """Enter the async context manager."""
        await self.connect()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Exit the async context manager."""
        await self.close()

    # ======================================================================= #
    #                         Connection Management                            #
    # ======================================================================= #

    @property
    def available(self) -> bool:
        """Whether the ADB connection is active."""
        return self._adb.available

    async def connect(self) -> bool:
        """Establish a connection to the device.

        Returns
        -------
        bool
            True if the connection was successful.

        """
        return await self._adb.connect(
            auth_timeout_s=self._config.auth_timeout_s,
            transport_timeout_s=self._config.transport_timeout_s,
        )

    async def close(self) -> None:
        """Close the ADB connection."""
        await self._adb.close()

    # ======================================================================= #
    #                         Device Properties                                #
    # ======================================================================= #

    @property
    def device_info(self) -> DeviceInfo:
        """The current device information."""
        return self._device_info

    async def get_device_properties(self) -> DeviceInfo:
        """Retrieve device properties via ADB.

        Returns
        -------
        DeviceInfo
            The device information.

        """
        response = await self._adb.shell(constants.CMD_DEVICE_PROPERTIES)
        self._device_info = self._parse_device_properties(response)

        # Get MAC addresses
        mac_wifi_response = await self._adb.shell(constants.CMD_MAC_WLAN0)
        mac_eth_response = await self._adb.shell(constants.CMD_MAC_ETH0)

        mac_wifi = self._parse_mac_address(mac_wifi_response)
        mac_eth = self._parse_mac_address(mac_eth_response)

        if mac_wifi or mac_eth:
            self._device_info = DeviceInfo(
                manufacturer=self._device_info.manufacturer,
                model=self._device_info.model,
                serial_number=self._device_info.serial_number,
                sw_version=self._device_info.sw_version,
                product_id=self._device_info.product_id,
                mac_wifi=mac_wifi,
                mac_ethernet=mac_eth,
            )

        return self._device_info

    async def get_installed_apps(self) -> list[str]:
        """Retrieve the list of installed apps.

        Returns
        -------
        list of str
            The installed application package names.

        """
        response = await self._adb.shell(constants.CMD_INSTALLED_APPS)
        apps = self._parse_installed_apps(response)
        if apps is not None:
            self._installed_apps = apps
        return self._installed_apps

    # ======================================================================= #
    #                         State Queries                                    #
    # ======================================================================= #

    async def screen_on(self) -> bool | None:
        """Check if the screen is on.

        Returns
        -------
        bool or None
            True if screen is on, None if indeterminate.

        """
        response = await self._adb.shell(
            constants.CMD_SCREEN_ON + constants.CMD_SUCCESS1_FAILURE0
        )
        if response is None:
            return None
        return response.strip() == "1"

    async def awake(self) -> bool | None:
        """Check if the device is awake.

        Returns
        -------
        bool or None
            True if device is awake, None if indeterminate.

        """
        response = await self._adb.shell(
            constants.CMD_AWAKE + constants.CMD_SUCCESS1_FAILURE0
        )
        if response is None:
            return None
        return response.strip() == "1"

    async def screen_on_awake_wake_lock_size(self) -> tuple[bool | None, bool | None, int | None]:
        """Get screen state, awake state, and wake lock size in a single call.

        Returns
        -------
        tuple
            (screen_on, awake, wake_lock_size) tuple.

        """
        response = await self._adb.shell(constants.CMD_SCREEN_ON_AWAKE_WAKE_LOCK_SIZE)
        return self._parse_screen_on_awake_wake_lock_size(response)

    async def current_app(self) -> str | None:
        """Get the current foreground application.

        Returns
        -------
        str or None
            The package name of the current app.

        """
        cmd = CommandRegistry.current_app(self._device_info.android_version)
        response = await self._adb.shell(cmd)
        return self._parse_current_app(response)

    async def current_app_media_session_state(self) -> tuple[str | None, int | None]:
        """Get the current app and its media session state.

        Returns
        -------
        tuple
            (current_app, media_session_state) tuple.

        """
        cmd = CommandRegistry.current_app_media_session_state(self._device_info.android_version)
        response = await self._adb.shell(cmd)
        return self._parse_current_app_media_session_state(response)

    async def audio_state(self) -> str | None:
        """Get the current audio state.

        Returns
        -------
        str or None
            The audio state: "idle", "paused", or "playing".

        """
        cmd = CommandRegistry.audio_state(self._device_info.android_version)
        response = await self._adb.shell(cmd)
        return self._parse_audio_state(response)

    async def wake_lock_size(self) -> int | None:
        """Get the current wake lock size.

        Returns
        -------
        int or None
            The wake lock size.

        """
        response = await self._adb.shell(constants.CMD_WAKE_LOCK_SIZE)
        return self._parse_wake_lock_size(response)

    async def running_apps(self) -> list[str] | None:
        """Get the list of running applications.

        Returns
        -------
        list of str or None
            The running app package names.

        """
        response = await self._adb.shell(constants.CMD_RUNNING_APPS)
        return self._parse_running_apps(response)

    async def get_hdmi_input(self) -> str | None:
        """Get the current HDMI input.

        Returns
        -------
        str or None
            The current HDMI input (e.g., "HW5").

        """
        cmd = CommandRegistry.hdmi_input(self._device_info.android_version)
        response = await self._adb.shell(cmd)
        return self._parse_hdmi_input(response)

    # ======================================================================= #
    #                         Volume Control                                   #
    # ======================================================================= #

    async def stream_music_properties(self) -> dict[str, Any]:
        """Get audio stream properties.

        Returns
        -------
        dict
            Dictionary with keys: is_volume_muted, volume_level, audio_output_device.

        """
        response = await self._adb.shell(constants.CMD_STREAM_MUSIC)
        stream_music = self._parse_stream_music(response)
        audio_output_device = self._parse_audio_output_device(stream_music)
        is_muted = self._parse_is_volume_muted(stream_music)
        volume = self._parse_volume(stream_music, audio_output_device)
        volume_level = self._volume_level(volume)

        return {
            "is_volume_muted": is_muted,
            "volume_level": volume_level,
            "audio_output_device": audio_output_device,
        }

    async def set_volume_level(self, volume_level: float) -> None:
        """Set the volume to a specific level (0.0 to 1.0).

        Parameters
        ----------
        volume_level : float
            The desired volume level between 0.0 and 1.0.

        """
        if self._max_volume is None:
            # Fetch max volume first
            await self.stream_music_properties()

        if self._max_volume:
            new_volume = int(round(self._max_volume * volume_level))
            cmd = CommandRegistry.volume_set(new_volume, self._device_info.android_version)
            await self._adb.shell(cmd)

    async def volume_up(self, *, current_volume: int | None = None) -> None:
        """Increase the volume by one step."""
        await self.send_key_code(constants.KEYS["VOLUME_UP"])

    async def volume_down(self, *, current_volume: int | None = None) -> None:
        """Decrease the volume by one step."""
        await self.send_key_code(constants.KEYS["VOLUME_DOWN"])

    # ======================================================================= #
    #                         Key Events                                       #
    # ======================================================================= #

    async def send_key(self, key_name: str) -> None:
        """Send a key event by name.

        Parameters
        ----------
        key_name : str
            The key name (must be in constants.KEYS).

        Raises
        ------
        KeyError
            If the key name is not recognized.

        """
        if key_name not in constants.KEYS:
            raise KeyError(f"Unknown key: {key_name}")
        await self.send_key_code(constants.KEYS[key_name])

    async def send_key_code(self, code: int) -> None:
        """Send a key event by code.

        Parameters
        ----------
        code : int
            The Android key event code.

        """
        await self._adb.shell(f"input keyevent {code}")

    async def power(self) -> None:
        """Send the POWER key event."""
        await self.send_key_code(constants.KEYS["POWER"])

    async def home(self) -> None:
        """Send the HOME key event."""
        await self.send_key_code(constants.KEYS["HOME"])

    async def back(self) -> None:
        """Send the BACK key event."""
        await self.send_key_code(constants.KEYS["BACK"])

    async def menu(self) -> None:
        """Send the MENU key event."""
        await self.send_key_code(constants.KEYS["MENU"])

    async def enter(self) -> None:
        """Send the ENTER key event."""
        await self.send_key_code(constants.KEYS["ENTER"])

    async def up(self) -> None:
        """Send the UP key event."""
        await self.send_key_code(constants.KEYS["UP"])

    async def down(self) -> None:
        """Send the DOWN key event."""
        await self.send_key_code(constants.KEYS["DOWN"])

    async def left(self) -> None:
        """Send the LEFT key event."""
        await self.send_key_code(constants.KEYS["LEFT"])

    async def right(self) -> None:
        """Send the RIGHT key event."""
        await self.send_key_code(constants.KEYS["RIGHT"])

    async def media_play(self) -> None:
        """Send the PLAY key event."""
        await self.send_key_code(constants.KEYS["PLAY"])

    async def media_pause(self) -> None:
        """Send the PAUSE key event."""
        await self.send_key_code(constants.KEYS["PAUSE"])

    async def media_play_pause(self) -> None:
        """Send the PLAY_PAUSE key event."""
        await self.send_key_code(constants.KEYS["PLAY_PAUSE"])

    async def media_stop(self) -> None:
        """Send the STOP key event."""
        await self.send_key_code(constants.KEYS["STOP"])

    async def media_next(self) -> None:
        """Send the NEXT key event."""
        await self.send_key_code(constants.KEYS["NEXT"])

    async def media_previous(self) -> None:
        """Send the PREVIOUS key event."""
        await self.send_key_code(constants.KEYS["PREVIOUS"])

    async def mute(self) -> None:
        """Send the MUTE key event."""
        await self.send_key_code(constants.KEYS["MUTE"])

    # ======================================================================= #
    #                         App Management                                   #
    # ======================================================================= #

    async def launch_app(self, app: str) -> None:
        """Launch an application.

        Parameters
        ----------
        app : str
            The package name of the app to launch.

        """
        cmd = CommandRegistry.launch_app(
            app,
            self._device_info.android_version,
            firetv=(self.DEVICE_TYPE == "firetv"),
        )
        await self._adb.shell(cmd)

    async def stop_app(self, app: str) -> None:
        """Force stop an application.

        Parameters
        ----------
        app : str
            The package name of the app to stop.

        """
        await self._adb.shell(f"am force-stop {app}")

    async def start_intent(self, intent: str) -> None:
        """Start an activity with the given intent.

        Parameters
        ----------
        intent : str
            The intent URI or component to start.

        """
        await self._adb.shell(f"am start {intent}")

    # ======================================================================= #
    #                         Power Control                                    #
    # ======================================================================= #

    async def turn_on(self) -> None:
        """Turn on the device."""
        await self._adb.shell(constants.CMD_TURN_ON_ANDROIDTV)

    async def turn_off(self) -> None:
        """Turn off the device."""
        await self._adb.shell(constants.CMD_TURN_OFF_ANDROIDTV)

    async def sleep(self) -> None:
        """Put the device to sleep."""
        await self.send_key_code(constants.KEYS["SLEEP"])

    # ======================================================================= #
    #                         Static Parsing Methods                           #
    # ======================================================================= #

    @staticmethod
    def _parse_device_properties(response: str | None) -> DeviceInfo:
        """Parse device properties from the ADB response.

        Parameters
        ----------
        response : str or None
            The output of CMD_DEVICE_PROPERTIES.

        Returns
        -------
        DeviceInfo
            Parsed device information.

        """
        if not response:
            return DeviceInfo()

        lines = response.strip().splitlines()
        if len(lines) != 5:
            return DeviceInfo()

        manufacturer, model, serialno, version, product_id = lines
        return DeviceInfo(
            manufacturer=manufacturer.strip(),
            model=model.strip(),
            serial_number=serialno.strip() or None,
            sw_version=version.strip(),
            product_id=product_id.strip(),
        )

    @staticmethod
    def _parse_mac_address(response: str | None) -> str | None:
        """Parse a MAC address from ADB response.

        Parameters
        ----------
        response : str or None
            The response from a MAC address command.

        Returns
        -------
        str or None
            The parsed MAC address.

        """
        if not response:
            return None
        match = constants.REGEX_MAC_ADDRESS.search(response)
        return match.group(1) if match else None

    @staticmethod
    def _parse_installed_apps(response: str | None) -> list[str] | None:
        """Parse the installed apps from the ADB response.

        Parameters
        ----------
        response : str or None
            The output of CMD_INSTALLED_APPS.

        Returns
        -------
        list of str or None
            The list of installed app package names.

        """
        if response is None:
            return None
        return [
            line.strip().rsplit("package:", 1)[-1]
            for line in response.splitlines()
            if line.strip()
        ]

    @staticmethod
    def _parse_screen_on_awake_wake_lock_size(
        output: str | None,
    ) -> tuple[bool | None, bool | None, int | None]:
        """Parse screen on, awake, and wake lock size from combined output.

        Parameters
        ----------
        output : str or None
            The output from CMD_SCREEN_ON_AWAKE_WAKE_LOCK_SIZE.

        Returns
        -------
        tuple
            (screen_on, awake, wake_lock_size).

        """
        if output is None:
            return None, None, None

        if output == "":
            return False, False, None

        screen_on = output[0] == "1"
        awake = None if len(output) < 2 else output[1] == "1"
        wake_lock_size = None if len(output) < 3 else BaseTV._parse_wake_lock_size(output[2:])

        return screen_on, awake, wake_lock_size

    @staticmethod
    def _parse_current_app(response: str | None) -> str | None:
        """Parse the current app from the ADB response.

        Parameters
        ----------
        response : str or None
            The output of the current app command.

        Returns
        -------
        str or None
            The current app package name.

        """
        if not response or "=" in response or "{" in response:
            return None
        return response.strip()

    @staticmethod
    def _parse_current_app_media_session_state(
        response: str | None,
    ) -> tuple[str | None, int | None]:
        """Parse current app and media session state from combined output.

        Parameters
        ----------
        response : str or None
            The combined output.

        Returns
        -------
        tuple
            (current_app, media_session_state).

        """
        if not response:
            return None, None

        lines = response.splitlines()
        current_app = BaseTV._parse_current_app(lines[0].strip())

        if len(lines) > 1:
            match = constants.REGEX_MEDIA_SESSION_STATE.search(response)
            if match:
                return current_app, int(match.group("state"))

        return current_app, None

    @staticmethod
    def _parse_audio_state(response: str | None) -> str | None:
        """Parse the audio state from the ADB response.

        Parameters
        ----------
        response : str or None
            The output of the audio state command.

        Returns
        -------
        str or None
            "idle", "paused", or "playing".

        """
        if not response:
            return None
        if response.strip() == "1":
            return AudioState.PAUSED
        if response.strip() == "2":
            return AudioState.PLAYING
        return AudioState.IDLE

    @staticmethod
    def _parse_wake_lock_size(response: str | None) -> int | None:
        """Parse the wake lock size from the ADB response.

        Parameters
        ----------
        response : str or None
            The output of CMD_WAKE_LOCK_SIZE.

        Returns
        -------
        int or None
            The wake lock size.

        """
        if not response:
            return None
        match = constants.REGEX_WAKE_LOCK_SIZE.search(response)
        return int(match.group("size")) if match else None

    @staticmethod
    def _parse_running_apps(response: str | None) -> list[str] | None:
        """Parse the running apps from the ADB response.

        Parameters
        ----------
        response : str or None
            The output of CMD_RUNNING_APPS.

        Returns
        -------
        list of str or None
            The list of running app package names.

        """
        if not response:
            return None
        return [
            line.strip().rsplit(" ", 1)[-1]
            for line in response.splitlines()
            if line.strip()
        ]

    @staticmethod
    def _parse_hdmi_input(response: str | None) -> str | None:
        """Parse the HDMI input from the ADB response.

        Parameters
        ----------
        response : str or None
            The output of the HDMI input command.

        Returns
        -------
        str or None
            The HDMI input identifier (e.g., "HW5").

        """
        return response.strip() if response and response.strip() else None

    @staticmethod
    def _parse_stream_music(response: str | None) -> str | None:
        """Parse the STREAM_MUSIC block from dumpsys audio output.

        Parameters
        ----------
        response : str or None
            The raw output of CMD_STREAM_MUSIC.

        Returns
        -------
        str or None
            The parsed STREAM_MUSIC block.

        """
        if not response:
            return None
        match = constants.REGEX_STREAM_MUSIC.search(response)
        return match.group(1) if match else None

    @staticmethod
    def _parse_audio_output_device(stream_music: str | None) -> str | None:
        """Parse the audio output device from STREAM_MUSIC.

        Parameters
        ----------
        stream_music : str or None
            The STREAM_MUSIC block.

        Returns
        -------
        str or None
            The audio output device name.

        """
        if not stream_music:
            return None
        match = constants.REGEX_DEVICE.search(stream_music)
        return match.group(1) if match else None

    @staticmethod
    def _parse_is_volume_muted(stream_music: str | None) -> bool | None:
        """Parse whether volume is muted from STREAM_MUSIC.

        Parameters
        ----------
        stream_music : str or None
            The STREAM_MUSIC block.

        Returns
        -------
        bool or None
            Whether volume is muted.

        """
        if not stream_music:
            return None
        match = constants.REGEX_MUTED.search(stream_music)
        return match.group(1) == "true" if match else None

    def _parse_volume(self, stream_music: str | None, audio_output_device: str | None) -> int | None:
        """Parse the volume from STREAM_MUSIC.

        Parameters
        ----------
        stream_music : str or None
            The STREAM_MUSIC block.
        audio_output_device : str or None
            The current audio output device.

        Returns
        -------
        int or None
            The absolute volume level.

        """
        if not stream_music:
            return None

        # Get max volume
        if self._max_volume is None:
            max_match = constants.REGEX_MAX_VOLUME.search(stream_music)
            if max_match:
                self._max_volume = float(max_match.group(1))

        if not audio_output_device:
            return None

        pattern = re.compile(re.escape(audio_output_device) + r"\): (\d{1,})")
        match = pattern.search(stream_music)
        return int(match.group(1)) if match else None

    def _volume_level(self, volume: int | None) -> float | None:
        """Convert absolute volume to a 0.0-1.0 level.

        Parameters
        ----------
        volume : int or None
            The absolute volume.

        Returns
        -------
        float or None
            The relative volume level.

        """
        if volume is not None and self._max_volume:
            return volume / self._max_volume
        return None
