"""The preview canvas: single, grid and 3D bead views, panning and zooming."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .heights import height_image
from ..ui.theme import Theme


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

    # The six faces of a unit cube: (normal, corners as offsets from the cube's low corner), and how lit each is
    CUBE_FACES = [((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
                  ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))),
                  ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
                  ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
                  ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
                  ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)))]
    FACE_LIGHT = {(0, 0, 1): 1.0, (0, 0, -1): 0.55, (1, 0, 0): 0.8, (-1, 0, 0): 0.7, (0, 1, 0): 0.65, (0, -1, 0): 0.9}

    def _draw_3d(self, t):
        """Perler-bead 3D: every pixel is a cube (as wide as it is tall and deep), and the visible image layers
        are stacked straight on top of each other, one bead deep each. Dragging turns the model."""
        app, c = self.app, self.canvas
        cw, ch = max(1, c.winfo_width()), max(1, c.winfo_height())
        layers = app.visible_image_layers()
        w, h = app.transformed_size()
        yaw, pitch = math.radians(self.yaw), math.radians(self.pitch)
        cy_, sy_ = math.cos(yaw), math.sin(yaw)
        cp, sp = math.cos(pitch), math.sin(pitch)

        def rot(x, y, z):
            x1 = x * cy_ + z * sy_
            z1 = -x * sy_ + z * cy_
            return x1, y * cp - z1 * sp, y * sp + z1 * cp

        # Occupied cells: (x, y, layer) -> color; the bottom layer sits farthest from the camera
        cells = {}
        slab = app.heights.max if app.heights.mode != "flat" else 1   # beads per layer
        for k, il in enumerate(layers):
            img = app.transform(app.layer_canvas(il, t))
            px = img.load()
            hmap = height_image(app, il, t, app.canvas_size())
            hp = hmap.load() if hmap is not None else None
            base = k * slab
            for y in range(img.height):
                for x in range(img.width):
                    r, g, b, a = px[x, y]
                    if a >= 128:
                        for z in range(hp[x, y] if hp is not None else 1):
                            cells[(x, y, base + z)] = (r, g, b)
        depth = max(1, len(layers) * slab)
        cx, cyc, cz = w / 2.0, h / 2.0, depth / 2.0
        # Orthographic: a cube corner projects linearly, so the axes are worked out once
        ex, ey, ez = rot(1, 0, 0), rot(0, 1, 0), rot(0, 0, 1)
        origin = rot(-cx, -cyc, -cz)
        visible = [(n, corners) for n, corners in self.CUBE_FACES if rot(*n)[2] > 1e-6]
        corners_box = [(x, y, z) for x in (0, w) for y in (0, h) for z in (0, depth)]
        proj = [rot(x - cx, y - cyc, z - cz) for x, y, z in corners_box]
        bw = max(1.0, max(q[0] for q in proj) - min(q[0] for q in proj))
        bh = max(1.0, max(q[1] for q in proj) - min(q[1] for q in proj))
        scale = self.zoom_scale()
        if scale is None:
            scale = min(cw * 0.9 / bw, ch * 0.9 / bh)
        ox, oy = cw / 2.0, ch / 2.0

        faces = []
        for (x, y, z), color in cells.items():   # z counts beads up from the bottom, toward the camera
            for n, corners in visible:
                if (x + n[0], y + n[1], z + n[2]) in cells:
                    continue  # hidden by the neighbouring bead
                pts = []
                dsum = 0.0
                for dx, dy, dz in corners:
                    X, Y, Z = x + dx, y + dy, z + dz
                    px_ = origin[0] + X * ex[0] + Y * ey[0] + Z * ez[0]
                    py_ = origin[1] + X * ex[1] + Y * ey[1] + Z * ez[1]
                    dsum += origin[2] + X * ex[2] + Y * ey[2] + Z * ez[2]
                    pts.append((ox + scale * px_, oy + scale * py_))
                light = self.FACE_LIGHT[n]
                faces.append((dsum, pts, tuple(int(v * light) for v in color)))
        faces.sort(key=lambda f: f[0])   # farthest first, the camera looks from +z

        colors = Theme.colors(app)
        backdrop = tuple(v // 256 for v in c.winfo_rgb(colors["canvas"]))
        out = Image.new("RGB", (cw, ch), backdrop)
        draw = ImageDraw.Draw(out)
        outline = scale >= 6
        for _d, pts, color in faces:
            draw.polygon(pts, fill=color, outline=tuple(max(0, v - 40) for v in color) if outline else None)
        photo = ImageTk.PhotoImage(out)
        c.create_image(0, 0, image=photo, anchor="nw")
        c.create_text(8, ch - 8, anchor="sw", fill="#888888", font=("Arial", 8),
                      text="3D bead view: drag to turn, Options > 3D Layer View to switch back to 2D")
        self.photos.append(photo)
        c.configure(scrollregion=(0, 0, cw, ch))

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
            view.rotate(event.x - state["lx"], event.y - state["ly"])
            state.update(lx=event.x, ly=event.y)
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
