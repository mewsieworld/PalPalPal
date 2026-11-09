"""Palette sorting: the Sort button and its popup."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import rgb_to_hsv_int
from .theme import Theme

ARROW_UP, ARROW_DOWN = "\u25b2", "\u25bc"  # ▲ ▼


def sort_indices(app, indices, palette):
    """Order palette indexes by the Sort setting: by index, or by the hue / saturation / value of their color."""
    key, ascending = app.store.get("active_sort") or ("index", True)
    if key != "index" and palette is not None:
        part = {"hue": 0, "sat": 1, "val": 2}[key]
        indices = sorted(indices, key=lambda i: (rgb_to_hsv_int(palette.colors[i])[part], i))
    else:
        indices = sorted(indices)
    return indices if ascending else list(reversed(indices))


def is_custom_sort(app):
    return tuple(app.store.get("active_sort") or ("index", True)) != ("index", True)


class SortButton:
    """'Sort: [Index]' button. Its list stays open while you switch keys and directions; click away to close."""

    CHOICES = [("index", "Default (Index)", "Index"), ("hue", "Hue", "Hue"), ("sat", "Saturation", "Sat"),
               ("val", "Value", "Val")]

    def __init__(self, app, parent, on_change):
        self.app, self.on_change, self.popup = app, on_change, None
        self.button = tk.Button(parent, command=self.toggle_popup, font=("Arial", 8))
        self.refresh_label()

    def pack(self, **kw):
        self.button.pack(**kw)
        return self

    def current(self):
        key, ascending = self.app.store.get("active_sort") or ("index", True)
        return key, bool(ascending)

    def refresh_label(self):
        key = self.current()[0]
        short = next(s for k, _l, s in self.CHOICES if k == key)
        key, ascending = self.current()
        self.button.configure(text="Sort: %s %s" % (short, ARROW_UP if ascending else ARROW_DOWN))

    def toggle_popup(self):
        if self.popup is not None:
            self.close()
            return
        c = Theme.colors(self.app)
        self.popup = tk.Toplevel(self.app.master)
        self.popup.wm_overrideredirect(True)
        self.popup.configure(bg="#888888")
        self.popup.geometry("+%d+%d" % (self.button.winfo_rootx(),
                                        self.button.winfo_rooty() + self.button.winfo_height()))
        self.rows = []
        for key, label, _short in self.CHOICES:
            row = tk.Label(self.popup, anchor="w", padx=10, pady=3, width=18, cursor="hand2",
                           bg=c["input"], fg=c["fg"])
            row.pack(fill="x", padx=1, pady=(1, 0))
            row.bind("<Button-1>", lambda e, k=key: self.choose(k))
            row.bind("<Enter>", lambda e, w=row: w.configure(bg=c["hover"]))
            row.bind("<Leave>", lambda e, w=row: w.configure(bg=c["input"]))
            self.rows.append((key, label, row))
        tk.Frame(self.popup, height=1, bg="#888888").pack(fill="x")
        self.relabel_rows()
        # Close on any click outside the list (or on the Sort button itself)
        self._click_id = self.app.master.bind_all("<Button-1>", self._outside_click, add="+")
        self.popup.bind("<Escape>", lambda e: self.close())
        self.popup.focus_set()

    def relabel_rows(self):
        key, ascending = self.current()
        for k, label, row in self.rows:
            row.configure(text=label + ((" " + (ARROW_UP if ascending else ARROW_DOWN)) if k == key else ""),
                          font=("Arial", 9, "bold" if k == key else "normal"))

    def choose(self, key):
        current, ascending = self.current()
        # Picking the active choice again flips its direction; a new choice starts ascending
        self.app.store.set("active_sort", [key, (not ascending) if key == current else True])
        self.relabel_rows()
        self.refresh_label()
        self.on_change()

    def _outside_click(self, event):
        if self.popup is None:
            return
        widget = event.widget
        try:
            inside = str(widget).startswith(str(self.popup)) or widget is self.button
        except tk.TclError:
            inside = False
        if not inside:
            self.close()

    def close(self):
        if self.popup is not None:
            self.popup.destroy()
            self.popup = None
            try:
                self.app.master.unbind_all("<Button-1>")
            except tk.TclError:
                pass
