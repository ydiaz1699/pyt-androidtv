"""Plataforma Media Player para pyt-androidtv.

Expone el dispositivo Android TV/Fire TV como una entidad media_player
compatible con Home Assistant y tarjetas Mushroom Media Player.

Bugs corregidos respecto a versión anterior:
- async_mute_volume ahora respeta el parámetro booleano mute
- STATE_MAP incluye estado "stopped"
- async_select_source valida el source
- Reconexión automática ante pérdida de ADB
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.media_player import (
    MediaPlayerDeviceClass,
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
    MediaType,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=SCAN_INTERVAL_SECONDS)

# Bug 5 corregido: Incluir "stopped" en STATE_MAP
STATE_MAP: dict[str, MediaPlayerState | None] = {
    "idle": MediaPlayerState.IDLE,
    "off": MediaPlayerState.OFF,
    "playing": MediaPlayerState.PLAYING,
    "paused": MediaPlayerState.PAUSED,
    "standby": MediaPlayerState.STANDBY,
    "stopped": MediaPlayerState.IDLE,  # HA no tiene STOPPED, mapear a IDLE
    "unavailable": None,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurar la entidad media_player desde una entrada de configuración."""
    data = hass.data[DOMAIN][entry.entry_id]
    device = data["device"]

    entity = PytAndroidTVMediaPlayer(device, entry)
    async_add_entities([entity])


