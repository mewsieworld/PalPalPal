"""Mass Frame Editor: the frame canvas, strip, zoom and eyedropper."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import bg_fill, to_hex
from ..ui.widgets import draw_swatch
from .constants import MASS_ZOOMS


class MassEditorCanvasMixin:
    """Mass Frame Editor: the frame canvas, strip, zoom and eyedropper."""

    # ----- drawing -----
    def frame_image(self, t, scale):
        img = Image.new("RGBA", self.layer.size, bg_fill(self.app.bg_color))
        img.alpha_composite(self.app.render_layer(self.layer, t))
        if scale != 1:
            img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.Resampling.NEAREST)
        return img

    def redraw(self):
        if not self.win.winfo_exists():
            return
        c = self.canvas
        c.delete("all")
        self.photos = []
        if self.layer is None:
            c.create_text(max(1, c.winfo_width()) // 2, max(1, c.winfo_height()) // 2, fill="#888888",
                          text="Select an image layer (or a palette over one) first.")
            return
        img = self.frame_image(self.frame, self.zoom)
        photo = ImageTk.PhotoImage(img)
        self.photos.append(photo)
        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        self.img_xy = (max(0, (cw - img.width) // 2), max(0, (ch - img.height) // 2))
        c.create_image(*self.img_xy, image=photo, anchor="nw")
        c.configure(scrollregion=(0, 0, max(cw, img.width), max(ch, img.height)))
        self.zoom_lbl.configure(text="%d%%" % (self.zoom * 100))
        self.frame_lbl.configure(text="%d/%d" % (self.frame + 1, len(self.layer.frames)))
        self.draw_strip()
        self.refresh_boxes()
        self.render_mappings()

    def draw_strip(self):
        s = self.strip
        s.delete("all")
        if self.layer is None:
            return
        try:
            count = max(1, min(32, int(self.strip_count.get())))
        except ValueError:
            count = 3
        self.strip_items = []
        self.strip_photos = []
        x = 4
        for k in range(min(count, len(self.layer.frames))):
            t = (self.frame + k) % len(self.layer.frames)
            img = self.frame_image(t, 1)
            img.thumbnail((90, 90), Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(img)
            self.strip_photos.append(photo)
            s.create_rectangle(x - 2, 2, x + 94, 108, outline="#7a86ff" if k == 0 else "#666666", width=2 if k == 0 else 1)
            s.create_image(x + 47, 48, image=photo)
            s.create_text(x + 47, 100, text="Frame %d" % (t + 1), fill="#888888", font=("Arial", 8))
            self.strip_items.append((x - 2, x + 94, t))
            x += 100

    def refresh_boxes(self):
        if self.palette is None:
            return
        chosen = self.multi if self.multi_on else ({self.selected} if self.selected is not None else set())
        for idx, sw in self.boxes.items():
            draw_swatch(self.app, sw, self.palette.colors[idx], idx in chosen)

    def render_mappings(self):
        if getattr(self, "_typing_mappings", False):
            return   # don't rewrite the box under the cursor while it's being edited
        self.map_text.delete("1.0", "end")
        if self.palette is None:
            return
        lines = ["%d=%s" % (i, to_hex(self.palette.colors[i]).upper())
                 for i in range(PALETTE_SIZE) if tuple(self.palette.colors[i]) != tuple(self.palette.loaded_colors[i])]
        self.map_text.insert("1.0", "\n".join(lines) if lines else "/* Your palette mappings will appear here. */")

    # ----- frames, zoom, pan -----
    def change_frame(self, step):
        if self.layer:
            self.frame = (self.frame + step) % len(self.layer.frames)
            self.redraw()

    def change_zoom(self, step):
        pos = MASS_ZOOMS.index(self.zoom) if self.zoom in MASS_ZOOMS else 1
        self.zoom = MASS_ZOOMS[max(0, min(len(MASS_ZOOMS) - 1, pos + step))]
        self.redraw()

    def reset_position(self):
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self.redraw()

    def on_strip_click(self, event):
        for x0, x1, t in getattr(self, "strip_items", []):
            if x0 <= event.x <= x1:
                self.frame = t
                self.redraw()
                return

    def on_press(self, event):
        self._press = (event.x, event.y, False)
        self.canvas.scan_mark(event.x, event.y)

    def on_drag(self, event):
        x, y, moved = self._press
        if abs(event.x - x) > 3 or abs(event.y - y) > 3:
            self._press = (x, y, True)
            self.canvas.scan_dragto(event.x, event.y, gain=1)

    def on_release(self, event):
        if self.eyedropper and not self._press[2]:
            hit = self.pixel_under(event)
            if hit is None:
                messagebox.showinfo("Eyedropper", "That spot is see-through. Pick a colored pixel.", parent=self.win)
            else:
                self.select_index(hit, event)
            self.toggle_eyedropper()

    def pixel_under(self, event):
        if self.layer is None:
            return None
        frame = self.layer.frames[self.frame]
        x = int((self.canvas.canvasx(event.x) - self.img_xy[0]) / self.zoom)
        y = int((self.canvas.canvasy(event.y) - self.img_xy[1]) / self.zoom)
        if not (0 <= x < frame.image.width and 0 <= y < frame.image.height):
            return None
        idx = frame.image.getpixel((x, y))
        if idx in self.app.key_indices(frame, self.app.effective_colors(self.layer)):
            return None
        return idx

    def on_move(self, event):
        if not self.eyedropper:
            return
        idx = self.pixel_under(event)
        for i, sw in self.boxes.items():
            sw.configure(highlightthickness=2 if i == idx else 0, highlightbackground="#ffcc00")
        if idx is None:
            self.read_lbl.configure(text="Color read: TRANSPARENT")
            self.live_lbl.configure(text="Live index: --")
        else:
            self.read_lbl.configure(text="Color read: %s" % to_hex(self.palette.colors[idx]).upper())
            self.live_lbl.configure(text="Live index: %d" % idx)

    def toggle_eyedropper(self):
        self.eyedropper = not self.eyedropper
        self.eye_btn.configure(text="🎨 Eyedropper ON (click to confirm)" if self.eyedropper else "🎨 Eyedropper",
                               relief="sunken" if self.eyedropper else "raised")
        self.canvas.configure(cursor="crosshair" if self.eyedropper else "fleur")
        if not self.eyedropper:
            for sw in self.boxes.values():
                sw.configure(highlightthickness=0)
