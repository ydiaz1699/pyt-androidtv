"""Constantes utilizadas en todo pyt-androidtv.

Enlaces:
    - Códigos de eventos de tecla ADB: https://developer.android.com/reference/android/view/KeyEvent
    - MediaSession PlaybackState: https://developer.android.com/reference/android/media/session/PlaybackState
"""

from __future__ import annotations

import re
from typing import Final

# ============================================================================
# Códigos de Teclas
# ============================================================================

KEYS: Final[dict[str, int]] = {
    "BACK": 4,
    "HOME": 3,
    "UP": 19,
    "DOWN": 20,
    "LEFT": 21,
    "RIGHT": 22,
    "CENTER": 23,
    "ENTER": 66,
    "MENU": 82,
    "POWER": 26,
    "SLEEP": 223,
    "WAKEUP": 224,
    "VOLUME_UP": 24,
    "VOLUME_DOWN": 25,
    "MUTE": 164,
    "PLAY": 126,
    "PAUSE": 127,
    "PLAY_PAUSE": 85,
    "STOP": 86,
    "NEXT": 87,
    "PREVIOUS": 88,
    "FAST_FORWARD": 90,
    "REWIND": 89,
    "RED": 183,
    "GREEN": 184,
    "YELLOW": 185,
    "BLUE": 186,
    "HDMI1": 243,
    "HDMI2": 244,
    "HDMI3": 245,
    "HDMI4": 246,
    "INPUT": 178,
    "SEARCH": 84,
    "SETTINGS": 176,
    "ESCAPE": 111,
    "SPACE": 62,
    # Teclas numéricas (0-9)
    "0": 7,
    "1": 8,
    "2": 9,
    "3": 10,
    "4": 11,
    "5": 12,
    "6": 13,
    "7": 14,
    "8": 15,
    "9": 16,
    # Teclas alfabéticas (A-Z)
    "A": 29,
    "B": 30,
    "C": 31,
    "D": 32,
    "E": 33,
    "F": 34,
    "G": 35,
    "H": 36,
    "I": 37,
    "J": 38,
    "K": 39,
    "L": 40,
    "M": 41,
    "N": 42,
    "O": 43,
    "P": 44,
    "Q": 45,
    "R": 46,
    "S": 47,
    "T": 48,
    "U": 49,
    "V": 50,
    "W": 51,
    "X": 52,
    "Y": 53,
    "Z": 54,
}

# ============================================================================
# Intents
# ============================================================================

INTENT_LAUNCH: Final[str] = "android.intent.category.LEANBACK_LAUNCHER"
INTENT_LAUNCH_FIRETV: Final[str] = "android.intent.category.LAUNCHER"

# ============================================================================
# Comandos de Shell ADB
# ============================================================================

#: Imprime '1' si el comando anterior tuvo éxito, '0' en caso contrario
CMD_SUCCESS1_FAILURE0: Final[str] = r" && echo -e '1\c' || echo -e '0\c'"

#: Determinar si la pantalla está encendida
CMD_SCREEN_ON: Final[str] = (
    "(dumpsys power | grep 'Display Power' | grep -q 'state=ON' "
    "|| dumpsys power | grep -q 'mScreenOn=true' "
    "|| dumpsys display | grep -q 'mScreenState=ON')"
)

#: Determinar si el dispositivo está despierto
CMD_AWAKE: Final[str] = "dumpsys power | grep mWakefulness | grep -q Awake"

#: Obtener el tamaño del wake lock
CMD_WAKE_LOCK_SIZE: Final[str] = "dumpsys power | grep Locks | grep 'size='"

#: Obtener pantalla encendida + despierto + tamaño del wake lock en una sola llamada
CMD_SCREEN_ON_AWAKE_WAKE_LOCK_SIZE: Final[str] = (
    CMD_SCREEN_ON + CMD_SUCCESS1_FAILURE0 + " && " + CMD_AWAKE + CMD_SUCCESS1_FAILURE0 + " && " + CMD_WAKE_LOCK_SIZE
)

#: Obtener las aplicaciones en ejecución
CMD_RUNNING_APPS: Final[str] = "ps -A | grep u0_a"

#: Obtener aplicaciones instaladas
CMD_INSTALLED_APPS: Final[str] = "pm list packages"

