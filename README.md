# pyt-androidtv

> Librería moderna de Python para comunicarse con dispositivos Android TV y Fire TV mediante ADB.

Reescritura completa de [python-androidtv](https://github.com/JeffLIrion/python-androidtv) con herramientas modernas, seguridad de tipos y arquitectura extensible.

**[Guía de integración con Home Assistant + Mushroom Cards](docs/HOME_ASSISTANT.md)**

## Características

- **Python moderno** (3.10+) con anotaciones de tipo completas
- **Soporte Sync y Async** mediante código base unificado (patrón wrapper síncrono)
- **Detección de estado extensible** vía patrón registry (sin reglas hardcodeadas por app)
- **Conexión inalámbrica** con descubrimiento automático y emparejamiento (inspirado en [ADBCommandCenter](https://github.com/joaomgcd/ADBCommandCenter))
- **Control de pantalla** — toque, deslizamiento, texto (inspirado en [adb-wireless-toolkit](https://github.com/shivamprasad1001/adb-wireless-toolkit))
- **Módulo de diagnóstico** del dispositivo (inspirado en [AndroidForensics](https://github.com/DouglasFreshHabian/AndroidForensics))
- **Herramientas modernas**: `uv` + `ruff` + `ty` + `pytest` + GitHub Actions
- **Android 11-14+** con enrutamiento de comandos por versión

## Inicio Rápido

### Instalación

```bash
# Usando uv (recomendado)
uv add pyt-androidtv

# Usando pip
pip install pyt-androidtv

# Con soporte async
pip install pyt-androidtv[async]

# Con diagnósticos (salida enriquecida)
pip install pyt-androidtv[diagnostics]

# Todo incluido
pip install pyt-androidtv[all]
```

### Uso Básico (Async)

```python
from pyt_androidtv import AndroidTV

# Conectar al dispositivo
async with AndroidTV("192.168.1.100") as tv:
    # Obtener estado del dispositivo
    estado = await tv.update()
    print(f"Estado: {estado.state}, App: {estado.current_app}")

    # Controlar el dispositivo
    await tv.home()
    await tv.launch_app("com.netflix.ninja")
    await tv.volume_up()
```

### Uso Síncrono

```python
from pyt_androidtv.sync import AndroidTVSync

tv = AndroidTVSync("192.168.1.100")
tv.connect()

estado = tv.update()
print(f"Estado: {estado.state}")

tv.close()
```

### Conexión Inalámbrica

```python
from pyt_androidtv.wireless import WirelessADB

# Descubrir dispositivos en la red local
dispositivos = await WirelessADB.discover()

# Conectar por WiFi (requiere emparejamiento previo)
wireless = WirelessADB("192.168.1.100")
await wireless.connect_tcp(port=5555)

# Emparejar dispositivo nuevo (código del dispositivo)
await wireless.pair(port=37123, code="123456")
```

### Control de Pantalla

```python
async with AndroidTV("192.168.1.100") as tv:
    # Tocar pantalla en coordenadas (x, y)
    await tv.tap(500, 800)

    # Deslizar (swipe)
    await tv.swipe(100, 500, 900, 500)

    # Presión larga
    await tv.long_press(500, 500, duration_ms=1500)

    # Escribir texto
    await tv.input_text("Hola Mundo")

    # Captura de pantalla
    imagen = await tv.screencap()
```

### Diagnósticos del Dispositivo

```python
from pyt_androidtv.diagnostics import DeviceDiagnostics

async with DeviceDiagnostics("192.168.1.100") as diag:
    # Reporte completo del sistema
    reporte = await diag.full_report()
    print(reporte.summary())

    # Información de red/WiFi
    red = await diag.network.get_wifi_info()

    # Análisis de apps instaladas
    apps = await diag.apps.get_apps_report()
```

## Desarrollo

```bash
# Clonar y configurar
git clone https://github.com/ydiaz1699/pyt-androidtv.git
cd pyt-androidtv

# Instalar con uv
uv sync --all-extras

# Ejecutar tests
uv run pytest

# Lint y formato
uv run ruff check .
uv run ruff format .

# Verificación de tipos
uv run ty check
```

## Arquitectura

```
src/pyt_androidtv/
├── __init__.py          # API pública
├── constants.py         # Teclas, estados, comandos (CommandRegistry)
├── exceptions.py        # Excepciones personalizadas
├── models.py            # Dataclasses para estado/config
├── sync.py              # Wrapper síncrono (elimina duplicación)
├── adb/                 # Gestión de conexiones ADB
│   ├── base.py          # Interfaz abstracta ADB
│   ├── tcp.py           # Conexión TCP/IP (adb-shell)
│   └── server.py        # Conexión vía servidor ADB (adbutils)
├── basetv/              # Funcionalidad base del TV
│   ├── base.py          # Lógica core (parsing, control, volumen)
│   └── state.py         # Motor de detección de estado
├── androidtv/           # Específico de Android TV
│   └── androidtv.py     # Clase AndroidTV
├── firetv/              # Específico de Fire TV
│   └── firetv.py        # Clase FireTV
├── wireless/            # Conexión inalámbrica y descubrimiento
│   ├── __init__.py
│   ├── discovery.py     # Descubrimiento mDNS de dispositivos
│   └── pairing.py       # Emparejamiento inalámbrico
└── diagnostics/         # Diagnóstico del dispositivo
    ├── system.py        # Info del sistema (batería, memoria, almacenamiento)
    ├── network.py       # Diagnóstico de red (WiFi, interfaces)
    ├── apps.py          # Análisis de apps
    └── report.py        # Generador de reportes
```

## Comparación con python-androidtv

| Característica | python-androidtv | pyt-androidtv |
|----------------|-----------------|---------------|
| Versión Python | 2.7+ | 3.10+ |
| Anotaciones de tipo | No | Completas (PEP 561) |
| Async/Sync | Archivos duplicados | Código base unificado |
| Detección de estado | Cadenas elif hardcodeadas | Basado en registry/config |
| Conexión WiFi | Manual | Descubrimiento + emparejamiento automático |
| Control de pantalla | No | Tap, swipe, long press, input text |
| CI/CD | Travis CI | GitHub Actions |
| Linting | flake8 + pylint | Ruff |
| Type checking | Ninguno | ty |
| Gestor de paquetes | setup.py | pyproject.toml + uv |
| Diagnósticos | Ninguno | Módulo completo |

## Herramientas Utilizadas

| Herramienta | Reemplaza | Descripción |
|---|---|---|
| [uv](https://docs.astral.sh/uv/) | pip/poetry/venv | Gestor de paquetes 10-100x más rápido |
| [Ruff](https://docs.astral.sh/ruff/) | flake8 + black + isort | Linter/formatter todo-en-uno en Rust |
| [ty](https://docs.astral.sh/ty/) | mypy/pyright | Type checker ultrarrápido de Astral |
| [pytest](https://pytest.org) | unittest | Framework de testing moderno |
| [adbutils](https://github.com/openatx/adbutils) | pure-python-adb | Librería ADB moderna |
| [GitHub Actions](https://github.com/features/actions) | Travis CI | CI/CD gratuito y moderno |

## Licencia

Licencia MIT - Ver [LICENSE](LICENSE) para detalles.

## Créditos

- Proyecto original: [python-androidtv](https://github.com/JeffLIrion/python-androidtv) por Jeff Irion
- Diagnósticos inspirados en: [AndroidForensics](https://github.com/DouglasFreshHabian/AndroidForensics) por Douglas Habian
- Conexión inalámbrica inspirada en: [ADBCommandCenter](https://github.com/joaomgcd/ADBCommandCenter) por João Dias
- Comandos de control inspirados en: [adb-wireless-toolkit](https://github.com/shivamprasad1001/adb-wireless-toolkit) por Shivam Prasad
