"""Super Swatch Switcher: selecting, editing, saving and loading colors."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import avoid_key, hsv_int_to_rgb, pad256, parse_hex, rgb_to_hsv_int, to_hex
from ..core.palettes import read_palette
from ..ui.theme import Theme, center_on
from ..ui.widgets import (SavedColorsPanel, SortButton, draw_swatch, hsv_row, is_custom_sort, make_swatch,
    picker_row, relay_swatches, set_pick_mode, sort_indices, swatch_grid)
from ..ui.gradient import GradientMenu, GradientTarget
from ..preview.canvas import PreviewView, bind_pan_and_zoom
from ..ui.dialogs import ask_save_sorted


class SwitcherEditMixin:
    """Super Swatch Switcher: selecting, editing, saving and loading colors."""

    # ----- drawing -----
    def redraw_swatch(self, idx):
        sw = self.swatches.get(idx)
        ly = self.layer()
        if sw is None or ly is None or not sw.winfo_exists():
            return
        draw_swatch(self.app, sw, ly.colors[idx], selected=idx in self.selected)

    def refresh_swatches(self):
        for idx in self.swatches:
            self.redraw_swatch(idx)

    def update_selection_ui(self):
        self.refresh_swatches()
        try:
            self.count_lbl.configure(text="(%d selected)" % len(self.selected))
        except (tk.TclError, AttributeError):
            pass

    def update_picker(self):
        ly = self.layer()
        if ly is None:
            return
        color = ly.colors[self.sel_index]
        self.idx_var.set(str(self.sel_index))
        if not self.picking:
            self.hex_var.set(to_hex(color, False))
        try:
            self.active_preview.configure(bg=to_hex(color))
        except tk.TclError:
            pass

    def sync_hsv(self):
        ly = self.layer()
        if ly is None:
            return
        h, s, v = rgb_to_hsv_int(ly.colors[self.sel_index])
        self._programmatic = (h, s, v)
        self.h_var.set(h)
        self.s_var.set(s)
        self.v_var.set(v)

    def update_preview(self):
        if self.preview is None or not self.preview.canvas.winfo_exists():
            return
        frames = self.app.visible_frame_indices()
        if not frames:
            self.preview.draw_message("No image loaded")
            return
        if self.frame_idx not in frames:
            self.frame_idx = frames[0]
        self.preview.draw_single(self.frame_idx, labels=False)
        if self.frame_lbl is not None:
            try:
                self.frame_lbl.configure(text="Frame %d / %d" % (frames.index(self.frame_idx) + 1, len(frames)))
            except tk.TclError:
                pass

    def update_preview_soon(self):
        """Debounced preview redraw so slider drags stay smooth (the old HSV debounce)."""
        if self._preview_job:
            self.win.after_cancel(self._preview_job)
        self._preview_job = self.win.after(25, self._run_preview_job)

    def _run_preview_job(self):
        self._preview_job = None
        self.update_preview()

    def step_frame(self, step):
        frames = self.app.visible_frame_indices()
        if not frames:
            return
        pos = frames.index(self.frame_idx) if self.frame_idx in frames else 0
        self.frame_idx = frames[(pos + step) % len(frames)]
        self.update_preview()

    def lift(self):
        if self.win.winfo_exists():
            self.win.lift()
            self.win.focus_force()

    # ----- selection -----
    def select_index(self, i, force=False):
        i = max(0, min(PALETTE_SIZE - 1, int(i)))
        if i == self.sel_index and not force:
            return
        self.sel_index = i
        self.update_picker()
        self.sync_hsv()
        self.snapshot()

    def on_swatch_click(self, i, event, button="left"):
        if self.picking:
            ly = self.layer()
            if ly is not None:
                self.hex_var.set(to_hex(ly.colors[i], False))
            return
        shift = bool(getattr(event, "state", 0) & 0x0001)
        if button == "right":
            # NuAge right click adds or removes an index from the selection
            if i in self.selected:
                self.selected.discard(i)
            else:
                self.selected.add(i)
                self.multi_var.set(True)
        elif self.multi_var.get():
            if shift and self.last_clicked is not None:
                lo, hi = sorted((self.last_clicked, i))
                editable = set(self.editable()) if self.skin != "Simple" else None
                for j in range(lo, hi + 1):
                    if editable is None or j in editable:
                        self.selected.add(j)
            elif i in self.selected:
                self.selected.discard(i)
            else:
                self.selected.add(i)
        else:
            self.selected = {i}
        self.last_clicked = i
        self.update_selection_ui()
        self.select_index(i, force=True)

    def on_multi_toggled(self):
        if not self.multi_var.get() and self.selected:
            keep = sorted(self.selected)[-1]
            self.selected = {keep}
            self.select_index(keep, force=True)
        self.snapshot()
        self.update_selection_ui()

    def select_all(self):
        self.multi_var.set(True)
        self.selected = set(self.editable())
        if self.selected:
            self.last_clicked = min(self.selected)
            self.select_index(self.last_clicked, force=True)
        self.update_selection_ui()

    def clear_selection(self):
        self.selected = set()
        self.last_clicked = None
        self.snapshot()
        self.update_selection_ui()

    def goto_index(self):
        try:
            i = max(0, min(255, int(self.idx_var.get())))
        except ValueError:
            return
        self.selected = (self.selected | {i}) if self.multi_var.get() else {i}
        self.select_index(i, force=True)
        self.update_selection_ui()

    def on_preview_click(self, event):
        hit = self.preview.hit(event) if self.preview else None
        if hit is None:
            return
        found = self.app.pixel_at(*hit)
        if found is None:
            return
        il, pixel = found
        palette = self.app.palette_coloring(il)
        if self.picking:
            self.hex_var.set(to_hex(palette.colors[pixel], False))
            return
        if palette is not self.layer():
            # Clicking another layer's pixel switches the editor to the palette that colors it
            self.target_var.set(self._names()[self.layers.index(palette)])
            self.on_target_changed()
        self.on_swatch_click(pixel, event)

    # ----- editing -----
    def mark_changed(self, indices=None):
        ly = self.layer()
        if ly is None:
            return
        self.dirty.add(id(ly))
        self.app.stats.add("indexes_changed", len(indices) if indices is not None else 1)
        for i in (indices if indices is not None else self.swatches):
            self.redraw_swatch(i)
        self.update_picker()
        self.app.request_redraw()
        self.app.layer_colors_changed(ly)

    def on_hsv_changed(self):
        ly = self.layer()
        if ly is None:
            return
        try:
            h, s, v = int(self.h_var.get()), int(self.s_var.get()), int(self.v_var.get())
        except tk.TclError:
            return
        if getattr(self, "_programmatic", None) == (h, s, v):
            return
        self._programmatic = None
        targets = self.targets()
        key = self.app.key_color
        if len(targets) > 1:
            bh, bs, bv = self.base_hsv
            dh = h - bh
            for i in targets:
                if self.app.is_key(self.base.get(i, ly.colors[i])):
                    continue  # keyed slots are left alone in group edits
                oh, os_, ov = rgb_to_hsv_int(self.base.get(i, ly.colors[i]))
                ns = os_ * s / float(bs) if bs > 1 else os_ + (s - bs)
                nv = ov * v / float(bv) if bv > 1 else ov + (v - bv)
                ly.colors[i] = avoid_key(hsv_int_to_rgb(oh + dh, int(round(ns)), int(round(nv))), key)
        else:
            ly.colors[targets[0]] = avoid_key(hsv_int_to_rgb(h, s, v), key)
        self.mark_changed(targets)

    def apply_color(self, color):
        if self.picking:  # in Pick mode a saved color only loads into the hex box, Apply commits it
            self.hex_var.set(to_hex(color, False))
            return
        ly = self.layer()
        if ly is None:
            return
        targets = self.targets()
        for i in targets:
            ly.colors[i] = tuple(color)
        self.sync_hsv()
        self.snapshot()
        self.mark_changed(targets)

    def apply_hex_entry(self):
        color = parse_hex(self.hex_var.get())
        if color is None:
            messagebox.showwarning("Hex", "Type a color as RRGGBB, for example ff8800.", parent=self.win)
            return
        was_picking = self.picking
        self.picking = False
        self.apply_color(color)
        self.picking = was_picking

    def current_color(self):
        ly = self.layer()
        return ly.colors[self.sel_index] if ly else None

    def toggle_pick(self):
        set_pick_mode(self, not self.picking)
        if self.preview:
            self.preview.canvas.configure(cursor="crosshair" if self.picking else "hand2")
        if not self.picking:
            self.update_picker()

    def open_gradient(self):
        def indices():
            return sorted(self.selected) if self.multi_var.get() and self.selected else self.editable()

        def changed():
            self.sync_hsv()
            self.snapshot()
            self.mark_changed()

        GradientMenu(self.app, self.win, GradientTarget(self.layer, indices, changed, self.step_frame))

    def reset_selected(self):
        ly = self.layer()
        if ly is None:
            return
        if not self.selected:
            messagebox.showinfo("Notice", "No colors selected to reset.", parent=self.win)
            return
        original = self.originals.get(id(ly), ly.loaded_colors)
        for i in self.selected:
            ly.colors[i] = original[i]
        self.sync_hsv()
        self.snapshot()
        self.mark_changed(sorted(self.selected))

    def reset_all(self):
        ly = self.layer()
        if ly is None:
            return
        ly.colors[:] = self.originals.get(id(ly), ly.loaded_colors)
        self.sync_hsv()
        self.snapshot()
        self.mark_changed()

    def on_target_changed(self):
        self.selected = set()
        self.last_clicked = None
        self.app.select_layer(self.layers.index(self.layer()))
        self.build()

    def save_palette(self):
        ly = self.layer()
        if ly is None:
            return
        colors = None
        if self.skin == "Advanced" and is_custom_sort(self.app):
            use_sorted = self.app.store.get("save_sorted_choice")
            if use_sorted is None:
                use_sorted = ask_save_sorted(self.app, self.win)
            if use_sorted is None:
                self.lift()
                return
            if use_sorted:
                # The shown order goes first; the indexes the image doesn't use follow in their usual order
                shown = self.sorted_editable()
                rest = [i for i in range(PALETTE_SIZE) if i not in set(shown)]
                colors = [ly.colors[i] for i in shown + rest]
        if self.app.save_layer_palette(ly, parent=self.win, colors=colors):
            self.dirty.discard(id(ly))
            self.originals[id(ly)] = list(ly.colors)
        self.lift()

    def load_into_layer(self):
        ly = self.layer()
        if ly is None:
            return
        path = filedialog.askopenfilename(title="Load Palette", filetypes=PALETTE_TYPES, parent=self.win)
        self.lift()
        if not path:
            return
        try:
            ly.colors[:] = pad256(read_palette(path))
        except Exception as exc:
            messagebox.showerror("Load Palette", str(exc), parent=self.win)
            return
        self.sync_hsv()
        self.snapshot()
        self.mark_changed()
