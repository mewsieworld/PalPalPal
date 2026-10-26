"""Dark / light theme, tooltips and window centering."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)


# ---------------------------------------------------------------------------
# Theme (ported from code/utils/theme_manager.py)
# ---------------------------------------------------------------------------

class Theme:
    LIGHT = dict(bg="#F0F0F0", fg="#000000", canvas="white", input="white", select="white",
                 button="#E0E0E0", hover="#D0D0D0", trough="#D6D6D6", accent="#5b6ee1", accent_hover="#7486f0")
    DARK = dict(bg="#1E1E1E", fg="#FFFFFF", canvas="#151515", input="#252525", select="#333333",
                button="#2D2D2D", hover="#333333", trough="#3A3A3A", accent="#7a86ff", accent_hover="#9aa3ff")

    @staticmethod
    def colors(app):
        return Theme.DARK if app.dark_mode else Theme.LIGHT

    @staticmethod
    def apply(app, widget=None):
        c = Theme.colors(app)
        if widget is None:
            widget = app.master
            Theme._style(app, c)
        if getattr(widget, "_cp_keep", False):
            return
        try:
            kind = widget.winfo_class()
            if kind in ("Frame", "Toplevel", "Tk", "Panedwindow"):
                widget.configure(bg=c["bg"])
            elif kind in ("Label", "Labelframe", "Radiobutton", "Checkbutton"):
                widget.configure(bg=c["bg"], fg=c["fg"])
                if kind in ("Radiobutton", "Checkbutton"):
                    widget.configure(selectcolor=c["select"], activebackground=c["hover"], activeforeground=c["fg"])
            elif kind == "Canvas":
                widget.configure(bg=c["canvas"] if getattr(widget, "_cp_preview", False) else c["bg"],
                                 highlightbackground=c["bg"])
            elif kind in ("Entry", "Listbox", "Text"):
                widget.configure(bg=c["input"], fg=c["fg"], insertbackground=c["fg"], highlightbackground=c["bg"])
            elif kind in ("Button", "Menubutton"):
                widget.configure(bg=c["button"] if app.dark_mode else c["bg"], fg=c["fg"],
                                 activebackground=c["hover"], activeforeground=c["fg"])
            elif kind == "Scale":
                # A Scale's bg is its slider knob, so it takes the accent color
                widget.configure(bg=c["accent"], fg=c["fg"], highlightbackground=c["bg"],
                                 troughcolor=c["trough"], activebackground=c["accent_hover"])
            elif kind == "Scrollbar":
                widget.configure(bg=c["button"], troughcolor=c["bg"])
            elif kind == "Menu":
                widget.configure(bg=c["input"], fg=c["fg"], activebackground=c["hover"], activeforeground=c["fg"])
        except tk.TclError:
            pass
        for child in widget.winfo_children():
            Theme.apply(app, child)

    @staticmethod
    def _style(app, c):
        style = ttk.Style()
        if app.dark_mode:
            style.theme_use("clam")
            style.configure(".", background=c["bg"], foreground=c["fg"])
            style.configure("TCombobox", fieldbackground=c["input"], background=c["input"], foreground=c["fg"],
                            selectbackground=c["select"], selectforeground=c["fg"])
            style.map("TCombobox", fieldbackground=[("readonly", c["input"])], background=[("readonly", c["input"])],
                      foreground=[("readonly", c["fg"])])
            app.master.option_add("*TCombobox*Listbox.background", c["input"])
            app.master.option_add("*TCombobox*Listbox.foreground", c["fg"])
            style.configure("TEntry", fieldbackground=c["input"], foreground=c["fg"])
            thumb, hover = "#4A4A4A", "#5E5E5E"
            for name in ("TScrollbar", "Vertical.TScrollbar", "Horizontal.TScrollbar"):
                style.configure(name, background=thumb, troughcolor=c["canvas"], arrowcolor=c["fg"],
                                bordercolor=c["bg"], lightcolor=thumb, darkcolor=thumb, gripcount=0)
                # clam's default hover / pressed / disabled colors are light grey; keep them dark
                style.map(name, background=[("disabled", c["bg"]), ("pressed", c["accent"]), ("active", hover)],
                          lightcolor=[("pressed", c["accent"]), ("active", hover)],
                          darkcolor=[("pressed", c["accent"]), ("active", hover)],
                          arrowcolor=[("disabled", "#666666")], troughcolor=[("disabled", c["bg"])])
            style.configure("TScale", background=c["bg"], troughcolor=c["trough"])
            style.configure("TButton", background=c["button"], foreground=c["fg"], bordercolor=c["bg"])
            style.map("TButton", background=[("active", c["hover"])])
            style.configure("TMenubutton", background=c["button"], foreground=c["fg"])
            style.configure("TCheckbutton", background=c["bg"], foreground=c["fg"])
            style.map("TCheckbutton", background=[("active", c["bg"])])
            style.configure("TLabel", background=c["bg"], foreground=c["fg"])
            style.configure("TFrame", background=c["bg"])
        else:
            for name in ("vista", "winnative", "clam", "default"):
                try:
                    style.theme_use(name)
                    break
                except tk.TclError:
                    continue


class Tooltip:
    def __init__(self, widget, text, app=None):
        self.widget, self.text, self.app, self.tip = widget, text, app, None
        widget.bind("<Enter>", self.show, add="+")
        widget.bind("<Leave>", self.hide, add="+")

    def show(self, _event=None):
        if self.tip:
            return
        dark = bool(self.app and self.app.dark_mode)
        x = self.widget.winfo_rootx() + 16
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry("+%d+%d" % (x, y))
        tk.Label(self.tip, text=self.text, bg="#333333" if dark else "#FFFFE0", fg="white" if dark else "black",
                 relief="solid", bd=1, font=("Arial", 8), padx=4, pady=2).pack()

    def hide(self, _event=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


def center_on(window, parent):
    window.update_idletasks()
    w, h = window.winfo_width(), window.winfo_height()
    try:
        x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    except tk.TclError:
        x = (window.winfo_screenwidth() - w) // 2
        y = (window.winfo_screenheight() - h) // 2
    window.geometry("+%d+%d" % (max(0, x), max(0, y)))
