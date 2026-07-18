"""Constantes para la integración pyt_androidtv."""

DOMAIN = "pyt_androidtv"

# Valores por defecto
DEFAULT_PORT = 5555
DEFAULT_ADB_SERVER_PORT = 5037
DEFAULT_NAME = "Android TV"

# Tipos de dispositivo
DEVICE_ANDROIDTV = "androidtv"
DEVICE_FIRETV = "firetv"

# Atributos personalizados expuestos a HA
ATTR_ADB_RESPONSE = "adb_response"
ATTR_HDMI_INPUT = "hdmi_input"
ATTR_DEVICE_CLASS = "device_class"

# Intervalo de polling (segundos)
SCAN_INTERVAL_SECONDS = 10
