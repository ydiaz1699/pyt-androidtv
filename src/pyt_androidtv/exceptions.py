"""Custom exceptions for pyt-androidtv."""

from __future__ import annotations


class PytAndroidTVError(Exception):
    """Base exception for all pyt-androidtv errors."""


class ADBConnectionError(PytAndroidTVError):
    """Raised when an ADB connection cannot be established or is lost."""

    def __init__(self, host: str, port: int, reason: str = "") -> None:
        self.host = host
        self.port = port
        self.reason = reason
        msg = f"ADB connection failed to {host}:{port}"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg)


class DeviceNotAvailableError(PytAndroidTVError):
    """Raised when the device is not available for communication."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        super().__init__(f"Device {host}:{port} is not available")


class LockNotAcquiredError(PytAndroidTVError):
    """Raised when the ADB lock could not be acquired within the timeout."""

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        super().__init__(f"ADB lock not acquired within {timeout}s timeout")


class InvalidStateDetectionRuleError(PytAndroidTVError):
    """Raised when a state detection rule is invalid."""

    def __init__(self, rule: object, reason: str) -> None:
        self.rule = rule
        self.reason = reason
        super().__init__(f"Invalid state detection rule: {rule!r} - {reason}")


class CommandError(PytAndroidTVError):
    """Raised when an ADB command fails unexpectedly."""

    def __init__(self, command: str, output: str | None = None) -> None:
        self.command = command
        self.output = output
        msg = f"ADB command failed: {command}"
        if output:
            msg += f"\nOutput: {output}"
        super().__init__(msg)
