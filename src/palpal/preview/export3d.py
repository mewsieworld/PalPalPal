"""Writing the 3D bead model to files other programs open:

  .obj (+ .mtl)  Blender, Unity, Godot, most 3D tools: one material per color, only the outer faces
  .vox           MagicaVoxel (and anything that reads it): real voxels, up to 256 beads each way, 255 colors
  .ply           MeshLab, Blender: colors stored on the vertices
  .schematic     Minecraft (MCEdit / WorldEdit / Schematica): every bead becomes the closest wool,
                 concrete or terracotta block

The model comes as cells {(x, y, z): (r, g, b)} with x right, y down (picture order) and z up the layer stack.
In the files, Y points up (the picture stands upright) and Z points out toward the viewer.
"""

import gzip
import os
import struct

from PIL import Image

from .beads import CUBE_FACES


def _outer_faces(cells):
    """(corner points in file space, color) for every bead face nothing covers."""
    h = max(y for _x, y, _z in cells) + 1 if cells else 0
    for (x, y, z), color in cells.items():
        for n, corners in CUBE_FACES:
            if (x + n[0], y + n[1], z + n[2]) in cells:
                continue
            # flip y so up is up; the quad keeps its outward winding because y and the corner order flip together
            pts = [(x + dx, h - (y + dy), z + dz) for dx, dy, dz in reversed(corners)]
            yield pts, color


def write_obj(path, cells):
    base = os.path.splitext(path)[0]
    mtl_name = os.path.basename(base) + ".mtl"
    colors = sorted(set(cells.values()))
    names = {c: "c%02x%02x%02x" % c for c in colors}
    with open(base + ".mtl", "w", encoding="utf-8") as m:
        m.write("# PalPalPal bead model colors\n")
        for c in colors:
            r, g, b = (v / 255.0 for v in c)
            m.write("newmtl %s\nKd %.4f %.4f %.4f\nKa 0 0 0\nd 1\nillum 1\n\n" % (names[c], r, g, b))
    index, verts = {}, []
    by_color = {}
    for pts, color in _outer_faces(cells):
        ids = []
        for p in pts:
            if p not in index:
                index[p] = len(verts) + 1
                verts.append(p)
            ids.append(index[p])
        by_color.setdefault(color, []).append(ids)
    with open(path, "w", encoding="utf-8") as f:
        f.write("# PalPalPal bead model (1 unit = 1 pixel)\nmtllib %s\n" % mtl_name)
        f.writelines("v %d %d %d\n" % v for v in verts)
        for color, quads in by_color.items():
            f.write("usemtl %s\n" % names[color])
            f.writelines("f %d %d %d %d\n" % tuple(q) for q in quads)
    return len(verts), sum(len(q) for q in by_color.values())


def write_ply(path, cells):
    index, verts, faces = {}, [], []
    for pts, color in _outer_faces(cells):
        ids = []
        for p in pts:
            key = (p, color)   # vertices carry the color, so faces of different colors don't share them
            if key not in index:
                index[key] = len(verts)
                verts.append(key)
            ids.append(index[key])
        faces.append(ids)
    with open(path, "w", encoding="utf-8") as f:
        f.write("ply\nformat ascii 1.0\ncomment PalPalPal bead model\nelement vertex %d\n" % len(verts))
        f.write("property float x\nproperty float y\nproperty float z\n"
                "property uchar red\nproperty uchar green\nproperty uchar blue\n")
        f.write("element face %d\nproperty list uchar int vertex_indices\nend_header\n" % len(faces))
        f.writelines("%d %d %d %d %d %d\n" % (p[0], p[1], p[2], c[0], c[1], c[2]) for p, c in verts)
        f.writelines("4 %d %d %d %d\n" % tuple(q) for q in faces)
    return len(verts), len(faces)


def write_vox(path, cells):
    """MagicaVoxel .vox (version 150): one model, its own 255-color palette."""
    if not cells:
        raise ValueError("The model is empty.")
    xs = [x for x, _y, _z in cells]
    ys = [y for _x, y, _z in cells]
    zs = [z for _x, _y, z in cells]
    x0, y0, z0 = min(xs), min(ys), min(zs)
    sx, sy, sz = max(xs) - x0 + 1, max(zs) - z0 + 1, max(ys) - y0 + 1   # vox: x, depth, up
    if max(sx, sy, sz) > 256:
        raise ValueError("MagicaVoxel models can be at most 256 beads in each direction (this one is %d x %d x %d)."
                         " Export it as OBJ or PLY instead." % (sx, sy, sz))
    colors = sorted(set(cells.values()))
    if len(colors) > 255:
        # More colors than a .vox palette holds: share the 255 closest
        strip = Image.new("RGB", (len(colors), 1))
        strip.putdata(colors)
        q = strip.quantize(255)
        pal = q.getpalette()[:765]
        lookup = {c: q.getpixel((i, 0)) + 1 for i, c in enumerate(colors)}
        palette = [tuple(pal[i * 3:i * 3 + 3]) for i in range(255)]
    else:
        lookup = {c: i + 1 for i, c in enumerate(colors)}
        palette = colors
    voxels = b"".join(struct.pack("<BBBB", x - x0, z - z0, (sz - 1) - (y - y0), lookup[c])
                      for (x, y, z), c in cells.items())

    def chunk(name, content, children=b""):
        return name + struct.pack("<ii", len(content), len(children)) + content + children

    rgba = b"".join(struct.pack("<BBBB", r, g, b, 255) for r, g, b in palette)
    rgba += b"\0\0\0\xff" * (256 - len(palette))
    children = chunk(b"SIZE", struct.pack("<iii", sx, sy, sz)) + \
        chunk(b"XYZI", struct.pack("<i", len(cells)) + voxels) + chunk(b"RGBA", rgba)
    with open(path, "wb") as f:
        f.write(b"VOX " + struct.pack("<i", 150) + chunk(b"MAIN", b"", children))
    return len(cells), len(palette)


