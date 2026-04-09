"""
gui.py - Full Tkinter GUI for FileOrganizer.
Provides dashboard, folder management, rule editor, log viewer, and tray support.
"""

import os
import sys
import logging
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, font as tkfont
from pathlib import Path
from typing import Optional, List
import time
import json

from .config import Config, DEFAULT_RULES
from .organizer import FileOrganizer, OrganizerResult
from .watcher import FolderWatcher
from .logger_setup import setup_logging, get_log_buffer, get_log_file_path
from .runtime import resource_path

logger = logging.getLogger("FileOrganizer")

# ── Palette ────────────────────────────────────────────────────────────────────
BG       = "#2b2b2b"
SURFACE  = "#404040"
SURFACE2 = "#505050"
BORDER   = "#606060"
ACCENT   = "#5B8AF5"
ACCENT2  = "#3D6FF0"
SUCCESS  = "#3DDC84"
WARNING  = "#F5A623"
DANGER   = "#F05C5C"
TEXT     = "#E8EAF0"
TEXT_DIM = "#B0B0B0"
WHITE    = "#FFFFFF"

# ── Fonts (resolved at runtime) ────────────────────────────────────────────────
def _pick(candidates, fallback):
    available = set(tkfont.families())
    for c in candidates:
        if c in available:
            return c
    return fallback

FONT_FAMILY   = None  # resolved in App.__init__
MONO_FAMILY   = None


class StyledButton(tk.Button):
    def __init__(self, parent, text, command=None, style="primary", **kw):
        colors = {
            "primary":   (ACCENT,   WHITE,   ACCENT2),
            "success":   (SUCCESS,  "#0F1117", "#2CB870"),
            "danger":    (DANGER,   WHITE,   "#C04444"),
            "ghost":     (SURFACE2, TEXT_DIM, BORDER),
            "secondary": (SURFACE2, TEXT,    BORDER),
        }
        bg, fg, active = colors.get(style, colors["primary"])
        # Allow callers to override padding via kwargs without causing
        # multiple-values-for-keyword errors. Default padding is 14x7.
        kw.setdefault("padx", 14)
        kw.setdefault("pady", 7)
        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg, fg=fg,
            activebackground=active,
            activeforeground=fg,
            relief="flat",
            bd=0,
            cursor="hand2",
            **kw
        )


class Badge(tk.Label):
    def __init__(self, parent, text, color=ACCENT, **kw):
        super().__init__(
            parent, text=text,
            bg=color, fg=WHITE,
            padx=8, pady=2,
            relief="flat",
            **kw
        )


class Separator(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BORDER, height=1, **kw)