#: Obtener el bloque STREAM_MUSIC de dumpsys audio
CMD_STREAM_MUSIC: Final[str] = r"dumpsys audio | grep '\- STREAM_MUSIC:' -A 11"

#: Obtener el fabricante
CMD_MANUFACTURER: Final[str] = "getprop ro.product.manufacturer"

#: Obtener el modelo
CMD_MODEL: Final[str] = "getprop ro.product.model"

#: Obtener el número de serie
CMD_SERIALNO: Final[str] = "getprop ro.serialno"

#: Obtener la versión de Android
CMD_VERSION: Final[str] = "getprop ro.build.version.release"

#: Obtener el ID del producto
CMD_PRODUCT_ID: Final[str] = "getprop ro.product.vendor.device"

#: Obtener la dirección MAC de WiFi
CMD_MAC_WLAN0: Final[str] = "ip addr show wlan0 | grep -m 1 ether"

#: Obtener la dirección MAC de Ethernet
CMD_MAC_ETH0: Final[str] = "ip addr show eth0 | grep -m 1 ether"

#: Obtener todas las propiedades del dispositivo en una sola llamada
CMD_DEVICE_PROPERTIES: Final[str] = (
    CMD_MANUFACTURER + " && " + CMD_MODEL + " && " + CMD_SERIALNO + " && " + CMD_VERSION + " && " + CMD_PRODUCT_ID
)

#: Obtener el estado de la sesión multimedia (requiere que CURRENT_APP esté definido)
CMD_MEDIA_SESSION_STATE: Final[str] = (
    "dumpsys media_session | grep -A 100 'Sessions Stack' "
    "| grep -A 100 $CURRENT_APP | grep -m 1 'state=PlaybackState {'"
)

#: Apagar un dispositivo Android TV
CMD_TURN_OFF_ANDROIDTV: Final[str] = CMD_SCREEN_ON + " && input keyevent 26"

#: Apagar un dispositivo Fire TV
CMD_TURN_OFF_FIRETV: Final[str] = CMD_SCREEN_ON + " && input keyevent 223"

#: Encender un dispositivo Android TV
CMD_TURN_ON_ANDROIDTV: Final[str] = CMD_SCREEN_ON + " || input keyevent 26"

#: Encender un dispositivo Fire TV
CMD_TURN_ON_FIRETV: Final[str] = CMD_SCREEN_ON + " || (input keyevent 26 && input keyevent 3)"

# ============================================================================
# Comandos de estado de audio
# ============================================================================

#: Obtener estado de audio (Android < 11)
_CMD_AUDIO_STATE: Final[str] = (
    r"dumpsys audio | grep paused | grep -qv 'Buffer Queue' && echo -e '1\c' "
    r"|| (dumpsys audio | grep started | grep -qv 'Buffer Queue' && echo '2\c' || echo '0\c')"
)

#: Obtener estado de audio (Android 11+)
_CMD_AUDIO_STATE11: Final[str] = (
    "CURRENT_AUDIO_STATE=$(dumpsys audio | sed -r -n "
    "'/[0-9]{2}-[0-9]{2}.*player piid:.*(state|event):(started|paused|stopped).*$/h; ${x;p;}') && "
    r"echo $CURRENT_AUDIO_STATE | grep -q paused && echo -e '1\c' "
    r"|| { echo $CURRENT_AUDIO_STATE | grep -q started && echo '2\c' || echo '0\c' ; }"
)

# ============================================================================
# Comandos de la app actual
# ============================================================================

_CMD_PARSE_CURRENT_APP: Final[str] = (
    "CURRENT_APP=${CURRENT_APP#*ActivityRecord{* * } "
    "&& CURRENT_APP=${CURRENT_APP#*{* * } "
    "&& CURRENT_APP=${CURRENT_APP%%/*} "
    r"&& CURRENT_APP=${CURRENT_APP%\}*}"
)

_CMD_PARSE_CURRENT_APP11: Final[str] = "CURRENT_APP=${CURRENT_APP%%/*} && CURRENT_APP=${CURRENT_APP##* }"

_CMD_DEFINE_CURRENT_APP: Final[str] = (
    "CURRENT_APP=$(dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp') && " + _CMD_PARSE_CURRENT_APP
)

