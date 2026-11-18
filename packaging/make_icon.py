"""FRIDAY halka simgesi. Kaynak görselden Windows ICO ve Android mipmap üretir."""

from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "assets" / "friday-mark.png"
ICO = ROOT / "assets" / "friday.ico"
ANDROID = ROOT / "phone-android" / "app" / "src" / "main" / "res"
ICO_SIZES = (16, 24, 32, 48, 64, 128, 256)
LEGACY = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}
ADAPTIVE = {
    "mipmap-mdpi": 108,
    "mipmap-hdpi": 162,
    "mipmap-xhdpi": 216,
    "mipmap-xxhdpi": 324,
    "mipmap-xxxhdpi": 432,
}


def main() -> None:
    image = Image.open(SOURCE).convert("RGBA")
    side = min(image.size)
    left = (image.width - side) // 2
    top = (image.height - side) // 2
    image = image.crop((left, top, left + side, top + side))
    master = image.resize((512, 512), Image.Resampling.LANCZOS)
    master.save(SOURCE)
    layers = [master.resize((size, size), Image.Resampling.LANCZOS) for size in ICO_SIZES]
    layers[-1].save(ICO, format="ICO", sizes=[(size, size) for size in ICO_SIZES], append_images=layers[:-1])
    for folder, size in LEGACY.items():
        dest = ANDROID / folder
        dest.mkdir(parents=True, exist_ok=True)
        tile = master.resize((size, size), Image.Resampling.LANCZOS)
        tile.save(dest / "ic_launcher.png")
        tile.save(dest / "ic_launcher_round.png")
    for folder, size in ADAPTIVE.items():
        dest = ANDROID / folder
        dest.mkdir(parents=True, exist_ok=True)
        tile = master.resize((size, size), Image.Resampling.LANCZOS)
        tile.save(dest / "ic_launcher_foreground.png")
    anydpi = ANDROID / "mipmap-anydpi-v26"
    anydpi.mkdir(parents=True, exist_ok=True)
    xml = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/ic_launcher_background"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
</adaptive-icon>
"""
    (anydpi / "ic_launcher.xml").write_text(xml, encoding="utf-8")
    (anydpi / "ic_launcher_round.xml").write_text(xml, encoding="utf-8")
    values = ANDROID / "values"
    values.mkdir(parents=True, exist_ok=True)
    (values / "colors.xml").write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<resources>
    <color name="ic_launcher_background">#050505</color>
</resources>
""",
        encoding="utf-8",
    )
    print("icon-ready")


if __name__ == "__main__":
    main()
