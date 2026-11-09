"""The preview canvas: single, grid and 3D bead views, panning and zooming."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .beads import build_model, model_key, moving_model, render
from ..ui.theme import Theme, hints_shown


# ---------------------------------------------------------------------------
# Preview canvas: 2D single view, frame grids, and the 3D layer view
# ---------------------------------------------------------------------------

ALIGNMENTS = [("Center", "c"), ("Top Left", "nw"), ("Top", "n"), ("Top Right", "ne"), ("Left", "w"),
              ("Right", "e"), ("Bottom Left", "sw"), ("Bottom", "s"), ("Bottom Right", "se")]


def align_offset(anchor, room_w, room_h, w, h, pad=0):
    """Top-left corner for a w x h block placed in a room_w x room_h area by a compass anchor."""
    if "w" in anchor:
        x = pad
    elif "e" in anchor:
        x = room_w - w - pad
    else:
        x = (room_w - w) // 2
    if "n" in anchor:
        y = pad
    elif "s" in anchor:
        y = room_h - h - pad
    else:
        y = (room_h - h) // 2
    return max(pad, x), max(pad, y)


class PreviewView:
    """Draws timeline frames on a canvas and maps clicks back to image pixels."""

    def __init__(self, app, canvas, zoom_var):
        self.app, self.canvas, self.zoom_var = app, canvas, zoom_var
        self.photos = []
        self.placements = []  # (timeline_index, x0, y0, scale, w, h)
        self.is_grid = False
        self.is_3d = False
        self.yaw, self.pitch = -30.0, 20.0
        self.buttons = []

    def zoom_scale(self):
        try:
            return int(self.zoom_var.get().rstrip("%")) / 100.0
        except ValueError:
            return None  # Fit

    def _clear(self):
        # Deleting the canvas items only unmaps the start buttons; they are kept and reused, because
        # destroying a button while its own command (an Open dialog) is still running locked the program up
        self.canvas.delete("all")
        self.photos, self.placements = [], []

    def draw_message(self, message, buttons=()):
        self._clear()
        self.is_grid = self.is_3d = False
        c = self.canvas
        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        c.create_text(cw // 2, ch // 2 - 20, text=message, fill="#888888", font=("Arial", 13, "bold"),
                      width=max(200, cw - 40), justify="center")
        colors = Theme.colors(self.app)
        while len(self.buttons) < len(buttons):
            self.buttons.append(tk.Button(c, width=14))
        x = cw // 2 - (len(buttons) * 130) // 2 + 65
        for b, (label, command) in zip(self.buttons, buttons):
            b.configure(text=label, command=command, bg=colors["button"], fg=colors["fg"],
                        activebackground=colors["hover"], activeforeground=colors["fg"])
            c.create_window(x, ch // 2 + 35, window=b)
            x += 130
        c.configure(scrollregion=(0, 0, cw, ch))

    def draw_single(self, t, labels=True):
        self._clear()
        self.is_grid = False
        self.is_3d = bool(self.app.view_3d) and len(self.app.visible_image_layers()) > 0
        if self.is_3d:
            self._draw_3d(t)
            return
        c = self.canvas
        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        scale = self.zoom_scale()
        if scale is None:
            w, h = self.app.transformed_size()
            scale = max(0.05, min(cw / float(w), (ch - (16 if labels else 0)) / float(h)))
        img = self.app.render(t, scale)
        photo = ImageTk.PhotoImage(img)
        label_h = 16 if labels else 0
        # Placed by the Align setting for this view + frame type (centred by default)
        x0, y0 = align_offset(self.app.current_alignment(), cw, ch, img.width, img.height + label_h)
        c.create_image(x0, y0, image=photo, anchor="nw")
        if labels:
            c.create_text(x0 + img.width // 2, y0 + img.height + 3, text=str(t + 1), anchor="n",
                          fill="#888888", font=("Arial", 8))
        self.photos.append(photo)
        self.placements.append((t, x0, y0, scale, img.width, img.height))
        c.configure(scrollregion=(0, 0, max(cw, img.width), max(ch, y0 + img.height + label_h)))

    def draw_grid(self, indices, labels=True, selected=()):
        """Several frames in centred rows. Zoom is kept; Fit sizes every frame so the whole set fits."""
        self._clear()
        self.is_grid, self.is_3d = True, False
        c = self.canvas
        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        pad = 10
        label_h = 16 if labels else 0
        w, h = self.app.transformed_size()
        n = len(indices)
        scale = self.zoom_scale()
        if scale is None:
            best = 0.05
            for cols in range(1, n + 1):
                rows = -(-n // cols)
                s = min((cw - pad * (cols + 1)) / float(cols * w), (ch - (pad + label_h) * rows - pad) / float(rows * h))
                best = max(best, s)
            scale = best
        fw, fh = max(1, int(w * scale)), max(1, int(h * scale))
        cols = max(1, min(n, (cw - pad) // (fw + pad)))
        rows = -(-n // cols)
        total_w = cols * (fw + pad) - pad
        total_h = rows * (fh + label_h + pad) - pad
        left, top = align_offset(self.app.current_alignment(), cw, ch, total_w, total_h, pad)
        for k, t in enumerate(indices):
            img = self.app.render(t, scale)
            x = left + (k % cols) * (fw + pad)
            y = top + (k // cols) * (fh + label_h + pad)
            photo = ImageTk.PhotoImage(img)
            c.create_image(x, y, image=photo, anchor="nw")
            if t in selected:
                c.create_rectangle(x - 2, y - 2, x + img.width + 1, y + img.height + 1, outline="#3d8bff", width=2)
            elif t == self.app.current_frame:
                c.create_rectangle(x - 1, y - 1, x + img.width, y + img.height, outline="red")
            if labels:
                c.create_text(x, y + img.height + 2, text="Frame %d" % (t + 1), anchor="nw", fill="#888888",
                              font=("Arial", 8))
            self.photos.append(photo)
            self.placements.append((t, x, y, scale, img.width, img.height))
        c.configure(scrollregion=(0, 0, max(cw, left + total_w + pad), max(ch, top + total_h + pad)))

    def _draw_3d(self, t):
        """Perler-bead 3D: every pixel is a cube and the visible image layers stack on top of each other.
        The bead model is cached (see beads.py); turning the view only re-projects it."""
        app, c = self.app, self.canvas
        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        layers = app.visible_image_layers()
        moving = time.time() < getattr(self, "fast_until", 0) and getattr(self, "move_mode", False)
        if moving:
            # Dragging a layer: reuse each layer's own faces and just shift the moved one
            if not hasattr(self, "_layer_faces"):
                self._layer_faces = {}
            if len(self._layer_faces) > 64:
                self._layer_faces.clear()
            faces, size = moving_model(app, t, layers, self._layer_faces)
        else:
            key = model_key(app, t, layers)
            if getattr(self, "_bead_key", None) != key:
                self._bead_model = build_model(app, t, layers)
                self._bead_key = key
            faces, size = self._bead_model
        backdrop = tuple(v // 256 for v in c.winfo_rgb(Theme.colors(app)["canvas"]))
        zoom = self.zoom_scale()
        if time.time() < getattr(self, "fast_until", 0):
            # Moving: draw at half size without bead outlines and stretch it, then redo it sharp when still
            half, self.axes = render(faces, size, self.yaw, self.pitch, (max(1, cw // 2), max(1, ch // 2)), backdrop,
                                     zoom / 2.0 if zoom else None, outlines=False)
            out = half.resize((cw, ch), Image.Resampling.NEAREST)
            ex, ey, sc = self.axes
            self.axes = (ex, ey, sc * 2)
            if getattr(self, "_sharp_job", None):
                c.after_cancel(self._sharp_job)
            self._sharp_job = c.after(250, self._sharp_redraw)
        else:
            out, self.axes = render(faces, size, self.yaw, self.pitch, (cw, ch), backdrop, zoom)
        photo = ImageTk.PhotoImage(out)
        c.create_image(0, 0, image=photo, anchor="nw")
        if hints_shown():
            c.create_text(8, ch - 8, anchor="sw", fill="#888888", font=("Arial", 8),
                          text="3D bead view: drag to move the selected layer (Shift+drag lifts it)"
                          if getattr(self, "move_mode", False) else
                          "3D bead view: drag to turn, Options > 3D Layer View to switch back to 2D")
        self.photos.append(photo)
        c.configure(scrollregion=(0, 0, cw, ch))

    def interacting(self):
        """Called while dragging or zooming: render quick until things settle."""
        self.fast_until = time.time() + 0.2

    def _sharp_redraw(self):
        self._sharp_job = None
        self.fast_until = 0
        self.app.request_redraw()

    def rotate(self, dx, dy):
        self.yaw = (self.yaw + dx * 0.5) % 360
        self.pitch = max(-89.0, min(89.0, self.pitch - dy * 0.5))

    def hit(self, event):
        """Return (timeline_index, src_x, src_y) under the mouse, or None."""
        cx, cy = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
        for t, x0, y0, scale, w, h in self.placements:
            if x0 <= cx < x0 + w and y0 <= cy < y0 + h:
                tx, ty = int((cx - x0) / scale), int((cy - y0) / scale)
                sx, sy = self.app.untransform_point(tx, ty)
                return t, sx, sy
        return None


def bind_pan_and_zoom(app, canvas, zoom_var, redraw, on_click=None, view=None, on_right_click=None, band=None):
    """Left click selects, left/middle drag pans (turns the stack in 3D view), wheel zooms or scrolls a grid.
    band = (start, move, end): in the All / Custom grids a left drag draws a frame selection box instead."""
    state = {"moved": False, "x": 0, "y": 0, "lx": 0, "ly": 0, "band": False}

    def press(event):
        state.update(moved=False, x=event.x, y=event.y, lx=event.x, ly=event.y,
                     band=bool(band and getattr(event, "num", 1) == 1 and view is not None and view.is_grid))
        canvas.scan_mark(event.x, event.y)
        if state["band"]:
            band[0](event)

    def drag(event):
        if abs(event.x - state["x"]) > 3 or abs(event.y - state["y"]) > 3:
            state["moved"] = True
        if not state["moved"]:
            return
        if state["band"]:
            band[1](event)
            return
        if view is not None and view.is_3d:
            dx, dy = event.x - state["lx"], event.y - state["ly"]
            state.update(lx=event.x, ly=event.y)
            view.interacting()
            if getattr(view, "move_mode", False) and getattr(view, "on_move3d", None):
                view.on_move3d(dx, dy, bool(event.state & 0x0001))   # Shift lifts / lowers the layer
                return
            view.rotate(dx, dy)
            redraw()
        else:
            canvas.scan_dragto(event.x, event.y, gain=1)

    def release(event):
        if state["band"] and state["moved"]:
            band[2](event)
            return
        if state["band"]:
            band[2](None)   # just a click: drop the empty box
        if not state["moved"] and on_click and not (view is not None and view.is_3d):
            on_click(event)

    def wheel(delta):
        if view is not None and view.is_grid:
            canvas.yview_scroll(int(-1 * (delta / 120)), "units")
        else:
            if view is not None and view.is_3d:
                view.interacting()
            app.cycle_zoom(delta, zoom_var, redraw)
        return "break"

    canvas.bind("<Button-1>", press)
    canvas.bind("<B1-Motion>", drag)
    canvas.bind("<ButtonRelease-1>", release)
    canvas.bind("<Button-2>", press)
    canvas.bind("<B2-Motion>", drag)
    canvas.bind("<MouseWheel>", lambda e: wheel(e.delta))
    canvas.bind("<Button-4>", lambda e: wheel(120))
    canvas.bind("<Button-5>", lambda e: wheel(-120))
    if on_right_click:
        canvas.bind("<Button-3>", on_right_click)


def xform_image(img, flip, rot):
    """Flip left-right, then turn clockwise rot quarter turns (a view transform)."""
    if flip:
        img = img.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    for _ in range(rot % 4):
        img = img.transpose(Image.Transpose.ROTATE_270)
    return img


def unxform_point(x, y, size, flip, rot):
    """The pixel of the original image (of size w x h) under (x, y) of its xform_image view."""
    w, h = size
    sizes = []
    cw, ch = w, h
    for _ in range(rot % 4):
        sizes.append((cw, ch))
        cw, ch = ch, cw
    for pw, ph in reversed(sizes):
        x, y = y, ph - 1 - x   # undo one clockwise turn of a pw x ph image
    if flip:
        x = w - 1 - x
    return x, y