_CMD_DEFINE_CURRENT_APP11: Final[str] = (
    "CURRENT_APP=$(dumpsys window windows | grep -E 'mInputMethod(Input)?Target') && " + _CMD_PARSE_CURRENT_APP11
)

_CMD_DEFINE_CURRENT_APP12: Final[str] = (
    "CURRENT_APP=$(dumpsys window windows | grep -E 'mCurrentFocus|mFocusedApp|mObscuringWindow') && "
    + _CMD_PARSE_CURRENT_APP11
)

_CMD_DEFINE_CURRENT_APP13: Final[str] = (
    "CURRENT_APP=$(dumpsys window windows | grep -E -m 1 'imeLayeringTarget|imeInputTarget|imeControlTarget') && "
    + _CMD_PARSE_CURRENT_APP11
)

#: Obtener la app actual (Android < 11)
_CMD_CURRENT_APP: Final[str] = _CMD_DEFINE_CURRENT_APP + " && echo $CURRENT_APP"

#: Obtener la app actual (Android 11)
_CMD_CURRENT_APP11: Final[str] = _CMD_DEFINE_CURRENT_APP11 + " && echo $CURRENT_APP"

#: Obtener la app actual (Android 12)
_CMD_CURRENT_APP12: Final[str] = _CMD_DEFINE_CURRENT_APP12 + " && echo $CURRENT_APP"

#: Obtener la app actual (Android 13+)
_CMD_CURRENT_APP13: Final[str] = _CMD_DEFINE_CURRENT_APP13 + " && echo $CURRENT_APP"

# ============================================================================
# Comandos de app actual + estado de sesión multimedia
# ============================================================================

_CMD_CURRENT_APP_MEDIA_SESSION_STATE: Final[str] = _CMD_CURRENT_APP + " && " + CMD_MEDIA_SESSION_STATE
_CMD_CURRENT_APP_MEDIA_SESSION_STATE11: Final[str] = _CMD_CURRENT_APP11 + " && " + CMD_MEDIA_SESSION_STATE
_CMD_CURRENT_APP_MEDIA_SESSION_STATE12: Final[str] = _CMD_CURRENT_APP12 + " && " + CMD_MEDIA_SESSION_STATE
_CMD_CURRENT_APP_MEDIA_SESSION_STATE13: Final[str] = _CMD_CURRENT_APP13 + " && " + CMD_MEDIA_SESSION_STATE

# ============================================================================
# Comandos de ajuste de volumen
# ============================================================================

_CMD_VOLUME_SET: Final[str] = "media volume --show --stream 3 --set {}"
_CMD_VOLUME_SET11: Final[str] = "cmd media_session volume --show --stream 3 --set {}"

# ============================================================================
# Comandos de entrada HDMI
# ============================================================================

_CMD_HDMI_INPUT: Final[str] = (
    "dumpsys activity starter | grep -E -o '(ExternalTv|HDMI)InputService/HW[0-9]' -m 1 | grep -o 'HW[0-9]'"
)

_CMD_HDMI_INPUT11: Final[str] = (
    "(HDMI=$(dumpsys tv_input | grep 'ResourceClientProfile {.*}' | grep -o -E '(hdmi_port=[0-9]|TV)') "
    "&& { echo ${HDMI/hdmi_port=/HW} | cut -d' ' -f1 ; }) || " + _CMD_HDMI_INPUT
)

# ============================================================================
# Comandos de lanzamiento de aplicaciones
# ============================================================================

_CMD_LAUNCH_APP_CONDITION: Final[str] = (
    "if [ $CURRENT_APP != '{0}' ]; then monkey -p {0} -c " + INTENT_LAUNCH + " --pct-syskeys 0 1; fi"
)

_CMD_LAUNCH_APP_CONDITION_FIRETV: Final[str] = (
    "if [ $CURRENT_APP != '{0}' ]; then monkey -p {0} -c " + INTENT_LAUNCH_FIRETV + " --pct-syskeys 0 1; fi"
)


# ============================================================================
# CommandRegistry - selección de comandos según la versión
# ============================================================================