class PytAndroidTVMediaPlayer(MediaPlayerEntity):
    """Entidad Media Player para Android TV / Fire TV.

    Compatible con tarjeta Mushroom Media Player Card.
    Incluye reconexión automática ante pérdida de conexión ADB.
    """

    _attr_has_entity_name = True
    _attr_device_class = MediaPlayerDeviceClass.TV

    def __init__(self, device: Any, entry: ConfigEntry) -> None:
        """Inicializar la entidad media player."""
        self._device = device
        self._entry = entry
        self._state: MediaPlayerState | None = None
        self._current_app: str | None = None
        self._volume_level: float | None = None
        self._is_volume_muted: bool | None = None
        self._running_apps: list[str] = []
        self._hdmi_input: str | None = None
        self._reconnect_attempts: int = 0
        self._max_reconnect_attempts: int = 3

        device_info = device.device_info
        self._attr_unique_id = f"pyt_androidtv_{entry.data['host']}_{entry.data.get('port', 5555)}"
        self._attr_name = entry.data.get("name", device_info.model or "Android TV")

    @property
    def device_info(self):
        """Información del dispositivo para el registro de dispositivos HA."""
        info = self._device.device_info
        return {
            "identifiers": {(DOMAIN, self._attr_unique_id)},
            "name": self._attr_name,
            "manufacturer": info.manufacturer or "Android",
            "model": info.model or "TV",
            "sw_version": info.sw_version,
        }

    @property
    def supported_features(self) -> MediaPlayerEntityFeature:
        """Características soportadas (reconocidas por Mushroom Media Card)."""
        return (
            MediaPlayerEntityFeature.TURN_ON
            | MediaPlayerEntityFeature.TURN_OFF
            | MediaPlayerEntityFeature.PLAY
            | MediaPlayerEntityFeature.PAUSE
            | MediaPlayerEntityFeature.STOP
            | MediaPlayerEntityFeature.NEXT_TRACK
            | MediaPlayerEntityFeature.PREVIOUS_TRACK
            | MediaPlayerEntityFeature.VOLUME_SET
            | MediaPlayerEntityFeature.VOLUME_MUTE
            | MediaPlayerEntityFeature.VOLUME_STEP
            | MediaPlayerEntityFeature.SELECT_SOURCE
        )

    @property
    def state(self) -> MediaPlayerState | None:
        """Estado actual del media player."""
        return self._state

    @property
    def volume_level(self) -> float | None:
        """Nivel de volumen (0.0 a 1.0)."""
        return self._volume_level

    @property
    def is_volume_muted(self) -> bool | None:
        """Si el volumen está silenciado."""
        return self._is_volume_muted

    @property
    def source(self) -> str | None:
        """App actualmente en ejecución."""
        return self._current_app

    @property
    def source_list(self) -> list[str]:
        """Lista de apps en ejecución como fuentes disponibles."""
        return self._running_apps

    @property
    def media_title(self) -> str | None:
        """Título del medio (nombre legible de la app actual)."""
        from pyt_androidtv.constants import KNOWN_APPS

        if self._current_app and self._current_app in KNOWN_APPS:
            return KNOWN_APPS[self._current_app]
        return self._current_app

    @property
    def media_content_type(self) -> MediaType | None:
        """Tipo de contenido multimedia."""
        if self._state == MediaPlayerState.PLAYING:
            return MediaType.APP
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Atributos adicionales expuestos en la UI de HA."""
        attrs: dict[str, Any] = {}
        if self._hdmi_input:
            attrs["hdmi_input"] = self._hdmi_input
        if self._current_app:
            attrs["app_id"] = self._current_app
        attrs["running_apps"] = self._running_apps
        return attrs

    # === Actualización de estado con reconexión automática (Feature 5) ===

    async def async_update(self) -> None:
        """Actualizar el estado del dispositivo.

        Incluye reconexión automática: si el dispositivo no está disponible,
        intenta reconectar antes de reportar unavailable.
        """
        # Feature 5: Reconexión automática ante pérdida de ADB
        if not self._device.available:
            if self._reconnect_attempts < self._max_reconnect_attempts:
                self._reconnect_attempts += 1
                _LOGGER.info(
                    "Dispositivo no disponible, intento de reconexión %d/%d",
                    self._reconnect_attempts,
                    self._max_reconnect_attempts,
                )
                connected = await self._device.connect(log_errors=False)
                if connected:
                    _LOGGER.info("Reconexión exitosa a %s", self._entry.data["host"])
                    self._reconnect_attempts = 0
                else:
                    self._state = None
                    return
            else:
                self._state = None
                return

        try:
            state = await self._device.update()
            self._reconnect_attempts = 0  # Reset en update exitoso

            self._state = STATE_MAP.get(state.state.value)
            self._current_app = state.current_app
            self._volume_level = state.volume_level
            self._is_volume_muted = state.is_volume_muted
            self._running_apps = state.running_apps or []
            self._hdmi_input = state.hdmi_input

        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Error actualizando estado: %s", exc)
            self._state = None
            # Marcar para reconexión en el próximo ciclo
            self._reconnect_attempts += 1

    # === Comandos de control ===

    async def async_turn_on(self) -> None:
        """Encender el dispositivo."""
        await self._device.turn_on()

    async def async_turn_off(self) -> None:
        """Apagar el dispositivo."""
        await self._device.turn_off()

    async def async_media_play(self) -> None:
        """Reproducir."""
        await self._device.media_play()

    async def async_media_pause(self) -> None:
        """Pausar."""
        await self._device.media_pause()

    async def async_media_stop(self) -> None:
        """Detener."""
        await self._device.media_stop()

    async def async_media_next_track(self) -> None:
        """Siguiente pista/capítulo."""
        await self._device.media_next()

    async def async_media_previous_track(self) -> None:
        """Pista/capítulo anterior."""
        await self._device.media_previous()

    async def async_volume_up(self) -> None:
        """Subir volumen."""
        await self._device.volume_up()

    async def async_volume_down(self) -> None:
        """Bajar volumen."""
        await self._device.volume_down()

    async def async_set_volume_level(self, volume: float) -> None:
        """Establecer nivel de volumen (0.0 a 1.0)."""
        await self._device.set_volume_level(volume)

    async def async_mute_volume(self, mute: bool) -> None:
        """Silenciar o des-silenciar el volumen.

        Bug 2 corregido: Ahora respeta el parámetro booleano `mute`.
        Solo envía MUTE si el estado actual difiere del deseado.

        Parámetros
        ----------
        mute : bool
            True para silenciar, False para des-silenciar.
        """
        current_muted = self._is_volume_muted
        # Solo toggle si el estado actual es diferente al deseado
        if current_muted is None or current_muted != mute:
            await self._device.mute()

    async def async_select_source(self, source: str) -> None:
        """Lanzar una aplicación (seleccionar fuente).

        Bug 7 corregido: Valida que el source sea un package ID válido
        antes de intentar lanzarlo.

        Parámetros
        ----------
        source : str
            El package ID de la app a lanzar.
        """
        # Validar formato básico de package ID (com.xxx.yyy)
        if not source or "." not in source:
            _LOGGER.warning(
                "Source '%s' no parece un package ID válido (debe contener '.')",
                source,
            )
            return

        # Validar contra apps conocidas o en ejecución (advertencia, no bloqueo)
        from pyt_androidtv.constants import KNOWN_APPS

        if source not in self._running_apps and source not in KNOWN_APPS:
            _LOGGER.debug(
                "Source '%s' no está en running_apps ni en KNOWN_APPS, "
                "intentando lanzar de todos modos.",
                source,
            )

        await self._device.launch_app(source)
