"""Saving and loading .palpal project files."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .colors import pad256
from .images import Frame, ImageLayer, PaletteLayer, to_indexed


# ---------------------------------------------------------------------------
# Project files (JSON with the frames embedded as indexed PNGs)
# ---------------------------------------------------------------------------

def _png_b64(img):
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _palette_state(p):
    return {"name": p.name, "colors": [list(c) for c in p.colors], "loaded": [list(c) for c in p.loaded_colors],
            "active": p.active, "size": p.size, "source": p.source_path, "blend": p.blend, "opacity": p.opacity}


def _apply_palette_state(p, d):
    p.name = d.get("name", p.name)
    p.colors = pad256(d.get("colors", p.colors))
    p.loaded_colors = pad256(d.get("loaded", p.colors))
    p.active = bool(d.get("active", True))
    p.size = int(d.get("size", PALETTE_SIZE))
    p.source_path = d.get("source", "")
    p.blend = d.get("blend", "Normal")
    p.opacity = float(d.get("opacity", 1.0))


def _source_state(il, stack):
    src = il.palette_source
    return {"palette": stack.index(src)} if isinstance(src, PaletteLayer) and src in stack else (
        src if src in ("stack", "own") else "stack")


def save_project_file(path, app):
    stack = []
    for entry in app.stack:
        if isinstance(entry, ImageLayer):
            stack.append({"type": "image", "name": entry.name, "visible": entry.visible, "opacity": entry.opacity,
                          "blend": entry.blend, "palette_source": _source_state(entry, app.stack),
                          "combined": entry.combined,
                          "height_map": _png_b64(entry.height_map) if getattr(entry, "height_map", None) else None,
                          "source": entry.source_path, "palette": _palette_state(entry.palettes[0]),
                          "frame_palettes": [_palette_state(q) for q in entry.palettes] if len(entry.palettes) > 1
                          else None,
                          "frames": [{"name": f.name, "png": _png_b64(f.image)} for f in entry.frames]})
        else:
            state = _palette_state(entry)
            state["type"] = "palette"
            stack.append(state)
    data = {"app": APP_NAME, "version": 1, "stack": stack,
            "key_color": list(app.key_color) if app.key_color else None,
            "bg_color": list(app.bg_color) if app.bg_color is not None else None,
            "bg_transparent": app.bg_color is None,
            "hidden_frames": sorted(app.hidden_frames), "flip": app.flip, "rotation": app.rotation,
            "loop_range": list(app.loop_range) if app.loop_range else None,
            "selected_layer": app.selected_layer, "split_palettes": app.split_palettes,
            "heights": app.heights.to_dict()}
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f)
    os.replace(tmp, path)  # never leaves a half-written project behind


def load_project_file(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    stack = []
    for d in data.get("stack", []):
        if d.get("type") == "image":
            frames = []
            for fd in d["frames"]:
                img = Image.open(io.BytesIO(base64.b64decode(fd["png"])))
                img.load()
                frames.append(Frame(to_indexed(img), fd.get("name", d["name"]), d.get("source", "")))
            il = ImageLayer(d["name"], frames, d.get("source", ""))
            il.visible = bool(d.get("visible", True))
            il.opacity = float(d.get("opacity", 1.0))
            il.blend = d.get("blend", "Normal")
            _apply_palette_state(il.palette, d.get("palette", {}))
            if d.get("frame_palettes"):
                il.palettes = []
                for state in d["frame_palettes"]:
                    q = PaletteLayer(state.get("name", il.name), state.get("colors", []), owner=il)
                    _apply_palette_state(q, state)
                    il.palettes.append(q)
            il.combined = bool(d.get("combined", True))
            if d.get("height_map"):
                il.height_map = Image.open(io.BytesIO(base64.b64decode(d["height_map"]))).convert("L")
            il.palette_source = d.get("palette_source", "stack")
            stack.append(il)
        else:
            p = PaletteLayer(d.get("name", "Palette"), d.get("colors", []))
            _apply_palette_state(p, d)
            stack.append(p)
    for il in stack:
        src = getattr(il, "palette_source", None)
        if isinstance(src, dict):
            i = src.get("palette")
            il.palette_source = stack[i] if isinstance(i, int) and 0 <= i < len(stack) and                 isinstance(stack[i], PaletteLayer) else "stack"
    return {"stack": stack,
            "key_color": tuple(data["key_color"]) if data.get("key_color") else None,
            "bg_color": tuple(data["bg_color"]) if data.get("bg_color") else None,
            "bg_transparent": bool(data.get("bg_transparent")),
            "hidden_frames": set(data.get("hidden_frames", [])),
            "flip": bool(data.get("flip", False)), "rotation": int(data.get("rotation", 0)) % 4,
            "selected_layer": int(data.get("selected_layer", 0)),
            "split_palettes": bool(data.get("split_palettes", False)),
            "heights": data.get("heights"),
            "loop_range": tuple(data["loop_range"]) if data.get("loop_range") else None}