# Minecraft's 16 dye colors, in data-value order (white, orange, ... black), as each block family looks
_DYES = ["white", "orange", "magenta", "light blue", "yellow", "lime", "pink", "gray", "light gray", "cyan",
         "purple", "blue", "brown", "green", "red", "black"]
MC_BLOCKS = [  # (legacy block id, name, average color per data value)
    (35, "wool", [(234, 236, 237), (241, 118, 20), (189, 68, 179), (58, 175, 217), (249, 198, 40), (112, 185, 26),
                  (238, 141, 172), (63, 68, 72), (142, 142, 135), (21, 138, 145), (122, 42, 173), (53, 57, 157),
                  (114, 72, 41), (85, 110, 28), (161, 39, 35), (21, 21, 26)]),
    (251, "concrete", [(207, 213, 214), (224, 97, 1), (169, 48, 159), (36, 137, 199), (241, 175, 21), (94, 169, 24),
                       (214, 101, 143), (55, 58, 62), (125, 125, 115), (21, 119, 136), (100, 32, 156), (45, 47, 143),
                       (96, 60, 32), (73, 91, 36), (142, 33, 33), (8, 10, 15)]),
    (159, "terracotta", [(210, 178, 161), (162, 84, 38), (150, 88, 109), (113, 109, 138), (186, 133, 35),
                         (104, 118, 53), (162, 78, 79), (58, 42, 36), (135, 107, 98), (87, 91, 91), (118, 70, 86),
                         (74, 60, 91), (77, 51, 36), (76, 83, 42), (143, 61, 47), (37, 23, 16)]),
]


def closest_block(color):
    """(block id, data value) of the wool / concrete / terracotta block that looks most like color."""
    r, g, b = color
    best, pick = None, (35, 0)
    for block, _name, shades in MC_BLOCKS:
        for data, (br, bg, bb) in enumerate(shades):
            # weighted RGB distance: close enough to how eyes judge it, and cheap
            mean = (r + br) / 2.0
            d = (2 + mean / 256) * (r - br) ** 2 + 4 * (g - bg) ** 2 + (2 + (255 - mean) / 256) * (b - bb) ** 2
            if best is None or d < best:
                best, pick = d, (block, data)
    return pick


def _nbt(tag, name, value):
    """One named NBT tag (big-endian), for the few tag types a schematic uses."""
    head = struct.pack(">bH", tag, len(name)) + name.encode("utf-8")
    if tag == 2:     # short
        return head + struct.pack(">h", value)
    if tag == 7:     # byte array
        return head + struct.pack(">i", len(value)) + bytes(value)
    if tag == 8:     # string
        raw = value.encode("utf-8")
        return head + struct.pack(">H", len(raw)) + raw
    if tag == 9:     # empty list of compounds
        return head + struct.pack(">bi", 10, 0)
    raise ValueError(tag)


def write_schematic(path, cells):
    """MCEdit .schematic (gzipped NBT, classic block ids): read by WorldEdit, MCEdit and Schematica.
    The picture stands upright facing south (+Z), so it reads the right way round from the south."""
    if not cells:
        raise ValueError("The model is empty.")
    xs = [x for x, _y, _z in cells]
    ys = [y for _x, y, _z in cells]
    zs = [z for _x, _y, z in cells]
    x0, y0, z0 = min(xs), min(ys), min(zs)
    width, height, length = max(xs) - x0 + 1, max(ys) - y0 + 1, max(zs) - z0 + 1
    if max(width, height, length) > 32767:
        raise ValueError("Schematics can be at most 32767 blocks each way.")
    blocks = bytearray(width * height * length)
    data = bytearray(width * height * length)
    picks = {}
    for (x, y, z), color in cells.items():
        if color not in picks:
            picks[color] = closest_block(color)
        block, value = picks[color]
        up = (height - 1) - (y - y0)
        i = (up * length + (z - z0)) * width + (x - x0)
        blocks[i], data[i] = block, value
    body = (_nbt(2, "Width", width) + _nbt(2, "Height", height) + _nbt(2, "Length", length) +
            _nbt(8, "Materials", "Alpha") + _nbt(7, "Blocks", blocks) + _nbt(7, "Data", data) +
            _nbt(9, "Entities", None) + _nbt(9, "TileEntities", None))
    with gzip.open(path, "wb") as f:
        f.write(struct.pack(">bH", 10, 9) + b"Schematic" + body + b"\0")
    return len(cells), len(set(picks.values()))


WRITERS = {".obj": write_obj, ".ply": write_ply, ".vox": write_vox, ".schematic": write_schematic}
MODEL_TYPES = [("Wavefront OBJ (+ MTL colors)", "*.obj"), ("MagicaVoxel VOX", "*.vox"), ("PLY (vertex colors)", "*.ply"),
               ("Minecraft schematic", "*.schematic")]
