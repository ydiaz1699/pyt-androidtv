"""Network diagnostics for Android TV / Fire TV devices."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..adb.base import ADBInterface


@dataclass(frozen=True, slots=True)
class WifiInfo:
    """WiFi connection information."""

    ssid: str = ""
    bssid: str = ""
    ip_address: str = ""
    link_speed_mbps: int = 0
    rssi: int = 0
    frequency_mhz: int = 0
    mac_address: str = ""
    state: str = "DISCONNECTED"


@dataclass(frozen=True, slots=True)
class NetworkInterface:
    """A network interface on the device."""

    name: str = ""
    ip_address: str = ""
    mac_address: str = ""
    state: str = "DOWN"


@dataclass(frozen=True, slots=True)
class WifiScanResult:
    """A single WiFi scan result."""

    ssid: str = ""
    bssid: str = ""
    frequency_mhz: int = 0
    level_dbm: int = 0
    capabilities: str = ""


@dataclass(frozen=True, slots=True)
class NetworkReport:
    """Complete network diagnostics report."""

    wifi: WifiInfo | None = None
    interfaces: list[NetworkInterface] = field(default_factory=list)
    scan_results: list[WifiScanResult] = field(default_factory=list)
    dns_servers: list[str] = field(default_factory=list)


class NetworkDiagnostics:
    """Network diagnostics for a connected device.

    Parameters
    ----------
    adb : ADBInterface
        The ADB connection to use for queries.

    """

    def __init__(self, adb: ADBInterface) -> None:
        self._adb = adb

    async def get_wifi_info(self) -> WifiInfo | None:
        """Get current WiFi connection information.

        Returns
        -------
        WifiInfo or None
            WiFi info, or None if not available.

        """
        response = await self._adb.shell("dumpsys wifi | grep 'mWifiInfo'")
        if not response:
            return None

        ssid = ""
        bssid = ""
        ip_address = ""
        link_speed = 0
        rssi = 0
        frequency = 0
        mac_address = ""
        state = "DISCONNECTED"

        # Parse mWifiInfo output
        ssid_match = re.search(r'SSID: "?([^",]+)"?', response)
        if ssid_match:
            ssid = ssid_match.group(1)

        bssid_match = re.search(r"BSSID: ([0-9a-f:]+)", response, re.IGNORECASE)
        if bssid_match:
            bssid = bssid_match.group(1)

        ip_match = re.search(r"IP: ([0-9.]+)", response)
        if ip_match:
            ip_address = ip_match.group(1)

        speed_match = re.search(r"Link speed: (\d+)", response)
        if speed_match:
            link_speed = int(speed_match.group(1))

        rssi_match = re.search(r"RSSI: (-?\d+)", response)
        if rssi_match:
            rssi = int(rssi_match.group(1))

        freq_match = re.search(r"Frequency: (\d+)", response)
        if freq_match:
            frequency = int(freq_match.group(1))

        mac_match = re.search(r"MAC: ([0-9a-f:]+)", response, re.IGNORECASE)
        if mac_match:
            mac_address = mac_match.group(1)

        if ssid:
            state = "CONNECTED"

        return WifiInfo(
            ssid=ssid,
            bssid=bssid,
            ip_address=ip_address,
            link_speed_mbps=link_speed,
            rssi=rssi,
            frequency_mhz=frequency,
            mac_address=mac_address,
            state=state,
        )

    async def get_network_interfaces(self) -> list[NetworkInterface]:
        """Get all network interfaces.

        Returns
        -------
        list of NetworkInterface
            All network interfaces on the device.

        """
        response = await self._adb.shell("ip addr show")
        if not response:
            return []

        interfaces: list[NetworkInterface] = []
        current_name = ""
        current_ip = ""
        current_mac = ""
        current_state = "DOWN"

        for line in response.splitlines():
            # New interface header
            iface_match = re.match(r"\d+: (\S+?):", line)
            if iface_match:
                # Save previous interface
                if current_name:
                    interfaces.append(
                        NetworkInterface(
                            name=current_name,
                            ip_address=current_ip,
                            mac_address=current_mac,
                            state=current_state,
                        )
                    )
                current_name = iface_match.group(1)
                current_ip = ""
                current_mac = ""
                current_state = "UP" if "UP" in line else "DOWN"
            else:
                # Parse inet address
                inet_match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", line)
                if inet_match:
                    current_ip = inet_match.group(1)

                # Parse MAC address
                ether_match = re.search(r"link/ether ([0-9a-f:]+)", line, re.IGNORECASE)
                if ether_match:
                    current_mac = ether_match.group(1)

        # Don't forget the last interface
        if current_name:
            interfaces.append(
                NetworkInterface(
                    name=current_name,
                    ip_address=current_ip,
                    mac_address=current_mac,
                    state=current_state,
                )
            )

        return interfaces

    async def get_wifi_scan_results(self) -> list[WifiScanResult]:
        """Get WiFi scan results (nearby networks).

        Returns
        -------
        list of WifiScanResult
            Nearby WiFi networks.

        """
        response = await self._adb.shell("dumpsys wifi | grep -A 5 'Latest scan results'")
        if not response:
            return []

        results: list[WifiScanResult] = []
        for line in response.splitlines():
            # Parse scan result lines: SSID BSSID freq level capabilities
            match = re.match(r"\s*(.+?)\s+([0-9a-f:]{17})\s+(\d+)\s+(-?\d+)\s+(.+)", line, re.IGNORECASE)
            if match:
                results.append(
                    WifiScanResult(
                        ssid=match.group(1).strip(),
                        bssid=match.group(2),
                        frequency_mhz=int(match.group(3)),
                        level_dbm=int(match.group(4)),
                        capabilities=match.group(5).strip(),
                    )
                )

        return results

    async def get_dns_servers(self) -> list[str]:
        """Get configured DNS servers.

        Returns
        -------
        list of str
            The DNS server addresses.

        """
        response = await self._adb.shell("getprop net.dns1 && getprop net.dns2")
        if not response:
            return []

        servers: list[str] = []
        for line in response.splitlines():
            addr = line.strip()
            if addr:
                servers.append(addr)
        return servers

    async def get_network_report(self) -> NetworkReport:
        """Get a complete network diagnostics report.

        Returns
        -------
        NetworkReport
            A comprehensive network report.

        """
        wifi = await self.get_wifi_info()
        interfaces = await self.get_network_interfaces()
        scan_results = await self.get_wifi_scan_results()
        dns_servers = await self.get_dns_servers()

        return NetworkReport(
            wifi=wifi,
            interfaces=interfaces,
            scan_results=scan_results,
            dns_servers=dns_servers,
        )
