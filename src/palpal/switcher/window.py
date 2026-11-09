"""The Super Swatch Switcher palette editor window (Simple, Advanced and NuAge skins)."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import rgb_to_hsv_int
from ..ui.theme import center_on
from .layouts import SwitcherLayoutMixin
from .editing import SwitcherEditMixin


# ---------------------------------------------------------------------------
# Serene Swatch Switcher (the palette editor window): Simple / Advanced / NuAge skins
# ---------------------------------------------------------------------------


class SwatchSwitcher(SwitcherLayoutMixin, SwitcherEditMixin):
    def __init__(self, app):
        self.app = app
        self.layers = app.layers
        self.target_var = tk.StringVar()
        self.multi_var = tk.BooleanVar(value=False)
        self.selected = set()
        self.sel_index = 0
        self.last_clicked = None
        self.originals = {id(ly): list(ly.colors) for ly in self.layers}
        self.dirty = set()
        self.base = {}
        self.base_hsv = (0, 0, 0)
        self.picking = False
        self.frame_idx = app.current_frame
        self.swatches = {}
        self.preview = None
        self._preview_job = None
        self.skin = app.store.get("live_pal_ui_mode")
        if self.skin not in SKINS:
            self.skin = "Simple"

        self.win = tk.Toplevel(app.master)
        self.win.title(SWITCHER_NAME)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.bind("<Left>", lambda e: self._key_nav(-1))
        self.win.bind("<Right>", lambda e: self._key_nav(1))

        start = app.selected_layer if 0 <= app.selected_layer < len(self.layers) else 0
        self.target_var.set(self._names()[start])
        self.build()
        center_on(self.win, app.master)

    # ----- state helpers -----
    def _names(self):
        return ["%d. %s" % (i + 1, ly.name) for i, ly in enumerate(self.layers)]

    def layer(self):
        names = self._names()
        try:
            return self.layers[names.index(self.target_var.get())]
        except ValueError:
            return self.layers[0] if self.layers else None

    def editable(self):
        return self.app.editable_indices(self.layer())

    def targets(self):
        if self.multi_var.get() and self.selected:
            return sorted(self.selected)
        return [self.sel_index]

    def snapshot(self):
        ly = self.layer()
        if ly is None:
            return
        self.base = {i: ly.colors[i] for i in self.targets()}
        self.base_hsv = rgb_to_hsv_int(ly.colors[self.sel_index])

    def show_preview(self):
        """No Preview mode (or a project without images) leaves the preview out of the editor."""
        return self.app.view_var.get() != "No Preview" and bool(self.app.image_layers())

    def _key_nav(self, step):
        if isinstance(self.win.focus_get(), (tk.Entry, ttk.Entry, ttk.Combobox)):
            return
        self.step_frame(step)

    def close(self):
        if self.dirty:
            names = ", ".join(ly.name for ly in self.layers if id(ly) in self.dirty)
            answer = messagebox.askyesnocancel(
                "Unsaved changes",
                "You haven't saved your changes to: %s\n\nSave them to a palette file before closing?\n\n"
                "Yes saves, No throws the changes away, Cancel keeps editing." % names, parent=self.win)
            if answer is None:
                return
            if answer:
                for ly in self.layers:
                    if id(ly) in self.dirty and not self.app.save_layer_palette(ly, parent=self.win):
                        return
            else:
                for ly in self.layers:
                    if id(ly) in self.dirty:
                        ly.colors[:] = self.originals.get(id(ly), ly.loaded_colors)
                        self.app.layer_colors_changed(ly)
                self.app.request_redraw()
        self.win.destroy()
        self.app.switcher = None
        self.app.saved_panels = [p for p in self.app.saved_panels if p.frame.winfo_exists()]
