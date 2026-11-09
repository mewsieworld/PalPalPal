"""The 3D bead view's model and renderer, kept light:

- The model (which bead faces can be seen at all, and their colors) is built once and cached. It is only
  rebuilt when something that changes it changes (frame, layers, colors, heights, 3D moves, flip / rotation).
  Turning the view reuses it and only re-projects.
- Only faces with no bead next to them are kept, stored as flat tuples (no per-bead objects).
- Projection is orthographic, so each face corner is the face's position plus one of 4 precomputed offsets.
"""

from ..core.common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)
from .heights import height_image

# The six faces of a unit cube: normal, then its corners as offsets from the bead's low corner
CUBE_FACES = [((0, 0, 1), ((0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))),
              ((0, 0, -1), ((0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 0, 0))),
              ((1, 0, 0), ((1, 0, 0), (1, 1, 0), (1, 1, 1), (1, 0, 1))),
              ((-1, 0, 0), ((0, 0, 0), (0, 0, 1), (0, 1, 1), (0, 1, 0))),
              ((0, 1, 0), ((0, 1, 0), (0, 1, 1), (1, 1, 1), (1, 1, 0))),
              ((0, -1, 0), ((0, 0, 0), (1, 0, 0), (1, 0, 1), (0, 0, 1)))]
FACE_LIGHT = (1.0, 0.55, 0.8, 0.7, 0.65, 0.9)   # same order as CUBE_FACES: lit from above
MIRROR_LIGHT = (1.0, 1.0, 0.8, 0.7, 0.65, 0.9)  # Mirror back: the back is lit like the front


def face_light(app):
    return MIRROR_LIGHT if app.heights.mirrored() else FACE_LIGHT


def model_key(app, t, layers):
    """Everything the bead model depends on (not the viewing angle)."""
    parts = [t, app.flip, app.rotation, app.key_color, app.canvas_size(), str(app.heights.to_dict())]
    for il in layers:
        frame = il.frame_at(t)
        parts.append((id(il), id(frame.image), hash(tuple(app.effective_colors(il, t))), il.opacity,
                      getattr(il, "offset3d", None), id(getattr(il, "height_map", None))))
    return tuple(parts)


def build_cells(app, t, layers):
    """Every bead of the model: (x, y, z) -> (r, g, b). x right, y down (as in the picture), z up the stack."""
    cells = {}
    slab = app.heights.slab()
    for k, il in enumerate(layers):
        img = app.transform(app.layer_canvas(il, t))
        px = img.load()
        hmap = height_image(app, il, t, app.canvas_size())
        hp = hmap.load() if hmap is not None else None
        ox, oy, oz = getattr(il, "offset3d", None) or (0, 0, 0)
        base = k * slab + oz
        for y in range(img.height):
            for x in range(img.width):
                r, g, b, a = px[x, y]
                if a >= 128:
                    for z in app.heights.span(hp[x, y] if hp is not None else 1):
                        cells[(x + ox, y + oy, base + z)] = (r, g, b)
    return cells


def build_model(app, t, layers):
    """faces: one (x, y, z, face_index, shaded color) per bead face that nothing covers; plus the model's size."""
    cells = build_cells(app, t, layers)
    slab = app.heights.slab()
    lights = face_light(app)
    faces = []
    for (x, y, z), (r, g, b) in cells.items():
        for i, (n, _corners) in enumerate(CUBE_FACES):
            if (x + n[0], y + n[1], z + n[2]) not in cells:
                light = lights[i]
                faces.append((x, y, z, i, (int(r * light), int(g * light), int(b * light))))
    w, h = app.transformed_size()
    return faces, (w, h, max(1, len(layers) * slab))


def layer_faces(app, t, k, il, slab):
    """One layer's visible faces on its own (in its own place, before any 3D move), for quick moving."""
    img = app.transform(app.layer_canvas(il, t))
    px = img.load()
    hmap = height_image(app, il, t, app.canvas_size())
    hp = hmap.load() if hmap is not None else None
    cells = {}
    base = k * slab
    for y in range(img.height):
        for x in range(img.width):
            r, g, b, a = px[x, y]
            if a >= 128:
                for z in app.heights.span(hp[x, y] if hp is not None else 1):
                    cells[(x, y, base + z)] = (r, g, b)
    lights = face_light(app)
    faces = []
    for (x, y, z), (r, g, b) in cells.items():
        for i, (n, _corners) in enumerate(CUBE_FACES):
            if (x + n[0], y + n[1], z + n[2]) not in cells:
                light = lights[i]
                faces.append((x, y, z, i, (int(r * light), int(g * light), int(b * light))))
    return faces


