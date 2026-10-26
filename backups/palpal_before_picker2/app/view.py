"""PalPalPal main window: rendering and the preview."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..ui.docs_viewer import open_doc
from ..core.colors import bg_fill, flat_palette, to_hex
from ..core.images import blend_color, blend_images
from ..ui.theme import Theme
from ..preview.canvas import ALIGNMENTS
from ..ui.dialogs import AllModeWarning


class AppViewMixin:
    """Rendering the layer stack and everything the preview canvas does."""

    # ----- rendering -----
    def transform(self, img):
        if self.flip:
            img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        for _ in range(self.rotation % 4):
            img = img.transpose(Image.Transpose.ROTATE_270)
        return img

    def transformed_size(self):
        w, h = self.canvas_size()
        return (h, w) if self.rotation % 2 else (w, h)

    def untransform_point(self, x, y):
        w, h = self.canvas_size()
        sizes = []
        cw, ch = w, h
        for _ in range(self.rotation % 4):
            sizes.append((cw, ch))
            cw, ch = ch, cw
        for pw, ph in reversed(sizes):
            # A clockwise turn sends (x, y) in pw x ph to (ph - 1 - y, x)
            x, y = y, ph - 1 - x
        if self.flip:
            x = w - 1 - x
        return max(0, min(w - 1, x)), max(0, min(h - 1, y))

    def effective_colors(self, il, t=None):
        """The colors an image layer is drawn with: its own palette, then every ticked stand-alone palette
        above it (up to the next image) laid on with that palette's blend mode and opacity."""
        own = il.palette if t is None else il.palette_at(t)
        colors = list(own.colors if own.active else own.loaded_colors)
        for entry in self.stacked_palettes(il):
            if entry.blend == "Normal" and entry.opacity >= 1.0:
                colors = list(entry.colors)
            else:
                colors = [blend_color(colors[i], entry.colors[i], entry.blend, entry.opacity)
                          for i in range(PALETTE_SIZE)]
        return colors

    def render_layer(self, il, t):
        """One image layer at timeline frame t, colored by its palette, keyed pixels see-through."""
        frame = il.frame_at(t)
        palette = self.effective_colors(il, t)
        img = frame.image.copy()
        img.putpalette(flat_palette(palette))
        rgba = img.convert("RGBA")
        keys = self.key_indices(frame, palette)
        lut = [0 if i in keys else 255 for i in range(256)]
        alpha = Image.frombytes("L", frame.image.size, frame.image.tobytes()).point(lut)
        if il.opacity < 1.0:
            alpha = alpha.point(lambda a: int(a * il.opacity))
        rgba.putalpha(alpha)
        return rgba

    def layer_canvas(self, il, t, background=False):
        """A layer drawn onto a project-sized canvas (used by the 3D view)."""
        size = self.canvas_size()
        base = Image.new("RGBA", size, bg_fill(self.bg_color) if background else (0, 0, 0, 0))
        base.alpha_composite(self.render_layer(il, t))
        return base

    def composite(self, t, background=True):
        """Every visible image layer stacked bottom to top, like layers in a paint program."""
        size = self.canvas_size()
        base = Image.new("RGBA", size, bg_fill(self.bg_color) if background else (0, 0, 0, 0))
        for il in self.visible_image_layers():
            layer = Image.new("RGBA", size, (0, 0, 0, 0))
            layer.alpha_composite(self.render_layer(il, t))
            if il.blend == "Normal":
                base.alpha_composite(layer)
            else:
                mixed = blend_images(base.convert("RGB"), layer.convert("RGB"), il.blend).convert("RGBA")
                base = Image.composite(mixed, base, layer.getchannel("A"))
        return base

    def render(self, t, scale=1.0, background=True):
        rgba = self.transform(self.composite(t, background))
        if scale != 1.0:
            size = (max(1, int(rgba.width * scale)), max(1, int(rgba.height * scale)))
            rgba = rgba.resize(size, Image.Resampling.NEAREST)
        return rgba

    def pixel_at(self, t, x, y):
        """(image layer, palette index) of the top visible, non-see-through pixel at x, y."""
        for il in reversed(self.visible_image_layers()):
            frame = il.frame_at(t)
            w, h = frame.image.size
            if x < w and y < h:
                idx = frame.image.getpixel((x, y))
                if idx not in self.key_indices(frame, self.effective_colors(il)):
                    return il, idx
        return None

    def visible_frame_indices(self):
        return [t for t in range(self.frame_count()) if t not in self.hidden_frames]

    def request_redraw(self):
        if self._redraw_job:
            self.master.after_cancel(self._redraw_job)
        self._redraw_job = self.master.after(25, self.update_image_display)

    def custom_range(self):
        """(start, end) frame indexes for Custom preview, from the 1-based settings."""
        last = self.frame_count() - 1
        start = max(0, min(last, int(self.store.get("custom_start") or 1) - 1))
        end = int(self.store.get("custom_end") or 0) - 1
        end = last if end < start or end > last else end
        return start, end

    def custom_frame_indices(self):
        """The page Custom preview shows: N visible frames from custom_pos within the range."""
        start, end = self.custom_range()
        pool = [t for t in range(start, end + 1) if t not in self.hidden_frames]
        if not pool:
            return []
        count = max(1, int(self.store.get("custom_count") or 1))
        if self.custom_pos not in pool:
            self.custom_pos = pool[0]
        first = pool.index(self.custom_pos)
        return [pool[(first + k) % len(pool)] for k in range(min(count, len(pool)))]

    def update_image_display(self):
        self._redraw_job = None
        if self.view_var.get() == "No Preview":
            self.update_nav_label()
            return
        frames = self.visible_frame_indices()
        if frames and self.current_frame not in frames:
            self.current_frame = frames[0]
        labels = bool(self.store.get("show_frame_labels"))
        mode = self.preview_var.get()
        if not self.stack:
            self.view.draw_message(self.START_MESSAGE, [("New Project", self.new_project),
                                                        ("Open Project", self.open_project),
                                                        ("Read the Manual", lambda: open_doc(self, "manual"))])
        elif not frames:
            self.view.draw_message("No image in this project yet" if not self.image_layers()
                                   else "All frames are hidden")
        elif mode == "all":
            self.view.draw_grid(frames, labels, self.selected_frames)
        elif mode == "custom":
            self.view.draw_grid(self.custom_frame_indices(), labels, self.selected_frames)
        else:
            self.view.draw_single(self.current_frame, labels)
        self.update_nav_label()
        self.refresh_align_button()

    def update_nav_label(self):
        frames = self.visible_frame_indices()
        if not frames:
            text = "No frames"
        elif self.preview_var.get() == "custom":
            shown = self.custom_frame_indices()
            text = ("Frames " + ", ".join(str(i + 1) for i in shown)) if shown else "No frames"
        else:
            text = "Frame %d / %d" % (frames.index(self.current_frame) + 1, len(frames))
        for lbl in (self.frame_lbl, getattr(self, "compact_frame_lbl", None)):
            if lbl is not None:
                lbl.configure(text=text)
        self.update_timeline()

    def alignment_key(self):
        return "%s|%s" % (self.view_var.get(), self.preview_var.get())

    def current_alignment(self):
        return (self.store.get("alignments") or {}).get(self.alignment_key(), "c")

    def set_alignment(self, anchor):
        aligns = dict(self.store.get("alignments") or {})
        aligns[self.alignment_key()] = anchor
        self.store.set("alignments", aligns)
        self.refresh_align_button()
        self.request_redraw()

    def refresh_align_button(self):
        anchor = self.current_alignment()
        self.align_var.set(anchor)
        self.align_btn.configure(text="Align: " + next(l for l, a in ALIGNMENTS if a == anchor))

    def on_preview_mode_change(self):
        if (self.preview_var.get() == "all" and self.frame_count() > 50 and self.store.get("all_mode_warning")
                and not AllModeWarning(self).show()):
            self.preview_var.set("single")
        self.request_redraw()

    def cycle_zoom(self, delta, var, redraw):
        self._zoom_acc += delta
        if abs(self._zoom_acc) < 120:
            return
        step = 1 if self._zoom_acc > 0 else -1
        self._zoom_acc = 0
        cur = ZOOM_LEVELS.index(var.get()) if var.get() in ZOOM_LEVELS else 0
        new = max(0, min(len(ZOOM_LEVELS) - 1, cur + step))
        if new != cur:
            var.set(ZOOM_LEVELS[new])
            redraw()

    # ----- canvas interaction -----
    def on_canvas_click(self, event):
        if self.alt_click_frame(event):
            return
        hit = self.view.hit(event)
        if hit is None:
            return
        t, x, y = hit
        if t != self.current_frame:
            self.current_frame = t
            self.request_redraw()
        found = self.pixel_at(t, x, y)
        if found is None:
            return
        il, pixel = found
        palette = self.palette_coloring(il)
        if self.compact.picking:
            self.compact.hex_var.set(to_hex(palette.colors[pixel], False))
            return
        # Clicking a layer's pixel selects the palette that colors it (the old click-to-identify)
        index = self.layers.index(palette)
        if index != self.selected_layer:
            self.select_layer(index)
        if self.view_var.get() == "Small Preview" and pixel in self.compact.swatches:
            self.compact.toggle(pixel)

    def on_canvas_right_click(self, event):
        hit = self.view.hit(event)
        if hit is None:
            return
        idx = hit[0]
        menu = tk.Menu(self.master, tearoff=0)
        menu.add_command(label="Set as Current Frame", command=lambda: self.set_current_frame(idx))
        menu.add_command(label="Switch to Single Preview", command=lambda: self.view_single_frame(idx))
        menu.add_command(label="Deselect Frame" if idx in self.selected_frames else "Select Frame",
                         command=lambda: self.toggle_frame_selection(idx))
        menu.add_command(label="Flip This Frame's Palette (F)", command=lambda: (self.set_current_frame(idx),
                                                                      self.flip_selected_frame()))
        menu.add_separator()
        menu.add_command(label="Hide This Frame", command=lambda: self.hide_frames({idx}))
        menu.add_command(label="Hide Selected Frames (%d)" % len(self.selected_frames),
                         state="normal" if self.selected_frames else "disabled",
                         command=lambda: self.hide_frames(set(self.selected_frames)))
        Theme.apply(self, menu)
        menu.tk_popup(event.x_root, event.y_root)

    def set_current_frame(self, idx):
        self.current_frame = self.custom_pos = idx
        self.request_redraw()

    def view_single_frame(self, idx):
        self.current_frame = idx
        self.preview_var.set("single")
        self.request_redraw()

    def toggle_frame_selection(self, idx):
        self.selected_frames ^= {idx}
        self.request_redraw()

    def step_frame(self, step):
        frames = self.visible_frame_indices()
        if not frames:
            return
        if self.preview_var.get() == "custom":
            # Custom preview moves a whole page of frames at a time, skipping hidden ones
            start, end = self.custom_range()
            pool = [t for t in frames if start <= t <= end]
            if pool:
                count = max(1, int(self.store.get("custom_count") or 1))
                pos = pool.index(self.custom_pos) if self.custom_pos in pool else 0
                self.custom_pos = pool[(pos + step * count) % len(pool)]
                self.current_frame = self.custom_pos
        else:
            pos = frames.index(self.current_frame) if self.current_frame in frames else 0
            self.current_frame = frames[(pos + step) % len(frames)]
        self.request_redraw()

    # ----- frame visibility (with undo, like the old frame tools) -----
    def save_visibility_state(self):
        self.visibility_history.append((set(self.hidden_frames), self.flip, self.rotation))
        del self.visibility_history[:-50]

    def visibility_changed(self):
        self.mark_dirty()
        self.update_compact_palette_editor()
        self.request_redraw()
        if self.switcher and self.switcher.win.winfo_exists():
            self.switcher.update_preview()

    def hide_frames(self, indices):
        if not indices:
            return
        self.save_visibility_state()
        self.hidden_frames |= set(indices)
        self.selected_frames -= set(indices)
        self.visibility_changed()

    def toggle_all_frames_visibility(self):
        """Hide every frame but the current one, or show them all again."""
        count = self.frame_count()
        if not count:
            return
        self.save_visibility_state()
        others = {t for t in range(count) if t != self.current_frame}
        self.hidden_frames = set() if others <= self.hidden_frames else others
        self.visibility_changed()

    def undo_frame_visibility(self):
        if not self.visibility_history:
            messagebox.showinfo("Undo", "No more undo steps available")
            return
        self.hidden_frames, self.flip, self.rotation = self.visibility_history.pop()
        self.visibility_changed()

    def toggle_flip(self):
        self.save_visibility_state()
        self.flip = not self.flip
        self.visibility_changed()

    def rotate_preview(self):
        self.save_visibility_state()
        self.rotation = (self.rotation + 1) % 4
        self.visibility_changed()
