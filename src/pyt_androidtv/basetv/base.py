"""Clase Base TV con lógica compartida para Android TV y Fire TV."""

from __future__ import annotations

import logging
import re
from typing import Any

from .. import constants
from ..adb.base import ADBInterface
from ..constants import CommandRegistry
from ..exceptions import DeviceNotAvailableError
from ..models import ADBConfig, AudioState, DeviceInfo, DeviceState, State
from .state import StateDetectionEngine

_LOGGER = logging.getLogger(__name__)


class BaseTV:
    """Clase base para dispositivos Android TV y Fire TV.

    Proporciona funcionalidad compartida para la comunicación con el dispositivo,
    detección de estado y control multimedia mediante ADB.

    Parámetros
    ----------
    adb : ADBInterface
        El manejador de conexión ADB.
    config : ADBConfig
        La configuración ADB.
    state_detection_rules : dict o None
        Reglas personalizadas de detección de estado.

    """

    DEVICE_TYPE: str = "base"

    def __init__(
        self,
        adb: ADBInterface,
        config: ADBConfig,
        state_detection_rules: dict[str, list[Any]] | None = None,
    ) -> None:
        self._adb = adb
        self._config = config
        self._device_info: DeviceInfo = DeviceInfo()
        self._installed_apps: list[str] = []
        self._max_volume: float | None = None
        self._state_engine = StateDetectionEngine(state_detection_rules)

    # ======================================================================= #
    #                         Administrador de Contexto                        #
    # ======================================================================= #

    async def __aenter__(self) -> BaseTV:
        """Entrar al administrador de contexto asíncrono."""
        await self.connect()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Salir del administrador de contexto asíncrono."""
        await self.close()

    # ======================================================================= #
    #                         Gestión de Conexión                              #
    # ======================================================================= #

    @property
    def available(self) -> bool:
        """Si la conexión ADB está activa."""
        return self._adb.available

    async def connect(self) -> bool:
        """Establecer una conexión con el dispositivo.

        Retorna
        -------
        bool
            True si la conexión fue exitosa.

        """
        return await self._adb.connect(
            auth_timeout_s=self._config.auth_timeout_s,
            transport_timeout_s=self._config.transport_timeout_s,
        )

    async def close(self) -> None:
        """Cerrar la conexión ADB."""
        await self._adb.close()

    # ======================================================================= #
    #                         Propiedades del Dispositivo                      #
    # ======================================================================= #

    @property
    def device_info(self) -> DeviceInfo:
        """La información actual del dispositivo."""
        return self._device_info

    async def get_device_properties(self) -> DeviceInfo:
        """Obtener las propiedades del dispositivo mediante ADB.

        Retorna
        -------
        DeviceInfo
            La información del dispositivo.

        """
        response = await self._adb.shell(constants.CMD_DEVICE_PROPERTIES)
        self._device_info = self._parse_device_properties(response)

        # Obtener direcciones MAC
        mac_wifi_response = await self._adb.shell(constants.CMD_MAC_WLAN0)
        mac_eth_response = await self._adb.shell(constants.CMD_MAC_ETH0)

        mac_wifi = self._parse_mac_address(mac_wifi_response)
        mac_eth = self._parse_mac_address(mac_eth_response)

        if mac_wifi or mac_eth:
            self._device_info = DeviceInfo(
                manufacturer=self._device_info.manufacturer,
                model=self._device_info.model,
                serial_number=self._device_info.serial_number,
                sw_version=self._device_info.sw_version,
                product_id=self._device_info.product_id,
                mac_wifi=mac_wifi,
                mac_ethernet=mac_eth,
            )

        return self._device_info

    async def get_installed_apps(self) -> list[str]:
        """Obtener la lista de aplicaciones instaladas.

        Retorna
        -------
        list of str
            Los nombres de paquetes de las aplicaciones instaladas.

        """
        response = await self._adb.shell(constants.CMD_INSTALLED_APPS)
        apps = self._parse_installed_apps(response)
        if apps is not None:
            self._installed_apps = apps
        return self._installed_apps

    # ======================================================================= #
    #                         Consultas de Estado                              #
    # ======================================================================= #

    async def screen_on(self) -> bool | None:
        """Verificar si la pantalla está encendida.

        Retorna
        -------
        bool o None
            True si la pantalla está encendida, None si es indeterminado.

        """
        response = await self._adb.shell(
            constants.CMD_SCREEN_ON + constants.CMD_SUCCESS1_FAILURE0
        )
        if response is None:
            return None
        return response.strip() == "1"

    async def awake(self) -> bool | None:
        """Verificar si el dispositivo está despierto.

        Retorna
        -------
        bool o None
            True si el dispositivo está despierto, None si es indeterminado.

        """
        response = await self._adb.shell(
            constants.CMD_AWAKE + constants.CMD_SUCCESS1_FAILURE0
        )
        if response is None:
            return None
        return response.strip() == "1"

    async def screen_on_awake_wake_lock_size(self) -> tuple[bool | None, bool | None, int | None]:
        """Obtener el estado de la pantalla, estado de despertar y tamaño del wake lock en una sola llamada.

        Retorna
        -------
        tuple
            Tupla (screen_on, awake, wake_lock_size).

        """
        response = await self._adb.shell(constants.CMD_SCREEN_ON_AWAKE_WAKE_LOCK_SIZE)
        return self._parse_screen_on_awake_wake_lock_size(response)

    async def current_app(self) -> str | None:
        """Obtener la aplicación en primer plano actual.

        Retorna
        -------
        str o None
            El nombre del paquete de la app actual.

        """
        cmd = CommandRegistry.current_app(self._device_info.android_version)
        response = await self._adb.shell(cmd)
        return self._parse_current_app(response)

    async def current_app_media_session_state(self) -> tuple[str | None, int | None]:
        """Obtener la app actual y su estado de sesión multimedia.

        Retorna
        -------
        tuple
            Tupla (current_app, media_session_state).

        """
        cmd = CommandRegistry.current_app_media_session_state(self._device_info.android_version)
        response = await self._adb.shell(cmd)
        return self._parse_current_app_media_session_state(response)

    async def audio_state(self) -> str | None:
        """Obtener el estado de audio actual.

        Retorna
        -------
        str o None
            El estado de audio: "idle", "paused" o "playing".

        """
        cmd = CommandRegistry.audio_state(self._device_info.android_version)
        response = await self._adb.shell(cmd)
        return self._parse_audio_state(response)

    async def wake_lock_size(self) -> int | None:
        """Obtener el tamaño actual del wake lock.

        Retorna
        -------
        int o None
            El tamaño del wake lock.

        """
        response = await self._adb.shell(constants.CMD_WAKE_LOCK_SIZE)
        return self._parse_wake_lock_size(response)

    async def running_apps(self) -> list[str] | None:
        """Obtener la lista de aplicaciones en ejecución.

        Retorna
        -------
        list of str o None
            Los nombres de paquetes de las apps en ejecución.

        """
        response = await self._adb.shell(constants.CMD_RUNNING_APPS)
        return self._parse_running_apps(response)

    async def get_hdmi_input(self) -> str | None:
        """Obtener la entrada HDMI actual.

        Retorna
        -------
        str o None
            La entrada HDMI actual (ej., "HW5").

        """
        cmd = CommandRegistry.hdmi_input(self._device_info.android_version)
        response = await self._adb.shell(cmd)
        return self._parse_hdmi_input(response)

    # ======================================================================= #
    #                         Control de Volumen                               #
    # ======================================================================= #

    async def stream_music_properties(self) -> dict[str, Any]:
        """Obtener las propiedades del flujo de audio.

        Retorna
        -------
        dict
            Diccionario con claves: is_volume_muted, volume_level, audio_output_device.

        """
        response = await self._adb.shell(constants.CMD_STREAM_MUSIC)
        stream_music = self._parse_stream_music(response)
        audio_output_device = self._parse_audio_output_device(stream_music)
        is_muted = self._parse_is_volume_muted(stream_music)
        volume = self._parse_volume(stream_music, audio_output_device)
        volume_level = self._volume_level(volume)

        return {
            "is_volume_muted": is_muted,
            "volume_level": volume_level,
            "audio_output_device": audio_output_device,
        }

    async def set_volume_level(self, volume_level: float) -> None:
        """Establecer el volumen a un nivel específico (0.0 a 1.0).

        Parámetros
        ----------
        volume_level : float
            El nivel de volumen deseado entre 0.0 y 1.0.

        """
        if self._max_volume is None:
            # Obtener primero el volumen máximo
            await self.stream_music_properties()

        if self._max_volume:
            new_volume = int(round(self._max_volume * volume_level))
            cmd = CommandRegistry.volume_set(new_volume, self._device_info.android_version)
            await self._adb.shell(cmd)

    async def volume_up(self, *, current_volume: int | None = None) -> None:
        """Aumentar el volumen un paso."""
        await self.send_key_code(constants.KEYS["VOLUME_UP"])

    async def volume_down(self, *, current_volume: int | None = None) -> None:
        """Disminuir el volumen un paso."""
        await self.send_key_code(constants.KEYS["VOLUME_DOWN"])

    # ======================================================================= #
    #                         Eventos de Tecla                                 #
    # ======================================================================= #

    async def send_key(self, key_name: str) -> None:
        """Enviar un evento de tecla por nombre.

        Parámetros
        ----------
        key_name : str
            El nombre de la tecla (debe estar en constants.KEYS).

        Lanza
        ------
        KeyError
            Si el nombre de la tecla no es reconocido.

        """
        if key_name not in constants.KEYS:
            raise KeyError(f"Unknown key: {key_name}")
        await self.send_key_code(constants.KEYS[key_name])

    async def send_key_code(self, code: int) -> None:
        """Enviar un evento de tecla por código.

        Parámetros
        ----------
        code : int
            El código de evento de tecla de Android.

        """
        await self._adb.shell(f"input keyevent {code}")

    async def power(self) -> None:
        """Enviar el evento de tecla POWER."""
        await self.send_key_code(constants.KEYS["POWER"])

    async def home(self) -> None:
        """Enviar el evento de tecla HOME."""
        await self.send_key_code(constants.KEYS["HOME"])

    async def back(self) -> None:
        """Enviar el evento de tecla BACK."""
        await self.send_key_code(constants.KEYS["BACK"])

    async def menu(self) -> None:
        """Enviar el evento de tecla MENU."""
        await self.send_key_code(constants.KEYS["MENU"])

    async def enter(self) -> None:
        """Enviar el evento de tecla ENTER."""
        await self.send_key_code(constants.KEYS["ENTER"])

    async def up(self) -> None:
        """Enviar el evento de tecla UP."""
        await self.send_key_code(constants.KEYS["UP"])

    async def down(self) -> None:
        """Enviar el evento de tecla DOWN."""
        await self.send_key_code(constants.KEYS["DOWN"])

    async def left(self) -> None:
        """Enviar el evento de tecla LEFT."""
        await self.send_key_code(constants.KEYS["LEFT"])

    async def right(self) -> None:
        """Enviar el evento de tecla RIGHT."""
        await self.send_key_code(constants.KEYS["RIGHT"])

    async def media_play(self) -> None:
        """Enviar el evento de tecla PLAY."""
        await self.send_key_code(constants.KEYS["PLAY"])

    async def media_pause(self) -> None:
        """Enviar el evento de tecla PAUSE."""
        await self.send_key_code(constants.KEYS["PAUSE"])

    async def media_play_pause(self) -> None:
        """Enviar el evento de tecla PLAY_PAUSE."""
        await self.send_key_code(constants.KEYS["PLAY_PAUSE"])

    async def media_stop(self) -> None:
        """Enviar el evento de tecla STOP."""
        await self.send_key_code(constants.KEYS["STOP"])

    async def media_next(self) -> None:
        """Enviar el evento de tecla NEXT."""
        await self.send_key_code(constants.KEYS["NEXT"])

    async def media_previous(self) -> None:
        """Enviar el evento de tecla PREVIOUS."""
        await self.send_key_code(constants.KEYS["PREVIOUS"])

    async def mute(self) -> None:
        """Enviar el evento de tecla MUTE."""
        await self.send_key_code(constants.KEYS["MUTE"])

    # ======================================================================= #
    #                         Gestión de Aplicaciones                          #
    # ======================================================================= #

    async def launch_app(self, app: str) -> None:
        """Lanzar una aplicación.

        Parámetros
        ----------
        app : str
            El nombre del paquete de la app a lanzar.

        """
        cmd = CommandRegistry.launch_app(
            app,
            self._device_info.android_version,
            firetv=(self.DEVICE_TYPE == "firetv"),
        )
        await self._adb.shell(cmd)

    async def stop_app(self, app: str) -> None:
        """Forzar la detención de una aplicación.

        Parámetros
        ----------
        app : str
            El nombre del paquete de la app a detener.

        """
        await self._adb.shell(f"am force-stop {app}")

    async def start_intent(self, intent: str) -> None:
        """Iniciar una actividad con el intent dado.

        Parámetros
        ----------
        intent : str
            El URI del intent o componente a iniciar.

        """
        await self._adb.shell(f"am start {intent}")

    # ======================================================================= #
    #                      Control de Pantalla (Touch)                         #
    # ======================================================================= #

    async def tap(self, x: int, y: int) -> None:
        """Simular un toque en la pantalla en las coordenadas dadas.

        Equivalente a: adb shell input tap <x> <y>

        Parámetros
        ----------
        x : int
            Coordenada horizontal (píxeles desde la izquierda).
        y : int
            Coordenada vertical (píxeles desde arriba).
        """
        await self._adb.shell(f"input tap {x} {y}")

    async def swipe(
        self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300
    ) -> None:
        """Simular un deslizamiento (swipe) en la pantalla.

        Equivalente a: adb shell input swipe <x1> <y1> <x2> <y2> <duración>

        Parámetros
        ----------
        x1 : int
            Coordenada X del punto de inicio.
        y1 : int
            Coordenada Y del punto de inicio.
        x2 : int
            Coordenada X del punto final.
        y2 : int
            Coordenada Y del punto final.
        duration_ms : int
            Duración del deslizamiento en milisegundos (por defecto 300ms).
        """
        await self._adb.shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")

    async def long_press(self, x: int, y: int, duration_ms: int = 1500) -> None:
        """Simular una presión larga en la pantalla.

        Se implementa como un swipe sin movimiento con duración extendida.
        Equivalente a: adb shell input swipe <x> <y> <x> <y> <duración>

        Parámetros
        ----------
        x : int
            Coordenada X del punto de presión.
        y : int
            Coordenada Y del punto de presión.
        duration_ms : int
            Duración de la presión en milisegundos (por defecto 1500ms).
        """
        await self._adb.shell(f"input swipe {x} {y} {x} {y} {duration_ms}")

    async def input_text(self, text: str) -> None:
        """Escribir texto en el campo de entrada activo.

        Los espacios se reemplazan por '%s' ya que 'input text' no acepta
        espacios directamente.
        Equivalente a: adb shell input text '<texto>'

        Parámetros
        ----------
        text : str
            El texto a escribir. Los espacios serán convertidos automáticamente.
        """
        # Escapar caracteres especiales de shell y reemplazar espacios
        escaped = text.replace(" ", "%s").replace("'", "\\'").replace("\"", "\\\"")
        await self._adb.shell(f"input text '{escaped}'")

    async def input_keyevent(self, keycode: int) -> None:
        """Enviar un evento de tecla por código numérico directamente.

        Útil para teclas que no están en el diccionario KEYS, como
        DELETE (67), TAB (61), CAPS_LOCK (115), etc.

        Parámetros
        ----------
        keycode : int
            Código de tecla Android (ver KeyEvent en documentación Android).
        """
        await self._adb.shell(f"input keyevent {keycode}")

    async def swipe_up(self, duration_ms: int = 300) -> None:
        """Deslizar hacia arriba (scroll down en contenido).

        Útil para navegar listas y menús.
        """
        await self.swipe(500, 1500, 500, 500, duration_ms)

    async def swipe_down(self, duration_ms: int = 300) -> None:
        """Deslizar hacia abajo (scroll up en contenido).

        Útil para navegar listas y menús.
        """
        await self.swipe(500, 500, 500, 1500, duration_ms)

    async def swipe_left(self, duration_ms: int = 300) -> None:
        """Deslizar hacia la izquierda.

        Útil para navegar carruseles horizontales.
        """
        await self.swipe(900, 500, 100, 500, duration_ms)

    async def swipe_right(self, duration_ms: int = 300) -> None:
        """Deslizar hacia la derecha.

        Útil para navegar carruseles horizontales.
        """
        await self.swipe(100, 500, 900, 500, duration_ms)

    async def screen_record(self, device_path: str = "/sdcard/record.mp4", duration_s: int = 10) -> None:
        """Iniciar grabación de pantalla.

        La grabación se guarda en el dispositivo. Usar adb pull para descargarla.
        Equivalente a: adb shell screenrecord <ruta> --time-limit <duración>

        Parámetros
        ----------
        device_path : str
            Ruta en el dispositivo donde se guardará el video.
        duration_s : int
            Duración máxima de la grabación en segundos (máximo 180).
        """
        max_duration = min(duration_s, 180)
        await self._adb.shell(f"screenrecord {device_path} --time-limit {max_duration}")

    async def get_screen_resolution(self) -> tuple[int, int] | None:
        """Obtener la resolución de pantalla del dispositivo.

        Retorna
        -------
        tuple[int, int] o None
            Tupla (ancho, alto) en píxeles, o None si no se pudo determinar.
        """
        response = await self._adb.shell("wm size")
        if response:
            match = re.search(r"(\d+)x(\d+)", response)
            if match:
                return int(match.group(1)), int(match.group(2))
        return None

    async def get_screen_density(self) -> int | None:
        """Obtener la densidad de pantalla (DPI) del dispositivo.

        Retorna
        -------
        int o None
            Densidad en DPI, o None si no se pudo determinar.
        """
        response = await self._adb.shell("wm density")
        if response:
            match = re.search(r"(\d+)", response)
            if match:
                return int(match.group(1))
        return None

    # ======================================================================= #
    #                         Control de Energía                               #
    # ======================================================================= #

    async def turn_on(self) -> None:
        """Encender el dispositivo."""
        await self._adb.shell(constants.CMD_TURN_ON_ANDROIDTV)

    async def turn_off(self) -> None:
        """Apagar el dispositivo."""
        await self._adb.shell(constants.CMD_TURN_OFF_ANDROIDTV)

    async def sleep(self) -> None:
        """Poner el dispositivo en suspensión."""
        await self.send_key_code(constants.KEYS["SLEEP"])

    # ======================================================================= #
    #                         Métodos Estáticos de Análisis                    #
    # ======================================================================= #

    @staticmethod
    def _parse_device_properties(response: str | None) -> DeviceInfo:
        """Analizar las propiedades del dispositivo desde la respuesta ADB.

        Parámetros
        ----------
        response : str o None
            La salida de CMD_DEVICE_PROPERTIES.

        Retorna
        -------
        DeviceInfo
            Información del dispositivo analizada.

        """
        if not response:
            return DeviceInfo()

        lines = response.strip().splitlines()
        if len(lines) != 5:
            return DeviceInfo()

        manufacturer, model, serialno, version, product_id = lines
        return DeviceInfo(
            manufacturer=manufacturer.strip(),
            model=model.strip(),
            serial_number=serialno.strip() or None,
            sw_version=version.strip(),
            product_id=product_id.strip(),
        )

    @staticmethod
    def _parse_mac_address(response: str | None) -> str | None:
        """Analizar una dirección MAC desde la respuesta ADB.

        Parámetros
        ----------
        response : str o None
            La respuesta de un comando de dirección MAC.

        Retorna
        -------
        str o None
            La dirección MAC analizada.

        """
        if not response:
            return None
        match = constants.REGEX_MAC_ADDRESS.search(response)
        return match.group(1) if match else None

    @staticmethod
    def _parse_installed_apps(response: str | None) -> list[str] | None:
        """Analizar las aplicaciones instaladas desde la respuesta ADB.

        Parámetros
        ----------
        response : str o None
            La salida de CMD_INSTALLED_APPS.

        Retorna
        -------
        list of str o None
            La lista de nombres de paquetes de las aplicaciones instaladas.

        """
        if response is None:
            return None
        return [
            line.strip().rsplit("package:", 1)[-1]
            for line in response.splitlines()
            if line.strip()
        ]

    @staticmethod
    def _parse_screen_on_awake_wake_lock_size(
        output: str | None,
    ) -> tuple[bool | None, bool | None, int | None]:
        """Analizar pantalla encendida, despierto y tamaño del wake lock desde la salida combinada.

        Parámetros
        ----------
        output : str o None
            La salida de CMD_SCREEN_ON_AWAKE_WAKE_LOCK_SIZE.

        Retorna
        -------
        tuple
            (screen_on, awake, wake_lock_size).

        """
        if output is None:
            return None, None, None

        if output == "":
            return False, False, None

        screen_on = output[0] == "1"
        awake = None if len(output) < 2 else output[1] == "1"
        wake_lock_size = None if len(output) < 3 else BaseTV._parse_wake_lock_size(output[2:])

        return screen_on, awake, wake_lock_size

    @staticmethod
    def _parse_current_app(response: str | None) -> str | None:
        """Analizar la app actual desde la respuesta ADB.

        Parámetros
        ----------
        response : str o None
            La salida del comando de la app actual.

        Retorna
        -------
        str o None
            El nombre del paquete de la app actual.

        """
        if not response or "=" in response or "{" in response:
            return None
        return response.strip()

    @staticmethod
    def _parse_current_app_media_session_state(
        response: str | None,
    ) -> tuple[str | None, int | None]:
        """Analizar la app actual y el estado de sesión multimedia desde la salida combinada.

        Parámetros
        ----------
        response : str o None
            La salida combinada.

        Retorna
        -------
        tuple
            (current_app, media_session_state).

        """
        if not response:
            return None, None

        lines = response.splitlines()
        current_app = BaseTV._parse_current_app(lines[0].strip())

        if len(lines) > 1:
            match = constants.REGEX_MEDIA_SESSION_STATE.search(response)
            if match:
                return current_app, int(match.group("state"))

        return current_app, None

    @staticmethod
    def _parse_audio_state(response: str | None) -> str | None:
        """Analizar el estado de audio desde la respuesta ADB.

        Parámetros
        ----------
        response : str o None
            La salida del comando de estado de audio.

        Retorna
        -------
        str o None
            "idle", "paused" o "playing".

        """
        if not response:
            return None
        if response.strip() == "1":
            return AudioState.PAUSED
        if response.strip() == "2":
            return AudioState.PLAYING
        return AudioState.IDLE

    @staticmethod
    def _parse_wake_lock_size(response: str | None) -> int | None:
        """Analizar el tamaño del wake lock desde la respuesta ADB.

        Parámetros
        ----------
        response : str o None
            La salida de CMD_WAKE_LOCK_SIZE.

        Retorna
        -------
        int o None
            El tamaño del wake lock.

        """
        if not response:
            return None
        match = constants.REGEX_WAKE_LOCK_SIZE.search(response)
        return int(match.group("size")) if match else None

    @staticmethod
    def _parse_running_apps(response: str | None) -> list[str] | None:
        """Analizar las apps en ejecución desde la respuesta ADB.

        Parámetros
        ----------
        response : str o None
            La salida de CMD_RUNNING_APPS.

        Retorna
        -------
        list of str o None
            La lista de nombres de paquetes de las apps en ejecución.

        """
        if not response:
            return None
        return [
            line.strip().rsplit(" ", 1)[-1]
            for line in response.splitlines()
            if line.strip()
        ]

    @staticmethod
    def _parse_hdmi_input(response: str | None) -> str | None:
        """Analizar la entrada HDMI desde la respuesta ADB.

        Parámetros
        ----------
        response : str o None
            La salida del comando de entrada HDMI.

        Retorna
        -------
        str o None
            El identificador de la entrada HDMI (ej., "HW5").

        """
        return response.strip() if response and response.strip() else None

    @staticmethod
    def _parse_stream_music(response: str | None) -> str | None:
        """Analizar el bloque STREAM_MUSIC desde la salida de dumpsys audio.

        Parámetros
        ----------
        response : str o None
            La salida sin procesar de CMD_STREAM_MUSIC.

        Retorna
        -------
        str o None
            El bloque STREAM_MUSIC analizado.

        """
        if not response:
            return None
        match = constants.REGEX_STREAM_MUSIC.search(response)
        return match.group(1) if match else None

    @staticmethod
    def _parse_audio_output_device(stream_music: str | None) -> str | None:
        """Analizar el dispositivo de salida de audio desde STREAM_MUSIC.

        Parámetros
        ----------
        stream_music : str o None
            El bloque STREAM_MUSIC.

        Retorna
        -------
        str o None
            El nombre del dispositivo de salida de audio.

        """
        if not stream_music:
            return None
        match = constants.REGEX_DEVICE.search(stream_music)
        return match.group(1) if match else None

    @staticmethod
    def _parse_is_volume_muted(stream_music: str | None) -> bool | None:
        """Analizar si el volumen está silenciado desde STREAM_MUSIC.

        Parámetros
        ----------
        stream_music : str o None
            El bloque STREAM_MUSIC.

        Retorna
        -------
        bool o None
            Si el volumen está silenciado.

        """
        if not stream_music:
            return None
        match = constants.REGEX_MUTED.search(stream_music)
        return match.group(1) == "true" if match else None

    def _parse_volume(self, stream_music: str | None, audio_output_device: str | None) -> int | None:
        """Analizar el volumen desde STREAM_MUSIC.

        Parámetros
        ----------
        stream_music : str o None
            El bloque STREAM_MUSIC.
        audio_output_device : str o None
            El dispositivo de salida de audio actual.

        Retorna
        -------
        int o None
            El nivel de volumen absoluto.

        """
        if not stream_music:
            return None

        # Obtener volumen máximo
        if self._max_volume is None:
            max_match = constants.REGEX_MAX_VOLUME.search(stream_music)
            if max_match:
                self._max_volume = float(max_match.group(1))

        if not audio_output_device:
            return None

        pattern = re.compile(re.escape(audio_output_device) + r"\): (\d{1,})")
        match = pattern.search(stream_music)
        return int(match.group(1)) if match else None

    def _volume_level(self, volume: int | None) -> float | None:
        """Convertir volumen absoluto a un nivel de 0.0-1.0.

        Parámetros
        ----------
        volume : int o None
            El volumen absoluto.

        Retorna
        -------
        float o None
            El nivel de volumen relativo.

        """
        if volume is not None and self._max_volume:
            return volume / self._max_volume
        return None
