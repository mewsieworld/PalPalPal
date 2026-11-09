"""Artwork Tool: the layers panel."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .model import Layer, default_effects


class LayersMixin:
    """The layers panel: add, delete, select, visibility, opacity, blend, masks, effects and renaming."""

    # ----- layers -----
    def render_layers(self):
        for w in self.layer_list.winfo_children():
            w.destroy()
        layers = self.layers()
        for i in range(len(layers) - 1, -1, -1):
            layer = layers[i]
            active = i == self.cur_layer
            row = tk.Frame(self.layer_list, relief="sunken" if active else "flat", bd=1,
                           bg="#1e3a5f" if active and self.colors.get("bg") == "#1E1E1E" else None)
            row.pack(fill="x", pady=1)
            top = tk.Frame(row)
            top.pack(fill="x")
            handle = tk.Label(top, text="☰", cursor="fleur")
            handle.pack(side="left")
            handle.bind("<ButtonRelease-1>", lambda e, i=i: self.drop_layer(e, i))
            thumb = layer.img.resize((24, max(1, int(24 * self.H / self.W))), Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(thumb)
            self.photos["layer%d" % i] = photo
            tk.Label(top, image=photo, relief="solid", bd=1).pack(side="left", padx=2)
            for text, tip, cmd in (("👁" if layer.visible else "🚫", "Show / hide", lambda i=i: self.toggle_layer_vis(i)),
                                   ("🎭" if layer.mask_enabled else "⬜", "Layer mask on / off", lambda i=i: self.toggle_mask(i)),
                                   (("✏️" if self.mask_mode and active else "🖊️") if layer.mask_enabled and layer.mask is not None
                                    else None, "Edit mask (paint to hide/reveal)", lambda i=i: self.toggle_mask_edit(i)),
                                   ("✨" if any(layer.effects.values()) else "🔘", "Layer effects", lambda i=i: self.effects_dialog(i))):
                if text is None:
                    continue
                b = tk.Label(top, text=text, cursor="hand2")
                b.pack(side="left")
                b.bind("<Button-1>", lambda e, cmd=cmd: cmd())
                self._tooltip(b, tip)
            name = tk.Label(top, text=layer.name, anchor="w", font=("Arial", 9, "bold" if active else "normal"))
            name.pack(side="left", fill="x", expand=True, padx=4)
            name.bind("<Double-Button-1>", lambda e, i=i: self.rename_layer(i))
            for w in (row, top, name):
                w.bind("<Button-1>", lambda e, i=i: self.select_layer(i), add="+")
            ctl = tk.Frame(row)
            ctl.pack(fill="x", padx=4)
            tk.Label(ctl, text="Opacity", font=("Arial", 7)).pack(side="left")
            ov = tk.IntVar(value=round(layer.opacity * 100))
            tk.Scale(ctl, from_=0, to=100, orient="horizontal", variable=ov, showvalue=True, length=80, width=8,
                     font=("Arial", 7), command=lambda v, i=i: self.set_layer_opacity(i, int(float(v)) / 100)).pack(side="left")
            bv = tk.StringVar(value=BLEND_LABEL.get(layer.blend, "Normal"))
            cb = ttk.Combobox(ctl, textvariable=bv, values=[l for _k, l in BLEND_MODES], state="readonly", width=11)
            cb.pack(side="left", padx=2)
            cb.bind("<<ComboboxSelected>>", lambda e, i=i, bv=bv: self.set_layer_blend(i, BLEND_KEY[bv.get()]))
        self.theme(self.layer_list)

    def drop_layer(self, event, src):
        target = self.layer_list.winfo_containing(event.x_root, event.y_root)
        rows = list(reversed(self.layer_list.winfo_children()))
        while target is not None and target not in rows:
            target = target.master
        if target is None:
            return
        dst = rows.index(target)
        if dst != src:
            self.save_state()
            layers = self.layers()
            layer = layers.pop(src)
            layers.insert(dst, layer)
            if self.cur_layer == src:
                self.cur_layer = dst
            self.changed()

    def add_layer(self):
        self.save_state()
        layers = self.layers()
        layers.append(Layer("Layer %d" % (len(layers) + 1), self.W, self.H))
        self.cur_layer = len(layers) - 1
        self.changed()

    def delete_layer(self):
        layers = self.layers()
        if len(layers) <= 1:
            messagebox.showinfo("Delete Layer", "Cannot delete the only layer.", parent=self.win)
            return
        self.save_state()
        del layers[self.cur_layer]
        self.cur_layer = min(self.cur_layer, len(layers) - 1)
        self.changed()

    def select_layer(self, i):
        if self.mask_mode and i != self.cur_layer:
            self.mask_mode = False
            self.set_status("")
        self.drawing = False
        self.last = (-1, -1)
        self.cur_layer = i
        self.update_tool_display()
        self.render_layers()

    def toggle_layer_vis(self, i):
        self.save_state()
        self.layers()[i].visible = not self.layers()[i].visible
        self.changed()

    def set_layer_opacity(self, i, v):
        self.layers()[i].opacity = max(0.0, min(1.0, v))
        self.redraw()
        self.render_thumbs()

    def set_layer_blend(self, i, mode):
        self.layers()[i].blend = mode
        self.redraw()
        self.render_thumbs()

    def toggle_mask(self, i):
        self.save_state()
        layer = self.layers()[i]
        if layer.mask is None:
            layer.mask = Image.new("L", (self.W, self.H), 255)
            layer.mask_enabled = True
        else:
            layer.mask_enabled = not layer.mask_enabled
        self.changed()

    def toggle_mask_edit(self, i):
        layer = self.layers()[i]
        if layer.mask is None or not layer.mask_enabled:
            messagebox.showinfo("Mask", "Please enable the layer mask first by clicking the mask icon (🎭)", parent=self.win)
            return
        if self.cur_layer != i:
            self.select_layer(i)
        self.mask_mode = not self.mask_mode
        self.mask_color = "#000000"
        self.set_status("🎭 MASK EDITING - Paint with BLACK (hide) - Scroll to switch - Right-click to exit"
                        if self.mask_mode else "Layer editing mode")
        self.update_tool_display()
        self.render_layers()

    def effects_dialog(self, i):
        layer = self.layers()[i]
        top = self.popup()
        top.title("✨ Layer Effects")
        tk.Label(top, text='"%s"' % layer.name, fg="gray").pack(pady=(10, 6), padx=20)
        buttons = {}

        def refresh():
            for key, label in (("dropShadow", "🌑 Drop Shadow"), ("glow", "✨ Outer Glow"), ("stroke", "⬛ Stroke")):
                on = layer.effects.get(key)
                buttons[key].configure(text="%s: %s" % (label, "ON" if on else "OFF"), bg="#4CAF50" if on else "#666666",
                                       fg="white")

        def toggle(key):
            self.save_state()
            layer.effects[key] = not layer.effects.get(key)
            refresh()
            self.changed()

        for key in ("dropShadow", "glow", "stroke"):
            buttons[key] = tk.Button(top, width=26, command=lambda k=key: toggle(k))
            buttons[key]._cp_keep = True
            buttons[key].pack(padx=20, pady=3)

        def all_off():
            self.save_state()
            layer.effects = default_effects()
            refresh()
            self.changed()

        row = tk.Frame(top)
        row.pack(pady=10)
        tk.Button(row, text="🚫 All OFF", bg="#f44336", fg="white", command=all_off).pack(side="left", padx=4)
        tk.Button(row, text="Close", command=top.destroy).pack(side="left", padx=4)
        top.bind("<Escape>", lambda e: top.destroy())
        self.theme(top)
        refresh()

    def rename_layer(self, i):
        name = simpledialog.askstring("✏️ Rename Layer", "Enter new layer name:", initialvalue=self.layers()[i].name,
                                      parent=self.win)
        if name and name.strip():
            self.save_state()
            self.layers()[i].name = name.strip()
            self.render_layers()
