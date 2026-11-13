"""README görselleri. Kişisel veri, anahtar ve telefon adresi içermez."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[1] / "docs"
GOLD = (230, 201, 138)
INK = (243, 230, 200)
BG = (7, 6, 5)


def frame(title: str, lines: list[str], name: str) -> None:
    image = Image.new("RGB", (960, 540), BG)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.ellipse((410, 70, 550, 210), outline=GOLD, width=4)
    draw.ellipse((450, 110, 510, 170), outline=GOLD, width=2)
    draw.text((48, 36), "FRIDAY", fill=GOLD, font=font)
    draw.text((48, 250), title, fill=INK, font=font)
    y = 290
    for line in lines:
        draw.text((48, y), line, fill=GOLD, font=font)
        y += 28
    OUT.mkdir(exist_ok=True)
    image.save(OUT / name, "PNG")


def main() -> None:
    frame("Merhaba, ben FRIDAY.", ["Gemini anahtarın bu bilgisayarda kalır.", "aistudio.google.com/apikey"], "karsilama.png")
    frame("Ana ekran", ["Altın halka, hava, takvim ve sohbet.", "Mikrofon açık. Ayarlar içeriden."], "ana-ekran.png")
    frame("Her şey çalıştı. FRIDAY ayakta.", ["Anahtar, bağlantı ve mikrofon hazır.", "Telefon aynı Wi-Fi’da."], "friday-ayakta.png")


if __name__ == "__main__":
    main()
