"""Mass Frame Editor: selecting and editing colors, mappings and export."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import export_dir
from ..core.colors import avoid_key, bg_fill, flat_palette, hsl_to_rgb, parse_hex, rgb_to_hsl, to_hex
from ..ui.theme import Theme, center_on
from ..ui.widgets import draw_swatch, swatch_grid
from .constants import FRAME_EXPORT_FORMATS


class MassEditorEditMixin:
    """Mass Frame Editor: selecting and editing colors, mappings and export."""

    # ----- selection -----
    def on_box_click(self, idx, event):
        self.select_index(idx, event)

    def toggle_multi(self):
        self.multi_on = not self.multi_on
        self.multi_btn.configure(text="Disable Multiselect" if self.multi_on else "Enable Multiselect")
        self.multi = set()
        self.last_clicked = None
        self.update_multi_label()
        self.refresh_boxes()

    def update_multi_label(self):
        self.multi_lbl.configure(text="Multiselect: %s | Selected: %d" % ("ON" if self.multi_on else "OFF",
                                                                          len(self.multi)))

    def select_index(self, idx, event=None):
        shift = bool(getattr(event, "state", 0) & 0x0001)
        if self.multi_on:
            if shift and self.last_clicked is not None:
                lo, hi = sorted((self.last_clicked, idx))
                self.multi |= {i for i in self.indices if lo <= i <= hi}
            elif idx in self.multi:
                self.multi.discard(idx)
            else:
                self.multi.add(idx)
            self.last_clicked = idx
            self.update_multi_label()
            # Changes are measured from the colors as they are right now
            self.base_values = {i: rgb_to_hsl(self.palette.colors[i]) for i in self.multi}
            if self.multi:
                first = sorted(self.multi)[0]
                self.base_hsl = rgb_to_hsl(self.palette.colors[first])
                self.show_target(self.palette.colors[first])
        else:
            self.selected = idx
            self.confirmed_lbl.configure(text="Confirmed index: %d" % idx)
            self.original_lbl.configure(text="Original color: %s" % to_hex(self.palette.loaded_colors[idx]).upper())
            self.show_target(self.palette.colors[idx])
        self.refresh_boxes()

    # ----- target color -----
    def show_target(self, color):
        self._lock = True
        h, s, l = rgb_to_hsl(color)
        self.h_var.set(round(h))
        self.s_var.set(round(s, 1))
        self.l_var.set(round(l, 1))
        self._lock = False
        self.show_values(color)

    def show_values(self, color):
        self.hue_value.configure(text="%d°" % round(self.h_var.get()))
        self.sat_value.configure(text="%.1f%%" % self.s_var.get())
        self.light_value.configure(text="%.1f%%" % self.l_var.get())
        self.hex_var.set(to_hex(color, False).upper())
        self.target_swatch.configure(bg=to_hex(color), activebackground=to_hex(color))

    def on_hsl(self):
        if self._lock:
            return
        color = hsl_to_rgb(self.h_var.get(), self.s_var.get(), self.l_var.get())
        self.show_values(color)
        self.commit(color)

    def on_hex(self):
        color = parse_hex(self.hex_var.get())
        if color is None:
            messagebox.showwarning("Hex", "Type a color as RRGGBB, for example ff00ff.", parent=self.win)
            return
        self.show_target(color)
        self.commit(color)

    def choose_color(self):
        result = colorchooser.askcolor(color=to_hex(parse_hex(self.hex_var.get()) or (255, 0, 255)),
                                       title="Target color", parent=self.win)
        if result and result[0]:
            color = tuple(int(v) for v in result[0])
            self.show_target(color)
            self.commit(color)

    def protected_indices(self, target):
        """Near black or white, keep some colors from collapsing into the same shade (as the original did)."""
        protected = set()
        if not (all(v < 30 for v in target) or all(v > 225 for v in target)):
            return protected
        for i in self.multi:
            c = self.palette.colors[i]
            if math.sqrt(sum((c[k] - target[k]) ** 2 for k in range(3))) < 100:
                protected.add(i)
        if len(self.multi) - len(protected) > 3:
            for i in sorted(self.multi):
                if len(protected) >= len(self.multi) // 2:
                    break
                protected.add(i)
        return protected

    def commit(self, color):
        """Live mapping: the change goes straight onto the palette, so every frame updates."""
        if self.palette is None:
            return
        key = self.app.key_color
        if self.multi_on:
            if not self.multi:
                return
            th, ts, tl = rgb_to_hsl(color)
            bh, bs, bl = self.base_hsl
            protected = self.protected_indices(color)
            for i in self.multi:
                if i in protected or i not in self.base_values:
                    continue
                h, s, l = self.base_values[i]
                self.palette.colors[i] = avoid_key(hsl_to_rgb(h + th - bh, s + ts - bs, l + tl - bl), key)
            if protected:
                self.read_lbl.configure(text="Protected %d colors from becoming identical" % len(protected))
        else:
            if self.selected is None:
                return
            self.palette.colors[self.selected] = avoid_key(color, key)
        self.app.stats.add("indexes_changed")
        self.app.layer_colors_changed(self.palette)
        self.app.request_redraw()
        self.redraw()

    # ----- output -----
    def copy_mappings(self):
        self.win.clipboard_clear()
        self.win.clipboard_append(self.map_text.get("1.0", "end").strip())

    def reset_all(self):
        if self.palette is None:
            return
        self.palette.colors[:] = self.palette.loaded_colors
        self.app.layer_colors_changed(self.palette)
        self.app.request_redraw()
        self.redraw()

    def export_frames(self, fmt):
        if self.layer is None:
            return
        self.app.store.set("mass_export_format", {f: label for label, f in FRAME_EXPORT_FORMATS}[fmt])
        name = "".join(ch if ch.isalnum() or ch in "-_ " else "_" for ch in self.layer.name)
        if fmt == "gif":
            path = filedialog.asksaveasfilename(title="Export animation", defaultextension=".gif",
                                                filetypes=[("GIF", "*.gif")], initialdir=export_dir("images"),
                                                initialfile=name, parent=self.win)
            if not path:
                return
            frames = [self.indexed_frame(n) for n in range(len(self.layer.frames))]
            frames[0].save(path, save_all=True, append_images=frames[1:], loop=0,
                           duration=int(1000 / ANIMATION_FPS), disposal=2)
            messagebox.showinfo("Export Frames", "Exported %d frames to\n%s" % (len(frames), path), parent=self.win)
            return
        folder = filedialog.askdirectory(title="Export frames to...", initialdir=export_dir("images"), parent=self.win)
        if not folder:
            return
        ext = {"bmp8": "bmp", "bmp24": "bmp"}.get(fmt, fmt)
        for n in range(len(self.layer.frames)):
            path = os.path.join(folder, "%s_%03d.%s" % (name, n + 1, ext))
            if fmt in ("png", "webp", "tga", "tiff"):
                self.app.render_layer(self.layer, n).save(path)   # keeps transparency
            elif fmt in ("bmp8", "pcx"):
                self.indexed_frame(n).save(path)
            else:
                self.frame_image(n, 1).convert("RGB").save(path)
        messagebox.showinfo("Export Frames", "Exported %d frames to\n%s" % (len(self.layer.frames), folder),
                            parent=self.win)

    def indexed_frame(self, n):
        """Frame n as a 256-color image with the colors it is shown with."""
        img = self.layer.frames[n].image.copy()
        img.putpalette(flat_palette(self.app.effective_colors(self.layer, n)))
        return img
