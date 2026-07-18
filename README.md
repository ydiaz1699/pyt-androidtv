# pyt-androidtv

A modern Python library to communicate with Android TV and Fire TV devices via ADB.

This is a ground-up rewrite of [python-androidtv](https://github.com/JeffLIrion/python-androidtv) using modern Python tooling and best practices.

## Features

- **Python 3.10+** — takes advantage of modern language features
- **Full type annotations** — PEP 561 compliant with a `py.typed` marker
- **Async and sync interfaces** — first-class `asyncio` support with a synchronous wrapper
- **Extensible state detection** — pluggable architecture for device state parsing
- **Diagnostics module** — built-in tooling for troubleshooting device communication
- **Modern tooling** — managed with `uv`, linted with `ruff`, type-checked with `ty`

## Quick Start

### Installation

```bash
pip install pyt-androidtv
```

### Async usage

```python
import asyncio
from pyt_androidtv import AndroidTVAsync

async def main():
    async with AndroidTVAsync("192.168.1.100") as atv:
        state = await atv.get_state()
        print(state)

asyncio.run(main())
```

### Sync usage

```python
from pyt_androidtv import AndroidTVSync

atv = AndroidTVSync("192.168.1.100")
atv.connect()
state = atv.get_state()
print(state)
atv.close()
```

## Development

```bash
# Install dependencies
uv sync

# Run tests
pytest

# Lint
ruff check .
ruff format --check .

# Type check
ty check src/
```

## Architecture

```
src/pyt_androidtv/
├── __init__.py
├── py.typed
├── adb/              # ADB connection management
├── androidtv/        # Android TV device interface
├── basetv/           # Base TV abstraction layer
├── diagnostics/      # Diagnostics and troubleshooting
└── firetv/           # Fire TV device interface
```

## Comparison with python-androidtv

| Feature | python-androidtv | pyt-androidtv |
|---------|-----------------|---------------|
| Python version | 3.7+ | 3.10+ |
| Type annotations | Partial | Full (PEP 561) |
| Async support | Yes | Yes (first-class) |
| Package manager | setuptools | uv |
| Linter | flake8 + pylint | ruff |
| Type checker | — | ty |
| State detection | Hard-coded | Extensible |
| Diagnostics | — | Built-in module |

## License

MIT

## Credits

- [JeffLIrion/python-androidtv](https://github.com/JeffLIrion/python-androidtv) — the original library this project is based on
- [DouglasFreshHabian/AndroidForensics](https://github.com/DouglasFreshHabian/AndroidForensics) — inspiration for ADB shell interactions and forensic tooling
