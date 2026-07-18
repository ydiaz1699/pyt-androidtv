"""Diagnósticos de aplicaciones para dispositivos Android TV / Fire TV."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..adb.base import ADBInterface


@dataclass(frozen=True, slots=True)
class AppInfo:
    """Información sobre una aplicación instalada."""

    package_name: str = ""
    version_name: str = ""
    version_code: int = 0
    install_time: str = ""
    update_time: str = ""
    is_system: bool = False


@dataclass(frozen=True, slots=True)
class RunningProcess:
    """Información sobre un proceso en ejecución."""

    pid: int = 0
    user: str = ""
    vsz_kb: int = 0
    rss_kb: int = 0
    name: str = ""
    state: str = ""


@dataclass(frozen=True, slots=True)
class AppsReport:
    """Informe completo de diagnósticos de aplicaciones."""

    all_packages: list[str] = field(default_factory=list)
    third_party_packages: list[str] = field(default_factory=list)
    running_processes: list[RunningProcess] = field(default_factory=list)
    top_memory_apps: list[tuple[str, int]] = field(default_factory=list)


class AppDiagnostics:
    """Diagnósticos de aplicaciones para un dispositivo conectado.

    Parámetros
    ----------
    adb : ADBInterface
        La conexión ADB a usar para consultas.

    """

    def __init__(self, adb: ADBInterface) -> None:
        self._adb = adb

    async def get_all_packages(self) -> list[str]:
        """Obtener todos los paquetes instalados.

        Retorna
        -------
        list of str
            Todos los nombres de paquetes.

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
        """Obtener paquetes de terceros (instalados por el usuario).

        Retorna
        -------
        list of str
            Nombres de paquetes de terceros.

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
        """Obtener todos los procesos en ejecución.

        Retorna
        -------
        list of RunningProcess
            Procesos en ejecución con detalles.

        """
        response = await self._adb.shell("ps -A -o PID,USER,VSZ,RSS,S,NAME")
        if not response:
            return []

        processes: list[RunningProcess] = []
        for line in response.splitlines()[1:]:  # Omitir encabezado
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
        """Obtener las aplicaciones que más memoria consumen.

        Parámetros
        ----------
        limit : int
            Número máximo de aplicaciones a retornar.

        Retorna
        -------
        list of tuple[str, int]
            Tuplas de (nombre_paquete, memoria_kb) ordenadas por uso de memoria descendente.

        """
        response = await self._adb.shell("dumpsys meminfo --sort-by-uss | head -50")
        if not response:
            return []

        apps: list[tuple[str, int]] = []
        for line in response.splitlines():
            # Coincidir líneas como: "123,456K: com.example.app (pid 1234)"
            match = re.match(r"\s*([\d,]+)K:\s+(\S+)", line)
            if match:
                try:
                    memory_kb = int(match.group(1).replace(",", ""))
                    package = match.group(2)
                    apps.append((package, memory_kb))
                except ValueError:
                    pass

        # Ordenar por memoria descendente y limitar
        apps.sort(key=lambda x: x[1], reverse=True)
        return apps[:limit]

    async def get_apps_report(self) -> AppsReport:
        """Obtener un informe completo de diagnósticos de aplicaciones.

        Retorna
        -------
        AppsReport
            Un informe completo de aplicaciones instaladas y en ejecución.

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
