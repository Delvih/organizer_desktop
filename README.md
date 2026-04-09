# FileOrganizer

Desktop application for automatic file organization with a Tkinter GUI and
`watchdog`-based folder monitoring.

## Run

On Windows, use:

```bat
START_APP.bat
```

Compatibility launchers:

```bat
RUN.bat
Запуск.bat
```

Direct Python start:

```bash
python main.py
```

## Install

```bash
pip install -r requirements.txt
```

Optional tray support is available when `pystray` and `Pillow` are installed.

## Verify

```bash
python test_components.py
python -m pytest -q
```

## Project Structure

```text
fileorganizer/
|-- main.py
|-- START_APP.bat
|-- app/
|   |-- gui.py
|   |-- config.py
|   |-- organizer.py
|   `-- watcher.py
|-- tests/
|-- assets/
|-- locales.json
`-- requirements.txt
```
