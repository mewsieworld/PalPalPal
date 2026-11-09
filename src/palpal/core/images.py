"""Indexed images: reading, converting, merging frame palettes and requantizing."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .colors import flat_palette, luminosity, pad256
from .layers import Frame


# ---------------------------------------------------------------------------
# Images, frames and layers
# ---------------------------------------------------------------------------

def read_image_frames(path):
    """Every frame of an image file as Pillow images (GIF frames keep their palettes)."""
    img = Image.open(path)
    frames = [frame.copy() for frame in ImageSequence.Iterator(img)]
    if not frames:
        raise ValueError("the file has no frames")
    return frames


def is_indexed(img):
    """True when the image already is a palette image PalPalPal can edit as-is."""
    return img.mode in ("P", "1", "L")


def to_indexed(img):
    """An indexed (or 1-bit / grey) image as a P-mode image."""
    if img.mode == "P":
        return img.copy()
    gray = img.convert("L")
    out = Image.frombytes("P", gray.size, gray.tobytes())
    out.putpalette([v for i in range(256) for v in (i, i, i)])
    return out


def exact_indexed(img):
    """A lossless palette copy of an image that has at most 256 colors and only fully clear or solid pixels."""
    rgba = img.convert("RGBA")
    colors = rgba.getcolors(PALETTE_SIZE + 1)
    if colors is None or any(0 < c[1][3] < 255 for c in colors):
        return None
    solid = sorted({c[1][:3] for c in colors if c[1][3] == 255})
    clear = any(c[1][3] == 0 for c in colors)
    if len(solid) + clear > PALETTE_SIZE:
        return None
    lookup = {color: i for i, color in enumerate(solid)}
    clear_index = len(solid) if clear else None
    data = bytes(clear_index if a == 0 else lookup[(r, g, b)] for r, g, b, a in rgba.getdata())
    out = Image.frombytes("P", rgba.size, data)
    out.putpalette(flat_palette(solid + ([(0, 0, 0)] if clear else [])))
    if clear:
        out.info["transparency"] = clear_index
    return out


def convert_image(img, colors=PALETTE_SIZE, key=None):
    """Make an indexed copy of any image (the Png32ToBmp8 approach, done in memory).

    Transparent areas are flattened onto the key color (magenta when there is none yet), then the
    picture is median-cut down to the palette size. Returns (P image, key color used or None).
    """
    has_alpha = img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info
    bg = tuple(key) if key else (255, 0, 255)
    if has_alpha:
        rgba = img.convert("RGBA")
        base = Image.new("RGBA", rgba.size, bg + (255,))
        base.alpha_composite(rgba)
        rgb = base.convert("RGB")
    else:
        rgb = img.convert("RGB")
    out = rgb.quantize(colors=max(2, min(PALETTE_SIZE, colors)), method=Image.Quantize.MEDIANCUT)
    if not has_alpha:
        return out, None
    # Median cut can blur the background color slightly, so pin the closest slot back to it exactly
    pal = out.getpalette()[:768]
    used = [i for i, n in enumerate(out.histogram()[:PALETTE_SIZE]) if n]
    nearest = min(used, key=lambda i: sum((pal[i * 3 + k] - bg[k]) ** 2 for k in range(3)))
    pal[nearest * 3:nearest * 3 + 3] = list(bg)
    out.putpalette(pal)
    out.info["transparency"] = nearest   # the slot the transparent areas went to stays see-through
    return out, bg


def dropped_colors(originals, converted, limit=PALETTE_SIZE):
    """Colors of the original picture that the converted palette left out, most used first."""
    kept = set()
    for img in converted:
        pal = img.getpalette() or []
        for i in [i for i, n in enumerate(img.histogram()[:PALETTE_SIZE]) if n]:
            kept.add(tuple(pal[i * 3:i * 3 + 3]))
    counts = {}
    for img in originals:
        rgba = img.convert("RGBA")
        for n, (r, g, b, a) in rgba.getcolors(rgba.width * rgba.height) or []:
            if a and (r, g, b) not in kept:
                counts[(r, g, b)] = counts.get((r, g, b), 0) + n
    return [c for c, _n in sorted(counts.items(), key=lambda item: -item[1])][:limit]


def unify_frame_palettes(frames):
    """Give every frame of an animation one shared palette, so one palette layer can color them all."""
    if len(frames) < 2 or all(f.palette == frames[0].palette and f.transparent_index == frames[0].transparent_index
                              for f in frames):
        return frames
    clear = "transparent"
    colors, lookup, tables = [], {}, []
    for f in frames:
        table = list(range(256))
        for i in f.used_indices():
            color = clear if i == f.transparent_index else f.palette[i]
            if color not in lookup:
                lookup[color] = len(colors)
                colors.append(color)
            table[i] = lookup[color]
        tables.append(table)
    if len(colors) <= PALETTE_SIZE:
        clear_index = lookup.get(clear)
        palette = [(0, 0, 0) if c == clear else c for c in colors]
        out = []
        for f, table in zip(frames, tables):
            img = Image.frombytes("P", f.image.size, f.image.tobytes().translate(bytes(table)))
            img.putpalette(flat_palette(palette))
            if clear_index is not None:
                img.info["transparency"] = clear_index
            out.append(Frame(img, f.name, f.source_path))
        return out
    # Too many colors between them: quantize the frames together on one sheet
    w = max(f.image.width for f in frames)
    sheet = Image.new("RGBA", (w, sum(f.image.height for f in frames)), (0, 0, 0, 0))
    y = 0
    for f in frames:
        sheet.paste(f.image.convert("RGBA"), (0, y))
        y += f.image.height
    indexed, key = convert_image(sheet)
    out, y = [], 0
    for f in frames:
        part = indexed.crop((0, y, f.image.width, y + f.image.height))
        part.putpalette(indexed.getpalette())
        out.append(Frame(part, f.name, f.source_path))
        y += f.image.height
    return out


def frame_fits_palette(frame, layer):
    """True when a frame's used colors already match the layer palette index for index."""
    pal = layer.palette.colors
    return all(frame.palette[i] == pal[i] for i in frame.used_indices() if i != frame.transparent_index)


