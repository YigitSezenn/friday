from __future__ import annotations


def web_search(query: str) -> str:
    text = " ".join(str(query or "").split())
    if not text:
        return "Arama cumlesi bos."
    try:
        import requests

        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": text, "format": "json", "no_html": "1", "skip_disambig": "1"},
            headers={"User-Agent": "jarvis-rebuild"},
            timeout=8,
        )
        response.raise_for_status()
        payload = response.json()
    except Exception as exc:
        return f"Arama yapilamadi: {exc}"
    lines = []
    abstract = str(payload.get("AbstractText") or "").strip()
    if abstract:
        lines.append(abstract)
    for item in payload.get("RelatedTopics") or []:
        if isinstance(item, dict) and item.get("Text"):
            lines.append(str(item["Text"]).strip())
        if len(lines) >= 4:
            break
    if not lines:
        return f"'{text}' icin kisa bir ozet donmedi. Tarayicida aramayi acmayi onerebilirsin."
    return "\n".join(lines[:4])
