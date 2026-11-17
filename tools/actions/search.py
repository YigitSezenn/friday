from __future__ import annotations

# Sirayla denenir: ilk yanit veren kazanir. Adlar ekran analizindeki listeyle ayni kaynaktan gelir.
SEARCH_MODELS = (
    "models/gemini-3.8-flash",
    "models/gemini-2.5-flash",
    "models/gemini-flash-latest",
)
ANSWER_LIMIT = 900
PROMPT = "Turkce, en fazla uc kisa cumleyle ve guncel bilgiyle yanitla. Sesli okunacak: liste, baslik ve kaynak adresi yazma.\n\nSoru: {query}"


def _label(model: str) -> str:
    return model.removeprefix("models/")


def _gemini_search(key: str, model: str, query: str) -> str:
    """Google aramasina bagli Gemini yaniti. Ag ve paket hatalari cagirana firlar."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=15000))
    response = client.models.generate_content(
        model=model,
        contents=PROMPT.format(query=query),
        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
    )
    return " ".join(str(response.text or "").split())


def _duckduckgo(query: str) -> str:
    import requests

    response = requests.get(
        "https://api.duckduckgo.com/",
        params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
        headers={"User-Agent": "jarvis-rebuild"},
        timeout=8,
    )
    response.raise_for_status()
    payload = response.json()
    lines = []
    abstract = str(payload.get("AbstractText") or "").strip()
    if abstract:
        lines.append(abstract)
    for item in payload.get("RelatedTopics") or []:
        if isinstance(item, dict) and item.get("Text"):
            lines.append(str(item["Text"]).strip())
        if len(lines) >= 4:
            break
    return "\n".join(lines[:4])


def web_search(query: str, ask=None, fallback=None) -> str:
    """Once Gemini (Google aramasi, uc model sirayla), olmazsa DuckDuckGo. Hicbiri olmazsa nedenleri soyler."""
    text = " ".join(str(query or "").split())
    if not text:
        return "Arama cumlesi bos."
    reasons: list[str] = []
    answer = _search_with_gemini(text, ask or _gemini_search, reasons)
    if answer:
        return answer[:ANSWER_LIMIT]
    try:
        summary = (fallback or _duckduckgo)(text)
    except Exception as exc:
        reasons.append(f"DuckDuckGo: {exc}")
    else:
        if summary:
            return summary
        if not reasons:
            return f"'{text}' icin kisa bir ozet donmedi. Tarayicida aramayi acmayi onerebilirsin."
        reasons.append("DuckDuckGo: ozet donmedi")
    return "Arama yapilamadi: " + "; ".join(reasons)


def _search_with_gemini(text: str, ask, reasons: list[str]) -> str:
    from jarvis.config import get_app_config_value
    from jarvis.gemini_errors import classify, clean_api_key, without_proxy_for_google

    key = clean_api_key(get_app_config_value("gemini_api_key", ""))
    if not key:
        return ""
    without_proxy_for_google()
    for model in SEARCH_MODELS:
        try:
            answer = ask(key, model, text)
        except Exception as exc:
            issue = classify(exc, key)
            reasons.append(f"{_label(model)}: {issue.code}")
            if issue.rejection:
                break  # hesap duzeyinde kapali: diger modeller de ayni sonucu verir
            continue
        if answer:
            return answer
        reasons.append(f"{_label(model)}: bos yanit")
    return ""
