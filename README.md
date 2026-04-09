# ⚡ FileOrganizer

**Automated cross-platform file organization with a real-time watcher and clean GUI.**

FileOrganizer monitors your chosen folders and automatically sorts every new file into subfolders (Documents, Images, Videos, Music, Archives, etc.) based on fully customizable rules.

---

## ✨ Features

| Feature | Details |
|---|---|
| Real-time monitoring | Uses `watchdog` for near-instant file detection |
| Rule-based sorting | Extension → Category mapping, fully editable |
| Cross-platform | Windows, macOS, Linux (Python 3.9+) |
| GUI | Clean dark-mode Tkinter interface |
| System tray | Optional background mode (requires `pystray`) |
| Conflict handling | Auto-rename, skip, or overwrite — your choice |
| Logging | Rotating log file + live in-app log viewer |

---

## 🚀 Quick Start

### 1. Install Python 3.9+

- **Windows**: https://www.python.org/downloads/
- **macOS**: `brew install python` or from python.org
- **Linux**: `sudo apt install python3 python3-pip` (or your distro's equivalent)

### 2. Install dependencies

```bash
# Clone or download the project
cd fileorganizer

# Install required library
pip install -r requirements.txt

# Optional: system tray support
pip install pystray Pillow
```

### 3. Run the app

```bash
python main.py
```

---

## 🖥️ User Guide

### Dashboard

The home screen shows:
- **File statistics** — total processed, moved, skipped, errors
- **Recent activity** — a live feed of file operations
- **▶ Start Watching** — starts real-time monitoring
- **⟳ Organize Now** — immediately sorts all current files in watched folders

### Folders Tab

**Watched Folders** — Add any number of directories to monitor. A green dot means the folder exists; red means it was deleted or moved.

**Destination Root Folder** — All organized subfolders will be created here. Example:
```
Destination: ~/Organized/
  └── Documents/
  └── Images/
  └── Videos/
  ...
```
Leave empty to sort files *in place* (subfolders created inside each watched folder).

### Rules Tab

Each category rule specifies:
- **Category name** (e.g., "Documents")
- **Extensions** (e.g., `.pdf`, `.docx`, `.txt`)
- **Icon** (emoji displayed in the UI)
- **Color** (hex color for the card accent)

You can:
- Enable / disable individual categories
- Add new categories
- Edit extensions for existing categories
- Delete categories
- Reset all rules to defaults

**Conflict Strategy** (choose one):
| Option | Behavior |
|---|---|
| Auto-rename | `file.pdf` → `file (1).pdf` if already exists |
| Skip | Leave the file in place, log it |
| Overwrite | Replace the existing file |

### Activity Log Tab

- Displays the full application log with color-coded severity
- Click **Open Log File** to view the log in your system editor
- Log is rotated at 5 MB (keeps last 3 backups)

### Settings Tab

| Setting | Description |
|---|---|
| Organize existing files on start | Sort pre-existing files when watcher activates |
| Minimize to system tray | Keep running in background on window close |
| Unknown Files Folder | Name of folder for unrecognized extensions (default: `Misc`) |
| Log level | DEBUG / INFO / WARNING / ERROR |

---

## 📦 Default Extension Mapping

| Category | Extensions |
|---|---|
| Documents | .pdf .doc .docx .txt .odt .rtf .md .csv .xls .xlsx .ppt .pptx .epub .mobi … |
| Images | .jpg .jpeg .png .gif .bmp .svg .webp .tiff .heic .raw .psd .ai … |
| Videos | .mp4 .mkv .avi .mov .wmv .flv .webm .m4v .mpeg .3gp … |
| Music | .mp3 .flac .wav .aac .ogg .wma .m4a .aiff .opus .mid … |
| Archives | .zip .tar .gz .7z .rar .iso .dmg .deb .rpm … |
| Executables | .exe .msi .app .apk .bat .sh .cmd .jar … |
| Code | .py .js .ts .html .css .java .cpp .c .go .rs .rb .php .swift … |
| Fonts | .ttf .otf .woff .woff2 |

---

## 🏗️ Build Standalone Executable

Requires PyInstaller:

```bash
pip install pyinstaller

# Build installer directory (recommended)
python build.py

# Or a single portable .exe / binary
python build.py --onefile
```

Output is in `dist/FileOrganizer/` (or `dist/FileOrganizer` binary).

---

## 🗂️ Project Structure

```
fileorganizer/
├── main.py              # Entry point
├── requirements.txt     # Dependencies
├── setup.py             # Package config
├── build.py             # PyInstaller helper
├── assets/              # Icons and images
│   └── icon.png
└── app/
    ├── __init__.py
    ├── config.py        # Configuration management
    ├── organizer.py     # File move + conflict logic
    ├── watcher.py       # Real-time watchdog monitor
    ├── logger_setup.py  # Logging configuration
    └── gui.py           # Full Tkinter GUI
```

---

## 🔧 Configuration File Location

Config is stored as JSON at:

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\FileOrganizer\config.json` |
| macOS | `~/Library/Application Support/FileOrganizer/config.json` |
| Linux | `~/.config/FileOrganizer/config.json` |

You can edit it manually if needed — it's human-readable JSON.

---

## 📋 Log File Location

| Platform | Path |
|---|---|
| Windows | `%APPDATA%\FileOrganizer\fileorganizer.log` |
| macOS | `~/Library/Logs/FileOrganizer/fileorganizer.log` |
| Linux | `~/.local/share/FileOrganizer/fileorganizer.log` |

---

## 🐛 Troubleshooting

**"watchdog not installed"** — Run `pip install watchdog` and restart.

**Files not moving** — Check that:
1. The destination folder is writable
2. The file extension is in an enabled rule
3. The watcher is running (green dot in sidebar)

**Tray icon missing** — Install optional deps: `pip install pystray Pillow`

**App won't start on Linux** — Install Tkinter: `sudo apt install python3-tk`

---

## 📄 License

MIT License — free to use, modify, and distribute.
