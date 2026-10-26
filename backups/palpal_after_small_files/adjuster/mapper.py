"""The Palette to Palette Mapper window of the Image to Image Palette Adjuster."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import to_hex
from ..ui.theme import Theme, center_on
from ..ui.widgets import draw_swatch, swatch_grid


class MapperMixin:
    """The Image to Image Adjuster's Palette to Palette Mapper window."""

    # ----- Palette to Palette Mapper -----
    def open_mapper(self):
        if not self.source_palette:
            messagebox.showinfo("Palette to Palette Mapper", "Choose both images first.", parent=self.win)
            return
        if self.mapper is not None and self.mapper.winfo_exists():
            self.mapper.lift()
            return
        self.mapper_snapshot = (dict(self.color_map), self.selected_target, self.modified_target)
        self.mapper = tk.Toplevel(self.win)
        self.mapper.title("Palette to Palette Mapper")
        self.mapper.geometry("570x600")
        self.mapper_undo, self.mapper_redo = [], []
        self.mapper.protocol("WM_DELETE_WINDOW", self.mapper_save_exit)
        self.target_boxes = self._mapper_section("Target Palette (click to select)", len(self.target_palette),
                                                 lambda i, e: self.select_target(i), self.mapper_reset_target)
        self.source_boxes = self._mapper_section("Source Palette (click to map the selected target onto it)",
                                                 len(self.source_palette), lambda i, e: self.map_source(i),
                                                 self.mapper_reset_source)
        self.mapper_info = tk.Label(self.mapper, text="", font=("Consolas", 8))
        self.mapper_info.pack(anchor="w", padx=8, pady=4)
        row = tk.Frame(self.mapper)
        row.pack(fill="x", padx=8, pady=(0, 8))
        tk.Button(row, text="Reset Both Palettes", command=self.mapper_reset).pack(side="left")
        tk.Button(row, text="Save and Exit", command=self.mapper_save_exit).pack(side="right")
        middle = tk.Frame(row)
        middle.pack(side="left", expand=True)
        tk.Button(middle, text="↶ Undo", command=self.mapper_undo_step).pack(side="left")
        tk.Button(middle, text="↷ Redo", command=self.mapper_redo_step).pack(side="left", padx=(4, 0))
        tk.Button(middle, text="🎨 Color Picker", command=self.mapper_pick_color).pack(side="left", padx=(8, 0))
        Theme.apply(self.app, self.mapper)
        center_on(self.mapper, self.win)
        self.refresh_mapper()

    def _mapper_section(self, title, count, on_click, on_reset):
        """A framed palette grid with its own Reset Palette button underneath."""
        box = tk.LabelFrame(self.mapper, text=title, font=("Arial", 10, "bold"), relief="groove", bd=2)
        box.pack(fill="both", expand=True, padx=8, pady=(8, 0))
        grid = tk.Frame(box)
        grid.pack(fill="both", expand=True, padx=6, pady=(4, 0))
        boxes = swatch_grid(grid, list(range(count)), 22, 18, on_click, height=150)
        tk.Button(box, text="Reset Palette", font=("Arial", 8), command=on_reset).pack(anchor="w", padx=6,
                                                                                      pady=(2, 6))
        return boxes

    def refresh_mapper(self):
        if self.mapper is None or not self.mapper.winfo_exists():
            return
        for i, sw in self.target_boxes.items():
            draw_swatch(self.app, sw, self.target_palette[i], i == self.modified_target)
        for i, sw in self.source_boxes.items():
            draw_swatch(self.app, sw, self.color_map.get(i, self.source_palette[i]), i == self.selected_source)
        target = "#%d %s" % (self.modified_target, to_hex(self.target_palette[self.modified_target])) \
            if self.modified_target is not None else "---"
        source = "#%d" % self.selected_source if self.selected_source is not None else "---"
        self.mapper_info.configure(text="Selected target: %s    Selected source: %s" % (target, source))

    def mapper_state(self):
        return dict(self.color_map), self.selected_target, self.modified_target, self.selected_source

    def mapper_restore(self, state):
        self.color_map, self.selected_target, self.modified_target, self.selected_source = dict(state[0]), \
            state[1], state[2], state[3]
        self.refresh_mapper()
        self.schedule()

    def mapper_push(self):
        self.mapper_undo.append(self.mapper_state())
        del self.mapper_undo[:-50]
        self.mapper_redo = []

    def mapper_undo_step(self):
        if self.mapper_undo:
            self.mapper_redo.append(self.mapper_state())
            self.mapper_restore(self.mapper_undo.pop())
            self.log("Mapper: undo.")

    def mapper_redo_step(self):
        if self.mapper_redo:
            self.mapper_undo.append(self.mapper_state())
            self.mapper_restore(self.mapper_redo.pop())
            self.log("Mapper: redo.")

    def mapper_reset_target(self):
        """Clear the target selection (and any shift on it)."""
        self.mapper_push()
        self.selected_target = self.modified_target = None
        self.shift_var.set(0)
        self.log("Target palette selection reset.")
        self.refresh_mapper()

    def mapper_reset_source(self):
        """Every source color back to how it was when the mapper opened."""
        self.mapper_push()
        self.color_map = dict(self.mapper_snapshot[0])
        self.selected_source = None
        self.log("Source palette mapping reset to its starting state.")
        self.refresh_mapper()
        self.schedule()

    def mapper_pick_color(self):
        """Any color from a real color picker, put straight onto the selected source index."""
        if self.selected_source is None:
            messagebox.showinfo("Color Picker", "Click a source color first (or use the eyedropper).",
                                parent=self.mapper or self.win)
            return
        current = self.color_map.get(self.selected_source, self.source_palette[self.selected_source])
        result = colorchooser.askcolor(color=to_hex(current), title="Color for source #%d" % self.selected_source,
                                       parent=self.mapper or self.win)
        if not result or not result[0]:
            return
        self.mapper_push()
        self.color_map[self.selected_source] = tuple(int(v) for v in result[0])
        self.log("Source index #%d set to %s with the color picker." % (self.selected_source,
                                                                       to_hex(self.color_map[self.selected_source])))
        self.refresh_mapper()
        self.schedule()

    def mapper_reset(self):
        """Reset Both Palettes: back to how the mapping was when this window opened (nothing else is touched)."""
        self.mapper_push()
        self.color_map, self.selected_target, self.modified_target = dict(self.mapper_snapshot[0]), \
            self.mapper_snapshot[1], self.mapper_snapshot[2]
        self.log("Palette to Palette Mapper reset to its starting state.")
        self.refresh_mapper()
        self.schedule()

    def mapper_save_exit(self):
        self.log("Palette to Palette Mapper changes kept.")
        self.mapper.destroy()
        self.mapper = None
