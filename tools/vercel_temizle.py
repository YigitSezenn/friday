"""Vercel'deki eski ve başarısız dağıtımları siler (site projesi).

Kullanım (kendi bilgisayarında): python tools\\vercel_temizle.py
Token gizli istemde sorulur (ekranda görünmez, hiçbir yere kaydedilmez) ya da VERCEL_TOKEN ortam değişkeninden okunur.
Önce ne silineceğini listeler; "SIL" yazmadan hiçbir şeyi silmez. Canlı (production) sürümlerden en yeni KEEP tanesi kalır.
"""
from __future__ import annotations

import getpass
import json
import os
import sys
import urllib.error
import urllib.request

TEAM = "team_qP2RxJZQ3iQZomXv33OdrfJW"
PROJECT = "prj_jyFsyJzjYWBFHKcpbeehp1scn43j"
KEEP = 5
API = "https://api.vercel.com"


def select_deletable(deployments: list[dict], keep: int = KEEP) -> list[dict]:
    """Başarısız/iptal olanların hepsi, hazır olanlardan en yeni `keep` taneden eskileri. Hiçbir zaman en yeni hazır dağıtımı silmez."""
    ordered = sorted(deployments, key=lambda d: d.get("created", 0), reverse=True)
    ready_kept = 0
    doomed = []
    for item in ordered:
        state = item.get("state") or item.get("readyState")
        if state == "READY":
            if ready_kept < keep:
                ready_kept += 1
                continue
            doomed.append(item)
        elif state in {"ERROR", "CANCELED"}:
            doomed.append(item)
    return doomed


def _call(token: str, method: str, path: str) -> dict:
    request = urllib.request.Request(API + path, method=method, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read() or b"{}")


def _all_deployments(token: str) -> list[dict]:
    found, until = [], ""
    while True:
        page = _call(token, "GET", f"/v6/deployments?projectId={PROJECT}&teamId={TEAM}&limit=100" + (f"&until={until}" if until else ""))
        items = page.get("deployments") or []
        found += items
        until = (page.get("pagination") or {}).get("next")
        if not items or not until:
            return found


def main() -> int:
    token = os.environ.get("VERCEL_TOKEN", "").strip() or getpass.getpass("Vercel token (görünmez): ").strip()
    if not token:
        print("Token verilmedi.")
        return 1
    try:
        deployments = _all_deployments(token)
    except urllib.error.HTTPError as exc:
        print(f"Vercel erişim hatası: HTTP {exc.code}. Token'ın bu ekip için yetkili olduğundan emin ol.")
        return 1
    doomed = select_deletable(deployments)
    print(f"Toplam {len(deployments)} dağıtım var; {len(doomed)} tanesi silinecek (başarısız/iptal ve en yeni {KEEP} hazır sürümden eskiler).")
    for item in doomed[:10]:
        print(" -", item.get("state"), item.get("url"), (item.get("meta") or {}).get("githubCommitMessage", "")[:50].replace("\n", " "))
    if len(doomed) > 10:
        print(f" … ve {len(doomed) - 10} tane daha")
    if not doomed or input('Silmek için SIL yaz (iptal için Enter): ').strip() != "SIL":
        print("Hiçbir şey silinmedi.")
        return 0
    failed = 0
    for item in doomed:
        try:
            _call(token, "DELETE", f"/v13/deployments/{item['uid'] if 'uid' in item else item['id']}?teamId={TEAM}")
        except urllib.error.HTTPError as exc:
            failed += 1
            print("Silinemedi:", item.get("url"), exc.code)
    print(f"{len(doomed) - failed} dağıtım silindi, {failed} silinemedi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
