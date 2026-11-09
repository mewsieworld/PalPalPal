"""The Mass Frame Editor (img2palette): edit every frame at once through their shared indexes."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..ui.theme import Theme, center_on
from .layout import MassEditorLayoutMixin
from .canvas import MassEditorCanvasMixin
from .editing import MassEditorEditMixin


# ---------------------------------------------------------------------------
# Frame Mass Editor (from PalletteEditor.html): edit every frame at once through their shared indexes
# ---------------------------------------------------------------------------


class FrameMassEditor(MassEditorLayoutMixin, MassEditorCanvasMixin, MassEditorEditMixin):
    """Step 0: frames and the eyedropper. Step 1: the source indexes. Then a live HSL target, the list of
    mappings, export, and a strip of the next frames. Every change lands on the layer palette, so it
    shows on every frame that shares the index."""

    def __init__(self, app):
        self.app = app
        self.palette = app.selected_palette()
        images = app.images_colored_by(self.palette)
        self.layer = images[0] if images else None
        self.frame = app.current_frame % len(self.layer.frames) if self.layer else 0
        self.zoom = 2
        self.selected = None
        self.multi = set()
        self.multi_on = False
        self.last_clicked = None
        self.base_hsl = (0, 0, 0)
        self.base_values = {}
        self.eyedropper = False
        self.boxes = {}
        self.photos = []
        self._lock = False
        # What the palette looked like when it was last applied; Close goes back to it
        self.applied_colors = list(self.palette.colors) if self.palette else []

        self.win = tk.Toplevel(app.master)
        self.win.title("Mass Frame Editor")
        self.win.geometry("1180x720")
        self.win.minsize(980, 600)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.win.bind("<Left>", lambda e: self.change_frame(-1))
        self.win.bind("<Right>", lambda e: self.change_frame(1))
        self.win.bind("<x>", lambda e: self.reset_position())
        self.build()
        Theme.apply(app, self.win)
        center_on(self.win, app.master)
        self.win.after(80, self.redraw)

    def apply_changes(self):
        """Apply (top right): keep the edits made so far."""
        if self.palette is None:
            return
        self.applied_colors = list(self.palette.colors)
        self.app.layer_colors_changed(self.palette)
        self.app.request_redraw()
        self.applied_lbl.configure(text="Applied")
        self.win.after(1500, lambda: self.applied_lbl.winfo_exists() and self.applied_lbl.configure(text=""))

    def close(self):
        """Close (bottom left, or the window's X): cancel anything not applied and put the preview back.
        Asks first when there are changes that weren't applied (or reset)."""
        if self.palette is not None and list(self.palette.colors) != self.applied_colors:
            if not messagebox.askyesno("Mass Frame Editor", "You changed the palette but didn't apply it.\n\n"
                                       "Close anyway and throw those changes away?", parent=self.win):
                return
            self.palette.colors[:] = self.applied_colors
            self.app.layer_colors_changed(self.palette)
            self.app.request_redraw()
        self.win.destroy()
        self.app.mass_editor = None
