"""Integración pyt-androidtv para Home Assistant.

Esta integración permite controlar dispositivos Android TV y Fire TV
mediante ADB, proporcionando:
- Entidad media_player con control completo
- Entidad camera para capturas de pantalla en vivo
- Sensor de apps instaladas
- Servicios personalizados (tap, swipe, input_text, adb_command, search_in_app, record_screen)
- Diagnóstico del dispositivo
- Compatible con tarjetas Mushroom (Media Player Card)
"""

from __future__ import annotations

import logging
import os

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.MEDIA_PLAYER, Platform.SENSOR, Platform.CAMERA]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Configurar la integración desde una entrada de configuración."""
    hass.data.setdefault(DOMAIN, {})

    from pyt_androidtv import AndroidTV
    from pyt_androidtv.models import ADBConfig

    config = ADBConfig(
        host=entry.data["host"],
        port=entry.data.get("port", 5555),
        adbkey=entry.data.get("adbkey", ""),
        adb_server_ip=entry.data.get("adb_server_ip", ""),
        adb_server_port=entry.data.get("adb_server_port", 5037),
    )

    device_class = entry.data.get("device_class", "androidtv")

    if device_class == "firetv":
        from pyt_androidtv import FireTV
        device = FireTV(config=config)
    else:
        device = AndroidTV(config=config)

    connected = await device.connect()
    if not connected:
        _LOGGER.error("No se pudo conectar a %s:%d", config.host, config.port)
        return False

    await device.get_device_properties()

    # Almacenar la instancia indexada por entry_id
    hass.data[DOMAIN][entry.entry_id] = {
        "device": device,
        "config": config,
        "entity_id": None,  # Se asigna cuando la entidad se registre
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
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


def _resolve_device_from_entity_id(hass: HomeAssistant, entity_id: str):
    """Resolver el dispositivo correcto a partir de un entity_id.

    Busca en el registry de entidades a qué config_entry pertenece
    el entity_id dado, y retorna el dispositivo asociado.

    Parámetros
    ----------
    hass : HomeAssistant
        La instancia de Home Assistant.
    entity_id : str
        El entity_id del media_player (ej: media_player.android_tv_salon).

    Retorna
    -------
    device o None
        La instancia del dispositivo pyt-androidtv, o None si no se encuentra.
    """
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)

    if entry and entry.config_entry_id:
        data = hass.data.get(DOMAIN, {}).get(entry.config_entry_id)
        if data:
            return data["device"]

    # Fallback: si solo hay un dispositivo, usarlo
    devices = hass.data.get(DOMAIN, {})
    if len(devices) == 1:
        return next(iter(devices.values()))["device"]

    _LOGGER.warning(
        "No se pudo resolver el dispositivo para entity_id=%s. "
        "Hay %d dispositivos configurados.",
        entity_id,
        len(devices),
    )
    return None


async def _async_register_services(hass: HomeAssistant) -> None:
    """Registrar servicios personalizados para control avanzado."""
    import voluptuous as vol
    from homeassistant.helpers import config_validation as cv

    async def handle_adb_command(call: ServiceCall) -> None:
        """Ejecutar un comando ADB personalizado."""
        entity_id = call.data["entity_id"]
        command = call.data["command"]

        device = _resolve_device_from_entity_id(hass, entity_id)
        if device is None:
            _LOGGER.error("Dispositivo no encontrado para %s", entity_id)
            return

        result = await device.adb_shell(command)
        _LOGGER.info("ADB [%s]: %s -> %s", entity_id, command, result)

    async def handle_tap(call: ServiceCall) -> None:
        """Ejecutar un toque en pantalla."""
        entity_id = call.data["entity_id"]
        x = call.data["x"]
        y = call.data["y"]

        device = _resolve_device_from_entity_id(hass, entity_id)
        if device is None:
            _LOGGER.error("Dispositivo no encontrado para %s", entity_id)
            return

        await device.tap(x, y)

    async def handle_swipe(call: ServiceCall) -> None:
        """Ejecutar un deslizamiento en pantalla."""
        entity_id = call.data["entity_id"]
        x1 = call.data["x1"]
        y1 = call.data["y1"]
        x2 = call.data["x2"]
        y2 = call.data["y2"]
        duration = call.data.get("duration_ms", 300)

        device = _resolve_device_from_entity_id(hass, entity_id)
        if device is None:
            _LOGGER.error("Dispositivo no encontrado para %s", entity_id)
            return

        await device.swipe(x1, y1, x2, y2, duration)

    async def handle_input_text(call: ServiceCall) -> None:
        """Escribir texto en el dispositivo."""
        entity_id = call.data["entity_id"]
        text = call.data["text"]

        device = _resolve_device_from_entity_id(hass, entity_id)
        if device is None:
            _LOGGER.error("Dispositivo no encontrado para %s", entity_id)
            return

        await device.input_text(text)

    async def handle_search_in_app(call: ServiceCall) -> None:
        """Lanzar una app y buscar texto dentro de ella.

        Combina launch_app + espera + input_text + ENTER.
        """
        entity_id = call.data["entity_id"]
        app = call.data["app"]
        query = call.data["query"]
        delay_s = call.data.get("delay_s", 3)

        device = _resolve_device_from_entity_id(hass, entity_id)
        if device is None:
            _LOGGER.error("Dispositivo no encontrado para %s", entity_id)
            return

        import asyncio

        # Lanzar la app
        await device.launch_app(app)
        # Esperar a que cargue
        await asyncio.sleep(delay_s)
        # Abrir búsqueda (click en icono búsqueda - normalmente la tecla SEARCH)
        await device.send_key_code(84)  # KEY_SEARCH
        await asyncio.sleep(1)
        # Escribir texto
        await device.input_text(query)
        await asyncio.sleep(0.5)
        # Enviar ENTER para buscar
        await device.send_key_code(66)  # KEY_ENTER

        _LOGGER.info("Búsqueda '%s' en %s completada", query, app)

    async def handle_record_screen(call: ServiceCall) -> None:
        """Grabar la pantalla y descargar el archivo.

        Graba la pantalla del dispositivo durante la duración especificada,
        luego descarga el archivo .mp4 al directorio www/ de HA.
        """
        entity_id = call.data["entity_id"]
        duration_s = call.data.get("duration_s", 10)
        filename = call.data.get("filename", "screen_recording.mp4")

        device = _resolve_device_from_entity_id(hass, entity_id)
        if device is None:
            _LOGGER.error("Dispositivo no encontrado para %s", entity_id)
            return

        import asyncio

        device_path = f"/sdcard/{filename}"
        local_dir = hass.config.path("www", "pyt_androidtv")
        local_path = os.path.join(local_dir, filename)

        # Crear directorio si no existe
        os.makedirs(local_dir, exist_ok=True)

        # Grabar pantalla
        max_duration = min(duration_s, 180)
        _LOGGER.info("Grabando pantalla por %d segundos...", max_duration)
        await device.adb_shell(f"screenrecord {device_path} --time-limit {max_duration}")

        # Esperar a que termine la grabación + margen
        await asyncio.sleep(max_duration + 2)

        # Descargar archivo
        try:
            await device._adb.pull(device_path, local_path)
            _LOGGER.info("Grabación descargada a: %s", local_path)

            # Limpiar archivo del dispositivo
            await device.adb_shell(f"rm {device_path}")

            # Notificar al usuario
            await hass.services.async_call(
                "persistent_notification",
                "create",
                {
                    "title": "Grabación de pantalla lista",
                    "message": f"Archivo disponible en: /local/pyt_androidtv/{filename}",
                },
            )
        except Exception as exc:  # noqa: BLE001
            _LOGGER.error("Error descargando grabación: %s", exc)

    # --- Registrar todos los servicios ---

    if not hass.services.has_service(DOMAIN, "adb_command"):
        hass.services.async_register(
            DOMAIN, "adb_command", handle_adb_command,
            schema=vol.Schema({
                vol.Required("entity_id"): cv.entity_id,
                vol.Required("command"): cv.string,
            }),
        )

    if not hass.services.has_service(DOMAIN, "tap"):
        hass.services.async_register(
            DOMAIN, "tap", handle_tap,
            schema=vol.Schema({
                vol.Required("entity_id"): cv.entity_id,
                vol.Required("x"): cv.positive_int,
                vol.Required("y"): cv.positive_int,
            }),
        )

    if not hass.services.has_service(DOMAIN, "swipe"):
        hass.services.async_register(
            DOMAIN, "swipe", handle_swipe,
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
            DOMAIN, "input_text", handle_input_text,
            schema=vol.Schema({
                vol.Required("entity_id"): cv.entity_id,
                vol.Required("text"): cv.string,
            }),
        )

    if not hass.services.has_service(DOMAIN, "search_in_app"):
        hass.services.async_register(
            DOMAIN, "search_in_app", handle_search_in_app,
            schema=vol.Schema({
                vol.Required("entity_id"): cv.entity_id,
                vol.Required("app"): cv.string,
                vol.Required("query"): cv.string,
                vol.Optional("delay_s", default=3): vol.Coerce(float),
            }),
        )

    if not hass.services.has_service(DOMAIN, "record_screen"):
        hass.services.async_register(
            DOMAIN, "record_screen", handle_record_screen,
            schema=vol.Schema({
                vol.Required("entity_id"): cv.entity_id,
                vol.Optional("duration_s", default=10): cv.positive_int,
                vol.Optional("filename", default="screen_recording.mp4"): cv.string,
            }),
        )
