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

## Install Dependencies

```bash
pip install -r requirements.txt
```

## Verify

```bash
python test_components.py
python -m pytest -q
```

## Build Windows Deliverables

Portable executable:

```bash
python build.py --onefile
```

Portable executable plus installer:

```bash
python build.py --onefile --installer
```

Build output is written to `dist/`.

## Project Structure

```text
fileorganizer/
|-- app/
|-- assets/
|-- installer/
|-- tests/
|-- build.py
|-- create_icon.py
|-- locales.json
|-- main.py
|-- START_APP.bat
`-- requirements.txt
```
