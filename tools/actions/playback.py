"""Calan medyayi durdurur: yeni bir sey acilmadan once eskisi susar, sesler ust uste binmez.

Windows'un ortak medya oturumlarini (SMTC) okur ve yalnizca `Playing` olanlari duraklatir.
Duraklatilmis bir oturuma dokunmaz; bu yuzden "oynat/duraklat" tusu gibi yanlislikla
bir seyi baslatmaz. Hata olursa sessizce 0 doner, acma islemini engellemez.
"""

from __future__ import annotations

import base64
import re
import subprocess
import sys

_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
function Await($op, $type) {
  $task = $asTask.MakeGenericMethod($type).Invoke($null, @($op))
  $task.Wait(-1) | Out-Null
  $task.Result
}
[Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime] | Out-Null
$manager = Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
$paused = 0
foreach ($session in $manager.GetSessions()) {
  if ($session.GetPlaybackInfo().PlaybackStatus -ne 'Playing') { continue }
  $skip = '__EXCLUDE__'
  if ($skip -ne '' -and $session.SourceAppUserModelId -match $skip) { continue }
  if (Await ($session.TryPauseAsync()) ([bool])) { $paused++ }
}
Write-Output $paused
"""


def _safe_pattern(exclude: str) -> str:
    """Betige gomulecek desen: yalniz harf, rakam, nokta, tire ve bosluk kalir."""
    return re.sub(r"[^A-Za-z0-9._ -]", "", str(exclude or ""))


def build_command(exclude: str = "") -> list[str]:
    script = _SCRIPT.replace("__EXCLUDE__", _safe_pattern(exclude))
    encoded = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-EncodedCommand", encoded]


def pause_playing_sessions(exclude: str = "", timeout: float = 8.0) -> int:
    """Duraklatilan oturum sayisini dondurur. Windows disinda ya da hata varsa 0."""
    if sys.platform != "win32":
        return 0
    try:
        result = subprocess.run(
            build_command(exclude),
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return int((result.stdout or "0").strip().splitlines()[-1])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return 0
