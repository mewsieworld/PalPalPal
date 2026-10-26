"""PalPalPal main window: selecting frames on the canvas (Alt+click, drag a box) and F to flip (reverse) a
frame's palette."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.images import ImageLayer

ALT_MASK = 0x20000   # Tk's Alt modifier bit on Windows
BAND_TAG = "frame_band"


class AppFrameSelectMixin:
    """In the All / Custom grids: Alt+click adds or removes a frame from the selection, and dragging a box
    selects every frame it touches (hold Alt to add to the selection). F reverses the selected layer's palette
    on that frame."""

    # ----- Alt+click -----
    def alt_click_frame(self, event):
        """Returns True when the click was an Alt+click on a frame (and was handled)."""
        if not (event.state & ALT_MASK) or not self.view.is_grid:
            return False
        hit = self.view.hit(event)
        if hit is not None:
            self.toggle_frame_selection(hit[0])
        return True

    # ----- drag a box -----
    def band_start(self, event):
        c = self.canvas
        self._band = (c.canvasx(event.x), c.canvasy(event.y), bool(event.state & ALT_MASK))
        c.delete(BAND_TAG)

    def band_move(self, event):
        if not getattr(self, "_band", None):
            return
        c = self.canvas
        x0, y0, _add = self._band
        x1, y1 = c.canvasx(event.x), c.canvasy(event.y)
        c.delete(BAND_TAG)
        c.create_rectangle(x0, y0, x1, y1, outline="#7a86ff", dash=(4, 3), width=2, tags=BAND_TAG)

    def band_end(self, event):
        band = getattr(self, "_band", None)
        self._band = None
        c = self.canvas
        c.delete(BAND_TAG)
        if not band or event is None:
            return
        x0, y0, add = band
        x1, y1 = c.canvasx(event.x), c.canvasy(event.y)
        left, right = sorted((x0, x1))
        top, bottom = sorted((y0, y1))
        picked = {t for t, fx, fy, _scale, fw, fh in self.view.placements
                  if fx < right and fx + fw > left and fy < bottom and fy + fh > top}
        self.selected_frames = (self.selected_frames | picked) if add else picked
        self.request_redraw()

    # ----- F: flip the palette -----
    def flip_selected_frame(self):
        """Reverse the color order of the palette that colors the selected layer on this frame (or on every
        selected frame in a grid). Only the slots the image uses are reversed (the key color stays put), so
        the picture's first color and last color trade places, and so on."""
        entry = self.entry_of(self.selected_palette())
        il = entry if isinstance(entry, ImageLayer) else self.target_image_layer()
        if il is None:
            return
        frames = sorted(self.selected_frames) if self.selected_frames and self.view.is_grid else [self.current_frame]
        done = set()
        for t in frames:
            over = self.stacked_palettes(il)
            palette = over[-1] if over else il.palette_at(t)   # a per-frame palette when they're separated
            if id(palette) in done:
                continue   # frames sharing one palette flip it once
            done.add(id(palette))
            frame = il.frame_at(t)
            keys = self.key_indices(frame, palette.colors)
            used = sorted(i for f in il.frames for i in f.used_indices() if i not in keys)
            used = sorted(set(used))
            colors = [palette.colors[i] for i in used]
            for i, c in zip(used, reversed(colors)):
                palette.colors[i] = c
            self.layer_colors_changed(palette)
        self.compact.snapshot()
        self.refresh_layers_box()
        self.request_redraw()
