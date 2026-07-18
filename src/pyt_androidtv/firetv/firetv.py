"""Implementación del dispositivo Fire TV."""

from __future__ import annotations

import logging
from typing import Any

from ..adb.server import ADBServerConnection
from ..adb.tcp import ADBConnection
from ..basetv.base import BaseTV
from ..constants import CMD_TURN_OFF_FIRETV, CMD_TURN_ON_FIRETV, CommandRegistry
from ..models import ADBConfig, DeviceState, DeviceType, State

_LOGGER = logging.getLogger(__name__)

# Reglas de detección de estado por defecto específicas de Fire TV
_FIRETV_DEFAULT_RULES: dict[str, list[Any]] = {
    "com.amazon.tv.launcher": ["idle"],
    "com.amazon.firebat": ["media_session_state"],
    "com.amazon.avod": ["media_session_state"],
    "com.netflix.ninja": ["media_session_state"],
    "com.spotify.tv.android": ["media_session_state"],
    "com.google.android.youtube.tv": ["media_session_state"],
    "com.plexapp.android": [
        {"paused": {"media_session_state": 3, "wake_lock_size": 1}},
        {"playing": {"media_session_state": 3}},
        "idle",
    ],
}


class FireTV(BaseTV):
    """Representa un dispositivo Fire TV.

    Parámetros
    ----------
    config : ADBConfig
        La configuración de conexión ADB.
    state_detection_rules : dict o None
        Reglas personalizadas de detección de estado. Si es None, se usan las predeterminadas de Fire TV.

    """

    DEVICE_TYPE: str = "firetv"

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

        # Usar reglas predeterminadas de Fire TV si no se proporcionan reglas personalizadas
        rules = state_detection_rules if state_detection_rules is not None else _FIRETV_DEFAULT_RULES

        super().__init__(adb=adb, config=config, state_detection_rules=rules)

    async def update(self, *, get_running_apps: bool = True, lazy: bool = True) -> DeviceState:
        """Actualizar el estado del dispositivo.

        Parámetros
        ----------
        get_running_apps : bool
            Si se debe obtener la lista de apps en ejecución.
        lazy : bool
            Si es True, omitir algunas consultas cuando el dispositivo está apagado.

        Retorna
        -------
        DeviceState
            El estado actual del dispositivo.

        """
        if not self.available:
            return DeviceState(state=State.UNAVAILABLE)

        # Obtener estado de pantalla, despierto y tamaño del wake lock
        screen_on, awake, wake_lock_size = await self.screen_on_awake_wake_lock_size()

        # Si la pantalla está apagada, el dispositivo está apagado/en espera
        if screen_on is None:
            return DeviceState(state=State.UNAVAILABLE)

        if not screen_on:
            return DeviceState(
                state=State.OFF,
                screen_on=False,
                awake=awake,
                wake_lock_size=wake_lock_size,
            )

        if not awake:
            return DeviceState(
                state=State.STANDBY,
                screen_on=True,
                awake=False,
                wake_lock_size=wake_lock_size,
            )

        # El dispositivo está encendido - obtener más información
        current_app, media_session_state = await self.current_app_media_session_state()

        # Obtener estado de audio
        audio_state_val = await self.audio_state()

        # Obtener apps en ejecución
        running_apps_list: list[str] = []
        if get_running_apps:
            apps = await self.running_apps()
            running_apps_list = apps if apps else []

        # Obtener entrada HDMI
        hdmi_input = await self.get_hdmi_input()

        # Obtener propiedades de volumen
        volume_props = await self.stream_music_properties()

        # Determinar el estado
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
        """Determinar el estado del dispositivo usando el motor de estado y respaldos de Fire TV.

        Parámetros
        ----------
        current_app : str o None
            La app en primer plano actual.
        media_session_state : int o None
            El estado de la sesión multimedia.
        wake_lock_size : int o None
            El tamaño del wake lock.
        audio_state : str o None
            El estado de audio.

        Retorna
        -------
        State
            El estado determinado.

        """
        # Intentar primero con el motor de detección de estado
        state = self._state_engine.detect_state(
            current_app=current_app,
            media_session_state=media_session_state,
            wake_lock_size=wake_lock_size,
            audio_state=audio_state,
        )
        if state is not None:
            return state

        # Respaldo de Fire TV: usar el estado de sesión multimedia
        if media_session_state == 2:
            return State.PAUSED
        if media_session_state == 3:
            return State.PLAYING

        # Respaldo de Fire TV: usar heurística del tamaño del wake lock
        # Fire TV típicamente tiene wake_lock_size >= 2 cuando está reproduciendo
        if wake_lock_size is not None:
            if wake_lock_size >= 3:
                return State.PLAYING
            if wake_lock_size == 2:
                return State.PAUSED

        # Respaldo: usar el estado de audio
        if audio_state == "paused":
            return State.PAUSED
        if audio_state == "playing":
            return State.PLAYING

        # Por defecto: inactivo
        return State.IDLE

    async def turn_on(self) -> None:
        """Encender el dispositivo Fire TV."""
        await self._adb.shell(CMD_TURN_ON_FIRETV)

    async def turn_off(self) -> None:
        """Apagar el dispositivo Fire TV."""
        await self._adb.shell(CMD_TURN_OFF_FIRETV)

    async def launch_app(self, app: str) -> None:
        """Lanzar una aplicación en Fire TV.

        Usa el intent LAUNCHER en lugar de LEANBACK_LAUNCHER.

        Parámetros
        ----------
        app : str
            El nombre del paquete de la app a lanzar.

        """
        cmd = CommandRegistry.launch_app(
            app,
            self._device_info.android_version,
            firetv=True,
        )
        await self._adb.shell(cmd)

    async def get_properties_dict(self) -> dict[str, Any]:
        """Obtener un diccionario de todas las propiedades del dispositivo.

        Retorna
        -------
        dict
            Un diccionario que contiene la información del dispositivo y el estado actual.

        """
        device_info = await self.get_device_properties()
        state = await self.update()

        return {
            "device_type": DeviceType.FIRE_TV,
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