def moving_model(app, t, layers, cache):
    """While a layer is being dragged: each layer's own faces (cached), shifted by its 3D move. Faces where two
    layers touch aren't hidden here; the full model takes over as soon as the drag stops."""
    slab = app.heights.slab()
    faces = []
    for k, il in enumerate(layers):
        key = (k, slab, t, app.flip, app.rotation, app.key_color, app.canvas_size(), str(app.heights.to_dict()),
               id(il), id(il.frame_at(t).image), hash(tuple(app.effective_colors(il, t))), il.opacity,
               id(getattr(il, "height_map", None)))   # everything but its 3D move
        if key not in cache:
            cache[key] = layer_faces(app, t, k, il, slab)
        ox, oy, oz = getattr(il, "offset3d", None) or (0, 0, 0)
        if ox or oy or oz:
            faces.extend((x + ox, y + oy, z + oz, i, c) for x, y, z, i, c in cache[key])
        else:
            faces.extend(cache[key])
    w, h = app.transformed_size()
    return faces, (w, h, max(1, len(layers) * slab))


def render(faces, size, yaw_deg, pitch_deg, canvas_size, backdrop, zoom=None, outlines=True):
    """Project the cached faces for this angle; returns (image, axes for the Move tool)."""
    w, h, depth = size
    cw, ch = canvas_size
    yaw, pitch = math.radians(yaw_deg), math.radians(pitch_deg)
    cy_, sy_ = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)

    def rot(x, y, z):
        x1 = x * cy_ + z * sy_
        z1 = -x * sy_ + z * cy_
        return x1, y * cp - z1 * sp, y * sp + z1 * cp

    ex, ey, ez = rot(1, 0, 0), rot(0, 1, 0), rot(0, 0, 1)
    cx, cyc, cz = w / 2.0, h / 2.0, depth / 2.0
    origin = rot(-cx, -cyc, -cz)
    box = [rot(x - cx, y - cyc, z - cz) for x in (0, w) for y in (0, h) for z in (0, depth)]
    bw = max(1.0, max(q[0] for q in box) - min(q[0] for q in box))
    bh = max(1.0, max(q[1] for q in box) - min(q[1] for q in box))
    scale = zoom if zoom else min(cw * 0.9 / bw, ch * 0.9 / bh)
    ox, oy = cw / 2.0 + scale * origin[0], ch / 2.0 + scale * origin[1]
    # screen steps for one bead along x, y and z, and each face's 4 corner offsets
    sx = (scale * ex[0], scale * ex[1])
    sy = (scale * ey[0], scale * ey[1])
    sz = (scale * ez[0], scale * ez[1])
    visible = [rot(*n)[2] > 1e-6 for n, _c in CUBE_FACES]
    offsets = [[(dx * sx[0] + dy * sy[0] + dz * sz[0], dx * sx[1] + dy * sy[1] + dz * sz[1])
                for dx, dy, dz in corners] for _n, corners in CUBE_FACES]
    dx_, dy_, dz_ = ex[2], ey[2], ez[2]

    shown = []
    for x, y, z, i, color in faces:
        if visible[i]:
            shown.append((x * dx_ + y * dy_ + z * dz_, x, y, z, i, color))
    shown.sort(key=lambda f: f[0])   # farthest first; the camera looks from +z

    out = Image.new("RGB", (cw, ch), backdrop)
    draw = ImageDraw.Draw(out)
    outline = outlines and scale >= 6
    for _d, x, y, z, i, color in shown:
        bx = ox + x * sx[0] + y * sy[0] + z * sz[0]
        by = oy + x * sx[1] + y * sy[1] + z * sz[1]
        pts = [(bx + a, by + b) for a, b in offsets[i]]
        if outline:
            draw.polygon(pts, fill=color, outline=(max(0, color[0] - 40), max(0, color[1] - 40), max(0, color[2] - 40)))
        else:
            draw.polygon(pts, fill=color)
    return out, ((ex[0], ex[1]), (ey[0], ey[1]), scale)
