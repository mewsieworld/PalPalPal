"""PalPalPal main window: the Layers box."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.colors import to_hex
from ..core.images import BLEND_MODES, ImageLayer, PaletteLayer, clone_palette
from ..ui.theme import Theme, Tooltip
from .layer_rows import AppLayerRowsMixin


class AppLayersMixin(AppLayerRowsMixin):
    """The Layers box: rows, selection, separate / combine, frame palette tabs."""

    def set_palette_source(self, il, source):
        il.palette_source = source
        self.mark_dirty()
        self.compact.clear_state()
        self.structure_changed()

    # ----- separate / combine, filter, frame tabs -----
    def separate_layer(self, il):
        """Split a combined image layer into an image-only layer and a palette layer right above it."""
        if not il.combined:
            return
        pos = self.stack.index(il)
        palette = clone_palette(il.palette, None, "%s palette" % il.name)
        self.stack.insert(pos + 1, palette)
        il.combined = False
        il.palette_source = "stack"
        self.selected_layer = self.layers.index(palette)
        self.compact.clear_state()
        self.structure_changed()
        self.request_redraw()

    def combine_layer(self, entry):
        """Fold a palette into an image: the image-only layer and the palette above it (or below a palette)."""
        if isinstance(entry, PaletteLayer):
            images = self.images_colored_by(entry)
            if not images:
                messagebox.showinfo("Combine", "There is no image under this palette to combine it with.")
                return
            il, palette = images[0], entry
        else:
            il = entry
            over = self.stacked_palettes(il)
            palette = over[-1] if over else None
        if palette is not None:
            il.palette.colors[:] = list(palette.colors)
            il.palette.size = palette.size
            if palette in self.stack and self.stack.index(palette) == self.stack.index(il) + 1 or \
                    il.palette_source is palette:
                self.stack.remove(palette)
        il.combined = True
        il.palette_source = "stack"
        self.selected_layer = self.layers.index(il.palette)
        self.compact.clear_state()
        self.structure_changed()
        self.request_redraw()

    def set_layer_filter(self, value):
        self.layer_filter = value
        self.refresh_layers_box()

    def refresh_palette_tabs(self):
        if not hasattr(self, "tab_row"):
            return
        count = self.frame_count()
        if self.split_palettes and count > 1:
            self.palette_tab %= count
            self.tab_lbl.configure(text="Frame %d / %d palettes" % (self.palette_tab + 1, count))
            if not self.tab_row.winfo_ismapped():
                self.tab_row.pack(fill="x", padx=4, before=self.layer_rows.master.master)
        else:
            self.tab_row.pack_forget()

    def set_palette_tab(self, tab):
        """Show (and edit) the palettes of another frame, and move the preview there."""
        count = self.frame_count()
        if not count:
            return
        palette = self.selected_palette()
        owner_pos = self.stack.index(palette.owner) if palette is not None and palette.owner in self.stack else None
        self.palette_tab = tab % count
        for il in self.image_layers():
            il.palette_frame = self.palette_tab % len(il.frames)
        if owner_pos is not None:
            self.selected_layer = self.layers.index(self.stack[owner_pos].palette)
        self.current_frame = self.palette_tab
        self.compact.clear_state()
        self.structure_changed()
        self.request_redraw()

    def set_split_palettes(self, on):
        if on == self.split_palettes:
            return
        if not on and any(len(il.palettes) > 1 and any(q.colors != il.palettes[0].colors for q in il.palettes)
                          for il in self.image_layers()):
            if not messagebox.askyesno("Separate Palettes by Frames",
                                       "Some frames have their own palette edits. Turning this off keeps only the "
                                       "palette of the frame you're on. Continue?"):
                return False
        for il in self.image_layers():
            il.palette_frame = self.palette_tab % len(il.frames) if on else il.palette_frame
            il.split_palettes(on)
        self.split_palettes = on
        self.palette_tab = 0
        self.compact.clear_state()
        self.structure_changed()
        self.request_redraw()
        return True

    def layer_colors_changed(self, layer):
        """Keep the other open editors in step when one of them edits a palette."""
        if layer is None:
            return
        self.mark_dirty()
        if self.switcher and self.switcher.win.winfo_exists() and self.switcher.layer() is layer:
            self.switcher.refresh_swatches()
            self.switcher.update_preview_soon()
        if layer is self.compact.layer():
            self.compact.redraw()

    def select_layer(self, index):
        if index == self.selected_layer:
            return
        self.selected_layer = index
        self.compact.clear_state()
        self.refresh_layers_box()
        self.update_compact_palette_editor()
        if self.switcher and self.switcher.win.winfo_exists():
            names = self.switcher._names()
            if 0 <= index < len(names) and self.switcher.target_var.get() != names[index]:
                self.switcher.target_var.set(names[index])
                self.switcher.on_target_changed()

    def structure_changed(self):
        """Layers, frames or the key color changed."""
        self.mark_dirty()
        for il in self.image_layers():
            il.sync_palette_count()
        if self.selected_layer >= len(self.layers):
            self.selected_layer = len(self.layers) - 1
        if self.selected_layer < 0 and self.layers:
            self.selected_layer = len(self.layers) - 1
        self.refresh_layers_box()
        self.apply_view_mode()
        if self.switcher and self.switcher.win.winfo_exists():
            if not self.layers:
                self.switcher.win.destroy()
                self.switcher = None
            else:
                self.switcher.layers = self.layers
                self.switcher.originals.update({id(ly): list(ly.colors) for ly in self.layers
                                                if id(ly) not in self.switcher.originals})
                names = self.switcher._names()
                if self.switcher.target_var.get() not in names:
                    self.switcher.target_var.set(names[max(0, self.selected_layer)])
                self.switcher.build()

    def toggle_entry(self, entry, on):
        if isinstance(entry, ImageLayer):
            entry.visible = on
        else:
            entry.active = on
        self.mark_dirty()
        self.refresh_layers_box()
        self.request_redraw()

    def move_layer(self, step):
        """Move the selected row up (+1) or down (-1) the stack."""
        entry = self.entry_of(self.selected_palette())
        if entry is None:
            return
        i = self.stack.index(entry)
        j = i + step
        if not 0 <= j < len(self.stack):
            return
        palette = self.selected_palette()
        self.stack[i], self.stack[j] = self.stack[j], self.stack[i]
        self.selected_layer = self.layers.index(palette)
        self.structure_changed()

    def remove_layer(self):
        entry = self.entry_of(self.selected_palette())
        if entry is None:
            return
        if not messagebox.askyesno("Remove layer", "Remove '%s' from the project?" % entry.name):
            return
        i = self.stack.index(entry)
        del self.stack[i]
        self.selected_layer = min(max(0, i - 1), len(self.layers) - 1)
        self.compact.clear_state()
        self.hidden_frames = {t for t in self.hidden_frames if t < self.frame_count()}
        self.structure_changed()

    # ----- layer row helpers -----
    def entry_shown(self, entry):
        return entry.visible if isinstance(entry, ImageLayer) else entry.active

    def set_entry_effect(self, entry, blend=None, opacity=None):
        if blend is not None:
            entry.blend = blend
        if opacity is not None:
            entry.opacity = max(0.0, min(1.0, opacity))
        self.mark_dirty()
        self.refresh_layers_box()
        self.request_redraw()

    def ask_opacity(self, entry):
        value = simpledialog.askinteger("Opacity", "Opacity for %s (0-100%%):" % entry.name,
                                        initialvalue=round(entry.opacity * 100), minvalue=0, maxvalue=100,
                                        parent=self.master)
        if value is not None:
            self.set_entry_effect(entry, opacity=value / 100.0)

    def new_palette_layer(self):
        """A new palette layer right above the selected row, starting from the colors that row shows."""
        entry = self.entry_of(self.selected_palette())
        if entry is None:
            colors, pos = [(0, 0, 0)] * PALETTE_SIZE, len(self.stack)
        else:
            pos = self.stack.index(entry) + 1
            if isinstance(entry, ImageLayer):
                colors = self.effective_colors(entry, self.current_frame)
            else:
                colors = list(entry.colors)
        count = sum(1 for e in self.stack if isinstance(e, PaletteLayer)) + 1
        palette = PaletteLayer("Palette %d" % count, colors)
        self.stack.insert(pos, palette)
        self.selected_layer = self.layers.index(palette)
        self.compact.clear_state()
        self.structure_changed()
        self.request_redraw()

    def toggle_selected_layer(self):
        """The timeline's Show / Hide Layer button."""
        entry = self.entry_of(self.selected_palette())
        if entry is not None:
            self.toggle_entry(entry, not self.entry_shown(entry))

    def refresh_layer_vis_button(self):
        btn = getattr(self, "layer_vis_btn", None)
        if btn is None:
            return
        entry = self.entry_of(self.selected_palette())
        btn.configure(text="Show Layer" if entry is not None and not self.entry_shown(entry) else "Hide Layer",
                      state="normal" if entry is not None else "disabled")

    def rename_entry(self, entry):
        """Local rename: kept in this computer's user file, keyed by where the layer came from."""
        name = simpledialog.askstring("Rename", "New name:", initialvalue=entry.name, parent=self.master)
        if not name:
            return
        entry.name = name
        if isinstance(entry, ImageLayer):
            entry.palette.name = "%s palette" % name
        key = entry.source_path or entry.name
        names = dict(self.store.get("local_names") or {})
        names[key] = name
        self.store.set("local_names", names)
        self.structure_changed()

    def apply_local_name(self, entry):
        name = (self.store.get("local_names") or {}).get(entry.source_path) if entry.source_path else None
        if name:
            entry.name = name
            if isinstance(entry, ImageLayer):
                entry.palette.name = "%s palette" % name
