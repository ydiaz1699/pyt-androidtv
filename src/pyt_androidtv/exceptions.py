"""Excepciones personalizadas para pyt-androidtv."""

from __future__ import annotations


class PytAndroidTVError(Exception):
    """Excepción base para todos los errores de pyt-androidtv."""


class ADBConnectionError(PytAndroidTVError):
    """Se lanza cuando no se puede establecer o se pierde una conexión ADB."""

    def __init__(self, host: str, port: int, reason: str = "") -> None:
        self.host = host
        self.port = port
        self.reason = reason
        msg = f"ADB connection failed to {host}:{port}"
        if reason:
            msg += f" - {reason}"
        super().__init__(msg)


class DeviceNotAvailableError(PytAndroidTVError):
    """Se lanza cuando el dispositivo no está disponible para comunicación."""

    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        super().__init__(f"Device {host}:{port} is not available")


class LockNotAcquiredError(PytAndroidTVError):
    """Se lanza cuando no se pudo adquirir el bloqueo ADB dentro del tiempo límite."""

    def __init__(self, timeout: float) -> None:
        self.timeout = timeout
        super().__init__(f"ADB lock not acquired within {timeout}s timeout")


class InvalidStateDetectionRuleError(PytAndroidTVError):
    """Se lanza cuando una regla de detección de estado es inválida."""

    def __init__(self, rule: object, reason: str) -> None:
        self.rule = rule
        self.reason = reason
        super().__init__(f"Invalid state detection rule: {rule!r} - {reason}")


class CommandError(PytAndroidTVError):
    """Se lanza cuando un comando ADB falla inesperadamente."""

    def __init__(self, command: str, output: str | None = None) -> None:
        self.command = command
        self.output = output
        msg = f"ADB command failed: {command}"
        if output:
            msg += f"\nOutput: {output}"
        super().__init__(msg)