class ScrollableFrame(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self.canvas = tk.Canvas(self, bg=kw.get("bg", SURFACE), highlightthickness=0)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=kw.get("bg", SURFACE))
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_frame_configure(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, e):
        self.canvas.itemconfig(self._window, width=e.width)

    def _on_mousewheel(self, e):
        if sys.platform == "darwin":
            self.canvas.yview_scroll(-1 * e.delta, "units")
        else:
            self.canvas.yview_scroll(-1 * (e.delta // 120), "units")


# ── Sidebar navigation item ────────────────────────────────────────────────────
class NavItem(tk.Frame):
    def __init__(self, parent, icon, label, command, **kw):
        super().__init__(parent, bg=SURFACE, cursor="hand2", **kw)
        self._cmd = command
        self._active = False

        self._indicator = tk.Frame(self, bg=SURFACE, width=3)
        self._indicator.pack(side="left", fill="y")

        inner = tk.Frame(self, bg=SURFACE, padx=12, pady=10)
        inner.pack(side="left", fill="both", expand=True)

        tk.Label(inner, text=icon, bg=SURFACE, fg=TEXT, font=(MONO_FAMILY, 14)).pack(side="left", padx=(0, 8))
        self._lbl = tk.Label(inner, text=label, bg=SURFACE, fg=TEXT_DIM,
                              font=(FONT_FAMILY, 11))
        self._lbl.pack(side="left")

        for w in [self, inner, self._lbl]:
            w.bind("<Button-1>", self._click)
            w.bind("<Enter>", self._hover_on)
            w.bind("<Leave>", self._hover_off)

    def set_active(self, active: bool):
        self._active = active
        if active:
            self._indicator.config(bg=ACCENT)
            self._lbl.config(fg=WHITE, font=(FONT_FAMILY, 11, "bold"))
            self.config(bg=SURFACE2)
            for w in self.winfo_children():
                w.config(bg=SURFACE2)
        else:
            self._indicator.config(bg=SURFACE)
            self._lbl.config(fg=TEXT_DIM, font=(FONT_FAMILY, 11))
            self.config(bg=SURFACE)
            for w in self.winfo_children():
                try:
                    w.config(bg=SURFACE)
                except Exception:
                    pass

    def _click(self, e=None):
        self._cmd()

    def _hover_on(self, e=None):
        if not self._active:
            self.config(bg=SURFACE2)

    def _hover_off(self, e=None):
        if not self._active:
            self.config(bg=SURFACE)


# ══════════════════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════
class FileOrganizerApp:
    def __init__(self):
        global FONT_FAMILY, MONO_FAMILY

        self.config = Config()
        setup_logging(self.config.get("log_level", "INFO"))

        self.root = tk.Tk()
        self.root.withdraw()

        # Load translations
        locales_path = resource_path("locales.json")
        with open(locales_path, 'r', encoding='utf-8') as f:
            self.translations = json.load(f)
        self.current_lang = self.config.get("language", "en")

        # Set up ttk style
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('.', background='#2b2b2b', foreground='#ffffff', font=('Segoe UI', 10))
        self.style.configure('TButton', relief='flat', borderwidth=0, padding=6)
        self.style.configure('TLabel', background='#2b2b2b', foreground='#ffffff')
        self.style.configure('TEntry', fieldbackground='#404040', borderwidth=1)
        self.style.configure('TCombobox', fieldbackground='#404040', borderwidth=1)

        # Resolve fonts after Tk is initialized
        FONT_FAMILY = _pick(["Segoe UI", "Helvetica"], "Helvetica")
        MONO_FAMILY = _pick(["Consolas", "Courier"], "Courier")

        self.root.title(self._t("title"))
        self.root.geometry("1100x700")
        self.root.minsize(900, 580)
        self.root.configure(bg='#2b2b2b')

        # Try to set window icon
        try:
            icon_path = resource_path("assets", "icon.ico")
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
            else:
                # Fallback to PNG if ICO not found
                png_path = resource_path("assets", "icon.png")
                if png_path.exists():
                    img = tk.PhotoImage(file=str(png_path))
                    self.root.iconphoto(True, img)
        except Exception:
            pass

        self.watcher = FolderWatcher(self.config, callback=self._handle_result)
        self._stats = {"moved": 0, "skipped": 0, "errors": 0, "total": 0}
        self._log_entries: List[tuple] = []
        self._current_page = None
        self._pages = {}
        self._nav_items = {}

        # Scan interval
        self.scan_interval = self.config.get("scan_interval", 30)
        self.scan_thread = None
        self.scan_running = False
        self.next_scan_time = time.time() + self.scan_interval

        self._build_ui()
        self._navigate("dashboard")
        self.root.deiconify()

        # Auto-start watcher if folders are configured
        if self.config.watched_folders:
            self._toggle_watcher(force_start=True)

        # Poll log buffer every second
        self._poll_logs()

        # Start the periodic scan thread immediately so first launch
        # works even before any folders are configured.
        self._start_periodic_scan()

    def _t(self, key):
        """Translate key to current language."""
        return self.translations.get(self.current_lang, {}).get(key, key)

    def _start_periodic_scan(self):
        if self.scan_thread and self.scan_thread.is_alive():
            return
        self.scan_running = True
        self.next_scan_time = time.time() + self.scan_interval
        self.scan_thread = threading.Thread(target=self._periodic_scan_loop, daemon=True)
        self.scan_thread.start()

    def _periodic_scan_loop(self):
        while self.scan_running:
            now = time.time()
            if now >= self.next_scan_time:
                self._perform_scan()
                self.next_scan_time = now + self.scan_interval
            time.sleep(1)

    def _perform_scan(self):
        if not self.config.watched_folders:
            return
        organizer = FileOrganizer(self.config)
        for folder in self.config.watched_folders:
            try:
                for file_path in Path(folder).rglob('*'):
                    if file_path.is_file():
                        result = organizer.organize_file(str(file_path))
                        self._on_file_organized(result)
            except Exception as e:
                logger.error(f"Scan error: {e}")

    def _update_scan_interval(self, new_interval):
        try:
            interval = int(new_interval)
            if interval > 0:
                self.scan_interval = interval
                self.config.set("scan_interval", interval)
                self.config.save()
                self.next_scan_time = time.time() + interval
        except ValueError:
            pass

    # ── Build skeleton ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=SURFACE, width=200)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Logo area
        logo_frame = tk.Frame(self.sidebar, bg=SURFACE, pady=20)
        logo_frame.pack(fill="x")
        tk.Label(logo_frame, text="⚡", bg=SURFACE, fg=ACCENT,
                 font=(FONT_FAMILY, 22)).pack()
        tk.Label(logo_frame, text="FileOrganizer", bg=SURFACE, fg=WHITE,
                 font=(FONT_FAMILY, 13, "bold")).pack()
        tk.Label(logo_frame, text="v1.0", bg=SURFACE, fg=TEXT_DIM,
                 font=(FONT_FAMILY, 9)).pack()

        Separator(self.sidebar).pack(fill="x", padx=16, pady=4)

        # Nav items
        nav_config = [
            ("dashboard",  "📊", self._t("dashboard")),
            ("folders",    "📁", self._t("folders")),
            ("rules",      "🗂️", self._t("rules")),
            ("log",        "📋", self._t("log")),
            ("settings",   "⚙️", self._t("settings")),
        ]
        for page, icon, label in nav_config:
            item = NavItem(self.sidebar, icon, label,
                           command=lambda p=page: self._navigate(p))
            item.pack(fill="x")
            self._nav_items[page] = item

        # Status pill at sidebar bottom
        Separator(self.sidebar).pack(fill="x", padx=16, pady=8, side="bottom")
        self._status_frame = tk.Frame(self.sidebar, bg=SURFACE, pady=12)
        self._status_frame.pack(side="bottom", fill="x")
        self._status_dot = tk.Label(self._status_frame, text="●", bg=SURFACE,
                                     fg=DANGER, font=(FONT_FAMILY, 12))
        self._status_dot.pack()
        self._status_lbl = tk.Label(self._status_frame, text="Not Watching",
                                     bg=SURFACE, fg=TEXT_DIM, font=(FONT_FAMILY, 9))
        self._status_lbl.pack()

        # Main content area
        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)

        # Build all pages (hidden initially)
        self._pages["dashboard"] = self._build_dashboard()
        self._pages["folders"]   = self._build_folders()
        self._pages["rules"]     = self._build_rules()
        self._pages["log"]       = self._build_log()
        self._pages["settings"]  = self._build_settings()

    def _navigate(self, page: str):
        if self._current_page:
            self._pages[self._current_page].pack_forget()
            self._nav_items[self._current_page].set_active(False)
        self._pages[page].pack(fill="both", expand=True)
        self._nav_items[page].set_active(True)
        self._current_page = page

        # Refresh pages that need live data
        if page == "dashboard":
            self._refresh_dashboard()
        elif page == "log":
            self._refresh_log()

    # ── Page: Dashboard ─────────────────────────────────────────────────────────
    def _build_dashboard(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=BG)

        # Header
        hdr = tk.Frame(page, bg=BG, padx=28, pady=22)
        hdr.pack(fill="x")
        tk.Label(hdr, text=self._t("dashboard"), bg=BG, fg=WHITE,
                 font=(FONT_FAMILY, 22, "bold")).pack(side="left")

        self._watch_btn = StyledButton(
            hdr, self._t("start_watching"), command=self._toggle_watcher, style="success"
        )
        self._watch_btn.pack(side="right", padx=4)

        StyledButton(hdr, self._t("organize_now"), command=self._organize_now,
                     style="primary").pack(side="right", padx=4)

        Separator(page).pack(fill="x", padx=28)

        # Stat cards row
        cards_row = tk.Frame(page, bg=BG, padx=28, pady=20)
        cards_row.pack(fill="x")

        self._stat_vars = {}
        stat_defs = [
            ("total",   "Files Processed", "📂", ACCENT),
            ("moved",   "Moved",           "✅", SUCCESS),
            ("skipped", "Skipped",         "⏭️",  WARNING),
            ("errors",  "Errors",          "❌", DANGER),
        ]
        for key, label, icon, color in stat_defs:
            var = tk.StringVar(value="0")
            self._stat_vars[key] = var
            card = tk.Frame(cards_row, bg=SURFACE, padx=20, pady=16, relief="flat")
            card.pack(side="left", fill="both", expand=True, padx=(0, 12))
            tk.Label(card, text=icon, bg=SURFACE, fg=color,
                     font=(FONT_FAMILY, 18)).pack(anchor="w")
            tk.Label(card, textvariable=var, bg=SURFACE, fg=color,
                     font=(FONT_FAMILY, 26, "bold")).pack(anchor="w")
            tk.Label(card, text=label, bg=SURFACE, fg=TEXT_DIM,
                     font=(FONT_FAMILY, 10)).pack(anchor="w")

        # Recent activity section
        activity_frame = tk.Frame(page, bg=BG, padx=28)
        activity_frame.pack(fill="both", expand=True, pady=(0, 20))

        tk.Label(activity_frame, text="Recent Activity", bg=BG, fg=TEXT,
                 font=(FONT_FAMILY, 14, "bold")).pack(anchor="w", pady=(0, 10))

        list_bg = tk.Frame(activity_frame, bg=SURFACE, pady=8)
        list_bg.pack(fill="both", expand=True)

        self._activity_text = tk.Text(
            list_bg, bg=SURFACE, fg=TEXT_DIM,
            font=(MONO_FAMILY, 10),
            relief="flat", bd=0,
            state="disabled", wrap="word",
            selectbackground=ACCENT,
        )
        self._activity_text.pack(fill="both", expand=True, padx=12, pady=8)
        self._activity_text.tag_config("moved",   foreground=SUCCESS)
        self._activity_text.tag_config("skipped", foreground=WARNING)
        self._activity_text.tag_config("error",   foreground=DANGER)
        self._activity_text.tag_config("renamed", foreground=ACCENT)
        self._activity_text.tag_config("dim",     foreground=TEXT_DIM)

        # Watcher status bar
        status_bar = tk.Frame(page, bg=SURFACE2, padx=28, pady=8)
        status_bar.pack(fill="x")
        self._status_bar_lbl = tk.Label(
            status_bar, text="Watcher: Stopped", bg=SURFACE2, fg=TEXT_DIM,
            font=(FONT_FAMILY, 9)
        )
        self._status_bar_lbl.pack(side="left")

        log_path_lbl = tk.Label(
            status_bar, text=f"Log: {get_log_file_path()}", bg=SURFACE2, fg=TEXT_DIM,
            font=(MONO_FAMILY, 8), cursor="hand2"
        )
        log_path_lbl.pack(side="right")
        log_path_lbl.bind("<Button-1>", lambda e: self._open_log_file())

        return page

    def _refresh_dashboard(self):
        for key, var in self._stat_vars.items():
            var.set(str(self._stats.get(key, 0)))

    def _add_activity(self, result: OrganizerResult):
        self._activity_text.config(state="normal")
        ts = result.timestamp.strftime("%H:%M:%S")
        name = Path(result.src).name
        tag = result.action if result.action in ("moved", "skipped", "error", "renamed") else "dim"
        icon = {"moved": "✅", "skipped": "⏭️", "error": "❌", "renamed": "🔄"}.get(result.action, "•")
        line = f"[{ts}] {icon} {name}  →  {Path(result.dst).parent.name if result.dst else '?'}\n"
        self._activity_text.insert("1.0", line, tag)
        # Keep last 100 lines
        lines = int(self._activity_text.index("end-1c").split(".")[0])
        if lines > 100:
            self._activity_text.delete(f"{101}.0", "end")
        self._activity_text.config(state="disabled")

    # ── Page: Folders ───────────────────────────────────────────────────────────
    def _build_folders(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=BG)

        hdr = tk.Frame(page, bg=BG, padx=28, pady=22)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Watched Folders", bg=BG, fg=WHITE,
                 font=(FONT_FAMILY, 22, "bold")).pack(side="left")
        StyledButton(hdr, "+ Add Folder", command=self._add_watch_folder,
                     style="primary").pack(side="right")

        Separator(page).pack(fill="x", padx=28)

        # Destination folder selector
        dest_frame = tk.Frame(page, bg=BG, padx=28, pady=16)
        dest_frame.pack(fill="x")
        tk.Label(dest_frame, text="Destination Root Folder", bg=BG, fg=TEXT,
                 font=(FONT_FAMILY, 12, "bold")).pack(anchor="w")
        tk.Label(dest_frame, text="Organized subfolders will be created here. Leave empty to sort in-place.",
                 bg=BG, fg=TEXT_DIM, font=(FONT_FAMILY, 9)).pack(anchor="w", pady=(2, 8))

        dest_row = tk.Frame(dest_frame, bg=BG)
        dest_row.pack(fill="x")
        self._dest_var = tk.StringVar(value=self.config.destination_folder)
        dest_entry = tk.Entry(dest_row, textvariable=self._dest_var,
                              bg=SURFACE2, fg=TEXT, relief="flat", bd=0,
                              insertbackground=WHITE, font=(FONT_FAMILY, 11))
        dest_entry.pack(side="left", fill="x", expand=True, ipady=8, padx=(0, 8))
        StyledButton(dest_row, "Browse", command=self._browse_dest, style="secondary").pack(side="left")
        StyledButton(dest_row, "Save", command=self._save_dest, style="primary").pack(side="left", padx=(6, 0))

        Separator(page).pack(fill="x", padx=28, pady=4)

        # Watched folders list
        lbl_frame = tk.Frame(page, bg=BG, padx=28, pady=8)
        lbl_frame.pack(fill="x")
        tk.Label(lbl_frame, text="Monitored Directories", bg=BG, fg=TEXT,
                 font=(FONT_FAMILY, 12, "bold")).pack(anchor="w")

        self._folders_container = tk.Frame(page, bg=BG, padx=28)
        self._folders_container.pack(fill="both", expand=True)
        self._refresh_folder_list()

        return page

    def _refresh_folder_list(self):
        for w in self._folders_container.winfo_children():
            w.destroy()

        folders = self.config.watched_folders
        if not folders:
            tk.Label(self._folders_container,
                     text="No folders added yet. Click '+ Add Folder' to get started.",
                     bg=BG, fg=TEXT_DIM, font=(FONT_FAMILY, 11)).pack(pady=40)
            return

        for i, folder in enumerate(folders):
            row = tk.Frame(self._folders_container, bg=SURFACE, pady=12, padx=16)
            row.pack(fill="x", pady=(0, 8))

            exists = Path(folder).is_dir()
            dot_color = SUCCESS if exists else DANGER
            tk.Label(row, text="●", bg=SURFACE, fg=dot_color,
                     font=(FONT_FAMILY, 11)).pack(side="left", padx=(0, 10))
            tk.Label(row, text=folder, bg=SURFACE, fg=TEXT,
                     font=(FONT_FAMILY, 11)).pack(side="left", fill="x", expand=True)
            StyledButton(row, "✕", command=lambda f=folder: self._remove_folder(f),
                         style="ghost", padx=8, pady=4).pack(side="right")

    def _add_watch_folder(self):
        folder = filedialog.askdirectory(title="Select folder to watch")
        if not folder:
            return
        folders = self.config.watched_folders
        if folder not in folders:
            folders.append(folder)
            self.config.watched_folders = folders
            if self.watcher.running:
                self.watcher.restart()
        self._refresh_folder_list()

    def _remove_folder(self, folder: str):
        folders = self.config.watched_folders
        if folder in folders:
            folders.remove(folder)
            self.config.watched_folders = folders
            if self.watcher.running:
                self.watcher.restart()
        self._refresh_folder_list()

    def _browse_dest(self):
        folder = filedialog.askdirectory(title="Select destination root folder")
        if folder:
            self._dest_var.set(folder)

    def _save_dest(self):
        self.config.destination_folder = self._dest_var.get().strip()
        messagebox.showinfo("Saved", "Destination folder saved.")

    # ── Page: Rules ─────────────────────────────────────────────────────────────
    def _build_rules(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=BG)

        hdr = tk.Frame(page, bg=BG, padx=28, pady=22)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Organization Rules", bg=BG, fg=WHITE,
                 font=(FONT_FAMILY, 22, "bold")).pack(side="left")
        StyledButton(hdr, "+ New Category", command=self._add_category,
                     style="primary").pack(side="right")
        StyledButton(hdr, "↺ Reset Defaults", command=self._reset_rules,
                     style="ghost").pack(side="right", padx=8)

        Separator(page).pack(fill="x", padx=28)

        # Conflict strategy
        cs_frame = tk.Frame(page, bg=BG, padx=28, pady=12)
        cs_frame.pack(fill="x")
        tk.Label(cs_frame, text="Conflict Strategy:", bg=BG, fg=TEXT,
                 font=(FONT_FAMILY, 11)).pack(side="left", padx=(0, 12))
        self._conflict_var = tk.StringVar(value=self.config.conflict_strategy)
        for val, label in [("rename", "Auto-rename"), ("skip", "Skip"), ("overwrite", "Overwrite")]:
            tk.Radiobutton(
                cs_frame, text=label, variable=self._conflict_var, value=val,
                bg=BG, fg=TEXT, selectcolor=SURFACE2, activebackground=BG,
                font=(FONT_FAMILY, 10), command=self._save_conflict_strategy
            ).pack(side="left", padx=8)

        Separator(page).pack(fill="x", padx=28, pady=4)

        # Scrollable rules list
        scroll = ScrollableFrame(page, bg=BG)
        scroll.pack(fill="both", expand=True, padx=28, pady=8)
        self._rules_inner = scroll.inner
        self._render_rules()

        return page

    def _render_rules(self):
        for w in self._rules_inner.winfo_children():
            w.destroy()

        rules = self.config.get_rules()
        for cat_name, rule in rules.items():
            self._render_rule_card(cat_name, rule)

    def _render_rule_card(self, cat_name: str, rule: dict):
        color = rule.get("color", ACCENT)
        icon  = rule.get("icon", "📁")
        enabled = rule.get("enabled", True)
        exts  = rule.get("extensions", [])

        card = tk.Frame(self._rules_inner, bg=SURFACE, pady=12, padx=16)
        card.pack(fill="x", pady=(0, 8))

        # Header row
        row = tk.Frame(card, bg=SURFACE)
        row.pack(fill="x")

        # Color swatch + icon + name
        tk.Frame(row, bg=color, width=4).pack(side="left", fill="y", padx=(0, 10))
        tk.Label(row, text=icon, bg=SURFACE, font=(FONT_FAMILY, 14)).pack(side="left", padx=(0, 6))
        tk.Label(row, text=cat_name, bg=SURFACE, fg=WHITE,
                 font=(FONT_FAMILY, 12, "bold")).pack(side="left")

        # Enable toggle
        enabled_var = tk.BooleanVar(value=enabled)
        chk = tk.Checkbutton(
            row, variable=enabled_var, text="Enabled",
            bg=SURFACE, fg=TEXT_DIM, selectcolor=SURFACE2,
            activebackground=SURFACE, font=(FONT_FAMILY, 9),
            command=lambda c=cat_name, v=enabled_var: self._toggle_rule(c, v.get())
        )
        chk.pack(side="right", padx=8)

        # Delete button
        StyledButton(row, "✕ Remove", style="ghost", padx=6, pady=3,
                     command=lambda c=cat_name: self._delete_category(c),
                     font=(FONT_FAMILY, 9)).pack(side="right")

        # Edit button
        StyledButton(row, "✎ Edit", style="secondary", padx=6, pady=3,
                     command=lambda c=cat_name, r=rule: self._edit_category(c, r),
                     font=(FONT_FAMILY, 9)).pack(side="right", padx=4)

        # Extensions preview
        ext_preview = "  ".join(exts[:12]) + ("  ..." if len(exts) > 12 else "")
        tk.Label(card, text=ext_preview or "(no extensions)", bg=SURFACE, fg=TEXT_DIM,
                 font=(MONO_FAMILY, 9), wraplength=700, justify="left").pack(anchor="w", pady=(6, 0))

    def _toggle_rule(self, cat_name: str, enabled: bool):
        rules = self.config.get_rules()
        if cat_name in rules:
            rules[cat_name]["enabled"] = enabled
            self.config.set_rules(rules)

    def _delete_category(self, cat_name: str):
        if not messagebox.askyesno("Delete", f"Remove category '{cat_name}'?"):
            return
        rules = self.config.get_rules()
        rules.pop(cat_name, None)
        self.config.set_rules(rules)
        self._render_rules()

    def _save_conflict_strategy(self):
        self.config.conflict_strategy = self._conflict_var.get()

    def _reset_rules(self):
        if messagebox.askyesno("Reset", "Reset all rules to defaults?"):
            self.config.set_rules(dict(DEFAULT_RULES))
            self._render_rules()

    def _add_category(self):
        self._open_rule_editor(None, None)

    def _change_language(self, event=None):
        self.current_lang = self.lang_var.get()
        self.config.set("language", self.current_lang)
        self.config.save()
        self._update_ui_texts()

    def _update_ui_texts(self):
        self.root.title(self._t("title"))
        for page, item in self._nav_items.items():
            item._lbl.config(text=self._t(page))
        if self._current_page:
            self._navigate(self._current_page)  # Rebuild current page

    def _update_status(self):
        remaining = max(0, int(self.next_scan_time - time.time()))
        self.status_label.config(text=f"{self._t('next_scan_in')} {remaining} {self._t('sec')}")
        self.root.after(1000, self._update_status)

    def _edit_category(self, cat_name: str, rule: dict):
        self._open_rule_editor(cat_name, rule)

    def _open_rule_editor(self, cat_name: Optional[str], rule: Optional[dict]):
        """Open a modal dialog for creating/editing a category rule."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Rule" if cat_name else "New Category")
        dialog.geometry("560x420")
        dialog.configure(bg=BG)
        dialog.resizable(False, False)
        dialog.grab_set()
        dialog.transient(self.root)

        tk.Label(dialog, text=("Edit Category" if cat_name else "New Category"),
                 bg=BG, fg=WHITE, font=(FONT_FAMILY, 16, "bold"),
                 padx=24, pady=16).pack(anchor="w")

        form = tk.Frame(dialog, bg=BG, padx=24)
        form.pack(fill="both", expand=True)

        def lbl(text): tk.Label(form, text=text, bg=BG, fg=TEXT_DIM,
                                  font=(FONT_FAMILY, 10)).pack(anchor="w", pady=(8, 2))
        def entry_var(default=""):
            v = tk.StringVar(value=default)
            e = tk.Entry(form, textvariable=v, bg=SURFACE2, fg=TEXT, relief="flat",
                         bd=0, insertbackground=WHITE, font=(FONT_FAMILY, 11))
            e.pack(fill="x", ipady=7)
            return v

        lbl("Category Name")
        name_var = entry_var(cat_name or "")

        lbl("Icon (emoji)")
        icon_var = entry_var(rule.get("icon", "📁") if rule else "📁")

        lbl("Extensions (comma-separated, e.g. .pdf, .docx)")
        exts_var = entry_var(", ".join(rule.get("extensions", [])) if rule else "")

        lbl("Color (hex)")
        color_var = entry_var(rule.get("color", ACCENT) if rule else ACCENT)

        def save():
            name = name_var.get().strip()
            if not name:
                messagebox.showerror("Error", "Category name required.", parent=dialog)
                return
            raw_exts = [e.strip().lower() for e in exts_var.get().split(",") if e.strip()]
            # Ensure leading dot
            exts = [e if e.startswith(".") else f".{e}" for e in raw_exts]
            rules = self.config.get_rules()
            # If renaming, remove old key
            if cat_name and cat_name != name:
                rules.pop(cat_name, None)
            rules[name] = {
                "extensions": exts,
                "icon": icon_var.get().strip() or "📁",
                "color": color_var.get().strip() or ACCENT,
                "enabled": rules.get(name, {}).get("enabled", True),
            }
            self.config.set_rules(rules)
            self._render_rules()
            dialog.destroy()

        btn_row = tk.Frame(dialog, bg=BG, padx=24, pady=16)
        btn_row.pack(fill="x")
        StyledButton(btn_row, "Save", command=save, style="primary").pack(side="right")
        StyledButton(btn_row, "Cancel", command=dialog.destroy, style="ghost").pack(side="right", padx=8)

    # ── Page: Log ───────────────────────────────────────────────────────────────
    def _build_log(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=BG)

        hdr = tk.Frame(page, bg=BG, padx=28, pady=22)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Activity Log", bg=BG, fg=WHITE,
                 font=(FONT_FAMILY, 22, "bold")).pack(side="left")
        StyledButton(hdr, "🗑 Clear", command=self._clear_log, style="ghost").pack(side="right")
        StyledButton(hdr, "📂 Open Log File", command=self._open_log_file,
                     style="secondary").pack(side="right", padx=8)

        Separator(page).pack(fill="x", padx=28)

        log_frame = tk.Frame(page, bg=SURFACE, padx=12, pady=8)
        log_frame.pack(fill="both", expand=True, padx=28, pady=16)

        self._log_text = tk.Text(
            log_frame, bg=SURFACE, fg=TEXT_DIM,
            font=(MONO_FAMILY, 10),
            relief="flat", bd=0, state="disabled",
            wrap="word", selectbackground=ACCENT,
        )
        vsb = tk.Scrollbar(log_frame, command=self._log_text.yview)
        self._log_text.config(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._log_text.pack(fill="both", expand=True)

        self._log_text.tag_config("INFO",    foreground=TEXT_DIM)
        self._log_text.tag_config("WARNING", foreground=WARNING)
        self._log_text.tag_config("ERROR",   foreground=DANGER)
        self._log_text.tag_config("DEBUG",   foreground=TEXT_DIM)

        return page

    def _refresh_log(self):
        entries = get_log_buffer()
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        for level, msg in entries:
            self._log_text.insert("end", msg + "\n", level)
        self._log_text.see("end")
        self._log_text.config(state="disabled")

    def _clear_log(self):
        from .logger_setup import _LOG_BUFFER
        _LOG_BUFFER.clear()
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    def _open_log_file(self):
        path = get_log_file_path()
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                os.system(f"open '{path}'")
            else:
                os.system(f"xdg-open '{path}'")
        except Exception:
            messagebox.showinfo("Log File", path)

    def _poll_logs(self):
        if self._current_page == "log":
            self._refresh_log()
        self.root.after(2000, self._poll_logs)

    # ── Page: Settings ──────────────────────────────────────────────────────────
    def _build_settings(self) -> tk.Frame:
        page = tk.Frame(self.content, bg=BG)

        hdr = tk.Frame(page, bg=BG, padx=28, pady=22)
        hdr.pack(fill="x")
        tk.Label(hdr, text=self._t("settings"), bg=BG, fg=WHITE,
                 font=(FONT_FAMILY, 22, "bold")).pack(side="left")

        Separator(page).pack(fill="x", padx=28)

        form = tk.Frame(page, bg=BG, padx=28, pady=20)
        form.pack(fill="both", expand=True)

        def section(title):
            tk.Label(form, text=title, bg=BG, fg=TEXT,
                     font=(FONT_FAMILY, 13, "bold")).pack(anchor="w", pady=(16, 4))
            Separator(form).pack(fill="x")

        def row_toggle(label, desc, key):
            r = tk.Frame(form, bg=BG, pady=8)
            r.pack(fill="x")
            left = tk.Frame(r, bg=BG)
            left.pack(side="left", fill="x", expand=True)
            tk.Label(left, text=label, bg=BG, fg=TEXT,
                     font=(FONT_FAMILY, 11)).pack(anchor="w")
            tk.Label(left, text=desc, bg=BG, fg=TEXT_DIM,
                     font=(FONT_FAMILY, 9)).pack(anchor="w")
            var = tk.BooleanVar(value=self.config.get(key, False))
            sw = tk.Checkbutton(r, variable=var, bg=BG, activebackground=BG,
                                 selectcolor=SURFACE2, fg=ACCENT,
                                 command=lambda: self.config.set(key, var.get()))
            sw.pack(side="right")
            return var

        section(self._t("language"))
        lang_r = tk.Frame(form, bg=BG, pady=8)
        lang_r.pack(fill="x")
        tk.Label(lang_r, text=self._t("language"), bg=BG, fg=TEXT,
                 font=(FONT_FAMILY, 11)).pack(side="left")
        self.lang_var = tk.StringVar(value=self.current_lang)
        lang_combo = ttk.Combobox(lang_r, textvariable=self.lang_var,
                                  values=["en", "ru", "es", "zh", "pt"], state="readonly", width=15)
        lang_combo.pack(side="right")
        lang_combo.bind("<<ComboboxSelected>>", self._change_language)

        section(self._t("scan_interval"))
        scan_r = tk.Frame(form, bg=BG, pady=8)
        scan_r.pack(fill="x")
        tk.Label(scan_r, text=self._t("scan_interval"), bg=BG, fg=TEXT,
                 font=(FONT_FAMILY, 11)).pack(side="left")
        self.scan_var = tk.StringVar(value=str(self.scan_interval))
        scan_entry = ttk.Entry(scan_r, textvariable=self.scan_var, width=15)
        scan_entry.pack(side="right", padx=(10, 0))
        StyledButton(scan_r, self._t("apply"),
                   command=lambda: self._update_scan_interval(self.scan_var.get()),
                   style="secondary", padx=8, pady=4).pack(side="right")
        
        self.status_label = tk.Label(form, text="", bg=BG, fg=TEXT_DIM,
                                     font=(FONT_FAMILY, 9))
        self.status_label.pack(anchor="w", pady=(8, 0))
        self._update_status()

        section("Behavior")

        self._org_existing_var = row_toggle(
            "Organize existing files on start",
            "When watcher starts, move pre-existing files in watched folders.",
            "organize_existing"
        )

        self._tray_var = row_toggle(
            "Minimize to system tray",
            "Keep app running in background when window is closed.",
            "minimize_to_tray"
        )

        # Unknown files
        r = tk.Frame(form, bg=BG, pady=8)
        r.pack(fill="x")
        tk.Label(r, text="Unknown Files Folder", bg=BG, fg=TEXT,
                 font=(FONT_FAMILY, 11)).pack(side="left")
        self._unknown_var = tk.StringVar(value=self.config.unknown_folder)
        e = tk.Entry(r, textvariable=self._unknown_var, bg=SURFACE2, fg=TEXT,
                     relief="flat", bd=0, insertbackground=WHITE,
                     font=(FONT_FAMILY, 11), width=16)
        e.pack(side="right", ipady=5, padx=8)
        StyledButton(r, "Save", command=self._save_unknown_folder,
                     style="secondary", padx=8, pady=4).pack(side="right")

        section("Logging")
        log_r = tk.Frame(form, bg=BG, pady=8)
        log_r.pack(fill="x")
        tk.Label(log_r, text="Log Level", bg=BG, fg=TEXT,
                 font=(FONT_FAMILY, 11)).pack(side="left")
        self._log_level_var = tk.StringVar(value=self.config.get("log_level", "INFO"))
        for level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            tk.Radiobutton(
                log_r, text=level, variable=self._log_level_var, value=level,
                bg=BG, fg=TEXT_DIM, selectcolor=SURFACE2, activebackground=BG,
                font=(FONT_FAMILY, 9),
                command=lambda: self.config.set("log_level", self._log_level_var.get())
            ).pack(side="left", padx=8)

        section("About")
        tk.Label(form, text="FileOrganizer v1.0  •  MIT License  •  github.com/fileorganizer",
                 bg=BG, fg=TEXT_DIM, font=(FONT_FAMILY, 10)).pack(anchor="w", pady=8)

        return page

    def _save_unknown_folder(self):
        self.config.set("unknown_folder", self._unknown_var.get().strip() or "Misc")

    # ── Watcher controls ────────────────────────────────────────────────────────
    def _toggle_watcher(self, force_start: bool = False):
        if self.watcher.running and not force_start:
            self.watcher.stop()
            self._update_watcher_ui(False)
            logger.info("Watcher stopped by user.")
        else:
            if not self.watcher.is_available():
                messagebox.showerror(
                    "Missing Dependency",
                    "The 'watchdog' library is not installed.\n\n"
                    "Install it with:\n  pip install watchdog"
                )
                return
            if not self.config.watched_folders:
                messagebox.showwarning("No Folders", "Add at least one folder to watch first.")
                self._navigate("folders")
                return
            ok = self.watcher.start()
            if ok:
                self._update_watcher_ui(True)
                if self.config.get("organize_existing", False):
                    threading.Thread(target=self._run_organize_existing, daemon=True).start()
            else:
                messagebox.showerror("Error", "Failed to start watcher. Check the log for details.")

    def _run_organize_existing(self):
        results = self.watcher.organize_existing()
        for r in results:
            self.root.after(0, self._on_file_organized, r)

    def _update_watcher_ui(self, running: bool):
        if running:
            self._watch_btn.config(text="⏹  Stop Watching", bg=DANGER)
            self._status_dot.config(fg=SUCCESS)
            self._status_lbl.config(text="Watching")
            self._status_bar_lbl.config(text=f"Watcher: Running  •  {len(self.config.watched_folders)} folder(s)")
        else:
            self._watch_btn.config(text="▶  Start Watching", bg=SUCCESS)
            self._status_dot.config(fg=DANGER)
            self._status_lbl.config(text="Not Watching")
            self._status_bar_lbl.config(text="Watcher: Stopped")

    def _organize_now(self):
        if not self.config.watched_folders:
            messagebox.showwarning("No Folders", "Add folders to watch first.")
            return
        threading.Thread(
            target=lambda: [self._on_file_organized(r)
                            for r in self.watcher.organize_existing()],
            daemon=True
        ).start()

    def _on_file_organized(self, result: OrganizerResult):
        """Called from watcher thread — schedule GUI update on main thread."""
        self.root.after(0, self._handle_result, result)

    def _handle_result(self, result: OrganizerResult):
        self._stats["total"] += 1
        if result.action == "error":
            self._stats["errors"] += 1
        elif result.action == "skipped":
            self._stats["skipped"] += 1
        else:
            self._stats["moved"] += 1

        if self._current_page == "dashboard":
            self._refresh_dashboard()

        self._add_activity(result)

    # ── System tray ─────────────────────────────────────────────────────────────
    def _setup_tray(self):
        try:
            import pystray
            from PIL import Image, ImageDraw
        except ImportError:
            return None

        # Create a simple icon
        img = Image.new("RGB", (64, 64), color=(91, 138, 245))
        d = ImageDraw.Draw(img)
        d.text((16, 18), "⚡", fill=(255, 255, 255))

        def show_window(icon, item):
            icon.stop()
            self.root.after(0, self.root.deiconify)

        def quit_app(icon, item):
            icon.stop()
            self.root.after(0, self._quit)

        menu = pystray.Menu(
            pystray.MenuItem("Show FileOrganizer", show_window, default=True),
            pystray.MenuItem("Quit", quit_app),
        )
        tray = pystray.Icon("FileOrganizer", img, "FileOrganizer", menu)
        return tray

    def _on_close(self):
        if self.config.minimize_to_tray:
            tray = self._setup_tray()
            if tray:
                self.root.withdraw()
                threading.Thread(target=tray.run, daemon=True).start()
                return
        self._quit()

    def _quit(self):
        self.scan_running = False
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=2)
        self.watcher.stop()
        self.root.destroy()

    # ── Run ─────────────────────────────────────────────────────────────────────
    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
