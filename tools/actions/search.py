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


def _plain(fragment: str) -> str:
    import html
    import re

    return " ".join(html.unescape(re.sub(r"<[^>]+>", "", fragment)).split())


def _parse_bing(page: str, limit: int = 5) -> list[str]:
    """Bing sonuç sayfasından 'başlık — özet' satırları çıkarır (<li class="b_algo"> blokları)."""
    import re

    lines = []
    for block in re.split(r'<li class="b_algo"', page)[1:]:
        title = re.search(r"<h2[^>]*>(.*?)</h2>", block, re.S)
        snippet = re.search(r'<p[^>]*class="b_lineclamp[^"]*"[^>]*>(.*?)</p>', block, re.S) or re.search(r"<p[^>]*>(.*?)</p>", block, re.S)
        head = _plain(title.group(1)) if title else ""
        if not head:
            continue
        body = _plain(snippet.group(1)) if snippet else ""
        lines.append(head + (f" — {body}" if body else ""))
        if len(lines) >= limit:
            break
    return lines


def _gemini_plain(key: str, model: str, query: str, prompt: str = "") -> str:
    """Aramasız Gemini yanıtı: arama kotası dolduğunda kendi bilgisiyle (ya da verilen notlara dayanarak) cevap verir."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=key, http_options=types.HttpOptions(timeout=30000))
    response = client.models.generate_content(model=model, contents=prompt or PROMPT.format(query=query))
    return " ".join(str(response.text or "").split())


def _readable(line: str) -> bool:
    """Türkçe/İngilizce okunabilir mi? Çince, Rusça, Arapça vb. sonuçlar elenir."""
    letters = [ch for ch in line if ch.isalpha()]
    if not letters:
        return False
    latin = sum(1 for ch in letters if ch.isascii() or "\u00c0" <= ch <= "\u024f")
    return latin / len(letters) >= 0.85


def _tidy(line: str, limit: int = 170) -> str:
    line = line.replace("Devamını oku", "").replace("...", " ").replace("…", " ")
    line = " ".join(line.split())
    if len(line) > limit:
        line = line[:limit].rsplit(" ", 1)[0]
    return line


def _bing_lines(query: str) -> list[str]:
    """Anahtarsız, ücretsiz web araması: Bing sonuç sayfasının okunabilir ilk sonuçları."""
    import urllib.parse
    import urllib.request

    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": query, "setlang": "tr", "mkt": "tr-TR", "cc": "TR"})
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.5",
    }
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=15) as response:
        page = response.read().decode("utf-8", "replace")
    lines = [_tidy(line) for line in _parse_bing(page, limit=8)]
    return [line for line in lines if line and _readable(line)][:4]


SUMMARY_PROMPT = (
    "Aşağıdaki arama sonucu notlarına dayanarak soruyu Türkçe, en fazla üç kısa cümleyle yanıtla. Sesli okunacak: liste, başlık, "
    "kaynak adı ve adres yazma; notlarda olmayan bilgi ekleme.\n\nSoru: {query}\n\nNotlar:\n{notes}"
)


def _summarize(query: str, lines: list[str]) -> str:
    """Ham sonuç satırlarını Gemini ile kısa Türkçe yanıta çevirir; olmazsa boş döner."""
    from jarvis.config import get_app_config_value
    from jarvis.gemini_errors import clean_api_key, without_proxy_for_google

    key = clean_api_key(get_app_config_value("gemini_api_key", ""))
    if not key:
        return ""
    without_proxy_for_google()
    prompt = SUMMARY_PROMPT.format(query=query, notes="\n".join(f"- {line}" for line in lines))
    for model in SEARCH_MODELS:
        try:
            answer = _gemini_plain(key, model, query, prompt)
        except Exception:
            continue
        if answer:
            return answer
    return ""


def _bing(query: str) -> str:
    lines = _bing_lines(query)
    if not lines:
        return ""
    answer = _summarize(query, lines)
    if answer:
        return answer
    # Özetlenemediyse: kısa notlar. Ham liste sesli okunmasın diye açık talimat.
    return "Arama notları (okuma; kendi cümlenle en fazla iki kısa cümleyle anlat): " + " | ".join(lines[:3])


def _duckduckgo(query: str) -> str:
    try:
        found = _bing(query)
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


def web_search(query: str, ask=None, fallback=None, tavily=None) -> str:
    """Once Gemini (Google aramasi, uc model sirayla), olmazsa DuckDuckGo. Hicbiri olmazsa nedenleri soyler."""
    text = " ".join(str(query or "").split())
    if not text:
        return "Arama cümlesi boş."
    reasons: list[str] = []
    found = _search_with_tavily(text, tavily, reasons)
    if found:
        return found[:ANSWER_LIMIT]
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


def _search_with_tavily(text: str, tavily, reasons: list[str]) -> str:
    """Tavily anahtarı kayıtlıysa önce o denenir (kotası Google'dan bağımsızdır)."""
    from jarvis.config import get_app_config_value
    from jarvis.gemini_errors import clean_api_key

    key = clean_api_key(get_app_config_value("tavily_api_key", ""))
    if not key:
        return ""
    try:
        return (tavily or _tavily)(key, text)
    except Exception as exc:
        reasons.append(f"Tavily: {_detail(exc, key)}")
        return ""
