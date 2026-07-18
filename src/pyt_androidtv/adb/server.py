"""Conexión ADB mediante un servidor ADB usando adbutils."""

from __future__ import annotations

import asyncio
import logging
from functools import partial
from typing import TYPE_CHECKING

from ..constants import DEFAULT_LOCK_TIMEOUT_S
from ..exceptions import ADBConnectionError, LockNotAcquiredError
from .base import ADBInterface

if TYPE_CHECKING:
    from adbutils import AdbDevice

_LOGGER = logging.getLogger(__name__)


class ADBServerConnection(ADBInterface):
    """Conexión ADB que delega comandos a un servidor ADB.

    Parámetros
    ----------
    host : str
        El serial/dirección del dispositivo (ej., "192.168.1.100:5555").
    adb_server_ip : str
        La dirección IP del servidor ADB.
    adb_server_port : int
        El puerto del servidor ADB (por defecto 5037).
    lock_timeout_s : float
        Tiempo límite para adquirir el bloqueo interno.

    """

    def __init__(
        self,
        host: str,
        port: int = 5555,
        adb_server_ip: str = "127.0.0.1",
        adb_server_port: int = 5037,
        lock_timeout_s: float = DEFAULT_LOCK_TIMEOUT_S,
    ) -> None:
        self._host = host
        self._port = port
        self._serial = f"{host}:{port}"
        self._adb_server_ip = adb_server_ip
        self._adb_server_port = adb_server_port
        self._lock_timeout_s = lock_timeout_s
        self._device: AdbDevice | None = None
        self._lock = asyncio.Lock()

    @property
    def available(self) -> bool:
        """Si la conexión ADB está activa actualmente."""
        return self._device is not None

    async def connect(
        self,
        *,
        log_errors: bool = True,
        auth_timeout_s: float = 10.0,
        transport_timeout_s: float = 1.0,
    ) -> bool:
        """Conectar al dispositivo mediante el servidor ADB.

        Parámetros
        ----------
        log_errors : bool
            Si se deben registrar los errores de conexión.
        auth_timeout_s : float
            No utilizado para conexiones de servidor (manejado por el servidor).
        transport_timeout_s : float
            No utilizado para conexiones de servidor (manejado por el servidor).

        Retorna
        -------
        bool
            True si la conexión fue establecida.

        """
        from adbutils import AdbClient

        try:
            async with asyncio.timeout(self._lock_timeout_s):
                await self._lock.acquire()
        except TimeoutError as err:
            raise LockNotAcquiredError(self._lock_timeout_s) from err

        try:
            loop = asyncio.get_running_loop()
            client = AdbClient(host=self._adb_server_ip, port=self._adb_server_port)

            # Conectar al dispositivo a través del servidor ADB
            device = await loop.run_in_executor(None, partial(client.device, serial=self._serial))
            # Verificar que el dispositivo es alcanzable
            await loop.run_in_executor(None, device.get_state)
            self._device = device
            _LOGGER.debug("Connected to %s via ADB server at %s:%d", self._serial, self._adb_server_ip, self._adb_server_port)
            return True

        except Exception as exc:  # noqa: BLE001
            if log_errors:
                _LOGGER.warning(
                    "Failed to connect to %s via ADB server: %s",
                    self._serial,
                    exc,
                )
            self._device = None
            return False
        finally:
            self._lock.release()

    async def close(self) -> None:
        """Cerrar la conexión ADB."""
        self._device = None

    async def shell(self, cmd: str) -> str | None:
        """Ejecutar un comando de shell ADB mediante el servidor ADB.

        Parámetros
        ----------
        cmd : str
            El comando de shell a ejecutar.

        Retorna
        -------
        str o None
            La salida del comando, o None si la ejecución falló.

        """
        if not self.available:
            _LOGGER.debug("Cannot execute shell command - not connected to %s", self._serial)
            return None

        try:
            async with asyncio.timeout(self._lock_timeout_s):
                await self._lock.acquire()
        except TimeoutError as err:
            raise LockNotAcquiredError(self._lock_timeout_s) from err

        try:
            assert self._device is not None  # noqa: S101
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, partial(self._device.shell, cmd))
            if isinstance(response, bytes):
                return response.decode("utf-8", errors="replace").strip()
            return response.strip() if response else None
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Shell command failed on %s: %s", self._serial, exc)
            return None
        finally:
            self._lock.release()

    async def pull(self, device_path: str, local_path: str) -> None:
        """Descargar un archivo del dispositivo mediante el servidor ADB.

        Parámetros
        ----------
        device_path : str
            La ruta en el dispositivo.
        local_path : str
            La ruta de destino local.

        """
        if not self.available:
            raise ADBConnectionError(self._host, self._port, "Not connected")

        try:
            async with asyncio.timeout(self._lock_timeout_s):
                await self._lock.acquire()
        except TimeoutError as err:
            raise LockNotAcquiredError(self._lock_timeout_s) from err

        try:
            assert self._device is not None  # noqa: S101
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, partial(self._device.sync.pull, device_path, local_path))
        finally:
            self._lock.release()

    async def push(self, local_path: str, device_path: str) -> None:
        """Enviar un archivo al dispositivo mediante el servidor ADB.

        Parámetros
        ----------
        local_path : str
            La ruta del archivo local.
        device_path : str
            La ruta de destino en el dispositivo.

        """
        if not self.available:
            raise ADBConnectionError(self._host, self._port, "Not connected")

        try:
            async with asyncio.timeout(self._lock_timeout_s):
                await self._lock.acquire()
        except TimeoutError as err:
            raise LockNotAcquiredError(self._lock_timeout_s) from err

        try:
            assert self._device is not None  # noqa: S101
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, partial(self._device.sync.push, local_path, device_path))
        finally:
            self._lock.release()

    async def screencap(self) -> bytes | None:
        """Capturar una captura de pantalla del dispositivo mediante el servidor ADB.

        Retorna
        -------
        bytes o None
            Los datos de la captura de pantalla en PNG, o None si la captura falló.

        """
        if not self.available:
            return None

        try:
            async with asyncio.timeout(self._lock_timeout_s):
                await self._lock.acquire()
        except TimeoutError as err:
            raise LockNotAcquiredError(self._lock_timeout_s) from err

        try:
            assert self._device is not None  # noqa: S101
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(None, self._device.shell, "screencap -p", timeout=10)
            if isinstance(response, bytes):
                return response
            return response.encode("latin-1") if response else None
        except Exception:  # noqa: BLE001
            return None
        finally:
            self._lock.release()