class CommandRegistry:
    """Registro para seleccionar el comando ADB correcto según la versión de Android."""

    # (versión_mínima, versión_máxima, comando) - versión_máxima es inclusiva, None significa sin límite
    _AUDIO_STATE_COMMANDS: Final[list[tuple[int | None, int | None, str]]] = [
        (None, 10, _CMD_AUDIO_STATE),
        (11, None, _CMD_AUDIO_STATE11),
    ]

    _CURRENT_APP_COMMANDS: Final[list[tuple[int | None, int | None, str]]] = [
        (None, 10, _CMD_CURRENT_APP),
        (11, 11, _CMD_CURRENT_APP11),
        (12, 12, _CMD_CURRENT_APP12),
        (13, None, _CMD_CURRENT_APP13),
    ]

    _CURRENT_APP_MEDIA_SESSION_STATE_COMMANDS: Final[list[tuple[int | None, int | None, str]]] = [
        (None, 10, _CMD_CURRENT_APP_MEDIA_SESSION_STATE),
        (11, 11, _CMD_CURRENT_APP_MEDIA_SESSION_STATE11),
        (12, 12, _CMD_CURRENT_APP_MEDIA_SESSION_STATE12),
        (13, None, _CMD_CURRENT_APP_MEDIA_SESSION_STATE13),
    ]

    _VOLUME_SET_COMMANDS: Final[list[tuple[int | None, int | None, str]]] = [
        (None, 10, _CMD_VOLUME_SET),
        (11, None, _CMD_VOLUME_SET11),
    ]

    _HDMI_INPUT_COMMANDS: Final[list[tuple[int | None, int | None, str]]] = [
        (None, 10, _CMD_HDMI_INPUT),
        (11, None, _CMD_HDMI_INPUT11),
    ]

    @staticmethod
    def _lookup(commands: list[tuple[int | None, int | None, str]], android_version: int | None) -> str:
        """Buscar el comando apropiado para la versión de Android dada.

        Parámetros
        ----------
        commands : list
            Lista de tuplas (versión_mín, versión_máx, comando).
        android_version : int o None
            La versión de Android, o None para usar el comando por defecto (primero).

        Retorna
        -------
        str
            La cadena de comando correspondiente.

        """
        if android_version is None:
            return commands[0][2]

        for min_ver, max_ver, cmd in commands:
            if (min_ver is None or android_version >= min_ver) and (max_ver is None or android_version <= max_ver):
                return cmd

        # Respaldo al último comando si ningún rango coincidió
        return commands[-1][2]

    @classmethod
    def audio_state(cls, android_version: int | None = None) -> str:
        """Obtener el comando de estado de audio para la versión de Android dada."""
        return cls._lookup(cls._AUDIO_STATE_COMMANDS, android_version)

    @classmethod
    def current_app(cls, android_version: int | None = None) -> str:
        """Obtener el comando de la app actual para la versión de Android dada."""
        return cls._lookup(cls._CURRENT_APP_COMMANDS, android_version)

    @classmethod
    def current_app_media_session_state(cls, android_version: int | None = None) -> str:
        """Obtener el comando de app actual + estado de sesión multimedia para la versión de Android dada."""
        return cls._lookup(cls._CURRENT_APP_MEDIA_SESSION_STATE_COMMANDS, android_version)

    @classmethod
    def volume_set(cls, volume: int, android_version: int | None = None) -> str:
        """Obtener el comando de ajuste de volumen para la versión de Android dada."""
        cmd_template = cls._lookup(cls._VOLUME_SET_COMMANDS, android_version)
        return cmd_template.format(volume)

    @classmethod
    def hdmi_input(cls, android_version: int | None = None) -> str:
        """Obtener el comando de entrada HDMI para la versión de Android dada."""
        return cls._lookup(cls._HDMI_INPUT_COMMANDS, android_version)

    @classmethod
    def launch_app(cls, app: str, android_version: int | None = None, *, firetv: bool = False) -> str:
        """Obtener el comando de lanzamiento de app para la versión de Android y tipo de dispositivo dados."""
        if firetv:
            define = _CMD_DEFINE_CURRENT_APP.replace("{", "{{").replace("}", "}}")
            condition = _CMD_LAUNCH_APP_CONDITION_FIRETV
        elif android_version is None or android_version < 11:
            define = _CMD_DEFINE_CURRENT_APP.replace("{", "{{").replace("}", "}}")
            condition = _CMD_LAUNCH_APP_CONDITION
        elif android_version == 11:
            define = _CMD_DEFINE_CURRENT_APP11.replace("{", "{{").replace("}", "}}")
            condition = _CMD_LAUNCH_APP_CONDITION
        elif android_version == 12:
            define = _CMD_DEFINE_CURRENT_APP12.replace("{", "{{").replace("}", "}}")
            condition = _CMD_LAUNCH_APP_CONDITION
        else:
            define = _CMD_DEFINE_CURRENT_APP13.replace("{", "{{").replace("}", "}}")
            condition = _CMD_LAUNCH_APP_CONDITION

        return (define + " && " + condition).format(app)


