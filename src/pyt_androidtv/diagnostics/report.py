"""Diagnostic report generation for Android TV / Fire TV devices."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, TYPE_CHECKING

from .apps import AppDiagnostics, AppsReport
from .network import NetworkDiagnostics, NetworkReport
from .system import SystemDiagnostics, SystemSnapshot

if TYPE_CHECKING:
    from ..adb.base import ADBInterface


@dataclass(slots=True)
class DiagnosticReport:
    """A complete diagnostic report for a device."""

    timestamp: str = ""
    system: SystemSnapshot | None = None
    network: NetworkReport | None = None
    apps: AppsReport | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert the report to a dictionary.

        Returns
        -------
        dict
            The report as a nested dictionary.

        """
        result: dict[str, Any] = {"timestamp": self.timestamp}

        if self.system:
            system_dict: dict[str, Any] = {"uptime": self.system.uptime, "boot_count": self.system.boot_count}

            if self.system.battery:
                system_dict["battery"] = {
                    "level": self.system.battery.level,
                    "status": self.system.battery.status,
                    "health": self.system.battery.health,
                    "temperature": self.system.battery.temperature,
                    "voltage": self.system.battery.voltage,
                    "technology": self.system.battery.technology,
                    "plugged": self.system.battery.plugged,
                }

            if self.system.memory:
                system_dict["memory"] = {
                    "total_kb": self.system.memory.total_kb,
                    "free_kb": self.system.memory.free_kb,
                    "available_kb": self.system.memory.available_kb,
                    "usage_percent": round(self.system.memory.usage_percent, 1),
                }

            if self.system.storage:
                system_dict["storage"] = [
                    {
                        "filesystem": s.filesystem,
                        "mount_point": s.mount_point,
                        "total_blocks": s.total_blocks,
                        "used_blocks": s.used_blocks,
                        "usage_percent": round(s.usage_percent, 1),
                    }
                    for s in self.system.storage
                ]

            system_dict["active_services_count"] = len(self.system.active_services)
            result["system"] = system_dict

        if self.network:
            network_dict: dict[str, Any] = {}

            if self.network.wifi:
                network_dict["wifi"] = {
                    "ssid": self.network.wifi.ssid,
                    "bssid": self.network.wifi.bssid,
                    "ip_address": self.network.wifi.ip_address,
                    "link_speed_mbps": self.network.wifi.link_speed_mbps,
                    "rssi": self.network.wifi.rssi,
                    "state": self.network.wifi.state,
                }

            network_dict["interfaces_count"] = len(self.network.interfaces)
            network_dict["dns_servers"] = self.network.dns_servers
            result["network"] = network_dict

        if self.apps:
            result["apps"] = {
                "total_packages": len(self.apps.all_packages),
                "third_party_packages": len(self.apps.third_party_packages),
                "running_processes": len(self.apps.running_processes),
                "top_memory_apps": self.apps.top_memory_apps[:5],
            }

        return result

    def summary(self) -> str:
        """Generate a human-readable summary of the report.

        Returns
        -------
        str
            A summary string.

        """
        lines: list[str] = [f"Diagnostic Report - {self.timestamp}", "=" * 50]

        if self.system:
            lines.append("\n[System]")
            lines.append(f"  Uptime: {self.system.uptime}")
            if self.system.boot_count is not None:
                lines.append(f"  Boot count: {self.system.boot_count}")
            if self.system.memory:
                lines.append(
                    f"  Memory: {self.system.memory.usage_percent:.1f}% used "
                    f"({self.system.memory.available_kb // 1024} MB available)"
                )
            if self.system.battery:
                lines.append(f"  Battery: {self.system.battery.level}% ({self.system.battery.status})")
            lines.append(f"  Active services: {len(self.system.active_services)}")

        if self.network:
            lines.append("\n[Network]")
            if self.network.wifi:
                lines.append(f"  WiFi: {self.network.wifi.ssid} ({self.network.wifi.state})")
                lines.append(f"  IP: {self.network.wifi.ip_address}")
                lines.append(f"  Signal: {self.network.wifi.rssi} dBm")
            lines.append(f"  Interfaces: {len(self.network.interfaces)}")
            lines.append(f"  DNS: {', '.join(self.network.dns_servers) or 'N/A'}")

        if self.apps:
            lines.append("\n[Applications]")
            lines.append(f"  Total packages: {len(self.apps.all_packages)}")
            lines.append(f"  Third-party: {len(self.apps.third_party_packages)}")
            lines.append(f"  Running processes: {len(self.apps.running_processes)}")
            if self.apps.top_memory_apps:
                lines.append("  Top memory usage:")
                for name, mem_kb in self.apps.top_memory_apps[:5]:
                    lines.append(f"    {name}: {mem_kb // 1024} MB")

        return "\n".join(lines)


class DeviceDiagnostics:
    """Complete device diagnostics coordinator.

    Provides access to system, network, and app diagnostics subsystems,
    and can generate comprehensive reports.

    Parameters
    ----------
    adb : ADBInterface
        The ADB connection to use for queries.

    """

    def __init__(self, adb: ADBInterface) -> None:
        self._adb = adb
        self.system = SystemDiagnostics(adb)
        self.network = NetworkDiagnostics(adb)
        self.apps = AppDiagnostics(adb)

    async def __aenter__(self) -> DeviceDiagnostics:
        """Enter the async context manager."""
        return self

    async def __aexit__(self, *_exc: object) -> None:
        """Exit the async context manager."""
        # No cleanup needed for diagnostics
        pass

    async def full_report(self) -> DiagnosticReport:
        """Generate a full diagnostic report.

        Returns
        -------
        DiagnosticReport
            A comprehensive report including system, network, and app data.

        """
        timestamp = datetime.now(tz=timezone.utc).isoformat()

        system_snapshot = await self.system.get_system_snapshot()
        network_report = await self.network.get_network_report()
        apps_report = await self.apps.get_apps_report()

        return DiagnosticReport(
            timestamp=timestamp,
            system=system_snapshot,
            network=network_report,
            apps=apps_report,
        )

    async def quick_check(self) -> DiagnosticReport:
        """Generate a quick diagnostic check (minimal data).

        Returns
        -------
        DiagnosticReport
            A lightweight report with basic system and network info.

        """
        timestamp = datetime.now(tz=timezone.utc).isoformat()

        # Only get basic info for a quick check
        memory = await self.system.get_memory_info()
        uptime = await self.system.get_uptime()
        wifi = await self.network.get_wifi_info()

        system_snapshot = SystemSnapshot(
            memory=memory,
            uptime=uptime,
        )

        network_report = NetworkReport(wifi=wifi)

        return DiagnosticReport(
            timestamp=timestamp,
            system=system_snapshot,
            network=network_report,
        )
