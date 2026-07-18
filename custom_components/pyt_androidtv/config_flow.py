"""Flujo de configuración para la integración pyt_androidtv.

Permite configurar el dispositivo desde la UI de Home Assistant
con un formulario paso a paso.
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

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manejar el paso de configuración del usuario.

        Se muestra un formulario para ingresar la IP, puerto,
        nombre y tipo de dispositivo.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Intentar conectar al dispositivo
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

                    # Usar el modelo como nombre si no se proporcionó
                    if user_input.get(CONF_NAME) == "Android TV" and info.model:
                        user_input[CONF_NAME] = info.model

                    await device.close()

                    # Verificar que no existe ya
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
