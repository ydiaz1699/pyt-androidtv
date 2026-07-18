"""Envoltorios síncronos para AndroidTV y FireTV."""

from __future__ import annotations

import asyncio
from typing import Any

from .androidtv.androidtv import AndroidTV
from .firetv.firetv import FireTV
from .models import ADBConfig, DeviceInfo, DeviceState


def _run_sync(coro: Any) -> Any:
    """Ejecutar una corrutina de forma síncrona.

    Parámetros
    ----------
    coro : coroutine
        La corrutina a ejecutar.

    Retorna
    -------
    Any
        El resultado de la corrutina.

    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Estamos dentro de un bucle de eventos existente - crear uno nuevo en un hilo
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class AndroidTVSync:
    """Envoltorio síncrono para AndroidTV.

    Proporciona la misma interfaz que AndroidTV pero con métodos síncronos.

    Parámetros
    ----------
    config : ADBConfig
        La configuración de conexión ADB.
    state_detection_rules : dict o None
        Reglas personalizadas de detección de estado.

    """

    def __init__(
        self,
        config: ADBConfig,
        state_detection_rules: dict[str, list[Any]] | None = None,
    ) -> None:
        self._atv = AndroidTV(config=config, state_detection_rules=state_detection_rules)

    def __enter__(self) -> AndroidTVSync:
        """Entrar al administrador de contexto síncrono."""
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        """Salir del administrador de contexto síncrono."""
        self.close()

    @property
    def available(self) -> bool:
        """Si la conexión ADB está activa."""
        return self._atv.available

    @property
    def device_info(self) -> DeviceInfo:
        """La información actual del dispositivo."""
        return self._atv.device_info

    def connect(self) -> bool:
        """Establecer una conexión con el dispositivo."""
        return _run_sync(self._atv.connect())

    def close(self) -> None:
        """Cerrar la conexión ADB."""
        _run_sync(self._atv.close())

    def get_device_properties(self) -> DeviceInfo:
        """Obtener las propiedades del dispositivo mediante ADB."""
        return _run_sync(self._atv.get_device_properties())

    def get_installed_apps(self) -> list[str]:
        """Obtener la lista de aplicaciones instaladas."""
        return _run_sync(self._atv.get_installed_apps())

    def update(self, *, get_running_apps: bool = True, lazy: bool = True) -> DeviceState:
        """Actualizar el estado del dispositivo."""
        return _run_sync(self._atv.update(get_running_apps=get_running_apps, lazy=lazy))

    def screen_on(self) -> bool | None:
        """Verificar si la pantalla está encendida."""
        return _run_sync(self._atv.screen_on())

    def awake(self) -> bool | None:
        """Verificar si el dispositivo está despierto."""
        return _run_sync(self._atv.awake())

    def current_app(self) -> str | None:
        """Obtener la aplicación en primer plano actual."""
        return _run_sync(self._atv.current_app())

    def current_app_media_session_state(self) -> tuple[str | None, int | None]:
        """Obtener la app actual y su estado de sesión multimedia."""
        return _run_sync(self._atv.current_app_media_session_state())

    def audio_state(self) -> str | None:
        """Obtener el estado de audio actual."""
        return _run_sync(self._atv.audio_state())

    def wake_lock_size(self) -> int | None:
        """Obtener el tamaño actual del wake lock."""
        return _run_sync(self._atv.wake_lock_size())

    def running_apps(self) -> list[str] | None:
        """Obtener la lista de aplicaciones en ejecución."""
        return _run_sync(self._atv.running_apps())

    def get_hdmi_input(self) -> str | None:
        """Obtener la entrada HDMI actual."""
        return _run_sync(self._atv.get_hdmi_input())

    def stream_music_properties(self) -> dict[str, Any]:
        """Obtener las propiedades del flujo de audio."""
        return _run_sync(self._atv.stream_music_properties())

    def set_volume_level(self, volume_level: float) -> None:
        """Establecer el volumen a un nivel específico (0.0 a 1.0)."""
        _run_sync(self._atv.set_volume_level(volume_level))

    def volume_up(self) -> None:
        """Aumentar el volumen un paso."""
        _run_sync(self._atv.volume_up())

    def volume_down(self) -> None:
        """Disminuir el volumen un paso."""
        _run_sync(self._atv.volume_down())

    def send_key(self, key_name: str) -> None:
        """Enviar un evento de tecla por nombre."""
        _run_sync(self._atv.send_key(key_name))

    def send_key_code(self, code: int) -> None:
        """Enviar un evento de tecla por código."""
        _run_sync(self._atv.send_key_code(code))

    def power(self) -> None:
        """Enviar el evento de tecla POWER."""
        _run_sync(self._atv.power())

    def home(self) -> None:
        """Enviar el evento de tecla HOME."""
        _run_sync(self._atv.home())

    def back(self) -> None:
        """Enviar el evento de tecla BACK."""
        _run_sync(self._atv.back())

    def menu(self) -> None:
        """Enviar el evento de tecla MENU."""
        _run_sync(self._atv.menu())

    def enter(self) -> None:
        """Enviar el evento de tecla ENTER."""
        _run_sync(self._atv.enter())

    def up(self) -> None:
        """Enviar el evento de tecla UP."""
        _run_sync(self._atv.up())

    def down(self) -> None:
        """Enviar el evento de tecla DOWN."""
        _run_sync(self._atv.down())

    def left(self) -> None:
        """Enviar el evento de tecla LEFT."""
        _run_sync(self._atv.left())

    def right(self) -> None:
        """Enviar el evento de tecla RIGHT."""
        _run_sync(self._atv.right())

    def media_play(self) -> None:
        """Enviar el evento de tecla PLAY."""
        _run_sync(self._atv.media_play())

    def media_pause(self) -> None:
        """Enviar el evento de tecla PAUSE."""
        _run_sync(self._atv.media_pause())

    def media_play_pause(self) -> None:
        """Enviar el evento de tecla PLAY_PAUSE."""
        _run_sync(self._atv.media_play_pause())

    def media_stop(self) -> None:
        """Enviar el evento de tecla STOP."""
        _run_sync(self._atv.media_stop())

    def media_next(self) -> None:
        """Enviar el evento de tecla NEXT."""
        _run_sync(self._atv.media_next())

    def media_previous(self) -> None:
        """Enviar el evento de tecla PREVIOUS."""
        _run_sync(self._atv.media_previous())

    def mute(self) -> None:
        """Enviar el evento de tecla MUTE."""
        _run_sync(self._atv.mute())

    def launch_app(self, app: str) -> None:
        """Lanzar una aplicación."""
        _run_sync(self._atv.launch_app(app))

    def stop_app(self, app: str) -> None:
        """Forzar la detención de una aplicación."""
        _run_sync(self._atv.stop_app(app))

    def start_intent(self, intent: str) -> None:
        """Iniciar una actividad con el intent dado."""
        _run_sync(self._atv.start_intent(intent))

    def turn_on(self) -> None:
        """Encender el dispositivo."""
        _run_sync(self._atv.turn_on())

    def turn_off(self) -> None:
        """Apagar el dispositivo."""
        _run_sync(self._atv.turn_off())

    def sleep(self) -> None:
        """Poner el dispositivo en suspensión."""
        _run_sync(self._atv.sleep())

    def get_properties_dict(self) -> dict[str, Any]:
        """Obtener un diccionario de todas las propiedades del dispositivo."""
        return _run_sync(self._atv.get_properties_dict())

    # --- Control de Pantalla (Touch) ---

    def tap(self, x: int, y: int) -> None:
        """Simular un toque en la pantalla."""
        _run_sync(self._atv.tap(x, y))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Simular un deslizamiento en la pantalla."""
        _run_sync(self._atv.swipe(x1, y1, x2, y2, duration_ms))

    def long_press(self, x: int, y: int, duration_ms: int = 1500) -> None:
        """Simular una presión larga en la pantalla."""
        _run_sync(self._atv.long_press(x, y, duration_ms))

    def input_text(self, text: str) -> None:
        """Escribir texto en el campo de entrada activo."""
        _run_sync(self._atv.input_text(text))

    def swipe_up(self, duration_ms: int = 300) -> None:
        """Deslizar hacia arriba."""
        _run_sync(self._atv.swipe_up(duration_ms))

    def swipe_down(self, duration_ms: int = 300) -> None:
        """Deslizar hacia abajo."""
        _run_sync(self._atv.swipe_down(duration_ms))

    def swipe_left(self, duration_ms: int = 300) -> None:
        """Deslizar hacia la izquierda."""
        _run_sync(self._atv.swipe_left(duration_ms))

    def swipe_right(self, duration_ms: int = 300) -> None:
        """Deslizar hacia la derecha."""
        _run_sync(self._atv.swipe_right(duration_ms))

    def get_screen_resolution(self) -> tuple[int, int] | None:
        """Obtener la resolución de pantalla."""
        return _run_sync(self._atv.get_screen_resolution())

    def get_screen_density(self) -> int | None:
        """Obtener la densidad de pantalla (DPI)."""
        return _run_sync(self._atv.get_screen_density())


