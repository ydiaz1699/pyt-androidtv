"""Flujo de configuración para la integración pyt_androidtv.

Permite configurar el dispositivo desde la UI de Home Assistant
con un formulario paso a paso.

Feature 4: Incluye OptionsFlow para configurar apps favoritas
desde la interfaz de HA después de la configuración inicial.
"""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME, CONF_PORT
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_PORT, DEVICE_ANDROIDTV, DEVICE_FIRETV, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
        vol.Optional(CONF_NAME, default="Android TV"): str,
        vol.Optional("device_class", default=DEVICE_ANDROIDTV): vol.In(
            [DEVICE_ANDROIDTV, DEVICE_FIRETV]
        ),
        vol.Optional("adbkey", default=""): str,
        vol.Optional("adb_server_ip", default=""): str,
    }
)


class PytAndroidTVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Flujo de configuración para pyt_androidtv."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> PytAndroidTVOptionsFlow:
        """Retornar el flujo de opciones para esta integración."""
        return PytAndroidTVOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manejar el paso de configuración del usuario.

        Se muestra un formulario para ingresar la IP, puerto,
        nombre y tipo de dispositivo.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                from pyt_androidtv import AndroidTV, FireTV
                from pyt_androidtv.models import ADBConfig

                config = ADBConfig(
                    host=user_input[CONF_HOST],
                    port=user_input.get(CONF_PORT, DEFAULT_PORT),
                    adbkey=user_input.get("adbkey", ""),
                    adb_server_ip=user_input.get("adb_server_ip", ""),
                )

                if user_input.get("device_class") == DEVICE_FIRETV:
                    device = FireTV(config=config)
                else:
                    device = AndroidTV(config=config)

                connected = await device.connect()
                if connected:
                    await device.get_device_properties()
                    info = device.device_info

                    if user_input.get(CONF_NAME) == "Android TV" and info.model:
                        user_input[CONF_NAME] = info.model

                    await device.close()

                    await self.async_set_unique_id(
                        f"{user_input[CONF_HOST]}:{user_input.get(CONF_PORT, DEFAULT_PORT)}"
                    )
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=user_input[CONF_NAME],
                        data=user_input,
                    )
                else:
                    errors["base"] = "cannot_connect"
                    await device.close()

            except Exception:  # noqa: BLE001
                _LOGGER.exception("Error durante la configuración")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )


class PytAndroidTVOptionsFlow(config_entries.OptionsFlow):
    """Flujo de opciones para configurar apps favoritas y preferencias.

    Permite al usuario seleccionar apps favoritas que se exponen como
    atributo 'favorite_apps' en la entidad media_player. Esto facilita
    la creación de chips Mushroom dinámicos sin editar YAML manualmente.

    Se accede desde: Ajustes > Integraciones > pyt-androidtv > Configurar
    """

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Inicializar el flujo de opciones."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Paso inicial del flujo de opciones."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Obtener las apps favoritas actuales
        current_favorites = self._config_entry.options.get("favorite_apps", "")
        current_scan_interval = self._config_entry.options.get("scan_interval", 10)
        current_reconnect_attempts = self._config_entry.options.get("reconnect_attempts", 3)

        # Obtener las apps instaladas del dispositivo para sugerencias
        installed_apps_hint = ""
        data = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
        if data and data.get("device") and data["device"].available:
            try:
                apps = await data["device"].get_installed_apps()
                if apps:
                    # Mostrar las primeras 10 como sugerencia
                    installed_apps_hint = ", ".join(apps[:10])
            except Exception:  # noqa: BLE001
                pass

        schema = vol.Schema(
            {
                vol.Optional(
                    "favorite_apps",
                    default=current_favorites,
                    description={
                        "suggested_value": current_favorites,
                    },
                ): str,
                vol.Optional(
                    "scan_interval",
                    default=current_scan_interval,
                ): vol.All(int, vol.Range(min=5, max=60)),
                vol.Optional(
                    "reconnect_attempts",
                    default=current_reconnect_attempts,
                ): vol.All(int, vol.Range(min=1, max=10)),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders={
                "installed_apps_hint": installed_apps_hint or "No disponible",
            },
        )
