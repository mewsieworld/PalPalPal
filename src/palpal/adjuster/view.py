"""Img2img Palette Swap: the canvas (side by side, flip / rotate, eyedropper)."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.storage import export_dir
from ..core.colors import bg_fill, color_dist, hsl_to_rgb, luminosity, rgb_to_hsl, to_hex
from ..core.images import Frame, ImageLayer, convert_image, sample_unique_colors
from ..ui.theme import Theme, Tooltip, center_on
from ..preview.canvas import unxform_point, xform_image
from ..ui.dialogs import ChoiceDialog
from .mapper import MapperMixin


class AdjusterViewMixin:
    """Img2img Palette Swap: the canvas (side by side, flip / rotate, eyedropper)."""

    def schedule(self):
        if self._job:
            self.win.after_cancel(self._job)
        self._job = self.win.after(60, self.redraw)

    def redraw(self):
        self._job = None
        if self.source is None or self.reference is None:
            self.show_prompt()
            return
        source = self.apply_filters(self.recolor())
        kinds = ["source", "reference"] if self.view_mode == "both" else [self.view_mode]
        self.draw_views([(k, source if k == "source" else self.reference) for k in kinds])

    def draw_image(self, img, label=None):
        self.draw_views([("source", img)], label)

    def draw_views(self, views, label=None):
        """One picture, or two side by side (source on the left), each with its own flip / rotation."""
        c = self.canvas
        c.delete("all")
        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        slot = cw / float(len(views))
        self.regions, self.photos = [], []
        for n, (kind, img) in enumerate(views):
            flip, rot = self.view_xform[kind]
            shown_img = xform_image(img, flip, rot)
            fit = min(slot / float(shown_img.width), ch / float(shown_img.height))
            scale = fit * self.zoom
            shown = shown_img.resize((max(1, int(shown_img.width * scale)), max(1, int(shown_img.height * scale))),
                                     Image.Resampling.NEAREST)
            backdrop = Image.new("RGBA", shown.size, bg_fill(self.app.bg_color))
            backdrop.alpha_composite(shown)
            photo = ImageTk.PhotoImage(backdrop)
            self.photos.append(photo)
            ox, oy = int(n * slot + (slot - shown.width) // 2), (ch - shown.height) // 2
            c.create_image(ox, oy, image=photo, anchor="nw")
            self.regions.append((kind, ox, oy, scale, img.size, shown.width, shown.height))
            if kind == "source":
                self.img_origin = (ox, oy, scale)
            if len(views) > 1 and kind == self.active_view and self.per_image.get():
                c.create_rectangle(ox - 2, oy - 2, ox + shown.width + 1, oy + shown.height + 1, outline="#7a86ff", width=2)
        self.photo = self.photos[0]
        if label:
            c.create_text(8, 8, anchor="nw", text=label, fill="#888888", font=("Arial", 9, "bold"))
        if len(views) > 1:
            self.per_image_box.pack(pady=(2, 0))
        else:
            self.per_image_box.pack_forget()

    def _thumb_click(self, choose):
        # Wait a moment: a double click on the thumbnail switches the view instead of opening a file
        if self._thumb_job:
            self.win.after_cancel(self._thumb_job)
        self._thumb_job = self.win.after(400, lambda: (setattr(self, "_thumb_job", None), choose()))

    def _thumb_view(self, mode):
        if self._thumb_job:
            self.win.after_cancel(self._thumb_job)
            self._thumb_job = None
        if mode != "both" and (self.source if mode == "source" else self.reference) is None:
            return
        self.view_mode = mode
        if mode != "both":
            self.active_view = mode
        self.log("Showing %s." % {"source": "the source (live result)", "reference": "the reference",
                                  "both": "source and reference side by side"}[mode])
        self.schedule()

    def view_transform(self, flip=False, rotate=False):
        """Flip / Rotate the view: the picture on screen, or with both shown, the clicked one or both."""
        if self.view_mode == "both":
            kinds = [self.active_view] if self.per_image.get() else ["source", "reference"]
        else:
            kinds = [self.view_mode]
        for kind in kinds:
            x = self.view_xform[kind]
            if flip:
                x[0] = not x[0]
            if rotate:
                x[1] = (x[1] + 1) % 4
        self.schedule()

    def region_at(self, event):
        """(kind, original image pixel) under a canvas click, or None."""
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for kind, ox, oy, scale, size, sw, sh in self.regions:
            if ox <= cx < ox + sw and oy <= cy < oy + sh:
                flip, rot = self.view_xform[kind]
                x, y = unxform_point(int((cx - ox) / scale), int((cy - oy) / scale), size, flip, rot)
                return kind, max(0, min(size[0] - 1, x)), max(0, min(size[1] - 1, y))
        return None

    def on_wheel(self, event):
        self.zoom = max(0.25, min(16.0, self.zoom * (1.25 if event.delta > 0 else 0.8)))
        self.schedule()

    # ----- eyedropper -----
    def toggle_eyedropper(self):
        self.eyedropper = not self.eyedropper
        self.eye_btn.configure(relief="sunken" if self.eyedropper else "raised")
        self.canvas.configure(cursor="crosshair" if self.eyedropper else "")
        self.log("Eyedropper %s." % ("activated" if self.eyedropper else "deactivated"))

    def on_canvas_click(self, event):
        hit = self.region_at(event)
        if hit is not None and self.view_mode == "both" and hit[0] != self.active_view:
            self.active_view = hit[0]   # the picture Flip / Rotate act on when "per image" is ticked
            self.schedule()
        if not self.eyedropper or self.source is None or not self.source_palette:
            return
        if hit is None:
            self.log("Click outside image boundaries.")
            return
        kind, x, y = hit
        if kind == "reference":
            r, g, b, a = self.reference.getpixel((x, y))
            if self.target_palette:
                self.select_target(min(range(len(self.target_palette)),
                                       key=lambda i: color_dist((r, g, b), self.target_palette[i])))
            return
        r, g, b, a = self.source.getpixel((x, y))
        match = min(range(len(self.source_palette)), key=lambda i: color_dist((r, g, b), self.source_palette[i]))
        self.selected_source = match
        self.refine_lbl.configure(text="Selected source index: #%d" % match)
        self.refine_var.set(0)
        mapped = self.color_map.get(match, self.source_palette[match])
        if self.target_palette:
            self.select_target(min(range(len(self.target_palette)),
                                   key=lambda i: color_dist(mapped, self.target_palette[i])), quiet=True)
        self.log("Eyedropper: pixel (%d, %d) %s -> source index #%d, now %s, closest target #%s."
                 % (x, y, to_hex((r, g, b)), match, to_hex(mapped), self.selected_target))
        self.show_hover(event, (r, g, b), match)
        self.refresh_mapper()

    def show_hover(self, event, color, match):
        """Eyedropper details in a small card you can dismiss."""
        if self.hover is not None and self.hover.winfo_exists():
            self.hover.destroy()
        self.hover = tk.Frame(self.canvas, relief="solid", bd=1)
        sw = tk.Label(self.hover, text="  ", bg=to_hex(color), width=2)
        sw._cp_keep = True
        sw.pack(side="left", padx=4, pady=4)
        target = to_hex(self.target_palette[self.selected_target]) if self.selected_target is not None else "---"
        tk.Label(self.hover, text="Picked %s\nSource #%d  ->  Target %s" % (to_hex(color), match, target),
                 justify="left", font=("Arial", 8)).pack(side="left", padx=(0, 4))
        tk.Button(self.hover, text="✕", relief="flat", command=self.hover.destroy).pack(side="left", anchor="n")
        Theme.apply(self.app, self.hover)
        self.canvas.create_window(event.x + 12, event.y + 12, window=self.hover, anchor="nw")
