"""ADB connection over TCP using adb-shell library."""

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
    """ADB connection over TCP using the adb-shell library.

    Parameters
    ----------
    host : str
        The device IP address or hostname.
    port : int
        The device ADB port (default 5555).
    adbkey : str
        Path to the ADB private key file.
    adb_timeout_s : float
        Timeout for ADB operations.
    lock_timeout_s : float
        Timeout for acquiring the internal lock.

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
        """Whether the ADB connection is currently active."""
        return self._adb_device is not None and self._adb_device.available

    async def connect(
        self,
        *,
        log_errors: bool = True,
        auth_timeout_s: float = DEFAULT_AUTH_TIMEOUT_S,
        transport_timeout_s: float = DEFAULT_TRANSPORT_TIMEOUT_S,
    ) -> bool:
        """Connect to the device via TCP.

        Parameters
        ----------
        log_errors : bool
            Whether to log connection errors.
        auth_timeout_s : float
            Timeout for authentication.
        transport_timeout_s : float
            Timeout for the transport layer.

        Returns
        -------
        bool
            True if the connection was established.

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
            # Close existing connection
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

            # Load or generate key
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
        """Close the ADB connection."""
        if self._adb_device is not None:
            try:
                await self._adb_device.close()
            except Exception:  # noqa: BLE001
                pass
            self._adb_device = None

    async def shell(self, cmd: str) -> str | None:
        """Execute an ADB shell command.

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
        """Pull a file from the device.

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
            assert self._adb_device is not None  # noqa: S101
            content = await self._adb_device.pull(device_path)
            import aiofiles

            async with aiofiles.open(local_path, "wb") as f:
                await f.write(content)
        finally:
            self._lock.release()

    async def push(self, local_path: str, device_path: str) -> None:
        """Push a file to the device.

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
            assert self._adb_device is not None  # noqa: S101
            import aiofiles

            async with aiofiles.open(local_path, "rb") as f:
                content = await f.read()
            await self._adb_device.push(content, device_path)
        finally:
            self._lock.release()

    async def screencap(self) -> bytes | None:
        """Capture a screenshot from the device.

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
        """Load or generate an ADB key for authentication.

        Parameters
        ----------
        adbkey_path : str
            Path to the ADB private key file.
        keygen_func : callable
            Function to generate a new key pair.
        signer_cls : type
            The RSA signer class.

        Returns
        -------
        object or None
            The signer instance, or None if no key is available.

        """
        if not adbkey_path:
            return None

        key_path = Path(adbkey_path)
        if not key_path.exists():
            # Generate a new key pair
            keygen_func(str(key_path))  # type: ignore[operator]

        with key_path.open("r") as f:
            private_key = f.read()

        pub_path = key_path.with_suffix(key_path.suffix + ".pub")
        public_key = ""
        if pub_path.exists():
            with pub_path.open("r") as f:
                public_key = f.read()

        return signer_cls(private_key, public_key)  # type: ignore[operator]
