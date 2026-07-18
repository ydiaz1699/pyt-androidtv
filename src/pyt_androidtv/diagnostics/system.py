"""System diagnostics for Android TV / Fire TV devices."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..adb.base import ADBInterface


@dataclass(frozen=True, slots=True)
class BatteryInfo:
    """Battery information (for battery-powered devices)."""

    level: int = 0
    status: str = "unknown"
    health: str = "unknown"
    temperature: float = 0.0
    voltage: float = 0.0
    technology: str = ""
    plugged: str = "none"


@dataclass(frozen=True, slots=True)
class MemoryInfo:
    """Memory usage information."""

    total_kb: int = 0
    free_kb: int = 0
    available_kb: int = 0
    buffers_kb: int = 0
    cached_kb: int = 0

    @property
    def used_kb(self) -> int:
        """Calculate used memory in KB."""
        return self.total_kb - self.available_kb

    @property
    def usage_percent(self) -> float:
        """Calculate memory usage as a percentage."""
        if self.total_kb == 0:
            return 0.0
        return (self.used_kb / self.total_kb) * 100.0


@dataclass(frozen=True, slots=True)
class StorageInfo:
    """Storage usage information."""

    filesystem: str = ""
    total_blocks: int = 0
    used_blocks: int = 0
    available_blocks: int = 0
    mount_point: str = ""

    @property
    def usage_percent(self) -> float:
        """Calculate storage usage as a percentage."""
        if self.total_blocks == 0:
            return 0.0
        return (self.used_blocks / self.total_blocks) * 100.0


@dataclass(frozen=True, slots=True)
class SystemSnapshot:
    """A snapshot of the system state."""

    battery: BatteryInfo | None = None
    memory: MemoryInfo | None = None
    storage: list[StorageInfo] = field(default_factory=list)
    uptime: str = ""
    boot_count: int | None = None
    active_services: list[str] = field(default_factory=list)


class SystemDiagnostics:
    """System diagnostics for a connected device.

    Parameters
    ----------
    adb : ADBInterface
        The ADB connection to use for queries.

    """

    def __init__(self, adb: ADBInterface) -> None:
        self._adb = adb

    async def get_battery_info(self) -> BatteryInfo | None:
        """Get battery information from the device.

        Returns
        -------
        BatteryInfo or None
            The battery info, or None if it could not be retrieved.

        """
        response = await self._adb.shell("dumpsys battery")
        if not response:
            return None

        level = 0
        status = "unknown"
        health = "unknown"
        temperature = 0.0
        voltage = 0.0
        technology = ""
        plugged = "none"

        for line in response.splitlines():
            line = line.strip()
            if line.startswith("level:"):
                try:
                    level = int(line.split(":", 1)[1].strip())
                except ValueError:
                    pass
            elif line.startswith("status:"):
                status_code = line.split(":", 1)[1].strip()
                status_map = {"1": "unknown", "2": "charging", "3": "discharging", "4": "not charging", "5": "full"}
                status = status_map.get(status_code, status_code)
            elif line.startswith("health:"):
                health_code = line.split(":", 1)[1].strip()
                health_map = {"1": "unknown", "2": "good", "3": "overheat", "4": "dead", "5": "over voltage"}
                health = health_map.get(health_code, health_code)
            elif line.startswith("temperature:"):
                try:
                    temperature = int(line.split(":", 1)[1].strip()) / 10.0
                except ValueError:
                    pass
            elif line.startswith("voltage:"):
                try:
                    voltage = int(line.split(":", 1)[1].strip()) / 1000.0
                except ValueError:
                    pass
            elif line.startswith("technology:"):
                technology = line.split(":", 1)[1].strip()
            elif line.startswith("plugged:"):
                plugged_code = line.split(":", 1)[1].strip()
                plugged_map = {"0": "none", "1": "AC", "2": "USB", "4": "wireless"}
                plugged = plugged_map.get(plugged_code, plugged_code)

        return BatteryInfo(
            level=level,
            status=status,
            health=health,
            temperature=temperature,
            voltage=voltage,
            technology=technology,
            plugged=plugged,
        )

    async def get_memory_info(self) -> MemoryInfo | None:
        """Get memory usage information.

        Returns
        -------
        MemoryInfo or None
            The memory info, or None if it could not be retrieved.

        """
        response = await self._adb.shell("cat /proc/meminfo")
        if not response:
            return None

        values: dict[str, int] = {}
        for line in response.splitlines():
            parts = line.split()
            if len(parts) >= 2:
                key = parts[0].rstrip(":")
                try:
                    values[key] = int(parts[1])
                except ValueError:
                    pass

        return MemoryInfo(
            total_kb=values.get("MemTotal", 0),
            free_kb=values.get("MemFree", 0),
            available_kb=values.get("MemAvailable", 0),
            buffers_kb=values.get("Buffers", 0),
            cached_kb=values.get("Cached", 0),
        )

    async def get_storage_info(self) -> list[StorageInfo]:
        """Get storage usage information.

        Returns
        -------
        list of StorageInfo
            Storage info for each mounted filesystem.

        """
        response = await self._adb.shell("df")
        if not response:
            return []

        storage_list: list[StorageInfo] = []
        for line in response.splitlines()[1:]:  # Skip header
            parts = line.split()
            if len(parts) >= 6:
                try:
                    storage_list.append(
                        StorageInfo(
                            filesystem=parts[0],
                            total_blocks=int(parts[1]) if parts[1].isdigit() else 0,
                            used_blocks=int(parts[2]) if parts[2].isdigit() else 0,
                            available_blocks=int(parts[3]) if parts[3].isdigit() else 0,
                            mount_point=parts[5],
                        )
                    )
                except (ValueError, IndexError):
                    pass

        return storage_list

    async def get_uptime(self) -> str:
        """Get the device uptime.

        Returns
        -------
        str
            The uptime string.

        """
        response = await self._adb.shell("uptime")
        return response.strip() if response else ""

    async def get_boot_count(self) -> int | None:
        """Get the device boot count.

        Returns
        -------
        int or None
            The number of times the device has booted.

        """
        response = await self._adb.shell("settings get global boot_count")
        if response and response.strip().isdigit():
            return int(response.strip())
        return None

    async def get_active_services(self) -> list[str]:
        """Get a list of active/running services.

        Returns
        -------
        list of str
            Active service names.

        """
        response = await self._adb.shell("dumpsys activity services | grep 'ServiceRecord'")
        if not response:
            return []

        services: list[str] = []
        for line in response.splitlines():
            # Extract service name from ServiceRecord line
            match = re.search(r"ServiceRecord\{[a-f0-9]+ [a-z0-9]+ (.+?)\}", line)
            if match:
                services.append(match.group(1))
        return services

    async def get_system_snapshot(self) -> SystemSnapshot:
        """Get a complete system snapshot.

        Returns
        -------
        SystemSnapshot
            A comprehensive snapshot of the system state.

        """
        battery = await self.get_battery_info()
        memory = await self.get_memory_info()
        storage = await self.get_storage_info()
        uptime = await self.get_uptime()
        boot_count = await self.get_boot_count()
        active_services = await self.get_active_services()

        return SystemSnapshot(
            battery=battery,
            memory=memory,
            storage=storage,
            uptime=uptime,
            boot_count=boot_count,
            active_services=active_services,
        )
