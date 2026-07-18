"""Synchronous wrappers for AndroidTV and FireTV."""

from __future__ import annotations

import asyncio
from typing import Any

from .androidtv.androidtv import AndroidTV
from .firetv.firetv import FireTV
from .models import ADBConfig, DeviceInfo, DeviceState


def _run_sync(coro: Any) -> Any:
    """Run a coroutine synchronously.

    Parameters
    ----------
    coro : coroutine
        The coroutine to run.

    Returns
    -------
    Any
        The result of the coroutine.

    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an existing event loop - create a new one in a thread
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class AndroidTVSync:
    """Synchronous wrapper for AndroidTV.

    Provides the same interface as AndroidTV but with synchronous methods.

    Parameters
    ----------
    config : ADBConfig
        The ADB connection configuration.
    state_detection_rules : dict or None
        Custom state detection rules.

    """

    def __init__(
        self,
        config: ADBConfig,
        state_detection_rules: dict[str, list[Any]] | None = None,
    ) -> None:
        self._atv = AndroidTV(config=config, state_detection_rules=state_detection_rules)

    def __enter__(self) -> AndroidTVSync:
        """Enter the sync context manager."""
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        """Exit the sync context manager."""
        self.close()

    @property
    def available(self) -> bool:
        """Whether the ADB connection is active."""
        return self._atv.available

    @property
    def device_info(self) -> DeviceInfo:
        """The current device information."""
        return self._atv.device_info

    def connect(self) -> bool:
        """Establish a connection to the device."""
        return _run_sync(self._atv.connect())

    def close(self) -> None:
        """Close the ADB connection."""
        _run_sync(self._atv.close())

    def get_device_properties(self) -> DeviceInfo:
        """Retrieve device properties via ADB."""
        return _run_sync(self._atv.get_device_properties())

    def get_installed_apps(self) -> list[str]:
        """Retrieve the list of installed apps."""
        return _run_sync(self._atv.get_installed_apps())

    def update(self, *, get_running_apps: bool = True, lazy: bool = True) -> DeviceState:
        """Update the device state."""
        return _run_sync(self._atv.update(get_running_apps=get_running_apps, lazy=lazy))

    def screen_on(self) -> bool | None:
        """Check if the screen is on."""
        return _run_sync(self._atv.screen_on())

    def awake(self) -> bool | None:
        """Check if the device is awake."""
        return _run_sync(self._atv.awake())

    def current_app(self) -> str | None:
        """Get the current foreground application."""
        return _run_sync(self._atv.current_app())

    def current_app_media_session_state(self) -> tuple[str | None, int | None]:
        """Get the current app and its media session state."""
        return _run_sync(self._atv.current_app_media_session_state())

    def audio_state(self) -> str | None:
        """Get the current audio state."""
        return _run_sync(self._atv.audio_state())

    def wake_lock_size(self) -> int | None:
        """Get the current wake lock size."""
        return _run_sync(self._atv.wake_lock_size())

    def running_apps(self) -> list[str] | None:
        """Get the list of running applications."""
        return _run_sync(self._atv.running_apps())

    def get_hdmi_input(self) -> str | None:
        """Get the current HDMI input."""
        return _run_sync(self._atv.get_hdmi_input())

    def stream_music_properties(self) -> dict[str, Any]:
        """Get audio stream properties."""
        return _run_sync(self._atv.stream_music_properties())

    def set_volume_level(self, volume_level: float) -> None:
        """Set the volume to a specific level (0.0 to 1.0)."""
        _run_sync(self._atv.set_volume_level(volume_level))

    def volume_up(self) -> None:
        """Increase the volume by one step."""
        _run_sync(self._atv.volume_up())

    def volume_down(self) -> None:
        """Decrease the volume by one step."""
        _run_sync(self._atv.volume_down())

    def send_key(self, key_name: str) -> None:
        """Send a key event by name."""
        _run_sync(self._atv.send_key(key_name))

    def send_key_code(self, code: int) -> None:
        """Send a key event by code."""
        _run_sync(self._atv.send_key_code(code))

    def power(self) -> None:
        """Send the POWER key event."""
        _run_sync(self._atv.power())

    def home(self) -> None:
        """Send the HOME key event."""
        _run_sync(self._atv.home())

    def back(self) -> None:
        """Send the BACK key event."""
        _run_sync(self._atv.back())

    def menu(self) -> None:
        """Send the MENU key event."""
        _run_sync(self._atv.menu())

    def enter(self) -> None:
        """Send the ENTER key event."""
        _run_sync(self._atv.enter())

    def up(self) -> None:
        """Send the UP key event."""
        _run_sync(self._atv.up())

    def down(self) -> None:
        """Send the DOWN key event."""
        _run_sync(self._atv.down())

    def left(self) -> None:
        """Send the LEFT key event."""
        _run_sync(self._atv.left())

    def right(self) -> None:
        """Send the RIGHT key event."""
        _run_sync(self._atv.right())

    def media_play(self) -> None:
        """Send the PLAY key event."""
        _run_sync(self._atv.media_play())

    def media_pause(self) -> None:
        """Send the PAUSE key event."""
        _run_sync(self._atv.media_pause())

    def media_play_pause(self) -> None:
        """Send the PLAY_PAUSE key event."""
        _run_sync(self._atv.media_play_pause())

    def media_stop(self) -> None:
        """Send the STOP key event."""
        _run_sync(self._atv.media_stop())

    def media_next(self) -> None:
        """Send the NEXT key event."""
        _run_sync(self._atv.media_next())

    def media_previous(self) -> None:
        """Send the PREVIOUS key event."""
        _run_sync(self._atv.media_previous())

    def mute(self) -> None:
        """Send the MUTE key event."""
        _run_sync(self._atv.mute())

    def launch_app(self, app: str) -> None:
        """Launch an application."""
        _run_sync(self._atv.launch_app(app))

    def stop_app(self, app: str) -> None:
        """Force stop an application."""
        _run_sync(self._atv.stop_app(app))

    def start_intent(self, intent: str) -> None:
        """Start an activity with the given intent."""
        _run_sync(self._atv.start_intent(intent))

    def turn_on(self) -> None:
        """Turn on the device."""
        _run_sync(self._atv.turn_on())

    def turn_off(self) -> None:
        """Turn off the device."""
        _run_sync(self._atv.turn_off())

    def sleep(self) -> None:
        """Put the device to sleep."""
        _run_sync(self._atv.sleep())

    def get_properties_dict(self) -> dict[str, Any]:
        """Get a dictionary of all device properties."""
        return _run_sync(self._atv.get_properties_dict())


class FireTVSync:
    """Synchronous wrapper for FireTV.

    Provides the same interface as FireTV but with synchronous methods.

    Parameters
    ----------
    config : ADBConfig
        The ADB connection configuration.
    state_detection_rules : dict or None
        Custom state detection rules.

    """

    def __init__(
        self,
        config: ADBConfig,
        state_detection_rules: dict[str, list[Any]] | None = None,
    ) -> None:
        self._ftv = FireTV(config=config, state_detection_rules=state_detection_rules)

    def __enter__(self) -> FireTVSync:
        """Enter the sync context manager."""
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        """Exit the sync context manager."""
        self.close()

    @property
    def available(self) -> bool:
        """Whether the ADB connection is active."""
        return self._ftv.available

    @property
    def device_info(self) -> DeviceInfo:
        """The current device information."""
        return self._ftv.device_info

    def connect(self) -> bool:
        """Establish a connection to the device."""
        return _run_sync(self._ftv.connect())

    def close(self) -> None:
        """Close the ADB connection."""
        _run_sync(self._ftv.close())

    def get_device_properties(self) -> DeviceInfo:
        """Retrieve device properties via ADB."""
        return _run_sync(self._ftv.get_device_properties())

    def get_installed_apps(self) -> list[str]:
        """Retrieve the list of installed apps."""
        return _run_sync(self._ftv.get_installed_apps())

    def update(self, *, get_running_apps: bool = True, lazy: bool = True) -> DeviceState:
        """Update the device state."""
        return _run_sync(self._ftv.update(get_running_apps=get_running_apps, lazy=lazy))

    def screen_on(self) -> bool | None:
        """Check if the screen is on."""
        return _run_sync(self._ftv.screen_on())

    def awake(self) -> bool | None:
        """Check if the device is awake."""
        return _run_sync(self._ftv.awake())

    def current_app(self) -> str | None:
        """Get the current foreground application."""
        return _run_sync(self._ftv.current_app())

    def current_app_media_session_state(self) -> tuple[str | None, int | None]:
        """Get the current app and its media session state."""
        return _run_sync(self._ftv.current_app_media_session_state())

    def audio_state(self) -> str | None:
        """Get the current audio state."""
        return _run_sync(self._ftv.audio_state())

    def wake_lock_size(self) -> int | None:
        """Get the current wake lock size."""
        return _run_sync(self._ftv.wake_lock_size())

    def running_apps(self) -> list[str] | None:
        """Get the list of running applications."""
        return _run_sync(self._ftv.running_apps())

    def get_hdmi_input(self) -> str | None:
        """Get the current HDMI input."""
        return _run_sync(self._ftv.get_hdmi_input())

    def stream_music_properties(self) -> dict[str, Any]:
        """Get audio stream properties."""
        return _run_sync(self._ftv.stream_music_properties())

    def set_volume_level(self, volume_level: float) -> None:
        """Set the volume to a specific level (0.0 to 1.0)."""
        _run_sync(self._ftv.set_volume_level(volume_level))

    def volume_up(self) -> None:
        """Increase the volume by one step."""
        _run_sync(self._ftv.volume_up())

    def volume_down(self) -> None:
        """Decrease the volume by one step."""
        _run_sync(self._ftv.volume_down())

    def send_key(self, key_name: str) -> None:
        """Send a key event by name."""
        _run_sync(self._ftv.send_key(key_name))

    def send_key_code(self, code: int) -> None:
        """Send a key event by code."""
        _run_sync(self._ftv.send_key_code(code))

    def power(self) -> None:
        """Send the POWER key event."""
        _run_sync(self._ftv.power())

    def home(self) -> None:
        """Send the HOME key event."""
        _run_sync(self._ftv.home())

    def back(self) -> None:
        """Send the BACK key event."""
        _run_sync(self._ftv.back())

    def menu(self) -> None:
        """Send the MENU key event."""
        _run_sync(self._ftv.menu())

    def enter(self) -> None:
        """Send the ENTER key event."""
        _run_sync(self._ftv.enter())

    def up(self) -> None:
        """Send the UP key event."""
        _run_sync(self._ftv.up())

    def down(self) -> None:
        """Send the DOWN key event."""
        _run_sync(self._ftv.down())

    def left(self) -> None:
        """Send the LEFT key event."""
        _run_sync(self._ftv.left())

    def right(self) -> None:
        """Send the RIGHT key event."""
        _run_sync(self._ftv.right())

    def media_play(self) -> None:
        """Send the PLAY key event."""
        _run_sync(self._ftv.media_play())

    def media_pause(self) -> None:
        """Send the PAUSE key event."""
        _run_sync(self._ftv.media_pause())

    def media_play_pause(self) -> None:
        """Send the PLAY_PAUSE key event."""
        _run_sync(self._ftv.media_play_pause())

    def media_stop(self) -> None:
        """Send the STOP key event."""
        _run_sync(self._ftv.media_stop())

    def media_next(self) -> None:
        """Send the NEXT key event."""
        _run_sync(self._ftv.media_next())

    def media_previous(self) -> None:
        """Send the PREVIOUS key event."""
        _run_sync(self._ftv.media_previous())

    def mute(self) -> None:
        """Send the MUTE key event."""
        _run_sync(self._ftv.mute())

    def launch_app(self, app: str) -> None:
        """Launch an application."""
        _run_sync(self._ftv.launch_app(app))

    def stop_app(self, app: str) -> None:
        """Force stop an application."""
        _run_sync(self._ftv.stop_app(app))

    def start_intent(self, intent: str) -> None:
        """Start an activity with the given intent."""
        _run_sync(self._ftv.start_intent(intent))

    def turn_on(self) -> None:
        """Turn on the device."""
        _run_sync(self._ftv.turn_on())

    def turn_off(self) -> None:
        """Turn off the device."""
        _run_sync(self._ftv.turn_off())

    def sleep(self) -> None:
        """Put the device to sleep."""
        _run_sync(self._ftv.sleep())

    def get_properties_dict(self) -> dict[str, Any]:
        """Get a dictionary of all device properties."""
        return _run_sync(self._ftv.get_properties_dict())
