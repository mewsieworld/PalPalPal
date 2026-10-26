"""The main window's own palette editor (Active Colors)."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import avoid_key, parse_hex, to_hex
from .theme import Theme
from .widgets import (SortButton, draw_swatch, hsv_row, picker_row, relay_swatches, set_pick_mode, sort_indices,
    swatch_grid)
from .gradient import GradientMenu, GradientTarget


class CompactEditor:
    """The main window's own palette editor. Edits the selected layer's palette with relative HSV shifts."""

    def __init__(self, app):
        self.app = app
        self.h_var, self.s_var, self.v_var = tk.IntVar(value=0), tk.IntVar(value=0), tk.IntVar(value=0)
        self.hex_var = tk.StringVar()
        self.idx_var = tk.StringVar(value="0")
        # Off by default so clicking a color edits only that color; turn Multi on to build a group
        self.multi_var = tk.BooleanVar(value=bool(app.store.get("compact_multi")))
        self.multi_var.trace_add("write", lambda *_: self._multi_changed())
        self.count_lbl = None
        self.selected = set()
        self.base = {}
        self.picking = False
        self.swatches = {}

    def layer(self):
        return self.app.selected_palette()

    def _multi_changed(self):
        self.app.store.set("compact_multi", bool(self.multi_var.get()))
        if not self.multi_var.get() and len(self.selected) > 1:
            self.selected = {sorted(self.selected)[-1]}
            self.snapshot()
            self.redraw()

    def _selection_controls(self, parent):
        """Multi checkbox and the "(n selected)" count, always next to the Active Colors title."""
        tk.Checkbutton(parent, text="Multi", variable=self.multi_var, font=("Arial", 8)).pack(side="left", padx=(8, 0))
        self.count_lbl = tk.Label(parent, text="", font=("Arial", 8))   # themed like every other label
        self.count_lbl.pack(side="left", padx=(4, 0))

    def build(self, frame, big=False):
        for w in frame.winfo_children():
            w.destroy()
        self.swatches = {}
        ly = self.layer()
        if ly is None:
            tk.Label(frame, text="Choose a palette to see active colors", fg="gray").pack(expand=True)
            Theme.apply(self.app, frame)
            return
        if big:
            self._build_big(frame)
        else:
            self._build_small(frame)
        self.redraw()
        Theme.apply(self.app, frame)

    def _hsv_block(self, parent):
        hsv_row(parent, 0, "Hue", self.h_var, -180, 180, self.hsv_changed)
        hsv_row(parent, 1, "Sat", self.s_var, -100, 100, self.hsv_changed)
        hsv_row(parent, 2, "Val", self.v_var, -100, 100, self.hsv_changed)

    def _reset_button(self, parent):
        reset = tk.Button(parent, text="Reset", bg="#f44336", fg="white", font=("Arial", 8, "bold"),
                          activebackground="#d32f2f", command=self.reset_sliders)
        reset._cp_keep = True
        return reset

    def _build_small(self, frame):
        left = tk.Frame(frame, width=205)
        left.pack(side="left", fill="y", padx=5, pady=5)
        left.pack_propagate(False)
        tk.Label(left, text="HSV Adjustments", font=("Arial", 9, "bold")).pack(pady=(0, 5))
        sl = tk.Frame(left)
        sl.pack(fill="x")
        self._hsv_block(sl)
        self._reset_button(left).pack(fill="x", pady=(8, 0))
        tk.Button(left, text="Toggle Saved Colors", font=("Arial", 8, "bold"),
                  command=self.app.toggle_saved_colors).pack(fill="x", pady=(5, 0))

        right = tk.Frame(frame)
        right.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        head = self.header = tk.Frame(right)
        head.pack(fill="x")
        tk.Label(head, text="Active Colors", font=("Arial", 9, "bold")).pack(side="left")
        self._selection_controls(head)
        SortButton(self.app, head, self.resort).pack(side="right")
        picker_row(right, self).pack(fill="x", pady=(2, 4))
        self.grid_holder = tk.Frame(right)
        self.grid_holder.pack(fill="both", expand=True)
        self.grid_shape = (22, 12)
        self.swatches = swatch_grid(self.grid_holder, self.sorted_indices(), 22, 12, self.toggle)

    def _build_big(self, frame):
        """No Preview layout: wide HSV sliders with Reset at their right, double-size index boxes."""
        top = tk.Frame(frame)
        top.pack(fill="x", padx=8, pady=(8, 4))
        tk.Label(top, text="HSV Adjustments", font=("Arial", 10, "bold")).pack(anchor="w")
        row = tk.Frame(top)
        row.pack(fill="x")
        sl = tk.Frame(row)
        sl.pack(side="left", fill="x", expand=True)
        self._hsv_block(sl)
        self._reset_button(row).pack(side="left", padx=(10, 0), ipadx=10)
        picker_row(frame, self).pack(fill="x", padx=8, pady=(4, 6))
        self.grid_holder = tk.Frame(frame)
        self.grid_holder.pack(fill="both", expand=True, padx=8)
        self.grid_shape = (44, 11)
        self.swatches = swatch_grid(self.grid_holder, self.sorted_indices(), 44, 11, self.toggle)
        bottom = tk.Frame(frame)
        bottom.pack(fill="x", padx=8, pady=(4, 8))
        tk.Label(bottom, text="Active Color Indexes", font=("Arial", 10, "bold")).pack(side="left")
        self._selection_controls(bottom)
        SortButton(self.app, bottom, self.resort).pack(side="left", padx=(12, 0))
        tk.Button(bottom, text="Toggle Saved Colors", font=("Arial", 8, "bold"),
                  command=self.app.toggle_saved_colors).pack(side="right")

    def sorted_indices(self):
        return sort_indices(self.app, self.app.editable_indices(), self.layer())

    def resort(self):
        """Re-lay only the swatch grid, so the open Sort list survives."""
        holder = getattr(self, "grid_holder", None)
        swatches = relay_swatches(holder, self.sorted_indices(), *self.grid_shape, on_click=self.toggle)
        if swatches is None:
            return
        self.swatches = swatches
        self.redraw()
        Theme.apply(self.app, holder)

    def snapshot(self):
        ly = self.layer()
        self.base = {i: ly.colors[i] for i in self.selected} if ly else {}
        self.h_var.set(0)
        self.s_var.set(0)
        self.v_var.set(0)

    def clear_state(self):
        self.selected = set()
        self.base = {}

    def redraw(self):
        ly = self.layer()
        if ly is None:
            return
        for idx, sw in self.swatches.items():
            if sw.winfo_exists():
                draw_swatch(self.app, sw, ly.colors[idx], idx in self.selected)
        if self.count_lbl is not None and self.count_lbl.winfo_exists():
            n = len(self.selected)
            self.count_lbl.configure(text="(%d selected)" % n if n else "")

    def toggle(self, idx, event=None):
        ly = self.layer()
        if ly is None:
            return
        if self.picking:
            self.hex_var.set(to_hex(ly.colors[idx], False))
            return
        if self.multi_var.get():
            self.selected ^= {idx}
        else:
            self.selected = set() if self.selected == {idx} else {idx}
        self.hex_var.set(to_hex(ly.colors[idx], False))
        self.idx_var.set(str(idx))
        self.snapshot()
        self.redraw()

    def select_all(self):
        self.selected = set(self.app.editable_indices())
        if len(self.selected) > 1:
            self.multi_var.set(True)
        self.snapshot()
        self.redraw()

    def clear(self):
        self.selected = set()
        self.snapshot()
        self.redraw()

    def goto_index(self):
        try:
            idx = max(0, min(255, int(self.idx_var.get())))
        except ValueError:
            return
        self.toggle(idx)

    def reset_sliders(self):
        self.h_var.set(0)
        self.s_var.set(0)
        self.v_var.set(0)
        self.hsv_changed()

    def hsv_changed(self):
        ly = self.layer()
        if ly is None or not self.selected:
            return
        try:
            dh, ds, dv = self.h_var.get(), self.s_var.get(), self.v_var.get()
        except tk.TclError:
            return
        for idx in self.selected:
            base = self.base.get(idx, ly.colors[idx])
            if (dh, ds, dv) == (0, 0, 0) or self.app.is_key(base):
                ly.colors[idx] = tuple(base)
                continue
            h, s, v = colorsys.rgb_to_hsv(base[0] / 255.0, base[1] / 255.0, base[2] / 255.0)
            h = ((h * 360 + dh) % 360) / 360.0
            s = max(0.0, min(1.0, s + ds / 100.0))
            v = max(0.0, min(1.0, v + dv / 100.0))
            r, g, b = colorsys.hsv_to_rgb(h, s, v)
            ly.colors[idx] = avoid_key((int(r * 255), int(g * 255), int(b * 255)), self.app.key_color)
        self.hex_var.set(to_hex(ly.colors[sorted(self.selected)[-1]], False))
        self.changed(ly)

    def changed(self, ly):
        self.redraw()
        self.app.layer_colors_changed(ly)
        self.app.request_redraw()

    def current_color(self):
        ly = self.layer()
        if ly is None or not self.selected:
            return None
        return ly.colors[sorted(self.selected)[0]]

    def apply_color(self, color):
        if self.picking:
            self.hex_var.set(to_hex(color, False))
            return
        ly = self.layer()
        if ly is None or not self.selected:
            return
        for idx in self.selected:
            ly.colors[idx] = tuple(color)
        self.snapshot()
        self.changed(ly)

    def apply_hex_entry(self):
        color = parse_hex(self.hex_var.get())
        if color is None:
            messagebox.showwarning("Hex", "Type a color as RRGGBB, for example ff8800.")
            return
        if not self.selected:
            messagebox.showinfo("Active Colors", "Select one or more colors first.")
            return
        was_picking, self.picking = self.picking, False
        self.apply_color(color)
        self.picking = was_picking

    def toggle_pick(self):
        set_pick_mode(self, not self.picking)
        self.app.canvas.configure(cursor="crosshair" if self.picking else "")

    def open_gradient(self):
        if not self.selected:
            messagebox.showinfo("Selection Required", "Please select one or more colors to apply a gradient.")
            return

        def changed():
            self.snapshot()
            self.changed(self.layer())

        GradientMenu(self.app, self.app.master, GradientTarget(self.layer, lambda: sorted(self.selected),
                                                               changed, self.app.step_frame))
