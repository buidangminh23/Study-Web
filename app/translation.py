import hashlib
import json
import re
from html import escape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


import os as _os
_STATIC_CACHE = Path(__file__).resolve().parent / "static" / "translation-cache" / "lessons"
_TMP_CACHE = Path("/tmp/translation-cache/lessons")
CACHE_DIR = _TMP_CACHE if _os.getenv("VERCEL") else _STATIC_CACHE
TRANSLATION_CACHE_VERSION = 7
GOOGLE_TRANSLATE_URL = "https://translate.googleapis.com/translate_a/single"
SEGMENT_SEPARATOR = "\nZXQJSEPZXQJ\n"
MAX_TRANSLATION_CHARS = 3200
PROTECTED_TAGS = {"code", "pre", "script", "style", "svg", "math", "kbd", "samp"}
LETTER_RE = re.compile(r"[A-Za-zÀ-ỹĐđ]")
VIETNAMESE_RE = re.compile(r"[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]")
URL_RE = re.compile(r"^(?:https?://|/static/|mailto:)", re.I)
SUPPORTED_LANGUAGES = {"en", "vi"}
ENGLISH_SEGMENT_RE = re.compile(r"(?<![A-Za-zÀ-ỹĐđ])([A-Za-z][A-Za-z0-9]*(?:[ /&,\-]+[A-Za-z][A-Za-z0-9]*)*)(?![A-Za-zÀ-ỹĐđ])")
TERM_TRANSLATIONS = {
    "atomic": "nguyên tử",
    "attribute": "thuộc tính",
    "attribute/field": "thuộc tính/trường",
    "cells": "ô",
    "column": "cột",
    "column names": "tên cột",
    "columns": "cột",
    "create, read, update, delete": "tạo, đọc, cập nhật, xóa",
    "database": "cơ sở dữ liệu",
    "duplicate data": "dữ liệu trùng lặp",
    "entity": "thực thể",
    "entity relationship diagram": "sơ đồ mối quan hệ thực thể",
    "field": "trường",
    "foreign key": "khóa ngoại",
    "inconsistent data": "dữ liệu không nhất quán",
    "multivalue fields": "trường đa giá trị",
    "order": "thứ tự",
    "primary key": "khóa chính",
    "record": "bản ghi",
    "relation": "quan hệ",
    "relational database": "cơ sở dữ liệu quan hệ",
    "relational database structure": "cấu trúc cơ sở dữ liệu quan hệ",
    "row": "hàng",
    "rows": "hàng",
    "rules of relations": "quy tắc quan hệ",
    "single values": "giá trị đơn",
    "table": "bảng",
    "tables": "bảng",
    "tables, columns, rows, rules of relations": "bảng, cột, hàng, quy tắc quan hệ",
    "unique": "duy nhất",
}
TERM_RE = re.compile(
    r"(?<![A-Za-zÀ-ỹĐđ])("
    + "|".join(re.escape(term) for term in sorted(TERM_TRANSLATIONS, key=len, reverse=True))
    + r")(?![A-Za-zÀ-ỹĐđ])",
    re.I,
)


def has_vietnamese_text(value: str) -> bool:
    return bool(VIETNAMESE_RE.search(value or ""))


def should_translate_text(value: str, target_language: str) -> bool:
    text = value.strip()
    if not text:
        return False
    if URL_RE.match(text):
        return False
    if target_language == "en" and not has_vietnamese_text(text):
        return False
    if len(LETTER_RE.findall(text)) < 2:
        return False
    compact = re.sub(r"\s+", "", text)
    if compact and len(LETTER_RE.findall(compact)) / len(compact) < 0.35:
        return False
    return True


def parse_google_translation(raw: bytes) -> str:
    data = json.loads(raw.decode("utf-8"))
    return "".join(part[0] for part in data[0] if part and part[0])


