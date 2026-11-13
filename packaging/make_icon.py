"""Altin halkali FRIDAY simgesi. Baska bir urunun simgesi degil."""

from pathlib import Path

from PIL import Image, ImageDraw

SIZE = 256
image = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 255))
draw = ImageDraw.Draw(image)
center = SIZE / 2
gold = (212, 175, 55, 255)
for radius, width in ((118, 8), (92, 5), (64, 4), (28, 0)):
    box = (center - radius, center - radius, center + radius, center + radius)
    if width:
        draw.ellipse(box, outline=gold, width=width)
    else:
        draw.ellipse(box, fill=gold)

out = Path(__file__).resolve().parents[1] / "assets" / "friday.ico"
out.parent.mkdir(parents=True, exist_ok=True)
image.save(out, format="ICO", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print(out)
