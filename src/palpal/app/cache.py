"""Clear Cache (Help menu and Document & 3D Settings): throw away files PalPalPal can rebuild by itself.

Cleared: Python's compiled-code caches (*.pyc), the Artwork Tool's autosave / recovery and saved workspace,
and leftovers from an update (PalPalPal.exe.new, palpalpal_update.bat). Kept: your settings, Saved Colors,
statistics, projects and exports.
"""

import glob

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import app_dir, cache_dir

ARTWORK_CACHE_FILES = ("sprite_autosave.json", "sprite_workspace.json")


def cache_files():
    """Every file Clear Cache would delete."""
    root = app_dir()
    found = set(glob.glob(os.path.join(root, "**", "__pycache__", "*.pyc"), recursive=True))
    for name in ARTWORK_CACHE_FILES:
        path = os.path.join(cache_dir(), name)
        if os.path.exists(path):
            found.add(path)
    for pattern in ("*.exe.new", "*.exe.new.part", "palpalpal_update.bat"):
        found.update(glob.glob(os.path.join(root, pattern)))
    return sorted(found)


def clear_cache(app, parent=None):
    files = cache_files()
    parent = parent or app.master
    if not files:
        messagebox.showinfo("Clear Cache", "The cache is already empty.", parent=parent)
        return 0
    size = sum(os.path.getsize(f) for f in files if os.path.exists(f))
    if not messagebox.askyesno("Clear Cache", "Delete %d cached file%s (%.1f MB)?\n\nThat's compiled Python code, the "
                                              "Artwork Tool's autosave and saved workspace, and update leftovers.\n"
                                              "Your settings, Saved Colors, projects and exports are kept."
                               % (len(files), "" if len(files) == 1 else "s", size / 1048576.0), parent=parent):
        return 0
    removed = 0
    for path in files:
        try:
            os.remove(path)
            removed += 1
        except OSError:
            pass   # in use right now (the running program's own code); it goes next time
    messagebox.showinfo("Clear Cache", "Cleared %d of %d files." % (removed, len(files)), parent=parent)
    return removed
