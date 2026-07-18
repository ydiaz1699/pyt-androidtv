"""Application diagnostics for Android TV / Fire TV devices."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..adb.base import ADBInterface


@dataclass(frozen=True, slots=True)
class AppInfo:
    """Information about an installed application."""

    package_name: str = ""
    version_name: str = ""
    version_code: int = 0
    install_time: str = ""
    update_time: str = ""
    is_system: bool = False


@dataclass(frozen=True, slots=True)
class RunningProcess:
    """Information about a running process."""

    pid: int = 0
    user: str = ""
    vsz_kb: int = 0
    rss_kb: int = 0
    name: str = ""
    state: str = ""


@dataclass(frozen=True, slots=True)
class AppsReport:
    """Complete applications diagnostics report."""

    all_packages: list[str] = field(default_factory=list)
    third_party_packages: list[str] = field(default_factory=list)
    running_processes: list[RunningProcess] = field(default_factory=list)
    top_memory_apps: list[tuple[str, int]] = field(default_factory=list)


class AppDiagnostics:
    """Application diagnostics for a connected device.

    Parameters
    ----------
    adb : ADBInterface
        The ADB connection to use for queries.

    """

    def __init__(self, adb: ADBInterface) -> None:
        self._adb = adb

    async def get_all_packages(self) -> list[str]:
        """Get all installed packages.

        Returns
        -------
        list of str
            All package names.

        """
        response = await self._adb.shell("pm list packages")
        if not response:
            return []

        return [
            line.strip().removeprefix("package:")
            for line in response.splitlines()
            if line.strip()
        ]

    async def get_third_party_packages(self) -> list[str]:
        """Get third-party (user-installed) packages.

        Returns
        -------
        list of str
            Third-party package names.

        """
        response = await self._adb.shell("pm list packages -3")
        if not response:
            return []

        return [
            line.strip().removeprefix("package:")
            for line in response.splitlines()
            if line.strip()
        ]

    async def get_running_processes(self) -> list[RunningProcess]:
        """Get all running processes.

        Returns
        -------
        list of RunningProcess
            Running processes with details.

        """
        response = await self._adb.shell("ps -A -o PID,USER,VSZ,RSS,S,NAME")
        if not response:
            return []

        processes: list[RunningProcess] = []
        for line in response.splitlines()[1:]:  # Skip header
            parts = line.split(None, 5)
            if len(parts) >= 6:
                try:
                    processes.append(
                        RunningProcess(
                            pid=int(parts[0]),
                            user=parts[1],
                            vsz_kb=int(parts[2]) if parts[2].isdigit() else 0,
                            rss_kb=int(parts[3]) if parts[3].isdigit() else 0,
                            state=parts[4],
                            name=parts[5].strip(),
                        )
                    )
                except (ValueError, IndexError):
                    pass
            elif len(parts) >= 2:
                try:
                    processes.append(
                        RunningProcess(
                            pid=int(parts[0]),
                            user=parts[1] if len(parts) > 1 else "",
                            name=parts[-1].strip(),
                        )
                    )
                except ValueError:
                    pass

        return processes

    async def get_top_memory_apps(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get the top memory-consuming apps.

        Parameters
        ----------
        limit : int
            Maximum number of apps to return.

        Returns
        -------
        list of tuple[str, int]
            Tuples of (package_name, memory_kb) sorted by memory usage descending.

        """
        response = await self._adb.shell("dumpsys meminfo --sort-by-uss | head -50")
        if not response:
            return []

        apps: list[tuple[str, int]] = []
        for line in response.splitlines():
            # Match lines like: "123,456K: com.example.app (pid 1234)"
            match = re.match(r"\s*([\d,]+)K:\s+(\S+)", line)
            if match:
                try:
                    memory_kb = int(match.group(1).replace(",", ""))
                    package = match.group(2)
                    apps.append((package, memory_kb))
                except ValueError:
                    pass

        # Sort by memory descending and limit
        apps.sort(key=lambda x: x[1], reverse=True)
        return apps[:limit]

    async def get_apps_report(self) -> AppsReport:
        """Get a complete applications diagnostics report.

        Returns
        -------
        AppsReport
            A comprehensive report of installed and running applications.

        """
        all_packages = await self.get_all_packages()
        third_party = await self.get_third_party_packages()
        running = await self.get_running_processes()
        top_memory = await self.get_top_memory_apps()

        return AppsReport(
            all_packages=all_packages,
            third_party_packages=third_party,
            running_processes=running,
            top_memory_apps=top_memory,
        )
