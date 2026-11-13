# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(ROOT / "ui" / "hud"), "ui/hud"),
    (str(ROOT / "jarvis" / "prompts"), "jarvis/prompts"),
    (str(ROOT / "assets" / "friday.ico"), "assets"),
]
binaries = []
hidden = [
    "ui",
    "ui.bridge",
    "tools",
    "tools.dispatch",
    "jarvis.app",
    "jarvis.live",
    "webview.platforms.edgechromium",
]
hidden += collect_submodules("tools.actions")
hidden += collect_submodules("jarvis")
hidden += collect_submodules("jarvis.actions")

for package in ("webview", "google.genai", "cv2", "PIL", "mss", "qrcode", "pyttsx3"):
    extra_datas, extra_binaries, extra_hidden = collect_all(package)
    datas += extra_datas
    binaries += extra_binaries
    hidden += extra_hidden

a = Analysis(
    [str(ROOT / "jarvis" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="FRIDAY",
    console=False,
    icon=str(ROOT / "assets" / "friday.ico"),
)
coll = COLLECT(exe, a.binaries, a.datas, name="FRIDAY")
