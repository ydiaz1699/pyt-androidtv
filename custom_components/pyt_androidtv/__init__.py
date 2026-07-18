"""Integración pyt-androidtv para Home Assistant.

Esta integración permite controlar dispositivos Android TV y Fire TV
mediante ADB, proporcionando:
- Entidad media_player con control completo
- Servicios personalizados (tap, swipe, input_text, screencap)
- Diagnóstico del dispositivo
- Compatible con tarjetas Mushroom (Media Player Card)
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.REMOTE]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurar la integración desde una entrada de configuración."""
    hass.data.setdefault(DOMAIN, {})

    # Importar pyt_androidtv y crear la conexión
    from pyt_androidtv import AndroidTV
    from pyt_androidtv.models import ADBConfig

    config = ADBConfig(
        host=entry.data["host"],
        port=entry.data.get("port", 5555),
        adbkey=entry.data.get("adbkey", ""),
        adb_server_ip=entry.data.get("adb_server_ip", ""),
        adb_server_port=entry.data.get("adb_server_port", 5037),
    )

    # Determinar tipo de dispositivo
    device_class = entry.data.get("device_class", "androidtv")

    if device_class == "firetv":
        from pyt_androidtv import FireTV
        device = FireTV(config=config)
    else:
        device = AndroidTV(config=config)

    # Conectar al dispositivo
    connected = await device.connect()
    if not connected:
        _LOGGER.error(
            "No se pudo conectar a %s:%d",
            config.host,
            config.port,
        )
        return False

    # Obtener propiedades del dispositivo
    await device.get_device_properties()

    # Almacenar la instancia
    hass.data[DOMAIN][entry.entry_id] = {
        "device": device,
        "config": config,
    }

    # Configurar plataformas
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Registrar servicios personalizados
    await _async_register_services(hass)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Descargar una entrada de configuración."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        device = data["device"]
        await device.close()

    return unload_ok


async def _async_register_services(hass: HomeAssistant) -> None:
    """Registrar servicios personalizados para control avanzado."""
    import voluptuous as vol
    from homeassistant.helpers import config_validation as cv

    async def handle_adb_command(call) -> None:
        """Ejecutar un comando ADB personalizado."""
        entity_id = call.data["entity_id"]
        command = call.data["command"]

        for entry_data in hass.data[DOMAIN].values():
            device = entry_data["device"]
            result = await device.adb_shell(command)
            _LOGGER.info("ADB [%s]: %s -> %s", entity_id, command, result)

    async def handle_tap(call) -> None:
        """Ejecutar un toque en pantalla."""
        x = call.data["x"]
        y = call.data["y"]

        for entry_data in hass.data[DOMAIN].values():
            device = entry_data["device"]
            await device.tap(x, y)

    async def handle_swipe(call) -> None:
        """Ejecutar un deslizamiento en pantalla."""
        x1 = call.data["x1"]
        y1 = call.data["y1"]
        x2 = call.data["x2"]
        y2 = call.data["y2"]
        duration = call.data.get("duration_ms", 300)

        for entry_data in hass.data[DOMAIN].values():
            device = entry_data["device"]
            await device.swipe(x1, y1, x2, y2, duration)

    async def handle_input_text(call) -> None:
        """Escribir texto en el dispositivo."""
        text = call.data["text"]

        for entry_data in hass.data[DOMAIN].values():
            device = entry_data["device"]
            await device.input_text(text)

    # Registrar servicios
    if not hass.services.has_service(DOMAIN, "adb_command"):
        hass.services.async_register(
            DOMAIN,
            "adb_command",
            handle_adb_command,
            schema=vol.Schema({
                vol.Required("entity_id"): cv.entity_id,
                vol.Required("command"): cv.string,
            }),
        )

    if not hass.services.has_service(DOMAIN, "tap"):
        hass.services.async_register(
            DOMAIN,
            "tap",
            handle_tap,
            schema=vol.Schema({
                vol.Required("entity_id"): cv.entity_id,
                vol.Required("x"): cv.positive_int,
                vol.Required("y"): cv.positive_int,
            }),
        )

    if not hass.services.has_service(DOMAIN, "swipe"):
        hass.services.async_register(
            DOMAIN,
            "swipe",
            handle_swipe,
            schema=vol.Schema({
                vol.Required("entity_id"): cv.entity_id,
                vol.Required("x1"): cv.positive_int,
                vol.Required("y1"): cv.positive_int,
                vol.Required("x2"): cv.positive_int,
                vol.Required("y2"): cv.positive_int,
                vol.Optional("duration_ms", default=300): cv.positive_int,
            }),
        )

    if not hass.services.has_service(DOMAIN, "input_text"):
        hass.services.async_register(
            DOMAIN,
            "input_text",
            handle_input_text,
            schema=vol.Schema({
                vol.Required("entity_id"): cv.entity_id,
                vol.Required("text"): cv.string,
            }),
        )
