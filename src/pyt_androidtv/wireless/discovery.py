"""Descubrimiento automático de dispositivos Android TV/Fire TV en la red local.

Utiliza mDNS (Multicast DNS) para encontrar servicios ADB publicados
en la red. Los dispositivos Android con depuración inalámbrica habilitada
publican servicios bajo:
- _adb-tls-connect._tcp — para conexiones ADB
- _adb-tls-pairing._tcp — para emparejamiento

Inspirado en ADBCommandCenter (AdbDiscoveryManager.kt) que usa NSD (Network
Service Discovery) en Android para el mismo propósito.
"""

from __future__ import annotations

import asyncio
import logging
import socket
from dataclasses import dataclass, field
from datetime import datetime

_LOGGER = logging.getLogger(__name__)

# Tipos de servicio mDNS para ADB inalámbrico
SERVICE_TYPE_CONNECT = "_adb-tls-connect._tcp.local."
SERVICE_TYPE_PAIRING = "_adb-tls-pairing._tcp.local."


@dataclass(slots=True)
class DiscoveredDevice:
    """Dispositivo descubierto en la red local.

    Atributos
    ---------
    host : str
        Dirección IP del dispositivo.
    port : int
        Puerto ADB del dispositivo.
    name : str
        Nombre del servicio mDNS (generalmente el modelo del dispositivo).
    service_type : str
        Tipo de servicio ('connect' o 'pairing').
    discovered_at : str
        Marca de tiempo del descubrimiento.
    properties : dict
        Propiedades adicionales del servicio TXT.
    """

    host: str = ""
    port: int = 5555
    name: str = ""
    service_type: str = "connect"
    discovered_at: str = ""
    properties: dict[str, str] = field(default_factory=dict)

    @property
    def address(self) -> str:
        """Dirección completa host:port."""
        return f"{self.host}:{self.port}"

    @property
    def is_pairing_service(self) -> bool:
        """Si este es un servicio de emparejamiento."""
        return self.service_type == "pairing"

    @property
    def is_connect_service(self) -> bool:
        """Si este es un servicio de conexión."""
        return self.service_type == "connect"


