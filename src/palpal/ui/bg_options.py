"""BG Options: background color, transparent BG and the key (see-through) color."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .color_picker import app_askcolor
from ..core.colors import to_hex
from .theme import Theme, Tooltip, hint
from .dialogs import Dialog


class BGOptionsDialog(Dialog):
    """BG Color (preview background) and Palette BG Color (the key / void color), in one place."""

    def __init__(self, app):
        Dialog.__init__(self, app, "BG Options")
        self.bg = app.bg_color
        self.key = app.key_color
        grid = tk.Frame(self.body)
        grid.pack()
        tk.Label(grid, text="BG Color:").grid(row=0, column=0, sticky="w", pady=3)
        self.bg_btn = tk.Button(grid, width=12, command=self.pick_bg)
        self.bg_btn._cp_keep = True
        self.bg_btn.grid(row=0, column=1, sticky="w", padx=(10, 0))
        clear_bg = tk.Button(grid, text="✖", width=2, command=self.clear_bg)
        clear_bg.grid(row=0, column=2, padx=(4, 0))
        Tooltip(clear_bg, "No BG color (transparent)", app)
        tk.Label(grid, text="Palette BG Color:").grid(row=1, column=0, sticky="w", pady=3)
        self.key_btn = tk.Button(grid, width=12, command=self.pick_key)
        self.key_btn._cp_keep = True
        self.key_btn.grid(row=1, column=1, sticky="w", padx=(10, 0))
        clear = tk.Button(grid, text="✖", width=2, command=self.clear_key)
        clear.grid(row=1, column=2, padx=(4, 0))
        Tooltip(clear, "No palette BG color", app)
        dropper = tk.Button(grid, text="💧", width=2, command=self.eyedrop_key)
        dropper.grid(row=1, column=3, padx=(4, 0))
        Tooltip(dropper, "Eyedropper: click a color in the preview to key it out (make it see-through)", app)
        hint(tk.Label(self.body, text="Palette slots with the Palette BG Color show as see-through.\n"
                                      "Use 💧 to pick that color straight from the picture.",
                      fg="gray", font=("Arial", 8)), pady=(6, 0))
        self.hide = tk.BooleanVar(value=bool(app.store.get("bg_options_in_menu")))
        tk.Checkbutton(self.body, text="Hide this menu on the Options Menu", variable=self.hide).pack(anchor="w",
                                                                                                    pady=(8, 0))
        buttons = tk.Frame(self.body)
        buttons.pack(pady=(10, 0))
        tk.Button(buttons, text="Ok", width=8, command=self.ok).pack(side="left", padx=4)
        tk.Button(buttons, text="Cancel", width=8, command=lambda: self.close(None)).pack(side="left", padx=4)
        self.finish()
        self.refresh()

    def _show(self, btn, color):
        if color is None:
            c = Theme.colors(self.app)
            btn.configure(text="none", bg=c["button"], fg=c["fg"], activebackground=c["hover"])
        else:
            btn.configure(text=to_hex(color, False), bg=to_hex(color), activebackground=to_hex(color),
                          fg="black" if sum(color) > 380 else "white")

    def refresh(self):
        self._show(self.bg_btn, self.bg)
        self._show(self.key_btn, self.key)

    def clear_bg(self):
        self.bg = None
        self.refresh()

    def pick_bg(self):
        result = app_askcolor(self.app, color=to_hex(self.bg) if self.bg else None, title="BG Color", parent=self.win)
        if result and result[0]:
            self.bg = tuple(int(v) for v in result[0])
            self.refresh()

    def pick_key(self):
        result = app_askcolor(self.app, color=to_hex(self.key) if self.key else None, title="Palette BG Color",
                                       parent=self.win)
        if result and result[0]:
            self.key = tuple(int(v) for v in result[0])
            self.refresh()

    def eyedrop_key(self):
        """Hide the dialog until a color is clicked in the main preview (Esc cancels)."""
        self.win.grab_release()
        self.win.withdraw()
        self.app.start_eyedropper(self._dropped)

    def _dropped(self, color):
        if not self.win.winfo_exists():
            return
        if color is not None:
            self.key = tuple(int(v) for v in color[:3])
            self.refresh()
        self.win.deiconify()
        self.win.lift()
        self.win.grab_set()
        self.win.focus_set()

    def clear_key(self):
        self.key = None
        self.refresh()

    def ok(self):
        self.app.store.set("bg_options_in_menu", self.hide.get())
        self.app.bg_color = self.bg
        self.close(True)
        self.app.set_key_color(self.key)
        self.app.update_bottom_bar()
        self.app.mark_dirty()
        self.app.request_redraw()