class FireTVSync:
    """Envoltorio síncrono para FireTV.

    Proporciona la misma interfaz que FireTV pero con métodos síncronos.

    Parámetros
    ----------
    config : ADBConfig
        La configuración de conexión ADB.
    state_detection_rules : dict o None
        Reglas personalizadas de detección de estado.

    """

    def __init__(
        self,
        config: ADBConfig,
        state_detection_rules: dict[str, list[Any]] | None = None,
    ) -> None:
        self._ftv = FireTV(config=config, state_detection_rules=state_detection_rules)

    def __enter__(self) -> FireTVSync:
        """Entrar al administrador de contexto síncrono."""
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        """Salir del administrador de contexto síncrono."""
        self.close()

    @property
    def available(self) -> bool:
        """Si la conexión ADB está activa."""
        return self._ftv.available

    @property
    def device_info(self) -> DeviceInfo:
        """La información actual del dispositivo."""
        return self._ftv.device_info

    def connect(self) -> bool:
        """Establecer una conexión con el dispositivo."""
        return _run_sync(self._ftv.connect())

    def close(self) -> None:
        """Cerrar la conexión ADB."""
        _run_sync(self._ftv.close())

    def get_device_properties(self) -> DeviceInfo:
        """Obtener las propiedades del dispositivo mediante ADB."""
        return _run_sync(self._ftv.get_device_properties())

    def get_installed_apps(self) -> list[str]:
        """Obtener la lista de aplicaciones instaladas."""
        return _run_sync(self._ftv.get_installed_apps())

    def update(self, *, get_running_apps: bool = True, lazy: bool = True) -> DeviceState:
        """Actualizar el estado del dispositivo."""
        return _run_sync(self._ftv.update(get_running_apps=get_running_apps, lazy=lazy))

    def screen_on(self) -> bool | None:
        """Verificar si la pantalla está encendida."""
        return _run_sync(self._ftv.screen_on())

    def awake(self) -> bool | None:
        """Verificar si el dispositivo está despierto."""
        return _run_sync(self._ftv.awake())

    def current_app(self) -> str | None:
        """Obtener la aplicación en primer plano actual."""
        return _run_sync(self._ftv.current_app())

    def current_app_media_session_state(self) -> tuple[str | None, int | None]:
        """Obtener la app actual y su estado de sesión multimedia."""
        return _run_sync(self._ftv.current_app_media_session_state())

    def audio_state(self) -> str | None:
        """Obtener el estado de audio actual."""
        return _run_sync(self._ftv.audio_state())

    def wake_lock_size(self) -> int | None:
        """Obtener el tamaño actual del wake lock."""
        return _run_sync(self._ftv.wake_lock_size())

    def running_apps(self) -> list[str] | None:
        """Obtener la lista de aplicaciones en ejecución."""
        return _run_sync(self._ftv.running_apps())

    def get_hdmi_input(self) -> str | None:
        """Obtener la entrada HDMI actual."""
        return _run_sync(self._ftv.get_hdmi_input())

    def stream_music_properties(self) -> dict[str, Any]:
        """Obtener las propiedades del flujo de audio."""
        return _run_sync(self._ftv.stream_music_properties())

    def set_volume_level(self, volume_level: float) -> None:
        """Establecer el volumen a un nivel específico (0.0 a 1.0)."""
        _run_sync(self._ftv.set_volume_level(volume_level))

    def volume_up(self) -> None:
        """Aumentar el volumen un paso."""
        _run_sync(self._ftv.volume_up())

    def volume_down(self) -> None:
        """Disminuir el volumen un paso."""
        _run_sync(self._ftv.volume_down())

    def send_key(self, key_name: str) -> None:
        """Enviar un evento de tecla por nombre."""
        _run_sync(self._ftv.send_key(key_name))

    def send_key_code(self, code: int) -> None:
        """Enviar un evento de tecla por código."""
        _run_sync(self._ftv.send_key_code(code))

    def power(self) -> None:
        """Enviar el evento de tecla POWER."""
        _run_sync(self._ftv.power())

    def home(self) -> None:
        """Enviar el evento de tecla HOME."""
        _run_sync(self._ftv.home())

    def back(self) -> None:
        """Enviar el evento de tecla BACK."""
        _run_sync(self._ftv.back())

    def menu(self) -> None:
        """Enviar el evento de tecla MENU."""
        _run_sync(self._ftv.menu())

    def enter(self) -> None:
        """Enviar el evento de tecla ENTER."""
        _run_sync(self._ftv.enter())

    def up(self) -> None:
        """Enviar el evento de tecla UP."""
        _run_sync(self._ftv.up())

    def down(self) -> None:
        """Enviar el evento de tecla DOWN."""
        _run_sync(self._ftv.down())

    def left(self) -> None:
        """Enviar el evento de tecla LEFT."""
        _run_sync(self._ftv.left())

    def right(self) -> None:
        """Enviar el evento de tecla RIGHT."""
        _run_sync(self._ftv.right())

    def media_play(self) -> None:
        """Enviar el evento de tecla PLAY."""
        _run_sync(self._ftv.media_play())

    def media_pause(self) -> None:
        """Enviar el evento de tecla PAUSE."""
        _run_sync(self._ftv.media_pause())

    def media_play_pause(self) -> None:
        """Enviar el evento de tecla PLAY_PAUSE."""
        _run_sync(self._ftv.media_play_pause())

    def media_stop(self) -> None:
        """Enviar el evento de tecla STOP."""
        _run_sync(self._ftv.media_stop())

    def media_next(self) -> None:
        """Enviar el evento de tecla NEXT."""
        _run_sync(self._ftv.media_next())

    def media_previous(self) -> None:
        """Enviar el evento de tecla PREVIOUS."""
        _run_sync(self._ftv.media_previous())

    def mute(self) -> None:
        """Enviar el evento de tecla MUTE."""
        _run_sync(self._ftv.mute())

    def launch_app(self, app: str) -> None:
        """Lanzar una aplicación."""
        _run_sync(self._ftv.launch_app(app))

    def stop_app(self, app: str) -> None:
        """Forzar la detención de una aplicación."""
        _run_sync(self._ftv.stop_app(app))

    def start_intent(self, intent: str) -> None:
        """Iniciar una actividad con el intent dado."""
        _run_sync(self._ftv.start_intent(intent))

    def turn_on(self) -> None:
        """Encender el dispositivo."""
        _run_sync(self._ftv.turn_on())

    def turn_off(self) -> None:
        """Apagar el dispositivo."""
        _run_sync(self._ftv.turn_off())

    def sleep(self) -> None:
        """Poner el dispositivo en suspensión."""
        _run_sync(self._ftv.sleep())

    def get_properties_dict(self) -> dict[str, Any]:
        """Obtener un diccionario de todas las propiedades del dispositivo."""
        return _run_sync(self._ftv.get_properties_dict())

    # --- Control de Pantalla (Touch) ---

    def tap(self, x: int, y: int) -> None:
        """Simular un toque en la pantalla."""
        _run_sync(self._ftv.tap(x, y))

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> None:
        """Simular un deslizamiento en la pantalla."""
        _run_sync(self._ftv.swipe(x1, y1, x2, y2, duration_ms))

    def long_press(self, x: int, y: int, duration_ms: int = 1500) -> None:
        """Simular una presión larga en la pantalla."""
        _run_sync(self._ftv.long_press(x, y, duration_ms))

    def input_text(self, text: str) -> None:
        """Escribir texto en el campo de entrada activo."""
        _run_sync(self._ftv.input_text(text))

    def swipe_up(self, duration_ms: int = 300) -> None:
        """Deslizar hacia arriba."""
        _run_sync(self._ftv.swipe_up(duration_ms))

    def swipe_down(self, duration_ms: int = 300) -> None:
        """Deslizar hacia abajo."""
        _run_sync(self._ftv.swipe_down(duration_ms))

    def swipe_left(self, duration_ms: int = 300) -> None:
        """Deslizar hacia la izquierda."""
        _run_sync(self._ftv.swipe_left(duration_ms))

    def swipe_right(self, duration_ms: int = 300) -> None:
        """Deslizar hacia la derecha."""
        _run_sync(self._ftv.swipe_right(duration_ms))

    def get_screen_resolution(self) -> tuple[int, int] | None:
        """Obtener la resolución de pantalla."""
        return _run_sync(self._ftv.get_screen_resolution())

    def get_screen_density(self) -> int | None:
        """Obtener la densidad de pantalla (DPI)."""
        return _run_sync(self._ftv.get_screen_density())
