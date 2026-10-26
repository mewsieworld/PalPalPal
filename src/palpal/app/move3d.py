"""PalPalPal main window: the 3D view's floating Turn / Move button. In Move mode, dragging moves the selected
image layer around in the bead model (Shift+drag lifts or lowers it) instead of turning the view."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.images import ImageLayer
from ..ui.rounded import round_button

TURN_TEXT, MOVE_TEXT = "⟳ Turn view", "✥ Move layer"


class AppMove3DMixin:
    def build_3d_toggle(self, parent):
        """The floating button in the canvas's top-right corner (only shown in the 3D view)."""
        self.move3d_btn = tk.Button(parent, text=TURN_TEXT, font=("Segoe UI", 9, "bold"), command=self.toggle_move3d)
        self.move3d_btn._cp_keep = True
        self._move_acc = [0.0, 0.0, 0.0]
        self.view.on_move3d = self.move_layer_3d

    def update_3d_toggle(self):
        btn = getattr(self, "move3d_btn", None)
        if btn is None:
            return
        if self.view.is_3d:
            moving = getattr(self.view, "move_mode", False)
            if getattr(btn, "_look", None) != moving:   # redrawing its picture every frame cost as much as the 3D
                btn._look = moving
                btn.configure(text=MOVE_TEXT if moving else TURN_TEXT)
                btn._round_size = None
                round_button(btn, "#7a86ff" if moving else "#607d8b")
            if not btn.winfo_ismapped():
                btn.place(relx=1.0, x=-24, y=8, anchor="ne")
                btn.lift()
        elif btn.winfo_ismapped():
            btn.place_forget()

    def toggle_move3d(self):
        self.view.move_mode = not getattr(self.view, "move_mode", False)
        self._move_acc = [0.0, 0.0, 0.0]
        self.canvas.configure(cursor="fleur" if self.view.move_mode else "")
        self.update_3d_toggle()
        self.request_redraw()

    def moving_layer(self):
        entry = self.entry_of(self.selected_palette())
        return entry if isinstance(entry, ImageLayer) else self.target_image_layer()

    def move_layer_3d(self, dx, dy, lift=False):
        """Turn a mouse drag (screen pixels) into whole-bead steps for the selected layer."""
        il = self.moving_layer()
        axes = getattr(self.view, "axes", None)
        if il is None or axes is None:
            return
        ex, ey, scale = axes
        acc = self._move_acc
        if lift:
            acc[2] += -dy / scale
        else:
            # screen delta = scale * (a * ex + b * ey): solve the 2x2 for the bead steps a (x) and b (y)
            det = ex[0] * ey[1] - ex[1] * ey[0]
            if abs(det) < 1e-6:
                return
            sx, sy = dx / scale, dy / scale
            acc[0] += (sx * ey[1] - sy * ey[0]) / det
            acc[1] += (ex[0] * sy - ex[1] * sx) / det
        step = [int(v) for v in acc]   # whole beads only; the rest carries over
        if not any(step):
            return
        off = list(getattr(il, "offset3d", None) or (0, 0, 0))
        for k in range(3):
            off[k] += step[k]
            acc[k] -= step[k]
        il.offset3d = tuple(off)
        self.mark_dirty()
        self.request_redraw()
