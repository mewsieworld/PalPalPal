"""Artwork Tool: global color swap and remap."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import color_match, hex_to_rgba, rgba_hex


class SwapRemapMixin:
    """Swap one color for another everywhere, or remap colors to the palette."""

    # ----- global colour tools -----
    def toggle_swap(self):
        if self.swap_frame.winfo_ismapped():
            self.swap_frame.pack_forget()
            if self.tool == "swap":
                self.activate_tool("pencil")
            return
        for w in self.swap_frame.winfo_children():
            w.destroy()
        self.tool = "swap"
        self.update_tool_display()
        self.set_status("🎨 Color Swap is active - Click a pixel to select source color, or type colors below")
        tk.Label(self.swap_frame, text="Source color (click a pixel or type):", font=("Arial", 8)).pack(anchor="w")
        self.swap_src = tk.Entry(self.swap_frame, width=10)
        self.swap_src.insert(0, "#000000")
        self.swap_src.pack(fill="x")
        tk.Label(self.swap_frame, text="Replace with:", font=("Arial", 8)).pack(anchor="w")
        self.swap_dst = tk.Entry(self.swap_frame, width=10)
        self.swap_dst.insert(0, self.color)
        self.swap_dst.pack(fill="x")
        tk.Button(self.swap_frame, text="Apply Color Swap to ALL Frames", bg="#8a2be2", fg="white",
                  command=self.apply_swap).pack(fill="x", pady=2)
        tk.Button(self.swap_frame, text="Cancel", command=self.toggle_swap).pack(fill="x")
        self.swap_frame.pack(fill="x", before=self.options_anchor)
        self.theme(self.swap_frame)

    def apply_swap(self):
        src, dst = hex_to_rgba(self.swap_src.get()), hex_to_rgba(self.swap_dst.get())
        if src is None or dst is None:
            messagebox.showerror("Color Swap", "Invalid hex color! Use format: #RRGGBB", parent=self.win)
            return
        self.save_state()
        for layer in self.all_layers():
            px = layer.img.load()
            for y in range(self.H):
                for x in range(self.W):
                    if color_match(px[x, y], src):
                        px[x, y] = dst
        self.toggle_swap()
        self.changed()
        messagebox.showinfo("Color Swap", "Color swap complete!\n%s → %s across all frames and layers!"
                            % (rgba_hex(src), rgba_hex(dst)), parent=self.win)

    def toggle_remap(self):
        if getattr(self, "remap_win", None) is not None and self.remap_win.winfo_exists():
            self.remap_win.destroy()
            self.set_status("")
            return
        self.refresh_palette()
        colors = [c for c in self.palette_colors if c[3] > 0]
        if not colors:
            messagebox.showinfo("Color Remap", "No colors found!\nDraw something first.", parent=self.win)
            return
        top = self.remap_win = self.popup()
        top.title("Color Remap (%d colors)" % len(colors))
        self.set_status("🎨 Color Remap (Multi) is active - set target colors and click Apply Remap to All Frames")
        holder = tk.Frame(top)
        holder.pack(fill="both", expand=True, padx=8, pady=8)
        cv = tk.Canvas(holder, height=320, width=260, highlightthickness=0)
        sb = ttk.Scrollbar(holder, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=sb.set)
        inner = tk.Frame(cv)
        cv.create_window((0, 0), window=inner, anchor="nw")
        inner.bind("<Configure>", lambda e: cv.configure(scrollregion=cv.bbox("all")))
        cv.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        entries = []
        for c in colors:
            r = tk.Frame(inner)
            r.pack(fill="x", pady=1)
            sw = tk.Label(r, bg=rgba_hex(c), width=3, relief="solid", bd=1)
            sw._cp_keep = True
            sw.pack(side="left")
            tk.Label(r, text="→").pack(side="left", padx=4)
            e = tk.Entry(r, width=9)
            e.insert(0, rgba_hex(c))
            e.pack(side="left")
            entries.append((c, e))

        def apply():
            mapping = {}
            for c, e in entries:
                t = hex_to_rgba(e.get())
                if t:
                    mapping[c] = t[:3] + (c[3],)
            self.save_state()
            n = 0
            for layer in self.all_layers():
                px = layer.img.load()
                for y in range(self.H):
                    for x in range(self.W):
                        new = mapping.get(px[x, y])
                        if new:
                            px[x, y] = new
                            n += 1
            top.destroy()
            self.set_status("")
            self.palette_colors = []
            self.changed()
            messagebox.showinfo("Color Remap", "Color remap complete!\n%d pixels remapped across all frames and layers!" % n,
                                parent=self.win)

        tk.Button(top, text="Apply Remap to All Frames", bg="#e91e63", fg="white", command=apply).pack(fill="x", padx=8)
        tk.Button(top, text="Cancel", command=self.toggle_remap).pack(fill="x", padx=8, pady=(2, 8))
        self.theme(top)