class DeviceDiscovery:
    """Descubrimiento de dispositivos Android TV/Fire TV en la red local.

    Utiliza escaneo de red para encontrar dispositivos con ADB habilitado.
    Soporta dos métodos:
    1. Escaneo de puertos TCP (funciona siempre)
    2. mDNS/Zeroconf (requiere zeroconf instalado, más rápido)

    Uso
    ---
        >>> discovery = DeviceDiscovery()
        >>> dispositivos = await discovery.scan_network()
        >>> for d in dispositivos:
        ...     print(f"{d.name} en {d.address}")

    Parámetros
    ----------
    subnet : str
        Subred a escanear (ej: "192.168.1"). Si es vacío, se detecta automáticamente.
    timeout_s : float
        Tiempo máximo de espera por dispositivo durante el escaneo.
    """

    def __init__(self, subnet: str = "", timeout_s: float = 1.0) -> None:
        self._subnet = subnet
        self._timeout_s = timeout_s
        self._discovered: list[DiscoveredDevice] = []

    @property
    def devices(self) -> list[DiscoveredDevice]:
        """Lista de dispositivos descubiertos."""
        return list(self._discovered)

    async def scan_network(
        self,
        *,
        port: int = 5555,
        start_ip: int = 1,
        end_ip: int = 254,
    ) -> list[DiscoveredDevice]:
        """Escanear la red local buscando dispositivos con ADB habilitado.

        Realiza un escaneo TCP de la subred en el puerto ADB especificado.
        Es más lento que mDNS pero funciona con cualquier dispositivo ADB.

        Parámetros
        ----------
        port : int
            Puerto ADB a escanear (por defecto 5555).
        start_ip : int
            Primer octeto final de IP a escanear.
        end_ip : int
            Último octeto final de IP a escanear.

        Retorna
        -------
        list[DiscoveredDevice]
            Lista de dispositivos encontrados con ADB abierto.
        """
        subnet = self._subnet or await self._detect_subnet()
        if not subnet:
            _LOGGER.warning("No se pudo detectar la subred local")
            return []

        _LOGGER.info("Escaneando %s.%d-%d en puerto %d...", subnet, start_ip, end_ip, port)

        # Escanear en paralelo con semáforo para limitar conexiones
        semaphore = asyncio.Semaphore(50)
        tasks = [
            self._check_port(f"{subnet}.{i}", port, semaphore)
            for i in range(start_ip, end_ip + 1)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        self._discovered = [r for r in results if isinstance(r, DiscoveredDevice)]
        _LOGGER.info("Encontrados %d dispositivos con ADB abierto", len(self._discovered))
        return self._discovered

    async def scan_mdns(self, duration_s: float = 5.0) -> list[DiscoveredDevice]:
        """Descubrir dispositivos usando mDNS/Zeroconf.

        Busca servicios _adb-tls-connect._tcp y _adb-tls-pairing._tcp
        publicados en la red local. Requiere la librería 'zeroconf'.

        Parámetros
        ----------
        duration_s : float
            Duración del descubrimiento en segundos.

        Retorna
        -------
        list[DiscoveredDevice]
            Dispositivos descubiertos vía mDNS.

        Raises
        ------
        ImportError
            Si la librería zeroconf no está instalada.
        """
        try:
            from zeroconf import ServiceBrowser, Zeroconf  # type: ignore[import-untyped]
        except ImportError as err:
            raise ImportError(
                "Se requiere la librería 'zeroconf' para descubrimiento mDNS. "
                "Instalar con: pip install zeroconf"
            ) from err

        discovered: list[DiscoveredDevice] = []

        class _Listener:
            """Listener interno para servicios mDNS."""

            def add_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                info = zc.get_service_info(type_, name)
                if info and info.addresses:
                    host = socket.inet_ntoa(info.addresses[0])
                    svc_type = "pairing" if "pairing" in type_ else "connect"
                    device = DiscoveredDevice(
                        host=host,
                        port=info.port,
                        name=info.server or name,
                        service_type=svc_type,
                        discovered_at=datetime.now().isoformat(),
                        properties={
                            k.decode(): v.decode() if v else ""
                            for k, v in (info.properties or {}).items()
                        },
                    )
                    discovered.append(device)
                    _LOGGER.info(
                        "Descubierto [%s]: %s en %s:%d",
                        svc_type, device.name, host, info.port,
                    )

            def remove_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass

            def update_service(self, zc: Zeroconf, type_: str, name: str) -> None:
                pass

        # Ejecutar descubrimiento en thread separado para no bloquear
        loop = asyncio.get_running_loop()

        def _run_discovery() -> None:
            zc = Zeroconf()
            listener = _Listener()
            browsers = [
                ServiceBrowser(zc, SERVICE_TYPE_CONNECT, listener),
                ServiceBrowser(zc, SERVICE_TYPE_PAIRING, listener),
            ]
            import time
            time.sleep(duration_s)
            for browser in browsers:
                browser.cancel()
            zc.close()

        await loop.run_in_executor(None, _run_discovery)
        self._discovered = discovered
        return discovered

    async def find_device(self, host: str, port: int = 5555) -> DiscoveredDevice | None:
        """Verificar si un dispositivo específico tiene ADB habilitado.

        Parámetros
        ----------
        host : str
            Dirección IP del dispositivo.
        port : int
            Puerto ADB (por defecto 5555).

        Retorna
        -------
        DiscoveredDevice o None
            El dispositivo si ADB está disponible, None si no.
        """
        semaphore = asyncio.Semaphore(1)
        result = await self._check_port(host, port, semaphore)
        if isinstance(result, DiscoveredDevice):
            return result
        return None

    async def _check_port(
        self, host: str, port: int, semaphore: asyncio.Semaphore
    ) -> DiscoveredDevice | Exception:
        """Verificar si un puerto está abierto en un host.

        Parámetros
        ----------
        host : str
            Dirección IP a verificar.
        port : int
            Puerto a verificar.
        semaphore : asyncio.Semaphore
            Semáforo para limitar conexiones simultáneas.

        Retorna
        -------
        DiscoveredDevice o Exception
            Dispositivo si el puerto está abierto, excepción si no.
        """
        async with semaphore:
            try:
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=self._timeout_s,
                )
                writer.close()
                await writer.wait_closed()

                return DiscoveredDevice(
                    host=host,
                    port=port,
                    name=f"Dispositivo ADB ({host})",
                    service_type="connect",
                    discovered_at=datetime.now().isoformat(),
                )
            except (OSError, asyncio.TimeoutError) as exc:
                return exc

    @staticmethod
    async def _detect_subnet() -> str:
        """Detectar automáticamente la subred local.

        Retorna
        -------
        str
            Los primeros 3 octetos de la IP local (ej: "192.168.1").
        """
        loop = asyncio.get_running_loop()

        def _get_local_ip() -> str:
            """Obtener IP local conectando a DNS público."""
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            try:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
            except OSError:
                return ""
            finally:
                s.close()

        ip = await loop.run_in_executor(None, _get_local_ip)
        if ip:
            parts = ip.split(".")
            if len(parts) == 4:  # noqa: PLR2004
                return ".".join(parts[:3])
        return ""
