"""Reading and writing palette files in every supported format."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .colors import _unit, cmyk_to_rgb, lab_to_rgb, pad256, parse_color_any, parse_hex, to_hex


def _read_aco(data):
    """Adobe Color Swatch (.aco): version 1 block (version 2 repeats it with names)."""
    version, count = struct.unpack(">HH", data[:4])
    out, pos = [], 4
    for _ in range(count):
        space, w, x, y, z = struct.unpack(">HHHHH", data[pos:pos + 10])
        pos += 10
        if version == 2:
            name_len = struct.unpack(">I", data[pos:pos + 4])[0]
            pos += 4 + name_len * 2
        if space == 0:
            out.append((w // 257, x // 257, y // 257))
        elif space == 1:
            r, g, b = colorsys.hsv_to_rgb(w / 65535.0, x / 65535.0, y / 65535.0)
            out.append((int(round(r * 255)), int(round(g * 255)), int(round(b * 255))))
        elif space == 2:
            out.append(cmyk_to_rgb(1 - w / 65535.0, 1 - x / 65535.0, 1 - y / 65535.0, 1 - z / 65535.0))
        elif space == 7:
            a, b = struct.unpack(">hh", struct.pack(">HH", x, y))  # a* and b* are signed
            out.append(lab_to_rgb(w / 100.0, a / 100.0, b / 100.0))
        elif space == 8:
            v = int(round(255 * (1 - w / 10000.0)))
            out.append((v, v, v))
    if version == 1 and pos + 4 <= len(data):
        try:
            v2 = _read_aco(data[pos:])  # prefer the named copy when it is there
            if v2:
                return v2
        except struct.error:
            pass
    return out


def _read_ase(data):
    """Adobe Swatch Exchange (.ase)."""
    count = struct.unpack(">I", data[8:12])[0]
    out, pos = [], 12
    for _ in range(count):
        kind, length = struct.unpack(">HI", data[pos:pos + 6])
        body = data[pos + 6:pos + 6 + length]
        pos += 6 + length
        if kind != 0x0001:
            continue  # group start / end
        name_len = struct.unpack(">H", body[:2])[0]
        q = 2 + name_len * 2
        model = body[q:q + 4]
        q += 4
        n = {b"RGB ": 3, b"CMYK": 4, b"LAB ": 3, b"Gray": 1}.get(model)
        if n is None:
            continue
        vals = struct.unpack(">%df" % n, body[q:q + 4 * n])
        if model == b"RGB ":
            out.append(tuple(_unit(v) for v in vals))
        elif model == b"CMYK":
            out.append(cmyk_to_rgb(*vals))
        elif model == b"LAB ":
            out.append(lab_to_rgb(vals[0] * 100, vals[1], vals[2]))
        else:
            v = _unit(vals[0])
            out.append((v, v, v))
    return out


def _read_kpl(data):
    """Krita palette (.kpl): a zip holding colorset.xml with 0-1 float RGB entries."""
    import xml.etree.ElementTree as ET
    import zipfile
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        root = ET.fromstring(z.read("colorset.xml"))
    out = []
    for entry in root.iter("ColorSetEntry"):
        for child in entry:
            tag = child.tag.upper()
            if tag in ("RGB", "SRGB") and child.get("r") is not None:
                out.append(tuple(_unit(child.get(k)) for k in "rgb"))
                break
            if tag == "CMYK" and child.get("c") is not None:
                out.append(cmyk_to_rgb(*(float(child.get(k)) for k in "cmyk")))
                break
            if tag == "GRAY" and child.get("g") is not None:
                v = _unit(child.get("g"))
                out.append((v, v, v))
                break
    return out


def _palette_from_image(path):
    """An indexed image gives its palette in index order; any other image gives its colors (up to 256)."""
    img = Image.open(path)
    if img.mode == "P":
        raw = img.getpalette() or []
        count = max([i for i, n in enumerate(img.histogram()[:PALETTE_SIZE]) if n] or [0]) + 1
        count = max(count, len(raw) // 3) if len(raw) // 3 <= PALETTE_SIZE else PALETTE_SIZE
        return [tuple(raw[i * 3:i * 3 + 3]) for i in range(min(count, len(raw) // 3))]
    rgba = img.convert("RGBA")
    colors = rgba.getcolors(PALETTE_SIZE)
    if colors is None:
        raise ValueError("That image has more than 256 colors, so it can't be used as a palette as-is.\n"
                         "Import it as an image instead (it will be converted).")
    seen = []
    for _n, c in sorted(colors, key=lambda nc: -nc[0]):
        if c[3] and c[:3] not in seen:
            seen.append(c[:3])
    return seen


def _rgb_rows(lines):
    """'r g b [name]' rows (GIMP .gpl, KDE .colors); header and comment lines are skipped."""
    out = []
    for line in lines:
        bits = line.split()
        if len(bits) >= 3 and all(b.isdigit() for b in bits[:3]):
            out.append(tuple(int(b) for b in bits[:3]))
    return out


def read_palette(path):
    """Read a palette file into a list of RGB tuples (not padded)."""
    with open(path, "rb") as f:
        data = f.read()
    ext = os.path.splitext(path)[1].lower()

    if data[:4] == b"RIFF" and data[8:12] == b"PAL ":
        pos = data.find(b"data", 12)
        count = struct.unpack("<H", data[pos + 10:pos + 12])[0]
        start = pos + 12
        return [tuple(data[start + 4 * k:start + 4 * k + 3]) for k in range(count)]
    if data[:4] == b"ASEF":
        return _read_ase(data)
    if ext == ".aco":
        return _read_aco(data)
    if ext == ".kpl" or (data[:2] == b"PK" and b"colorset.xml" in data):
        return _read_kpl(data)
    if ext in (".afpalette", ".cls"):
        app = "Affinity" if ext == ".afpalette" else "Clip Studio Paint"
        raise ValueError("%s palettes use a private format that can't be read reliably.\nExport the palette from "
                         "%s as .ase (Adobe Swatch Exchange) or .aco and import that instead." % (app, app))
    signature = data[:8] == b"\x89PNG\r\n\x1a\n" or data[:2] == b"BM" or data[:3] == b"GIF"
    if ext in IMAGE_PALETTE_EXTS or (signature and ext not in (".pal", ".act")):
        return _palette_from_image(path)

    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = None

    if text is not None:
        stripped = text.lstrip()
        if stripped.startswith("JASC-PAL"):
            lines = [l.split() for l in stripped.splitlines() if l.strip()]
            count = int(lines[2][0])
            return [tuple(int(v) for v in l[:3]) for l in lines[3:3 + count] if len(l) >= 3]
        if stripped.startswith(("GIMP Palette", "KDE RGB Palette")):
            return _rgb_rows(stripped.splitlines()[1:])
        if ext in (".json", ".sketchpalette") or stripped[:1] in ("[", "{"):
            obj = json.loads(text)
            if isinstance(obj, dict):
                obj = obj.get("colors", obj.get("palette", obj.get("swatches", [])))
            out = [parse_color_any(c) for c in obj]
            return [c for c in out if c is not None]
        if ext in (".hex", ".txt") or ext not in (".act", ".pal"):
            out = []
            for line in text.splitlines():
                line = line.strip()
                if not line or line[0] in ";/!":
                    continue
                color = parse_hex(line.split()[0])
                if color:
                    out.append(color)
            if out:
                return out

    if ext == ".act" or len(data) in (768, 772) or (len(data) % 3 == 0 and len(data) <= 768):
        raw = data[:768]
        colors = [tuple(raw[i:i + 3]) for i in range(0, len(raw) - len(raw) % 3, 3)]
        if len(data) == 772:  # Photoshop ACT footer: color count, then the transparent index
            count = struct.unpack(">H", data[768:770])[0]
            if 0 < count <= PALETTE_SIZE:
                colors = colors[:count]
        return colors
    raise ValueError("This palette file is not in a format PalPalPal can read yet.")


def palette_grid_image(colors, size=503):
    """The old 'PNG Grid' palette export: a 16x16 swatch sheet."""
    small = Image.new("RGB", (16, 16))
    small.putdata(pad256(colors))
    return small.resize((size, size), Image.Resampling.NEAREST)


def write_palette(path, colors, pal_style="vga"):
    """Write colors by file extension. pal_style picks raw VGA ("vga") or "jasc" text for .pal files."""
    ext = os.path.splitext(path)[1].lower()
    colors = [parse_color_any(c) or (0, 0, 0) for c in colors]
    if ext == ".json":
        with open(path, "w", encoding="utf-8") as f:
            json.dump([list(c) for c in colors], f)
    elif ext == ".gpl":
        with open(path, "w", encoding="utf-8") as f:
            f.write("GIMP Palette\nName: %s\nColumns: 16\n#\n" % os.path.splitext(os.path.basename(path))[0])
            for i, (r, g, b) in enumerate(colors):
                f.write("%3d %3d %3d\tIndex %d\n" % (r, g, b, i))
    elif ext in (".hex", ".txt"):
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(to_hex(c, False) for c in colors) + "\n")
    elif ext == ".pal" and pal_style == "jasc":
        with open(path, "w", encoding="utf-8") as f:
            f.write("JASC-PAL\n0100\n%d\n" % len(colors))
            for r, g, b in colors:
                f.write("%d %d %d\n" % (r, g, b))
    else:  # .pal raw VGA 24-bit, .act and anything else
        with open(path, "wb") as f:
            for r, g, b in pad256(colors):
                f.write(bytes((r, g, b)))
