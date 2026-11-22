# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_dynamic_libs, collect_submodules

ROOT = Path(SPECPATH).resolve().parent

datas = [
    (str(ROOT / "ui" / "hud"), "ui/hud"),
    (str(ROOT / "jarvis" / "prompts"), "jarvis/prompts"),
    (str(ROOT / "site" / "public" / "indir" / "yenilikler.json"), "jarvis"),
    (str(ROOT / "assets" / "friday.ico"), "assets"),
    (str(ROOT / "assets" / "sounds"), "assets/sounds"),
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
    "win32com.client",
    "pythoncom",
]
hidden += collect_submodules("ui")
hidden += collect_submodules("tools.actions")
hidden += collect_submodules("jarvis")


for package in ("webview", "google.genai", "cv2", "PIL", "mss", "qrcode", "pyttsx3", "pycaw", "comtypes"):
    extra_datas, extra_binaries, extra_hidden = collect_all(package)
    datas += extra_datas
    binaries += extra_binaries
    hidden += extra_hidden

# El takibi: mediapipe yalnızca görev API'si ve yerel kitaplıklarıyla (test dosyaları, matplotlib ve opencv-contrib yok).
datas += collect_data_files("mediapipe", excludes=["**/test/**", "**/tests/**"])
binaries += collect_dynamic_libs("mediapipe")
hidden += collect_submodules("mediapipe.tasks", filter=lambda name: ".test" not in name)

a = Analysis(
    [str(ROOT / "jarvis" / "__main__.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    excludes=["matplotlib", "jax", "jaxlib", "tensorflow"],
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
