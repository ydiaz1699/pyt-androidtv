"""Conexión y emparejamiento inalámbrico ADB.

Proporciona la clase WirelessADB que maneja:
- Conexión TCP/IP directa (después del emparejamiento)
- Emparejamiento inalámbrico con código de 6 dígitos
- Cambio de modo USB a TCP/IP
- Reconexión automática

Inspirado en:
- ADBCommandCenter (AdbConnectionManager.kt, AdbPairingClient.kt)
- adb-wireless-toolkit (flujo connect/tcpip/pair)

Nota: El emparejamiento TLS nativo (como en ADBCommandCenter) requiere
implementación nativa del protocolo SPAKE2. Esta implementación usa
el binario adb del sistema como fallback para emparejamiento.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
from dataclasses import dataclass

from ..adb.base import ADBInterface
from ..adb.tcp import ADBConnection
from ..exceptions import ADBConnectionError
from .discovery import DeviceDiscovery, DiscoveredDevice

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ConnectionStatus:
    """Estado de la conexión inalámbrica.

    Atributos
    ---------
    connected : bool
        Si la conexión está activa.
    host : str
        Dirección IP del dispositivo.
    port : int
        Puerto de la conexión.
    paired : bool
        Si el dispositivo ha sido emparejado previamente.
    error : str
        Mensaje de error si la conexión falló.
    """

    connected: bool = False
    host: str = ""
    port: int = 5555
    paired: bool = False
    error: str = ""


class WirelessADB:
    """Gestión de conexiones inalámbricas ADB.

    Proporciona una interfaz de alto nivel para conectar dispositivos
    Android TV/Fire TV por WiFi sin necesidad de cable USB (después del
    emparejamiento inicial).

    Uso
    ---
        >>> wireless = WirelessADB("192.168.1.100")
        >>> # Emparejar (solo primera vez, código del dispositivo)
        >>> await wireless.pair(port=37123, code="123456")
        >>> # Conectar
        >>> conexion = await wireless.connect_tcp()
        >>> # Usar la conexión
        >>> resultado = await conexion.shell("getprop ro.product.model")

    Parámetros
    ----------
    host : str
        Dirección IP del dispositivo.
    port : int
        Puerto ADB por defecto (5555 para TCP, variable para emparejamiento).
    adbkey : str
        Ruta al archivo de clave ADB para autenticación.
    """

    def __init__(self, host: str, port: int = 5555, adbkey: str = "") -> None:
        self._host = host
        self._port = port
        self._adbkey = adbkey
        self._connection: ADBConnection | None = None
        self._discovery = DeviceDiscovery()

    @property
    def host(self) -> str:
        """Dirección IP del dispositivo."""
        return self._host

    @property
    def port(self) -> int:
        """Puerto actual de la conexión."""
        return self._port

    @property
    def is_connected(self) -> bool:
        """Si hay una conexión activa al dispositivo."""
        return self._connection is not None and self._connection.available

    @property
    def connection(self) -> ADBConnection | None:
        """La conexión ADB activa, o None si no está conectado."""
        return self._connection

    async def connect_tcp(self, *, port: int | None = None, timeout_s: float = 10.0) -> ADBConnection:
        """Conectar al dispositivo vía TCP/IP.

        Establece una conexión ADB directa al dispositivo por la red.
        El dispositivo debe tener ADB por red habilitado (ya sea por
        emparejamiento inalámbrico o por `adb tcpip 5555`).

        Parámetros
        ----------
        port : int o None
            Puerto de conexión. Si es None, usa el puerto por defecto.
        timeout_s : float
            Timeout para la conexión en segundos.

        Retorna
        -------
        ADBConnection
            La conexión ADB establecida.

        Raises
        ------
        ADBConnectionError
            Si no se puede establecer la conexión.
        """
        connect_port = port or self._port
        _LOGGER.info("Conectando a %s:%d vía TCP...", self._host, connect_port)

        self._connection = ADBConnection(
            host=self._host,
            port=connect_port,
            adbkey=self._adbkey,
        )

        success = await self._connection.connect(auth_timeout_s=timeout_s)
        if not success:
            self._connection = None
            raise ADBConnectionError(
                self._host, connect_port,
                "No se pudo establecer conexión TCP. "
                "Verificar que ADB inalámbrico esté habilitado en el dispositivo."
            )

        _LOGGER.info("Conexión TCP establecida a %s:%d", self._host, connect_port)
        return self._connection

    async def pair(self, *, port: int, code: str) -> bool:
        """Emparejar con el dispositivo usando código de emparejamiento.

        El emparejamiento es necesario una sola vez. Después, el dispositivo
        recordará la clave y se podrá conectar directamente con connect_tcp().

        Para obtener el código:
        1. En el dispositivo: Ajustes > Opciones de desarrollador > Depuración inalámbrica
        2. Tocar "Emparejar dispositivo con código de emparejamiento"
        3. Se muestra un código de 6 dígitos y un puerto

        Parámetros
        ----------
        port : int
            Puerto de emparejamiento mostrado en el dispositivo.
        code : str
            Código de 6 dígitos mostrado en el dispositivo.

        Retorna
        -------
        bool
            True si el emparejamiento fue exitoso.

        Raises
        ------
        RuntimeError
            Si el binario 'adb' no está disponible en el sistema.
        ADBConnectionError
            Si el emparejamiento falla.
        """
        adb_path = shutil.which("adb")
        if not adb_path:
            raise RuntimeError(
                "No se encontró el binario 'adb' en el PATH del sistema. "
                "Instalar Android Platform Tools: "
                "https://developer.android.com/tools/releases/platform-tools"
            )

        _LOGGER.info("Emparejando con %s:%d...", self._host, port)

        # Usar el binario adb del sistema para emparejamiento
        # (El protocolo SPAKE2 nativo requiere implementación en C)
        pair_address = f"{self._host}:{port}"
        process = await asyncio.create_subprocess_exec(
            adb_path, "pair", pair_address, code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30.0)

        output = (stdout or b"").decode() + (stderr or b"").decode()

        if process.returncode == 0 and "Successfully paired" in output:
            _LOGGER.info("Emparejamiento exitoso con %s:%d", self._host, port)
            return True

        error_msg = output.strip() or "Emparejamiento rechazado por el dispositivo"
        _LOGGER.warning("Emparejamiento fallido: %s", error_msg)
        raise ADBConnectionError(self._host, port, f"Emparejamiento fallido: {error_msg}")

    async def enable_tcpip(self, *, usb_port: int = 5555) -> bool:
        """Habilitar ADB por TCP/IP desde una conexión USB.

        Este método requiere que el dispositivo esté conectado por USB.
        Ejecuta 'adb tcpip <port>' para habilitar ADB por red.

        Parámetros
        ----------
        usb_port : int
            Puerto TCP en el que se habilitará ADB (por defecto 5555).

        Retorna
        -------
        bool
            True si se habilitó exitosamente.
        """
        adb_path = shutil.which("adb")
        if not adb_path:
            raise RuntimeError(
                "No se encontró el binario 'adb' en el PATH del sistema."
            )

        _LOGGER.info("Habilitando ADB TCP en puerto %d...", usb_port)

        process = await asyncio.create_subprocess_exec(
            adb_path, "tcpip", str(usb_port),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=10.0)

        output = (stdout or b"").decode() + (stderr or b"").decode()

        if process.returncode == 0 or "restarting in TCP mode" in output:
            self._port = usb_port
            _LOGGER.info("ADB TCP habilitado en puerto %d", usb_port)
            return True

        _LOGGER.warning("No se pudo habilitar TCP: %s", output)
        return False

    async def disconnect(self) -> None:
        """Cerrar la conexión inalámbrica activa."""
        if self._connection:
            await self._connection.close()
            self._connection = None
            _LOGGER.info("Desconectado de %s", self._host)

    async def reconnect(self, *, max_retries: int = 3, delay_s: float = 2.0) -> bool:
        """Intentar reconectar al dispositivo.

        Útil cuando la conexión se pierde temporalmente (ej: dispositivo
        se suspende y despierta).

        Parámetros
        ----------
        max_retries : int
            Número máximo de intentos de reconexión.
        delay_s : float
            Espera entre intentos en segundos.

        Retorna
        -------
        bool
            True si se reconectó exitosamente.
        """
        await self.disconnect()

        for attempt in range(1, max_retries + 1):
            _LOGGER.info(
                "Intento de reconexión %d/%d a %s:%d...",
                attempt, max_retries, self._host, self._port,
            )
            try:
                await self.connect_tcp()
                return True
            except ADBConnectionError:
                if attempt < max_retries:
                    await asyncio.sleep(delay_s)

        _LOGGER.warning(
            "Reconexión fallida después de %d intentos", max_retries
        )
        return False

    async def get_status(self) -> ConnectionStatus:
        """Obtener el estado actual de la conexión.

        Retorna
        -------
        ConnectionStatus
            Estado detallado de la conexión.
        """
        return ConnectionStatus(
            connected=self.is_connected,
            host=self._host,
            port=self._port,
            paired=self.is_connected,
        )

    @classmethod
    async def discover(
        cls,
        *,
        subnet: str = "",
        timeout_s: float = 1.0,
    ) -> list[DiscoveredDevice]:
        """Descubrir dispositivos Android TV/Fire TV en la red local.

        Método de conveniencia que crea un DeviceDiscovery y escanea la red.

        Parámetros
        ----------
        subnet : str
            Subred a escanear (ej: "192.168.1"). Autodetecta si está vacío.
        timeout_s : float
            Timeout por dispositivo durante el escaneo.

        Retorna
        -------
        list[DiscoveredDevice]
            Lista de dispositivos encontrados.
        """
        discovery = DeviceDiscovery(subnet=subnet, timeout_s=timeout_s)
        return await discovery.scan_network()

    @classmethod
    async def discover_mdns(cls, duration_s: float = 5.0) -> list[DiscoveredDevice]:
        """Descubrir dispositivos usando mDNS (Zeroconf).

        Más rápido y preciso que el escaneo de puertos, pero requiere
        que los dispositivos publiquen servicios mDNS (Android 11+).

        Parámetros
        ----------
        duration_s : float
            Duración del descubrimiento en segundos.

        Retorna
        -------
        list[DiscoveredDevice]
            Dispositivos descubiertos.
        """
        discovery = DeviceDiscovery()
        return await discovery.scan_mdns(duration_s=duration_s)
