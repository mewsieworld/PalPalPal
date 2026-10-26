"""Artwork Tool: mouse handling for every tool."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import color_match, hex_to_rgba, rgba_hex, walk


class MouseMixin:
    """What every tool does on press, drag, release, double-click, right-click and wheel."""

    # ----- mouse -----
    def on_press(self, event):
        self.win.focus_set()
        if self.tool == "pan":
            self._pan_start = (event.x, event.y)
            return
        coords = self.grid_coords(event)
        if coords is None:
            return
        gx, gy = coords
        self.last = (gx, gy)
        t = self.tool
        alt = bool(event.state & 0x20000) or bool(event.state & 0x0008)
        if t == "gradient":
            self.drawing = True
            self.grad_start, self.grad_stroke = (gx, gy), 0
            self.last = (-1, -1)
            self.draw_pixel(gx, gy, self.gradient_color(0), tool="pencil")
            self.last = (gx, gy)
        elif t in ("rectselect", "lasso", "circleselect"):
            if self.selection and self.in_selection(gx, gy):
                self.moving_sel = True
                x1 = min(self.selection["x1"], self.selection["x2"])
                y1 = min(self.selection["y1"], self.selection["y2"])
                self.sel_offset = (gx - x1, gy - y1)
            else:
                self.clear_selection()
                self.drawing = True
                if t == "rectselect":
                    self.selection = {"x1": gx, "y1": gy, "x2": gx, "y2": gy, "kind": "Rectangle", "layer": self.cur_layer}
                elif t == "lasso":
                    self.lasso = [(gx, gy)]
                else:
                    self.circle_center = (gx, gy)
        elif t == "colorselect":
            if self.selection and self.in_selection(gx, gy):
                self.clear_selection()
            else:
                self.select_by_color(gx, gy)
        elif t == "edgeselect":
            self.select_by_edges(gx, gy)
        elif t == "erasecolor":
            if not self.selection:
                messagebox.showinfo("Erase Color", "Erase Color only works within a selection!\nPlease create a "
                                                   "selection first.", parent=self.win)
                return
            self.save_state()
            target = self.get_px(gx, gy)
            px = self.layer().img.load()
            for y in range(self.H):
                for x in range(self.W):
                    if self.in_selection(x, y) and color_match(px[x, y], target):
                        px[x, y] = (0, 0, 0, 0)
            self.changed()
        elif t == "magiceraser":
            tol = simpledialog.askinteger("🪄 Magic Eraser", "Color tolerance (0-255):\n\n0 = Exact match only\n"
                                                           "50 = Similar colors\n100 = Broader range",
                                          initialvalue=30, minvalue=0, maxvalue=255, parent=self.win)
            if tol is None:
                return
            self.save_state()
            self.flood(gx, gy, lambda x, y: (0, 0, 0, 0), tol, ignore_selection=True)
            self.changed()
        elif t == "gradientmesh":
            self.mesh_points.append((gx, gy, self.color))
            self.set_status("Mesh point %d added. Press Enter to fill, ESC to cancel." % len(self.mesh_points))
            self.redraw_overlay()
        elif t == "beziercurve":
            self.bezier_points.append((gx, gy))
            if len(self.bezier_points) < 4:
                self.set_status("Bezier point %d/4. Click %d more." % (len(self.bezier_points), 4 - len(self.bezier_points)))
            else:
                self.save_state()
                self.draw_bezier(self.bezier_points, self.color)
                self.bezier_points = []
                self.set_status("")
                self.changed()
            self.redraw_overlay()
        elif t in ("rectangle", "circle"):
            if not self.shape_start:
                self.save_state()
                self.shape_start = (gx, gy)
                self.set_status("Rectangle: Click opposite corner" if t == "rectangle" else "Circle: Click edge point")
            else:
                sx, sy = self.shape_start
                if t == "rectangle":
                    self.draw_rect(sx, sy, gx, gy, self.color, self.fill_shape.get())
                else:
                    cx, cy = round((sx + gx) / 2), round((sy + gy) / 2)
                    r = math.sqrt((gx - sx) ** 2 + (gy - sy) ** 2) / 2
                    self.draw_circle(cx, cy, r, self.color, self.fill_shape.get())
                self.shape_start = None
                self.set_status("")
                self.changed()
            self.redraw_overlay()
        elif t == "line":
            if not self.line_start:
                self.save_state()
                self.line_start = (gx, gy)
                self.set_status("Line: Click end point")
            else:
                self.draw_line(self.line_start[0], self.line_start[1], gx, gy, self.color)
                self.line_start = None
                self.set_status("")
                self.changed()
            self.redraw_overlay()
        elif t in ("contour", "polygon"):
            self.shape_points.append((gx, gy))
            self.set_status(("Polygon: %d points - Double-click to finish" if t == "polygon"
                             else "Contour: %d points - Double-click to close") % len(self.shape_points))
            self.redraw_overlay()
        elif t == "curve":
            if not self.curve_points:
                self.save_state()
                self.curve_points.append((gx, gy))
                self.set_status("Curve: Click end point")
            elif len(self.curve_points) == 1:
                self.curve_points.append((gx, gy))
                self.set_status("Curve: Click control point")
            else:
                (x0, y0), (x2, y2) = self.curve_points
                self.draw_quad(x0, y0, x2, y2, gx, gy, self.color)
                self.curve_points = []
                self.set_status("")
                self.changed()
            self.redraw_overlay()
        elif t in ("pencil", "pencilsquare", "eraser", "blend", "depth", "symmetrical", "rainbow", "highlight",
                   "sharpen", "jumble", "spray", "dither", "clone", "liquify"):
            if t == "clone" and alt:
                self.clone_src, self.clone_off = (gx, gy), (0, 0)
                self.set_status("Clone source set at (%d, %d)" % (gx, gy))
                return
            if t == "clone" and self.clone_src != (-1, -1):
                self.clone_off = (gx - self.clone_src[0], gy - self.clone_src[1])
            self.drawing = True
            self.stroke_pixels.clear()
            erase = t == "eraser"
            color = self.mask_color if self.mask_mode else ("#000000" if erase else self.color)
            self.last = (-1, -1)
            self.draw_pixel(gx, gy, color, erase, t)
            self.last = (gx, gy)
            self.redraw()
        elif t == "refined":
            self.last = (-1, -1)
            self.draw_pixel(gx, gy, self.mask_color if self.mask_mode else self.color, False, t)
            self.last = (-1, -1)
            self.changed()
        elif t in ("fill", "pattern"):
            self.save_state()
            if t == "fill":
                c = hex_to_rgba(self.color)
                self.flood(gx, gy, lambda x, y: c, 0, skip_if_same=c)
            else:
                self.flood(gx, gy, lambda x, y: self.pattern_color(x, y), 0)
            self.changed()
        elif t == "swap":
            p = self.get_px(gx, gy)
            self.swap_src.delete(0, "end")
            self.swap_src.insert(0, rgba_hex(p))
            self.swap_dst.delete(0, "end")
            self.swap_dst.insert(0, self.color)

    def on_move(self, event):
        if self.tool == "pan" and hasattr(self, "_pan_start"):
            self.on_pan_drag(event, left=True)
            return
        coords = self.grid_coords(event)
        if coords is None:
            return
        gx, gy = coords
        if self.moving_sel and self.selection:
            if self.selection.get("data") is None:
                self.capture_selection()
            sel = self.selection
            w = abs(sel["x2"] - sel["x1"])
            h = abs(sel["y2"] - sel["y1"])
            nx, ny = gx - self.sel_offset[0], gy - self.sel_offset[1]
            sel["x1"], sel["y1"], sel["x2"], sel["y2"] = nx, ny, nx + w, ny + h
            self.redraw_overlay()
            return
        if not self.drawing:
            return
        t = self.tool
        if t == "rectselect":
            self.selection["x2"], self.selection["y2"] = gx, gy
            self.update_selection_info()
            self.redraw_overlay()
            return
        if t == "lasso":
            if self.lasso[-1] != (gx, gy):
                self.lasso.append((gx, gy))
                self.redraw_overlay()
            return
        if t == "circleselect":
            self._circle_end = (gx, gy)
            self.redraw_overlay()
            return
        if t == "gradient":
            if (gx, gy) != self.last:
                cur = math.sqrt((gx - self.grad_start[0]) ** 2 + (gy - self.grad_start[1]) ** 2)
                for x, y, t in walk(self.last, (gx, gy)):
                    ratio = min(1, (self.grad_stroke + (cur - self.grad_stroke) * t) / self.grad_len)
                    self.draw_core(x, y, self.gradient_color(ratio), False, "pencil")
                self.grad_stroke = cur
                self.last = (gx, gy)
                self.redraw()
            return
        if self.brush_delay and self._brush_wait:
            return
        erase = t == "eraser"
        color = self.mask_color if self.mask_mode else ("#000000" if erase else self.color)
        for x, y, _t in walk(self.last, (gx, gy)):
            self.draw_pixel(x, y, color, erase, t)
        self.last = (gx, gy)
        self.redraw()
        if self.brush_delay:
            self._brush_wait = True
            self.win.after(self.brush_delay, lambda: setattr(self, "_brush_wait", False))

    def on_release(self, event):
        if hasattr(self, "_pan_start"):
            del self._pan_start
        if self.moving_sel:
            self.moving_sel = False
            if self.selection and self.selection.get("data") is not None:
                self.save_state()
                self.paste_selection(min(self.selection["x1"], self.selection["x2"]),
                                     min(self.selection["y1"], self.selection["y2"]))
                self.clear_selection()
            return
        if self.tool == "lasso" and self.drawing and self.lasso:
            pixels = self.lasso_pixels(self.lasso)
            if pixels:
                self.make_pixel_selection(pixels, "Lasso")
            self.lasso = []
            self.redraw_overlay()
        if self.tool == "circleselect" and self.drawing and self.circle_center:
            coords = self.grid_coords(event)
            if coords:
                cx, cy = self.circle_center
                r = math.sqrt((coords[0] - cx) ** 2 + (coords[1] - cy) ** 2) / 2
                if r >= 0.5:
                    pix = {(x, y) for y in range(self.H) for x in range(self.W) if (x - cx) ** 2 + (y - cy) ** 2 <= r * r}
                    if pix:
                        self.make_pixel_selection(pix, "Circle")
            self.circle_center = None
            self.redraw_overlay()
        if self.drawing:
            self.drawing = False
            self.last = (-1, -1)
            self.grad_start, self.grad_stroke = (-1, -1), 0
            self.stroke_pixels.clear()
            self.changed()
        self.update_selection_info()

    def on_double(self, event):
        if self.tool in ("contour", "polygon") and len(self.shape_points) >= 2:
            self.save_state()
            pts = self.shape_points
            if self.tool == "polygon" and self.fill_shape.get():
                self.fill_polygon(pts, self.color)
            else:
                for i in range(len(pts)):
                    a, b = pts[i], pts[(i + 1) % len(pts)]
                    self.draw_line(a[0], a[1], b[0], b[1], self.color)
            self.shape_points = []
            self.set_status("")
            self.changed()

    def on_right_press(self, event):
        if self.mask_mode:
            self.toggle_mask_edit(self.cur_layer)
        elif self.moving_sel:
            self.cancel_selection()
        elif self.selection:
            self.clear_selection()
        elif self.tool == "swap":
            self.toggle_swap()
        elif self.tool == "pan":
            self.pan = [0, 0]
            self.redraw()
        else:
            self._pan_start = (event.x, event.y)

    def on_pan_drag(self, event, left=False):
        start = getattr(self, "_pan_start", None)
        if start is None:
            self._pan_start = (event.x, event.y)
            return
        self.pan[0] += event.x - start[0]
        self.pan[1] += event.y - start[1]
        self._pan_start = (event.x, event.y)
        self.redraw()

    def on_wheel(self, event):
        if self.mask_mode:
            # Scroll switches the mask paint between black (hide) and white (reveal), as in the web tool
            self.mask_color = "#FFFFFF" if self.mask_color == "#000000" else "#000000"
            self.set_status("🎭 MASK EDITING - Paint with %s - Scroll to switch - Right-click to exit"
                            % ("BLACK (hide)" if self.mask_color == "#000000" else "WHITE (reveal)"))
            return
        self.zoom_by(1 if event.delta > 0 else -1)

    def zoom_by(self, step):
        self.zoom = 1 if step == 0 else max(1, min(MAX_ZOOM, self.zoom + step))
        if step == 0:
            self.pan = [0, 0]
        self.zoom_lbl.configure(text="%dx" % self.zoom)
        self.redraw()
