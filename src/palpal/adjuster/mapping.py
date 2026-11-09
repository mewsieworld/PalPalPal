"""Img2img Palette Swap: recoloring, filters and the mapping tools."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import color_dist, hsl_to_rgb, luminosity, rgb_to_hsl, to_hex


class AdjusterMappingMixin:
    """Img2img Palette Swap: recoloring, filters and the mapping tools."""

    # ----- recoloring -----
    def nearest_source(self, rgb):
        """Closest source index within the tolerance (no match when the tolerance is 0 and it isn't exact)."""
        cached = self._map_cache.get(rgb)
        if cached is not None:
            return cached
        best, best_d = -1, None
        for i, c in enumerate(self.source_palette):
            d = color_dist(rgb, c)
            if d <= self.tolerance and (best_d is None or d < best_d):
                best, best_d = i, d
        self._map_cache[rgb] = best
        return best

    def recolor(self):
        if self.source is None:
            return None
        lookup = {}
        out = []
        for r, g, b, a in self.source.getdata():
            if a < 10:
                out.append((r, g, b, a))
                continue
            key = (r, g, b)
            if key not in lookup:
                i = self.nearest_source(key)
                lookup[key] = self.color_map.get(i, key) if i >= 0 else key
            m = lookup[key]
            out.append((m[0], m[1], m[2], a))
        img = Image.new("RGBA", self.source.size)
        img.putdata(out)
        return img

    def apply_filters(self, img):
        """The visual-only global filters (hue rotate, saturation, brightness, contrast)."""
        from PIL import ImageEnhance
        alpha = img.getchannel("A")
        rgb = img.convert("RGB")
        if self.filters["hue"]:
            h, s, v = rgb.convert("HSV").split()
            shift = int(self.filters["hue"] / 360.0 * 255)
            h = h.point(lambda x: (x + shift) % 256)
            rgb = Image.merge("HSV", (h, s, v)).convert("RGB")
        for key, enhancer in (("saturation", ImageEnhance.Color), ("brightness", ImageEnhance.Brightness),
                              ("contrast", ImageEnhance.Contrast)):
            if self.filters[key] != 100:
                rgb = enhancer(rgb).enhance(self.filters[key] / 100.0)
        out = rgb.convert("RGBA")
        out.putalpha(alpha)
        return out

    # ----- mapping actions -----
    def select_target(self, index, quiet=False):
        self.selected_target = self.modified_target = index
        self.shift_var.set(0)
        self.autoswap_sel_btn.configure(state="normal")
        if not quiet:
            self.log("Target index #%d (%s) selected." % (index, to_hex(self.target_palette[index])))
        self.refresh_mapper()

    def map_source(self, source_index):
        if self.modified_target is None:
            messagebox.showinfo("Mapper", "Select a target color first.", parent=self.mapper or self.win)
            return
        self.mapper_push()
        self.selected_source = source_index
        self.color_map[source_index] = self.target_palette[self.modified_target]
        self.log("Source index #%d mapped to target index #%d (%s). Affected index: %d."
                 % (source_index, self.modified_target, to_hex(self.target_palette[self.modified_target]),
                    source_index))
        self.refresh_mapper()
        self.schedule()

    def on_target_shift(self):
        if self.selected_target is None:
            return
        try:
            shift = int(self.shift_var.get())
        except tk.TclError:
            return
        self.modified_target = max(0, min(len(self.target_palette) - 1, self.selected_target + shift))
        self.log("Selected target #%d shifted by %d -> uses target #%d (%s)." % (
            self.selected_target, shift, self.modified_target, to_hex(self.target_palette[self.modified_target])))
        self.refresh_mapper()

    def on_tolerance(self):
        try:
            self.tolerance = int(self.tol_var.get())
        except tk.TclError:
            return
        self._map_cache = {}
        self.log("Color Swap Tolerance set to %d." % self.tolerance)
        self.schedule()

    def on_filter(self, key):
        try:
            self.filters[key] = int(self.filter_vars[key].get())
        except tk.TclError:
            return
        self.log("Global %s filter set to %d." % (key, self.filters[key]))
        self.schedule()

    def autoswap(self, target_index):
        if not self.source_palette or not self.target_palette:
            self.log("Error: palettes must be loaded before autoswap.")
            return
        if target_index is not None:
            for i in range(len(self.source_palette)):
                self.color_map[i] = self.target_palette[target_index]
            self.log("Autoswap: all %d source indexes mapped to target #%d (%s)." % (
                len(self.source_palette), target_index, to_hex(self.target_palette[target_index])))
        else:
            lums = [luminosity(c) for c in self.target_palette]
            for i, c in enumerate(self.source_palette):
                j = min(range(len(lums)), key=lambda k: abs(lums[k] - luminosity(c)))
                self.color_map[i] = self.target_palette[j]
            self.log("Autoswap: %d source indexes mapped by closest luminosity." % len(self.source_palette))
        self.refresh_mapper()
        self.schedule()

    def apply_refinement(self):
        if self.selected_source is None:
            self.log("Error: select a source index (use the eyedropper) before refining.")
            return
        shift = int(self.refine_var.get())
        current = self.color_map.get(self.selected_source, self.source_palette[self.selected_source])
        if shift == 0:
            reset = min(self.target_palette, key=lambda c: color_dist(current, c)) if self.target_palette else \
                self.source_palette[self.selected_source]
            self.color_map[self.selected_source] = reset
            self.log("Source #%d refinement cleared, reset to %s." % (self.selected_source, to_hex(reset)))
        else:
            h, s, l = rgb_to_hsl(current)
            new = hsl_to_rgb(h + shift, s, l)
            self.color_map[self.selected_source] = new
            self.log("Source #%d refined: hue shifted %d°, now %s." % (self.selected_source, shift, to_hex(new)))
        self.refresh_mapper()
        self.schedule()

    def _ints(self, vars_):
        try:
            return [int(v.get()) for v in vars_]
        except ValueError:
            self.log("Error: index boxes need whole numbers.")
            return None

    def run_gradient(self):
        vals = self._ints(self.grad_vars)
        if vals is None:
            return
        s0, s1, t0, t1 = vals
        if s0 < 0 or s1 >= len(self.source_palette) or s1 <= s0 or t0 < 0 or t1 >= len(self.target_palette):
            self.log("Error: gradient index range or path is invalid.")
            return
        step = (t1 - t0) / float(s1 - s0)
        for k in range(s1 - s0 + 1):
            self.color_map[s0 + k] = self.target_palette[int(round(t0 + k * step))]
        self.log("Gradient: source %d-%d mapped along target path %d-%d. Affected indexes: %d-%d." % (
            s0, s1, t0, t1, s0, s1))
        self.refresh_mapper()
        self.schedule()

    def run_index_shift(self):
        vals = self._ints(self.range_vars)
        if vals is None:
            return
        start, end, target = vals
        length = end - start + 1
        if start < 0 or end >= len(self.source_palette) or end < start or target < 0 or \
                target + length > len(self.target_palette):
            self.log("Error: index shift range or target index is invalid.")
            return
        for k in range(length):
            self.color_map[start + k] = self.target_palette[target + k]
        self.log("Index mapping: source %d-%d -> target %d-%d." % (start, end, target, target + length - 1))
        self.refresh_mapper()
        self.schedule()

    def reset_mapping(self):
        if not self.source_palette:
            return
        self.color_map = {i: c for i, c in enumerate(self.source_palette)}
        self.selected_source = self.selected_target = self.modified_target = None
        self.tol_var.set(0)
        self.tolerance = 0
        self._map_cache = {}
        for key, var in self.filter_vars.items():
            var.set(0 if key == "hue" else 100)
            self.filters[key] = var.get()
        self.refine_var.set(0)
        self.refine_lbl.configure(text="Selected source index: ---")
        self.view_mode, self.active_view = "source", "source"
        self.view_xform = {"source": [False, 0], "reference": [False, 0]}
        self.log("Mapping, view and global filters fully reset.")
        self.refresh_mapper()
        self.schedule()
