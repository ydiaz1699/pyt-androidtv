"""Conexión ADB sobre TCP usando la biblioteca adb-shell."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ..constants import DEFAULT_ADB_TIMEOUT_S, DEFAULT_AUTH_TIMEOUT_S, DEFAULT_LOCK_TIMEOUT_S, DEFAULT_TRANSPORT_TIMEOUT_S
from ..exceptions import ADBConnectionError, LockNotAcquiredError
from .base import ADBInterface

if TYPE_CHECKING:
    from adb_shell.adb_device_async import AdbDeviceTcpAsync

_LOGGER = logging.getLogger(__name__)


class ADBConnection(ADBInterface):
    """Conexión ADB sobre TCP usando la biblioteca adb-shell.

    Parámetros
    ----------
    host : str
        La dirección IP o nombre de host del dispositivo.
    port : int
        El puerto ADB del dispositivo (por defecto 5555).
    adbkey : str
        Ruta al archivo de clave privada ADB.
    adb_timeout_s : float
        Tiempo límite para operaciones ADB.
    lock_timeout_s : float
        Tiempo límite para adquirir el bloqueo interno.

    """

    def __init__(
        self,
        host: str,
        port: int = 5555,
        adbkey: str = "",
        adb_timeout_s: float = DEFAULT_ADB_TIMEOUT_S,
        lock_timeout_s: float = DEFAULT_LOCK_TIMEOUT_S,
    ) -> None:
        self._host = host
        self._port = port
        self._adbkey = adbkey
        self._adb_timeout_s = adb_timeout_s
        self._lock_timeout_s = lock_timeout_s
        self._adb_device: AdbDeviceTcpAsync | None = None
        self._lock = asyncio.Lock()

    @property
    def available(self) -> bool:
        """Si la conexión ADB está activa actualmente."""
        return self._adb_device is not None and self._adb_device.available

    async def connect(
        self,
        *,
        log_errors: bool = True,
        auth_timeout_s: float = DEFAULT_AUTH_TIMEOUT_S,
        transport_timeout_s: float = DEFAULT_TRANSPORT_TIMEOUT_S,
    ) -> bool:
        """Conectar al dispositivo mediante TCP.

        Parámetros
        ----------
        log_errors : bool
            Si se deben registrar los errores de conexión.
        auth_timeout_s : float
            Tiempo límite para la autenticación.
        transport_timeout_s : float
            Tiempo límite para la capa de transporte.

        Retorna
        -------
        bool
            True si la conexión fue establecida.

        """
        from adb_shell.adb_device_async import AdbDeviceTcpAsync
        from adb_shell.auth.keygen import keygen
        from adb_shell.auth.sign_pythonrsa import PythonRSASigner

        try:
            async with asyncio.timeout(self._lock_timeout_s):
                await self._lock.acquire()
        except TimeoutError as err:
            raise LockNotAcquiredError(self._lock_timeout_s) from err

        try:
            # Cerrar conexión existente
            if self._adb_device is not None:
                try:
                    await self._adb_device.close()
                except Exception:  # noqa: BLE001
                    pass

            self._adb_device = AdbDeviceTcpAsync(
                self._host,
                self._port,
                default_transport_timeout_s=transport_timeout_s,
            )

            # Cargar o generar clave
            signer = await self._load_adbkey(self._adbkey, keygen, PythonRSASigner)

            await self._adb_device.connect(
                rsa_keys=[signer] if signer else None,
                transport_timeout_s=transport_timeout_s,
                auth_timeout_s=auth_timeout_s,
            )

            if self.available:
                _LOGGER.debug("Connected to %s:%d", self._host, self._port)
                return True

            if log_errors:
                _LOGGER.warning("Connection to %s:%d not available after connect", self._host, self._port)
            return False

        except Exception as exc:  # noqa: BLE001
            if log_errors:
                _LOGGER.warning("Failed to connect to %s:%d: %s", self._host, self._port, exc)
            self._adb_device = None
            return False
        finally:
            self._lock.release()

    async def close(self) -> None:
        """Cerrar la conexión ADB."""
        if self._adb_device is not None:
            try:
                await self._adb_device.close()
            except Exception:  # noqa: BLE001
                pass
            self._adb_device = None

    async def shell(self, cmd: str) -> str | None:
        """Ejecutar un comando de shell ADB.

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
            _LOGGER.debug("Cannot execute shell command - not connected to %s:%d", self._host, self._port)
            return None

        try:
            async with asyncio.timeout(self._lock_timeout_s):
                await self._lock.acquire()
        except TimeoutError as err:
            raise LockNotAcquiredError(self._lock_timeout_s) from err

        try:
            assert self._adb_device is not None  # noqa: S101
            response = await self._adb_device.shell(cmd, timeout_s=self._adb_timeout_s)
            if isinstance(response, bytes):
                return response.decode("utf-8", errors="replace").strip()
            return response.strip() if response else None
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Shell command failed on %s:%d: %s", self._host, self._port, exc)
            return None
        finally:
            self._lock.release()

    async def pull(self, device_path: str, local_path: str) -> None:
        """Descargar un archivo del dispositivo.

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
            assert self._adb_device is not None  # noqa: S101
            content = await self._adb_device.pull(device_path)
            import aiofiles

            async with aiofiles.open(local_path, "wb") as f:
                await f.write(content)
        finally:
            self._lock.release()

    async def push(self, local_path: str, device_path: str) -> None:
        """Enviar un archivo al dispositivo.

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
            assert self._adb_device is not None  # noqa: S101
            import aiofiles

            async with aiofiles.open(local_path, "rb") as f:
                content = await f.read()
            await self._adb_device.push(content, device_path)
        finally:
            self._lock.release()

    async def screencap(self) -> bytes | None:
        """Capturar una captura de pantalla del dispositivo.

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
            assert self._adb_device is not None  # noqa: S101
            response = await self._adb_device.shell("screencap -p", timeout_s=self._adb_timeout_s)
            if isinstance(response, bytes):
                return response
            return response.encode("latin-1") if response else None
        except Exception:  # noqa: BLE001
            return None
        finally:
            self._lock.release()

    @staticmethod
    async def _load_adbkey(
        adbkey_path: str,
        keygen_func: object,
        signer_cls: type,
    ) -> object | None:
        """Cargar o generar una clave ADB para autenticación.

        Parámetros
        ----------
        adbkey_path : str
            Ruta al archivo de clave privada ADB.
        keygen_func : callable
            Función para generar un nuevo par de claves.
        signer_cls : type
            La clase de firmante RSA.

        Retorna
        -------
        object o None
            La instancia del firmante, o None si no hay clave disponible.

        """
        if not adbkey_path:
            return None

        key_path = Path(adbkey_path)
        if not key_path.exists():
            # Generar un nuevo par de claves
            keygen_func(str(key_path))  # type: ignore[operator]

        with key_path.open("r") as f:
            private_key = f.read()

        pub_path = key_path.with_suffix(key_path.suffix + ".pub")
        public_key = ""
        if pub_path.exists():
            with pub_path.open("r") as f:
                public_key = f.read()

        return signer_cls(private_key, public_key)  # type: ignore[operator]