def merge_frames_into_palette(layer, frames):
    """Re-index frames onto a layer's palette, adding new colors into slots no frame of the layer uses."""
    pal = layer.palette.colors
    used = set()
    for f in layer.frames:
        used.update(f.used_indices())
    lookup = {pal[i]: i for i in sorted(used)}
    free = [i for i in range(PALETTE_SIZE) if i not in used]
    clear = next((f.transparent_index for f in layer.frames if f.transparent_index is not None), None)
    out = []
    for f in frames:
        table = list(range(256))
        for i in f.used_indices():
            if i == f.transparent_index:
                if clear is None:
                    clear = free.pop(0) if free else 0
                table[i] = clear
                continue
            color = f.palette[i]
            if color not in lookup:
                if free:
                    j = free.pop(0)
                    pal[j] = color
                    layer.palette.loaded_colors[j] = color
                    lookup[color] = j
                else:
                    lookup[color] = min(range(PALETTE_SIZE),
                                        key=lambda k: sum((pal[k][c] - color[c]) ** 2 for c in range(3)))
            table[i] = lookup[color]
        img = Image.frombytes("P", f.image.size, f.image.tobytes().translate(bytes(table)))
        img.putpalette(flat_palette(pal))
        if clear is not None:
            img.info["transparency"] = clear
        out.append(Frame(img, f.name, f.source_path))
    return out


def sample_unique_colors(img, limit=PALETTE_SIZE):
    """The first `limit` distinct opaque colors of an image, darkest first (as the web tool sampled them)."""
    seen, out = set(), []
    for r, g, b, a in img.convert("RGBA").getdata():
        if a < 10 or (r, g, b) in seen:
            continue
        seen.add((r, g, b))
        out.append((r, g, b))
        if len(out) >= limit:
            break
    out.sort(key=luminosity)
    return out


def requantize_layer(il, n, key=None):
    """Bring an image layer down to n colors: all frames together on one shared palette."""
    w, h = max(f.image.width for f in il.frames), max(f.image.height for f in il.frames)
    colors = il.palette.colors
    sheet = Image.new("RGBA", (w * len(il.frames), h), (0, 0, 0, 0))
    for k, f in enumerate(il.frames):
        img = f.image.copy()
        img.putpalette(flat_palette(colors))
        rgba = img.convert("RGBA")
        if f.transparent_index is not None:
            rgba.putalpha(Image.frombytes("L", img.size, img.tobytes()).point(
                [0 if i == f.transparent_index else 255 for i in range(256)]))
        sheet.paste(rgba, (k * w, 0))
    indexed, _key = convert_image(sheet, n, key)
    il.frames = [Frame(indexed.crop((k * w, 0, k * w + f.image.width, f.image.height)), f.name, f.source_path)
                 for k, f in enumerate(il.frames)]
    for q in il.palettes:
        q.colors[:] = pad256(il.frames[0].palette)
        q.loaded_colors = list(q.colors)
