"""Módulo de conexión inalámbrica ADB.

Proporciona funcionalidades para:
- Descubrimiento automático de dispositivos en la red local (mDNS/Zeroconf)
- Emparejamiento inalámbrico (pairing) sin cable USB
- Conexión TCP/IP directa por WiFi
- Gestión de conexiones con reconexión automática

Inspirado en:
- ADBCommandCenter (https://github.com/joaomgcd/ADBCommandCenter) - Protocolo de emparejamiento
- adb-wireless-toolkit (https://github.com/shivamprasad1001/adb-wireless-toolkit) - Flujo de trabajo WiFi
"""

from .discovery import DeviceDiscovery, DiscoveredDevice
from .pairing import WirelessADB

__all__ = [
    "WirelessADB",
    "DeviceDiscovery",
    "DiscoveredDevice",
]
