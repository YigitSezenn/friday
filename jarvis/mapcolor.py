from __future__ import annotations

from PIL import Image, ImageOps


def tint_gray(image: Image.Image, color_hex: str, black: str = "#140e08") -> Image.Image:
    white = color_hex if str(color_hex).startswith("#") and len(str(color_hex)) == 7 else "#e6c98a"
    return ImageOps.colorize(image.convert("L"), black=black, white=white)
