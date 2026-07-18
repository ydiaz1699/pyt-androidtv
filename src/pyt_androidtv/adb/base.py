"""Abstract base class for ADB connections."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ADBInterface(ABC):
    """Abstract interface for ADB communication with a device."""

    @property
    @abstractmethod
    def available(self) -> bool:
        """Whether the ADB connection is currently active and usable."""

    @abstractmethod
    async def connect(
        self,
        *,
        log_errors: bool = True,
        auth_timeout_s: float = 10.0,
        transport_timeout_s: float = 1.0,
    ) -> bool:
        """Establish a connection to the device.

        Parameters
        ----------
        log_errors : bool
            Whether to log connection errors.
        auth_timeout_s : float
            Timeout for authentication in seconds.
        transport_timeout_s : float
            Timeout for transport layer in seconds.

        Returns
        -------
        bool
            True if the connection was successful.

        """

    @abstractmethod
    async def close(self) -> None:
        """Close the ADB connection."""

    @abstractmethod
    async def shell(self, cmd: str) -> str | None:
        """Execute an ADB shell command.

        Parameters
        ----------
        cmd : str
            The shell command to execute.

        Returns
        -------
        str or None
            The command output, or None if the command failed.

        """

    @abstractmethod
    async def pull(self, device_path: str, local_path: str) -> None:
        """Pull a file from the device.

        Parameters
        ----------
        device_path : str
            The path on the device.
        local_path : str
            The local destination path.

        """

    @abstractmethod
    async def push(self, local_path: str, device_path: str) -> None:
        """Push a file to the device.

        Parameters
        ----------
        local_path : str
            The local file path.
        device_path : str
            The destination path on the device.

        """

    @abstractmethod
    async def screencap(self) -> bytes | None:
        """Capture a screenshot from the device.

        Returns
        -------
        bytes or None
            The PNG screenshot data, or None if the capture failed.

        """
