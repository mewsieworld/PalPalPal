"""Where PalPalPal keeps things: the program folder, Documents/PalPalPal, and the user settings file."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)


# ---------------------------------------------------------------------------
# Paths and user storage
# ---------------------------------------------------------------------------

def app_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # The program folder is src/ (this file is src/palpal/core/storage.py)
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def documents_dir():
    if sys.platform == "win32":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(260)
            # CSIDL_PERSONAL = 5 (Documents), honours redirected folders
            if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buf) == 0 and buf.value:
                return buf.value
        except Exception:
            pass
    return os.path.join(os.path.expanduser("~"), "Documents")


def _is_writable(folder):
    try:
        os.makedirs(folder, exist_ok=True)
        probe = os.path.join(folder, ".cp_write_probe")
        with open(probe, "w"):
            pass
        os.remove(probe)
        return True
    except OSError:
        return False


def cache_dir():
    """The __pycache__ folder that holds user info, next to the program when writable."""
    local = os.path.join(app_dir(), "__pycache__")
    if _is_writable(local):
        return local
    base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), ".local", "share")
    folder = os.path.join(base, APP_NAME, "__pycache__")
    os.makedirs(folder, exist_ok=True)
    return folder


HOME_DIR = os.path.join(documents_dir(), APP_NAME)


EXPORT_DIRS = {
    "colors": os.path.join(HOME_DIR, "Excess-colors"),  # where Saved Colors load and save
    "images": os.path.join(HOME_DIR, "exports", "images"),
    "palettes": os.path.join(HOME_DIR, "exports", "palettes"),
    "projects": os.path.join(HOME_DIR, "projects"),
    "reports": os.path.join(HOME_DIR, "exports", "reports"),
}


def export_dir(kind):
    folder = EXPORT_DIRS[kind]
    try:
        os.makedirs(folder, exist_ok=True)
    except OSError:
        return os.path.expanduser("~")
    return folder


class UserStore:
    """User settings and saved colors, kept in the __pycache__ user file."""

    FILE = "palpalpal_user.json"
    OLD_FILE = "corneas_user.json"  # read once if present, from before the rename
    DEFAULTS = {
        "dark_mode": False,
        "preview_mode": "Big Preview",
        "live_pal_ui_mode": "Simple",
        "gradient_ui": "Strips",
        "palette_format": "pal",     # pal, png (swatch grid) or both
        "pal_style": "vga",          # how .pal files are written: raw vga or jasc text
        "show_excess_prompt": True,
        "show_frame_labels": True,
        "custom_count": 3,
        "custom_start": 1,
        "custom_end": 0,             # 0 means "the last frame"
        "all_mode_warning": True,
        "view_3d": False,
        "bg_options_in_menu": False,
        "new_project_remember": None,  # remembered New Project answers, to fly through the prompts
        "alignments": {},  # "Big Preview|single" -> compass anchor; centred when missing
        "save_sorted_choice": None,  # remembered answer to "Save with custom sorting?"
        "mass_editor_default": False,
        "use_right_click": True,
        "hide_hints": False,        # Document & 3D Settings > Show helpful hints (unticked hides them)
        "show_debug_menu": False,   # Help > Current Display Info / Debug Info (Document & 3D Settings turns them on)
        "active_sort": ["index", True],  # Active Colors order: key and ascending?
        "compact_multi": False,  # Active Colors: clicking adds to a group instead of picking one color
        "saved_colors": [None] * DEFAULT_SAVED_SLOTS,
        "stats": {},
    }

    def __init__(self):
        self.path = os.path.join(cache_dir(), self.FILE)
        self.data = dict(self.DEFAULTS)
        old = os.path.join(os.path.dirname(self.path), self.OLD_FILE)
        migrating = not os.path.exists(self.path)
        try:
            with open(old if migrating else self.path, "r", encoding="utf-8") as f:
                self.data.update(json.load(f))
        except (OSError, ValueError):
            pass
        self.data.pop("picker_style", None)
        if migrating:
            self.data["gradient_ui"] = self.DEFAULTS["gradient_ui"]
            # Simple and Advanced swapped names when the editor became the Super Swatch Switcher
            swap = {"Simple": "Advanced", "Advanced": "Simple"}
            self.data["live_pal_ui_mode"] = swap.get(self.data.get("live_pal_ui_mode"), "Simple")

    def get(self, key):
        return self.data.get(key, self.DEFAULTS.get(key))

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=1)
        except OSError:
            pass