# ============================================================================
# Expresiones Regulares
# ============================================================================

REGEX_MEDIA_SESSION_STATE: Final[re.Pattern[str]] = re.compile(r"state=(?P<state>[0-9]+)", re.MULTILINE)
REGEX_WAKE_LOCK_SIZE: Final[re.Pattern[str]] = re.compile(r"size=(?P<size>[0-9]+)")
REGEX_MAC_ADDRESS: Final[re.Pattern[str]] = re.compile(r"ether (.*?) brd")
REGEX_DEVICE: Final[re.Pattern[str]] = re.compile(r"Devices: (.*?)\W")
REGEX_MAX_VOLUME: Final[re.Pattern[str]] = re.compile(r"Max: (\d{1,})")
REGEX_MUTED: Final[re.Pattern[str]] = re.compile(r"Muted: (.*?)\W")
REGEX_STREAM_MUSIC: Final[re.Pattern[str]] = re.compile(r"STREAM_MUSIC(.*?)- STREAM", re.DOTALL | re.MULTILINE)
REGEX_VOLUME: Final[re.Pattern[str]] = re.compile(r"\): (\d{1,})")

# ============================================================================
# Aplicaciones Conocidas
# ============================================================================

KNOWN_APPS: Final[dict[str, str]] = {
    "com.amazon.avod": "Amazon Video",
    "com.amazon.avod.thirdpartyclient": "Amazon Prime Video",
    "com.apple.atve.android.appletv": "Apple TV+",
    "com.disney.disneyplus": "Disney+",
    "com.google.android.tvlauncher": "Android TV Launcher",
    "com.google.android.youtube.tv": "YouTube",
    "com.google.android.youtube.tvmusic": "YouTube Music",
    "com.hbo.hbonow": "HBO Max",
    "com.hulu.plus": "Hulu",
    "com.netflix.ninja": "Netflix",
    "com.plexapp.android": "Plex",
    "com.spotify.tv.android": "Spotify",
    "com.amazon.tv.launcher": "Fire TV Launcher",
    "com.amazon.firebat": "Prime Video (Fire TV)",
    "org.xbmc.kodi": "Kodi",
    "tv.emby.embyatv": "Emby",
    "org.jellyfin.androidtv": "Jellyfin",
    "org.videolan.vlc": "VLC",
    "com.google.android.apps.mediashell": "Google Cast",
    "com.google.android.apps.tv.launcherx": "Google TV Launcher",
}

# ============================================================================
# Reglas de Detección de Estado por Defecto
# ============================================================================

DEFAULT_STATE_RULES: Final[dict[str, list[object]]] = {
    "com.google.android.tvlauncher": ["idle"],
    "com.amazon.tv.launcher": ["idle"],
    "com.google.android.apps.tv.launcherx": ["idle"],
    "com.netflix.ninja": ["media_session_state"],
    "com.spotify.tv.android": ["media_session_state"],
    "com.google.android.youtube.tv": ["media_session_state"],
    "com.plexapp.android": [
        {"paused": {"media_session_state": 3, "wake_lock_size": 1}},
        {"playing": {"media_session_state": 3}},
        "idle",
    ],
}

# ============================================================================
# Valores por Defecto de Tiempo Límite
# ============================================================================

DEFAULT_AUTH_TIMEOUT_S: Final[float] = 10.0
DEFAULT_TRANSPORT_TIMEOUT_S: Final[float] = 1.0
DEFAULT_ADB_TIMEOUT_S: Final[float] = 9.0
DEFAULT_LOCK_TIMEOUT_S: Final[float] = 3.0