def request_google_translation(text: str, target_language: str) -> str:
    source_language = "en" if target_language == "vi" else "vi"
    query = urlencode({"client": "gtx", "sl": source_language, "tl": target_language, "dt": "t", "q": text})
    req = Request(f"{GOOGLE_TRANSLATE_URL}?{query}", headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(req, timeout=10) as response:
            return parse_google_translation(response.read())
    except Exception:
        return text


def chunk_texts(texts: list[str]) -> list[list[str]]:
    chunks = []
    current = []
    current_length = 0
    for text in texts:
        item_length = len(text) + len(SEGMENT_SEPARATOR)
        if current and current_length + item_length > MAX_TRANSLATION_CHARS:
            chunks.append(current)
            current = []
            current_length = 0
        current.append(text)
        current_length += item_length
    if current:
        chunks.append(current)
    return chunks


def translate_chunk(texts: list[str], target_language: str) -> list[str]:
    translated = request_google_translation(SEGMENT_SEPARATOR.join(texts), target_language)
    parts = [part.strip() for part in translated.split(SEGMENT_SEPARATOR)]
    if len(parts) == len(texts):
        return parts
    return [request_google_translation(text, target_language).strip() for text in texts]


def translate_texts(texts: list[str], target_language: str) -> list[str]:
    if not texts:
        return []
    if target_language == "vi":
        return translate_texts_to_vietnamese(texts)
    return translate_texts_full(texts, target_language)


def translate_texts_full(texts: list[str], target_language: str) -> list[str]:
    unique_texts = []
    translated_by_text = {}
    for text in texts:
        if text not in translated_by_text:
            translated_by_text[text] = ""
            unique_texts.append(text)
    for chunk in chunk_texts(unique_texts):
        for source, translated in zip(chunk, translate_chunk(chunk, target_language)):
            translated_by_text[source] = translated
    return [translated_by_text[text] for text in texts]


def normalize_english_segment(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip()).lower()


def should_translate_english_segment(value: str) -> bool:
    segment = value.strip()
    if len(segment) < 2:
        return False
    if segment.isupper() and len(segment) <= 6:
        return False
    if normalize_english_segment(segment) not in TERM_TRANSLATIONS and segment.islower() and not TERM_RE.search(segment):
        return False
    return bool(re.search(r"[A-Za-z]", segment))


def apply_segment_case(source: str, translated: str) -> str:
    if source[:1].isupper() and translated:
        return translated[:1].upper() + translated[1:]
    return translated


def collect_english_segments(value: str) -> list[str]:
    segments = []
    if not has_vietnamese_text(value):
        return segments
    for match in ENGLISH_SEGMENT_RE.finditer(value):
        segment = re.sub(r"\s+", " ", match.group(1).strip())
        if should_translate_english_segment(segment):
            segments.append(segment)
    return segments


def translate_texts_to_vietnamese(texts: list[str]) -> list[str]:
    full_texts = []
    mixed_segments = []
    for text in texts:
        if has_vietnamese_text(text):
            mixed_segments.extend(collect_english_segments(text))
        else:
            full_texts.append(text)
    translated_full = dict(zip(full_texts, translate_texts_full(full_texts, "vi")))
    unique_segments = []
    translated_by_segment = {}
    for segment in mixed_segments:
        key = normalize_english_segment(segment)
        if key in translated_by_segment:
            continue
        if key in TERM_TRANSLATIONS:
            translated_by_segment[key] = TERM_TRANSLATIONS[key]
        else:
            translated_by_segment[key] = ""
            unique_segments.append(segment)
    if unique_segments:
        for source, translated in zip(unique_segments, translate_texts_full(unique_segments, "vi")):
            translated_by_segment[normalize_english_segment(source)] = translated
    results = []
    for text in texts:
        if not has_vietnamese_text(text):
            results.append(translated_full[text])
            continue
        results.append(translate_mixed_text_to_vietnamese(text, translated_by_segment))
    return results


def translate_mixed_text_to_vietnamese(value: str, translated_by_segment: dict[str, str]) -> str:
    def replace(match: re.Match) -> str:
        segment = re.sub(r"\s+", " ", match.group(1).strip())
        if not should_translate_english_segment(segment):
            return match.group(0)
        if normalize_english_segment(segment) not in TERM_TRANSLATIONS and TERM_RE.search(segment):
            return translate_known_terms_to_vietnamese(segment)
        translated = translated_by_segment.get(normalize_english_segment(segment))
        if not translated:
            return match.group(0)
        if value[match.start() - 1:match.start()] == "(":
            return translated
        return apply_segment_case(segment, translated)

    return ENGLISH_SEGMENT_RE.sub(replace, value)


def translate_known_terms_to_vietnamese(value: str) -> str:
    def replace(match: re.Match) -> str:
        source = match.group(1)
        translated = TERM_TRANSLATIONS.get(normalize_english_segment(source))
        if not translated:
            return source
        return apply_segment_case(source, translated)

    return TERM_RE.sub(replace, value)


class TranslationHTMLParser(HTMLParser):
    def __init__(self, target_language: str) -> None:
        super().__init__(convert_charrefs=True)
        self.output: list[str] = []
        self.texts: list[str] = []
        self.tokens: list[str] = []
        self.protected_depth = 0
        self.target_language = target_language

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.output.append(self.get_starttag_text() or self.render_start_tag(tag, attrs))
        if tag.lower() in PROTECTED_TAGS:
            self.protected_depth += 1

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.output.append(self.get_starttag_text() or self.render_start_tag(tag, attrs, True))

    def handle_endtag(self, tag: str) -> None:
        self.output.append(f"</{tag}>")
        if tag.lower() in PROTECTED_TAGS and self.protected_depth:
            self.protected_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.protected_depth:
            self.output.append(escape(data, quote=False))
            return
        match = re.match(r"^(\s*)(.*?)(\s*)$", data, re.DOTALL)
        if not match:
            self.output.append(escape(data, quote=False))
            return
        leading, core, trailing = match.groups()
        if not should_translate_text(core, self.target_language):
            self.output.append(escape(data, quote=False))
            return
        token = f"ZXQJNODE{len(self.texts)}ZXQJ"
        self.texts.append(core)
        self.tokens.append(token)
        self.output.append(f"{leading}{token}{trailing}")

    def handle_comment(self, data: str) -> None:
        self.output.append(f"<!--{data}-->")

    def handle_decl(self, decl: str) -> None:
        self.output.append(f"<!{decl}>")

    def handle_pi(self, data: str) -> None:
        self.output.append(f"<?{data}>")

    def render_start_tag(self, tag: str, attrs: list[tuple[str, str | None]], closed: bool = False) -> str:
        attr_html = ""
        for name, value in attrs:
            if value is None:
                attr_html += f" {name}"
            else:
                attr_html += f' {name}="{escape(value, quote=True)}"'
        suffix = " /" if closed else ""
        return f"<{tag}{attr_html}{suffix}>"


def translate_html_fragment(content_html: str, target_language: str) -> str:
    parser = TranslationHTMLParser(target_language)
    parser.feed(content_html or "")
    parser.close()
    html = "".join(parser.output)
    translations = translate_texts(parser.texts, target_language)
    for token, translated in zip(parser.tokens, translations):
        html = html.replace(token, escape(translated, quote=False))
    return html


def translate_plain_text(value: str, target_language: str) -> str:
    if not should_translate_text(value, target_language):
        return value
    return translate_texts([value], target_language)[0]


def cache_key(target_language: str, title: str, summary: str, content_html: str) -> str:
    payload = json.dumps([TRANSLATION_CACHE_VERSION, target_language, title, summary, content_html], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def read_cached_translation(path: Path, key: str) -> dict | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if payload.get("hash") != key:
        return None
    return payload


def write_cached_translation(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    temp_path.replace(path)


def build_lesson_translation(lesson_id: int, title: str, summary: str, content_html: str, target_language: str = "vi") -> dict:
    if target_language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language")
    key = cache_key(target_language, title, summary, content_html)
    static_path = _STATIC_CACHE / target_language / f"{lesson_id}.json"
    cached = read_cached_translation(static_path, key)
    if cached:
        return cached
    path = CACHE_DIR / target_language / f"{lesson_id}.json"
    if path != static_path:
        cached = read_cached_translation(path, key)
        if cached:
            return cached
    try:
        payload = {
            "hash": key,
            "language": target_language,
            "title": translate_plain_text(title, target_language),
            "summary": translate_plain_text(summary, target_language),
            "content_html": translate_html_fragment(content_html, target_language),
        }
        try:
            write_cached_translation(path, payload)
        except Exception:
            pass
        return payload
    except Exception:
        return {
            "hash": key,
            "language": target_language,
            "title": title,
            "summary": summary,
            "content_html": content_html,
        }
