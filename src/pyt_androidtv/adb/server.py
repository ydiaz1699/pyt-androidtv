"""ADB connection via an ADB server using adbutils."""

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
    """ADB connection that delegates commands to an ADB server.

    Parameters
    ----------
    host : str
        The device serial/address (e.g., "192.168.1.100:5555").
    adb_server_ip : str
        The IP address of the ADB server.
    adb_server_port : int
        The port of the ADB server (default 5037).
    lock_timeout_s : float
        Timeout for acquiring the internal lock.

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
        """Whether the ADB connection is currently active."""
        return self._device is not None

    async def connect(
        self,
        *,
        log_errors: bool = True,
        auth_timeout_s: float = 10.0,
        transport_timeout_s: float = 1.0,
    ) -> bool:
        """Connect to the device via the ADB server.

        Parameters
        ----------
        log_errors : bool
            Whether to log connection errors.
        auth_timeout_s : float
            Unused for server connections (handled by the server).
        transport_timeout_s : float
            Unused for server connections (handled by the server).

        Returns
        -------
        bool
            True if the connection was established.

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

            # Connect to the device through the ADB server
            device = await loop.run_in_executor(None, partial(client.device, serial=self._serial))
            # Verify the device is reachable
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
        """Close the ADB connection."""
        self._device = None

    async def shell(self, cmd: str) -> str | None:
        """Execute an ADB shell command via the ADB server.

        Parameters
        ----------
        cmd : str
            The shell command to execute.

        Returns
        -------
        str or None
            The command output, or None if execution failed.

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
        """Pull a file from the device via the ADB server.

        Parameters
        ----------
        device_path : str
            The path on the device.
        local_path : str
            The local destination path.

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
        """Push a file to the device via the ADB server.

        Parameters
        ----------
        local_path : str
            The local file path.
        device_path : str
            The destination path on the device.

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
        """Capture a screenshot from the device via the ADB server.

        Returns
        -------
        bytes or None
            The PNG screenshot data, or None if the capture failed.

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
