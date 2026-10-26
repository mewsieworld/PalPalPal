"""Artwork Tool: layers, frames and the animation preview."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .look import round_button
from .model import Layer, default_effects


class LayersFramesMixin:
    """Layers panel, animation frames, timeline and the animation preview."""

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

    # ----- frames -----
    def load_frame(self, index):
        index = max(0, min(len(self.frames) - 1, index))
        self.cur_frame = index
        self.cur_layer = 0
        self.refresh_all()

    def add_frame(self, kind="clone"):
        self.save_state()
        new = [l.clone() for l in self.layers()] if kind == "clone" else [Layer("Layer 1", self.W, self.H)]
        pos = self.cur_frame + 1
        self.frames.insert(pos, new)
        self.tags.insert(pos, "")
        self.durations.insert(pos, None)
        self.load_frame(pos)

    def delete_frame(self):
        if len(self.frames) <= 1:
            messagebox.showinfo("Delete", "Cannot delete the only frame.", parent=self.win)
            return
        self.save_state()
        del self.frames[self.cur_frame]
        del self.tags[self.cur_frame]
        del self.durations[self.cur_frame]
        self.load_frame(min(self.cur_frame, len(self.frames) - 1))

    def copy_frame(self):
        self.frame_clip = [l.clone() for l in self.layers()]
        messagebox.showinfo("Copy", "Frame %d copied to clipboard!\n(%d layers)" % (self.cur_frame + 1, len(self.frame_clip)),
                            parent=self.win)

    def paste_frame(self):
        if not self.frame_clip:
            messagebox.showinfo("Paste", "No frame in clipboard!\nUse 'Copy' first.", parent=self.win)
            return
        self.save_state()
        self.frames[self.cur_frame] = [l.clone() for l in self.frame_clip]
        self.cur_layer = 0
        self.changed()

    def move_frame(self, a, b):
        if a == b or not (0 <= a < len(self.frames)) or not (0 <= b < len(self.frames)):
            return
        self.save_state()
        for seq in (self.frames, self.tags, self.durations):
            seq.insert(b, seq.pop(a))
        if a == self.cur_frame:
            self.cur_frame = b
        self.load_frame(self.cur_frame)

    def move_frame_left(self):
        self.move_frame(self.cur_frame, self.cur_frame - 1 if self.cur_frame > 0 else len(self.frames) - 1)

    def move_frame_right(self):
        self.move_frame(self.cur_frame, self.cur_frame + 1 if self.cur_frame < len(self.frames) - 1 else 0)

    def set_loop(self):
        choice = simpledialog.askstring("🔄 Loop Settings", "Current: Start=%d, End=%s\n\n1 = Set CURRENT frame as loop START (%d)\n"
                                                         "2 = Set CURRENT frame as loop END (%d)\n3 = Reset to full animation"
                                        % (self.loop_start, "Last Frame" if self.loop_end == -1 else self.loop_end,
                                           self.cur_frame, self.cur_frame), parent=self.win)
        if choice == "1":
            self.loop_start = self.cur_frame
        elif choice == "2":
            self.loop_end = self.cur_frame
        elif choice == "3":
            self.loop_start, self.loop_end = 0, -1
        self.loop_lbl.configure(text="Loop: %d-%s" % (self.loop_start + 1, "end" if self.loop_end == -1 else self.loop_end + 1))

    def clear_frame(self):
        self.save_state()
        for layer in self.layers():
            layer.img = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        self.changed()

    def render_thumbs(self):
        c = self.thumb_canvas
        c.delete("all")
        x = 4
        default = self.speed_var.get()
        for i in range(len(self.frames)):
            img = self.composite_frame(i)
            img.thumbnail((THUMB, THUMB), Image.Resampling.NEAREST)
            photo = ImageTk.PhotoImage(img)
            self.photos["thumb%d" % i] = photo
            c.create_rectangle(x - 2, 2, x + THUMB + 2, THUMB + 6, outline="#2196f3" if i == self.cur_frame else "#888",
                               width=2 if i == self.cur_frame else 1)
            c.create_image(x + THUMB // 2, THUMB // 2 + 4, image=photo)
            c.create_text(x + THUMB, THUMB + 4, text=str(i + 1), anchor="se", fill="#888", font=("Arial", 7))
            if self.tags[i]:
                c.create_text(x, 4, text=self.tags[i], anchor="nw", fill="#ff9800", font=("Arial", 7, "bold"))
            if self.durations[i] and self.durations[i] != default:
                c.create_text(x + THUMB, 4, text="%dms" % self.durations[i], anchor="ne", fill="#2196f3", font=("Arial", 7))
            x += THUMB + 8
        c.configure(scrollregion=(0, 0, x, THUMB + 16))
        self.update_timeline()

    def thumb_at(self, event):
        i = int((self.thumb_canvas.canvasx(event.x) - 2) // (THUMB + 8))
        return i if 0 <= i < len(self.frames) else None

    def on_thumb_click(self, event):
        i = self.thumb_at(event)
        if i is not None:
            self._thumb_drag = i
            self.load_frame(i)

    def on_thumb_release(self, event):
        """Dropping a dragged thumbnail on another one moves the frame there."""
        src = getattr(self, "_thumb_drag", None)
        self._thumb_drag = None
        dst = self.thumb_at(event)
        if src is not None and dst is not None and src != dst:
            self.move_frame(src, dst)

    def on_thumb_right(self, event):
        i = self.thumb_at(event)
        if i is None:
            return
        tag = simpledialog.askstring("🏷️ Tag Frame", 'Tag frame %d:\n\nExamples: "idle", "walk-1", "attack"\n\n'
                                                   "Leave empty to remove tag." % (i + 1), initialvalue=self.tags[i],
                                     parent=self.win)
        if tag is not None:
            self.tags[i] = tag.strip()
            self.render_thumbs()

    def on_thumb_double(self, event):
        i = self.thumb_at(event)
        if i is None:
            return
        default = self.speed_var.get()
        v = simpledialog.askinteger("⏱️ Frame Duration", "Frame %d duration (milliseconds):\n\nDefault: %dms\n"
                                                       "0 = use default" % (i + 1, default),
                                    initialvalue=self.durations[i] or default, minvalue=0, parent=self.win)
        if v is not None:
            self.durations[i] = v or None
            self.render_thumbs()

    def toggle_timeline(self):
        if self.timeline_var.get():
            self.timeline_row.pack(fill="x", before=self.thumb_canvas.master)
        else:
            self.timeline_row.pack_forget()
        self.update_timeline()

    def update_timeline(self):
        self.scrub.configure(to=max(0, len(self.frames) - 1))
        self.scrub_var.set(self.cur_frame)
        self.timeline_lbl.configure(text="%d/%d" % (self.cur_frame + 1, len(self.frames)))

    # ----- animation preview -----
    def toggle_preview(self):
        self.playing = not self.playing
        self.play_btn.configure(text="Pause Preview" if self.playing else "Play Preview")
        self.play_btn._paint = "#dc3545" if self.playing else "#28a745"
        round_button(self.play_btn, self.play_btn._paint)
        if self.playing:
            self.preview_tick()

    def preview_tick(self):
        if not self.win.winfo_exists():
            return
        if not self.frames:
            return
        self.anim_frame = min(self.anim_frame, len(self.frames) - 1)
        img = self.composite_frame(self.anim_frame).resize((PREVIEW, PREVIEW), Image.Resampling.NEAREST)
        self.photos["preview"] = ImageTk.PhotoImage(img)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(0, 0, image=self.photos["preview"], anchor="nw")
        self.preview_lbl.configure(text="Frame %d / %d" % (self.anim_frame + 1, len(self.frames)))
        mult = float(self.mult_var.get().rstrip("x"))
        duration = (self.durations[self.anim_frame] or self.speed_var.get()) / mult
        self.fps_lbl.configure(text="FPS ~%.1f" % (1000 / duration))
        end = len(self.frames) - 1 if self.loop_end == -1 else min(self.loop_end, len(self.frames) - 1)
        self.anim_frame += 1
        if self.anim_frame > end:
            self.anim_frame = self.loop_start
        if self.playing:
            self.win.after(max(16, int(duration)), self.preview_tick)
