# FileOrganizer

Desktop app that watches folders and automatically sorts files into categories (Documents, Images, Videos, Music, Archives, Code, and more) using a Tkinter GUI and real-time `watchdog` monitoring.

## Requirements

- Python 3.9+
- `pip install -r requirements.txt`

## Run

```bat
START_APP.bat        # Windows (auto-detects Python / venv)
```

```bash
python main.py       # any platform
```

## Build (Windows)

```bash
python build.py --onefile            # portable .exe
python build.py --onefile --installer  # portable .exe + installer
```

Output goes to `dist/`.

## Test

```bash
python -m pytest -q
```

## Features

- Real-time folder monitoring (watchdog)
- 8 built-in file categories with customisable extension rules
- Conflict strategies: rename, skip, overwrite
- 5 languages: English, Russian, Spanish, Chinese, Portuguese
- System tray support (optional — requires `pystray` + `Pillow`)
