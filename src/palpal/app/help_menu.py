"""PalPalPal main window: the Help menu (the debug items only show when Document Settings turns them on)
and Help > Reset Layers."""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from ..core.images import ImageLayer
from ..ui.docs_viewer import open_doc
from .cache import clear_cache


class AppHelpMixin:
    def fill_help_menu(self, menu=None):
        """(Re)build the Help menu; Current Display Info and Debug Info only when "show_debug_menu" is on."""
        menu = menu or self.help_menu
        self.help_menu = menu
        menu.delete(0, "end")
        menu.add_command(label="Statistics", command=self.show_statistics)
        menu.add_command(label="Manual", command=lambda: open_doc(self, "manual"))
        menu.add_command(label="Changelog", command=lambda: open_doc(self, "changelog"))
        menu.add_command(label="About %s" % APP_NAME, command=self.show_about)
        menu.add_separator()
        menu.add_command(label="Reset Frames", command=self.reset_frames)
        menu.add_command(label="Reset Pals", command=self.reset_pals)
        menu.add_command(label="Reset Layers", command=self.reset_layers)
        if self.store.get("show_debug_menu"):
            menu.add_separator()
            menu.add_command(label="Current Display Info", command=self.show_current_display_info)
            menu.add_command(label="Debug Info", command=self.debug_info)
            menu.add_separator()
            menu.add_command(label="Clear Cache", command=lambda: clear_cache(self))

    def reset_layers(self):
        """Every layer shown again, at Normal / 100%, images colored by the stack, and the Layers box showing all."""
        if not self.stack:
            messagebox.showinfo("Reset Layers", "There are no layers to reset.")
            return
        if not messagebox.askyesno("Reset Layers", "Show every layer again and put each one back to Normal blend, "
                                                   "100% opacity and the stack's palettes?\n\nThe layers and their "
                                                   "colors themselves stay as they are."):
            return
        for entry in self.stack:
            entry.blend, entry.opacity = "Normal", 1.0
            if isinstance(entry, ImageLayer):
                entry.visible = True
                entry.palette_source = "stack"
            else:
                entry.active = True
        self.layer_filter = "all"
        self.compact.clear_state()
        self.structure_changed()
        self.request_redraw()
