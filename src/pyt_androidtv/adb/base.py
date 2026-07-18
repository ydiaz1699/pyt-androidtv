"""Clase base abstracta para conexiones ADB."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ADBInterface(ABC):
    """Interfaz abstracta para la comunicación ADB con un dispositivo."""

    @property
    @abstractmethod
    def available(self) -> bool:
        """Si la conexión ADB está activa y utilizable actualmente."""

    @abstractmethod
    async def connect(
        self,
        *,
        log_errors: bool = True,
        auth_timeout_s: float = 10.0,
        transport_timeout_s: float = 1.0,
    ) -> bool:
        """Establecer una conexión con el dispositivo.

        Parámetros
        ----------
        log_errors : bool
            Si se deben registrar los errores de conexión.
        auth_timeout_s : float
            Tiempo límite para la autenticación en segundos.
        transport_timeout_s : float
            Tiempo límite para la capa de transporte en segundos.

        Retorna
        -------
        bool
            True si la conexión fue exitosa.

        """

    @abstractmethod
    async def close(self) -> None:
        """Cerrar la conexión ADB."""

    @abstractmethod
    async def shell(self, cmd: str) -> str | None:
        """Ejecutar un comando de shell ADB.

        Parámetros
        ----------
        cmd : str
            El comando de shell a ejecutar.

        Retorna
        -------
        str o None
            La salida del comando, o None si el comando falló.

        """

    @abstractmethod
    async def pull(self, device_path: str, local_path: str) -> None:
        """Descargar un archivo del dispositivo.

        Parámetros
        ----------
        device_path : str
            La ruta en el dispositivo.
        local_path : str
            La ruta de destino local.

        """

    @abstractmethod
    async def push(self, local_path: str, device_path: str) -> None:
        """Enviar un archivo al dispositivo.

        Parámetros
        ----------
        local_path : str
            La ruta del archivo local.
        device_path : str
            La ruta de destino en el dispositivo.

        """

    @abstractmethod
    async def screencap(self) -> bytes | None:
        """Capturar una captura de pantalla del dispositivo.

        Retorna
        -------
        bytes o None
            Los datos de la captura de pantalla en PNG, o None si la captura falló.

        """
