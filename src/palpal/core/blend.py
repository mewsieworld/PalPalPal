"""Blend modes, for one color or whole images."""

from .common import *  # noqa: F401,F403  (stdlib, Tk, Pillow and the app constants)


BLEND_MODES = ["Normal", "Multiply", "Screen", "Overlay", "Darken", "Lighten", "Difference", "Add",
               "Soft Light", "Hard Light"]


def blend_channel(a, b, mode):
    """One 0-255 channel of color b laid over color a with a blend mode."""
    if mode == "Multiply":
        return a * b // 255
    if mode == "Screen":
        return 255 - (255 - a) * (255 - b) // 255
    if mode == "Overlay":
        return 2 * a * b // 255 if a < 128 else 255 - 2 * (255 - a) * (255 - b) // 255
    if mode == "Hard Light":
        return 2 * a * b // 255 if b < 128 else 255 - 2 * (255 - a) * (255 - b) // 255
    if mode == "Soft Light":
        return min(255, ((255 - 2 * b) * a * a // 255 + 2 * b * a) // 255)
    if mode == "Darken":
        return min(a, b)
    if mode == "Lighten":
        return max(a, b)
    if mode == "Difference":
        return abs(a - b)
    if mode == "Add":
        return min(255, a + b)
    return b


def blend_color(under, over, mode, opacity):
    mixed = [blend_channel(under[k], over[k], mode) for k in range(3)]
    return tuple(int(round(under[k] + (mixed[k] - under[k]) * opacity)) for k in range(3))


def blend_images(under, over, mode):
    """RGB result of laying image over on image under with a blend mode (both RGB, same size)."""
    ops = {"Multiply": ImageChops.multiply, "Screen": ImageChops.screen, "Overlay": ImageChops.overlay,
           "Darken": ImageChops.darker, "Lighten": ImageChops.lighter, "Difference": ImageChops.difference,
           "Add": lambda a, b: ImageChops.add(a, b), "Soft Light": ImageChops.soft_light,
           "Hard Light": ImageChops.hard_light}
    op = ops.get(mode)
    return op(under, over) if op else over
