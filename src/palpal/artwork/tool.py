"""Artwork Tool: the SpriteTool window class that ties the mixins together."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .look import center_over, paint_buttons
from .model import Layer
from .ui import UiMixin
from .drawing import DrawingMixin
from .mouse import MouseMixin
from .selection import SelectionMixin
from .render import RenderMixin
from .layers_frames import LayersFramesMixin
from .color_tools import ColorToolsMixin
from .transforms import TransformsMixin
from .files import FilesMixin
from .options import OptionsMixin


# ---------------------------------------------------------------------------
# The editor window
# ---------------------------------------------------------------------------

class SpriteTool(UiMixin, DrawingMixin, MouseMixin, SelectionMixin, RenderMixin, LayersFramesMixin, ColorToolsMixin, TransformsMixin, FilesMixin, OptionsMixin):
    def __init__(self, master, width=32, height=32, on_return=None, theme=None, colors=None, start_frames=None,
                 store_dir=None, read_palette=None, palette_types=None, dark_mode=None):
        self.master = master
        # store_dir replaces the web tool's localStorage (autosave + workspace); read_palette lets the host
        # app read every palette format it knows; dark_mode is (get, toggle) for the Display Options checkbox,
        # where toggle returns the new colours
        self.store_dir = store_dir or os.path.join(os.path.expanduser("~"), ".spooksie_sprite_tool")
        self.read_palette = read_palette
        self.palette_types = palette_types or [("Palettes", "*.pal *.vga"), ("All files", "*.*")]
        self.dark_mode = dark_mode
        self.on_return = on_return
        self._host_theme = theme or (lambda w: None)
        self.colors = colors or {"bg": "#F0F0F0", "fg": "#000000", "canvas": "white", "input": "white",
                                 "button": "#E0E0E0", "hover": "#D0D0D0"}
        self.W, self.H = max(1, width), max(1, height)
        self.frames = [[Layer("Layer 1", self.W, self.H)]]
        if start_frames:
            self.frames = [[Layer("Layer 1", self.W, self.H, img.convert("RGBA").resize((self.W, self.H)))]
                           for img in start_frames]
        self.tags = [""] * len(self.frames)
        self.durations = [None] * len(self.frames)
        self.cur_frame = 0
        self.cur_layer = 0
        self.zoom = 1
        self.tool = "pencil"
        self.color = "#000000"
        self.color2 = "#FFFFFF"
        self.recent = []
        self.brush_size = 1
        self.saved_size = None
        self.brush_shape = "circle"
        self.brush_delay = 0
        self.custom_brush = None
        self.custom_size = 8
        self.pattern = "dots"
        self.symmetry = "horizontal"
        self.grad_len = 32
        self.undo_stack, self.redo_stack = [], []
        self.selection = None
        self.lasso = []
        self.moving_sel = False
        self.sel_offset = (0, 0)
        self.circle_center = None
        self.drawing = False
        self.last = (-1, -1)
        self.stroke_pixels = set()
        self.grad_start = (-1, -1)
        self.grad_stroke = 0
        self.line_start = None
        self.shape_points = []
        self.curve_points = []
        self.shape_start = None
        self.mesh_points = []
        self.bezier_points = []
        self.clone_src = (-1, -1)
        self.clone_off = (0, 0)
        self.mask_mode = False
        self.mask_color = "#000000"
        self.frame_clip = None
        self.loop_start, self.loop_end = 0, -1
        self.playing = True
        self.anim_frame = 0
        self.palette_colors = []
        self._brush_wait = False
        self.v_guides, self.h_guides = [], []
        self.photos = {}

        self.win = tk.Toplevel(master)
        self.win.title("Artwork Tool")
        self.win.geometry("1320x820")
        self.win.withdraw()
        self.win.minsize(1100, 700)
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self._vars()
        self.build()
        self.theme(self.win)
        center_over(self.win, master)
        self.win.deiconify()
        self.activate_tool("pencil")
        self.refresh_all()
        self.win.after(100, self.preview_tick)
        self.win.bind("<KeyPress>", self.on_key)
        self.autosave_job = None

    # ----- tk variables -----
    def _vars(self):
        v = tk
        self.size_var = v.IntVar(value=1)
        self.shape_var = v.StringVar(value="Circle")
        self.delay_var = v.IntVar(value=0)
        self.pattern_var = v.StringVar(value="Dots")
        self.sym_var = v.StringVar(value="Horizontal (2-way)")
        self.grad_var = v.IntVar(value=32)
        self.fill_shape = v.BooleanVar(value=True)
        self.grad_shape = v.BooleanVar(value=False)
        self.perfect_circle = v.BooleanVar(value=False)
        self.grid_vis = v.StringVar(value="high")
        self.grid_color = "#333333"
        self.dark_grid = v.BooleanVar(value=True)
        self.dark_every = v.IntVar(value=4)
        self.dark_color = "#000000"
        self.bg_preset = v.StringVar(value="#ffffff")
        self.bg_custom = "#ffffff"
        self.persp = v.BooleanVar(value=False)
        self.guides = v.BooleanVar(value=False)
        self.autosave = v.BooleanVar(value=False)
        self.tilemap = v.BooleanVar(value=False)
        self.tile_size = v.IntVar(value=8)
        self.onion = v.BooleanVar(value=False)
        self.onion_prev = v.IntVar(value=30)
        self.onion_next = v.IntVar(value=30)
        self.onion_count = v.IntVar(value=1)
        self.speed_var = v.IntVar(value=150)
        self.mult_var = v.StringVar(value="1x")
        self.timeline_var = v.BooleanVar(value=False)
        self.show_palette = v.BooleanVar(value=False)
        self.show_hist_var = v.BooleanVar(value=False)
        self.w_var = v.IntVar(value=self.W)
        self.h_var = v.IntVar(value=self.H)
        self.link_var = v.BooleanVar(value=True)

    # ----- basics -----
    def layers(self):
        return self.frames[self.cur_frame]

    def layer(self):
        layers = self.layers()
        self.cur_layer = max(0, min(self.cur_layer, len(layers) - 1))
        return layers[self.cur_layer]

    def all_layers(self):
        for frame in self.frames:
            yield from frame

    def connected(self, sx, sy, accept):
        """4-way connected pixels from (sx, sy) for which accept(x, y) holds."""
        stack, seen, found = [(sx, sy)], set(), set()
        while stack:
            x, y = stack.pop()
            if (x, y) in seen or not self.in_bounds(x, y):
                continue
            seen.add((x, y))
            if accept(x, y):
                found.add((x, y))
                stack.extend((x + dx, y + dy) for dx, dy in NEIGHBOURS_4)
        return found

    def neighbour_colors(self, x, y, include_centre):
        """Opaque colours around (x, y) that the selection allows (the blend / sharpen sample)."""
        cells = NEIGHBOURS_8 + (((0, 0),) if include_centre else ())
        out = []
        for dx, dy in cells:
            sx, sy = x + dx, y + dy
            if self.in_bounds(sx, sy) and self.allowed(sx, sy):
                p = self.get_px(sx, sy)
                if p[3] > 0:
                    out.append(p)
        return out

    def get_px(self, x, y):
        return self.layer().img.getpixel((x, y))

    def in_bounds(self, x, y):
        return 0 <= x < self.W and 0 <= y < self.H

    def set_status(self, text):
        self.status.configure(text=text or "")

    def scale(self):
        base = CANVAS_DIM / float(max(self.W, self.H))
        return max(1.0, base * self.zoom)

    def origin(self):
        s = self.scale()
        cw, ch = max(1, self.canvas.winfo_width()), max(1, self.canvas.winfo_height())
        return (cw - self.W * s) / 2 + self.pan[0], (ch - self.H * s) / 2 + self.pan[1]

    def grid_coords(self, event):
        s = self.scale()
        ox, oy = self.origin()
        gx = int(math.floor((event.x - ox) / s))
        gy = int(math.floor((event.y - oy) / s))
        if self.tilemap.get():
            ts = self.tile_size.get()
            gx, gy = gx // ts * ts, gy // ts * ts
        if self.guides.get():
            for g in self.v_guides:
                if abs(gx - g) <= 2:
                    gx = g
                    break
            for g in self.h_guides:
                if abs(gy - g) <= 2:
                    gy = g
                    break
        return (gx, gy) if self.in_bounds(gx, gy) else None

    # ----- undo -----
    def snapshot(self):
        return {"W": self.W, "H": self.H, "frame": self.cur_frame, "layer": self.cur_layer,
                "frames": [[l.clone() for l in f] for f in self.frames], "bg": (self.bg_preset.get(), self.bg_custom)}

    def save_state(self, kind="general"):
        state = self.snapshot()
        state["kind"] = kind
        self.undo_stack.append(state)
        del self.undo_stack[:-MAX_UNDO]
        self.redo_stack = []

    def restore(self, state):
        self.W, self.H = state["W"], state["H"]
        self.w_var.set(self.W)
        self.h_var.set(self.H)
        self.frames = state["frames"]
        self.cur_frame = min(state["frame"], len(self.frames) - 1)
        self.cur_layer = state["layer"]
        self.bg_preset.set(state["bg"][0])
        self.bg_custom = state["bg"][1]
        while len(self.tags) < len(self.frames):
            self.tags.append("")
            self.durations.append(None)
        del self.tags[len(self.frames):]
        del self.durations[len(self.frames):]
        self.refresh_all()

    def undo(self):
        if not self.undo_stack:
            return
        self.redo_stack.append(self.snapshot())
        self.restore(self.undo_stack.pop())

    def redo(self):
        if not self.redo_stack:
            return
        self.undo_stack.append(self.snapshot())
        self.restore(self.redo_stack.pop())

    def undo_transformations(self):
        if not self.undo_stack or self.undo_stack[-1].get("kind") != "transform":
            messagebox.showinfo("Undo", "No recent transformations to undo. (Make sure you haven't used other tools "
                                        "since your last transform)", parent=self.win)
            return
        state = None
        while self.undo_stack and self.undo_stack[-1].get("kind") == "transform":
            state = self.undo_stack.pop()
        self.redo_stack = []
        self.restore(state)

    # ----- refresh & finish -----
    def refresh_all(self):
        self.size_lbl.configure(text="Size %dx%d" % (self.brush_size, self.brush_size))
        self.set_color(self.color)
        self.set_color2(self.color2)
        self.update_tool_display()
        self.render_layers()
        self.render_thumbs()
        self.redraw()
        if self.show_palette.get():
            self.refresh_palette()

    def save_and_return(self):
        """Send the sprite back to PalPalPal as one layer (one frame per sprite frame)."""
        if self.on_return:
            self.on_return([self.composite_frame(i) for i in range(len(self.frames))])
        self.win.destroy()

    def close(self):
        if messagebox.askyesno("Close", "Close the Artwork Tool without returning the drawing?", parent=self.win):
            self.win.destroy()

    def theme(self, widget):
        """The host app's theme, then the Artwork Tool's colourful buttons."""
        self._host_theme(widget)
        paint_buttons(widget)

    def askcolor(self, color=None, parent=None, title="Pick a color"):
        """PalPalPal's color picker (square + hue strip + numbers + recent colors), MS Paint's no more."""
        from ..ui.color_picker import askcolor
        return askcolor(color, parent or self.win, title, theme=self.theme, colors=self.colors, recent=self.recent)

    def popup(self):
        """A pop-up window that opens centred on the Artwork Tool instead of the screen's top-left corner."""
        top = tk.Toplevel(self.win)
        top.withdraw()
        top.transient(self.win)

        def show():
            if top.winfo_exists():
                paint_buttons(top)
                center_over(top, self.win)
                top.deiconify()

        top.after(20, show)
        return top
