"""Plataforma Camera para pyt-androidtv.

Feature 3: Expone una entidad camera que muestra capturas de pantalla
del dispositivo en tiempo real (con caché para no saturar ADB).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from homeassistant.components.camera import Camera
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Mínimo 5 segundos entre capturas para no saturar ADB
MIN_INTERVAL_SECONDS = 5


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurar la entidad camera desde una entrada de configuración."""
    data = hass.data[DOMAIN][entry.entry_id]
    device = data["device"]

    entity = PytAndroidTVCamera(device, entry)
    async_add_entities([entity])


class PytAndroidTVCamera(Camera):
    """Entidad Camera que muestra capturas de pantalla del dispositivo.

    Usa device.screencap() para obtener imágenes PNG del dispositivo.
    Implementa un caché temporal para evitar saturar la conexión ADB
    con demasiadas peticiones de captura.
    """

    _attr_has_entity_name = True
    _attr_is_streaming = False

    def __init__(self, device: Any, entry: ConfigEntry) -> None:
        """Inicializar la entidad camera."""
        super().__init__()
        self._device = device
        self._entry = entry
        self._last_image: bytes | None = None
        self._last_capture_time: float = 0
        self._attr_unique_id = f"pyt_androidtv_{entry.data['host']}_screen"
        self._attr_name = f"{entry.data.get('name', 'Android TV')} Pantalla"

    @property
    def device_info(self):
        """Información del dispositivo (se agrupa con el media_player)."""
        return {
            "identifiers": {
                (DOMAIN, f"pyt_androidtv_{self._entry.data['host']}_{self._entry.data.get('port', 5555)}")
            },
        }

    @property
    def is_on(self) -> bool:
        """Si la cámara está disponible."""
        return self._device.available

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Obtener una captura de pantalla del dispositivo.

        Implementa caché: si se pidió una imagen hace menos de
        MIN_INTERVAL_SECONDS, retorna la imagen cacheada.

        Parámetros
        ----------
        width : int o None
            Ancho deseado (no soportado, se ignora).
        height : int o None
            Alto deseado (no soportado, se ignora).

        Retorna
        -------
        bytes o None
            Imagen PNG de la pantalla, o None si no disponible.
        """
        if not self._device.available:
            return self._last_image

        # Caché: no capturar más seguido que MIN_INTERVAL_SECONDS
        now = time.time()
        if now - self._last_capture_time < MIN_INTERVAL_SECONDS:
            return self._last_image

        try:
            image = await self._device.screencap()
            if image:
                self._last_image = image
                self._last_capture_time = now
            return self._last_image
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Error capturando pantalla: %s", exc)
            return self._last_image
