"""Plataforma Sensor para pyt-androidtv.

Feature 2: Expone un sensor con la lista de aplicaciones instaladas
en el dispositivo. Se actualiza con menor frecuencia que el media_player
(cada 1 hora por defecto) para no saturar ADB.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Actualizar apps instaladas cada hora (es una operación pesada)
SCAN_INTERVAL = timedelta(hours=1)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Configurar el sensor de apps instaladas."""
    data = hass.data[DOMAIN][entry.entry_id]
    device = data["device"]

    entities = [
        InstalledAppsSensor(device, entry),
        RunningAppsSensor(device, entry),
    ]
    async_add_entities(entities)


class InstalledAppsSensor(SensorEntity):
    """Sensor que muestra el número de aplicaciones instaladas.

    El atributo extra 'apps' contiene la lista completa de package IDs.
    Útil para poblar dinámicamente chips de Mushroom o selectores.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:apps"

    def __init__(self, device: Any, entry: ConfigEntry) -> None:
        """Inicializar el sensor de apps instaladas."""
        self._device = device
        self._entry = entry
        self._apps: list[str] = []
        self._attr_unique_id = f"pyt_androidtv_{entry.data['host']}_installed_apps"
        self._attr_name = f"{entry.data.get('name', 'Android TV')} Apps Instaladas"

    @property
    def device_info(self):
        """Información del dispositivo (se agrupa con el media_player)."""
        return {
            "identifiers": {
                (DOMAIN, f"pyt_androidtv_{self._entry.data['host']}_{self._entry.data.get('port', 5555)}")
            },
        }

    @property
    def native_value(self) -> int:
        """Número de apps instaladas."""
        return len(self._apps)

    @property
    def native_unit_of_measurement(self) -> str:
        """Unidad de medida."""
        return "apps"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Lista completa de apps como atributo."""
        return {
            "apps": self._apps,
            "total": len(self._apps),
        }

    async def async_update(self) -> None:
        """Actualizar la lista de apps instaladas."""
        try:
            if self._device.available:
                self._apps = await self._device.get_installed_apps()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Error obteniendo apps instaladas: %s", exc)


class RunningAppsSensor(SensorEntity):
    """Sensor que muestra el número de aplicaciones en ejecución.

    Se actualiza con la misma frecuencia que el media_player.
    """

    _attr_has_entity_name = True
    _attr_icon = "mdi:application-cog"

    def __init__(self, device: Any, entry: ConfigEntry) -> None:
        """Inicializar el sensor de apps en ejecución."""
        self._device = device
        self._entry = entry
        self._apps: list[str] = []
        self._attr_unique_id = f"pyt_androidtv_{entry.data['host']}_running_apps"
        self._attr_name = f"{entry.data.get('name', 'Android TV')} Apps en Ejecución"

    @property
    def device_info(self):
        """Información del dispositivo."""
        return {
            "identifiers": {
                (DOMAIN, f"pyt_androidtv_{self._entry.data['host']}_{self._entry.data.get('port', 5555)}")
            },
        }

    @property
    def native_value(self) -> int:
        """Número de apps en ejecución."""
        return len(self._apps)

    @property
    def native_unit_of_measurement(self) -> str:
        """Unidad de medida."""
        return "apps"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Lista de apps en ejecución como atributo."""
        return {
            "apps": self._apps,
            "total": len(self._apps),
        }

    async def async_update(self) -> None:
        """Actualizar la lista de apps en ejecución."""
        try:
            if self._device.available:
                apps = await self._device.running_apps()
                self._apps = apps or []
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Error obteniendo apps en ejecución: %s", exc)
