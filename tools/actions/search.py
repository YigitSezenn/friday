from __future__ import annotations

# Sirayla denenir: ilk yanit veren kazanir. Adlar ekran analizindeki listeyle ayni kaynaktan gelir.
SEARCH_MODELS = (
    "models/gemini-3.8-flash",
    "models/gemini-flash-latest",
)
PLAIN_NOTE = "(Canlı arama şu an kullanılamadığı için bu yanıt modelin kendi bilgisine dayanıyor, güncel olmayabilir.) "
ANSWER_LIMIT = 900
PROMPT = "Türkçe, en fazla üç kısa cümleyle ve güncel bilgiyle yanıtla. Sesli okunacak: liste, başlık ve kaynak adresi yazma.\n\nSoru: {query}"


def _detail(exc: BaseException, key: str) -> str:
    """Hata türü + varsa HTTP kodu ve kısa Google mesajı (anahtar çıkarılır)."""
    import re

    code = getattr(exc, "code", None) or getattr(exc, "status_code", None)
    message = str(getattr(exc, "message", "") or exc)
    if key:
        message = message.replace(key, "")
    message = re.sub(r"\s+", " ", message).strip()[:110]
    head = type(exc).__name__ + (f" {code}" if code else "")
    return f"{head}: {message}" if message else head


def _label(model: str) -> str:
    return model.removeprefix("models/")


def _gemini_search(key: str, model: str, query: str) -> str:
    """Google aramasina bagli Gemini yaniti. Ag ve paket hatalari cagirana firlar."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=30000))
    response = client.models.generate_content(
        model=model,
        contents=PROMPT.format(query=query),
        config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]),
    )
    return " ".join(str(response.text or "").split())


def _parse_results(page: str, limit: int = 5) -> list[str]:
    """DuckDuckGo HTML sonuç sayfasından 'başlık — özet' satırları çıkarır."""
    import html
    import re

    def plain(fragment: str) -> str:
        return " ".join(html.unescape(re.sub(r"<[^>]+>", "", fragment)).split())

    titles = re.findall(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>', page, re.S)
    snippets = re.findall(r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', page, re.S)
    lines = []
    for index, title in enumerate(titles[:limit]):
        snippet = plain(snippets[index]) if index < len(snippets) else ""
        line = plain(title) + (f" — {snippet}" if snippet else "")
        if line.strip():
            lines.append(line)
    return lines


def _gemini_plain(key: str, model: str, query: str) -> str:
    """Aramasız Gemini yanıtı: arama kotası dolduğunda kendi bilgisiyle cevap verir."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=30000))
    response = client.models.generate_content(model=model, contents=PROMPT.format(query=query))
    return " ".join(str(response.text or "").split())


def _duckduckgo_html(query: str) -> str:
    """Gerçek web araması: ilk sonuçların başlık ve özetleri. Model bunları kendi cümleleriyle anlatır."""
    import requests

    response = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query, "kl": "tr-tr"},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) FRIDAY"},
        timeout=12,
    )
    response.raise_for_status()
    lines = _parse_results(response.text)
    if not lines:
        return ""
    return "Web arama sonuçları (bunları kendi cümlelerinle özetleyip anlat):\n" + "\n".join(f"{i}. {line}" for i, line in enumerate(lines, 1))


def _duckduckgo(query: str) -> str:
    try:
        found = _duckduckgo_html(query)
    except Exception:
        found = ""
    if found:
        return found
    return _duckduckgo_instant(query)


def _duckduckgo_instant(query: str) -> str:
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
        return "Arama cümlesi boş."
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
            return f"'{text}' için kısa bir özet dönmedi. Tarayıcıda aramayi acmayi onerebilirsin."
        reasons.append("DuckDuckGo: özet dönmedi")
    if ask is None:
        plain = _plain_answer(text)
        if plain:
            return (PLAIN_NOTE + plain)[:ANSWER_LIMIT]
    return "Arama yapılamadı: " + "; ".join(reasons)


def _search_with_gemini(text: str, ask, reasons: list[str]) -> str:
    from jarvis.config import get_app_config_value
    from jarvis.gemini_errors import classify, clean_api_key, without_proxy_for_google

    key = clean_api_key(get_app_config_value("gemini_api_key", ""))
    if not key:
        return ""
    without_proxy_for_google()
    for model in SEARCH_MODELS:
        try:
            try:
                answer = ask(key, model, text)
            except Exception as exc:
                if not classify(exc, key).retry or classify(exc, key).rejection:
                    raise
                answer = ask(key, model, text)  # geçici ağ kopmasına karşı aynı modeli bir kez daha dene
        except Exception as exc:
            issue = classify(exc, key)
            # Genel "BAĞLANTI KOPTU" nedeni gizlemesin: hata türünü de yaz.
            reasons.append(f"{_label(model)}: {issue.code} ({_detail(exc, key)})")
            if issue.rejection:
                break  # hesap duzeyinde kapali: diger modeller de ayni sonucu verir
            continue
        if answer:
            return answer
        reasons.append(f"{_label(model)}: boş yanıt")
    return ""


def _plain_answer(text: str) -> str:
    from jarvis.config import get_app_config_value
    from jarvis.gemini_errors import clean_api_key

    key = clean_api_key(get_app_config_value("gemini_api_key", ""))
    if not key:
        return ""
    for model in SEARCH_MODELS:
        for _ in range(2):  # 503 (yoğunluk) geçicidir: bir kez daha dene
            try:
                answer = _gemini_plain(key, model, text)
            except Exception:
                continue
            if answer:
                return answer
    return ""
