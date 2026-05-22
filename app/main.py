import json
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime
from html import escape, unescape
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload
from starlette.middleware.sessions import SessionMiddleware

from .database import Base, engine, get_db
from .models import Exercise, ExerciseAttempt, Lesson, LessonProgress, Section, Subject, User
from .security import hash_password, verify_password
from .seed import normalize_options, seed_data
from .translation import build_lesson_translation


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = next(get_db())
    try:
        seed_data(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Study Web", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SESSION_SECRET", "study-web-local-secret"), same_site="lax")
_BASE = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=str(_BASE / "static")), name="static")
templates = Jinja2Templates(directory=str(_BASE / "templates"))


SOURCE_TEXT_RE = re.compile(
    r"<pre(?P<attrs>[^>]*)class=[\"'][^\"']*\bsource-text\b[^\"']*[\"'][^>]*>(?P<body>.*?)</pre>",
    re.IGNORECASE | re.DOTALL,
)
PRE_CODE_RE = re.compile(r"<pre[^>]*>\s*<code[^>]*>(?P<body>.*?)</code>\s*</pre>", re.IGNORECASE | re.DOTALL)
HTML_TOKEN_RE = re.compile(r"(<[^>]+>)")
HTML_TAG_NAME_RE = re.compile(r"^<\s*([A-Za-z0-9:-]+)")
HTML_END_TAG_RE = re.compile(r"^</\s*([A-Za-z0-9:-]+)")
HTML_SELF_CLOSING_RE = re.compile(r"/\s*>$")
MATH_RENDER_SKIP_TAGS = {"style", "script", "pre", "code", "textarea"}
RADICAL_PAREN_RE = re.compile(r"√\s*\(([^<>]*?)\)")
RADICAL_SIMPLE_RE = re.compile(r"√\s*([A-Za-z0-9]+[A-Za-z0-9₀₁₂₃₄₅₆₇₈₉⁰¹²³⁴⁵⁶⁷⁸⁹]*)")
SQL_CODE_RE = re.compile(r"\b(?:SELECT|FROM|WHERE|ORDER\s+BY|GROUP\s+BY|HAVING|INSERT|UPDATE|DELETE|CREATE|JOIN)\b", re.I)
ASCII_RULE_RE = re.compile(r"^[\s\-|:]+$")
KEY_VALUE_RE = re.compile(r"^(?P<term>[A-Za-z][A-Za-z0-9 /()'._-]{0,70})\s*=\s*(?P<definition>.+)$")
KEY_CHOICE_RE = re.compile(r"^(?P<label>Good PK|Bad PK):\s*(?P<field>[A-Za-z0-9_]+)\s*(?P<reason>\(.+\))?$", re.I)
RELATION_TYPE_RE = re.compile(r"^(?P<name>One-to-One|One-to-Many|Many-to-Many)\s*(?P<notation>\([^)]+\))\s*-\s*(?P<description>.+)$", re.I)
SCHEMA_LINE_RE = re.compile(r"^(?P<name>[A-Za-z][A-Za-z ]+ table):\s*(?P<columns>.+)$", re.I)
COLON_DEFINITION_RE = re.compile(r"^(?P<term>[A-Za-z0-9][A-Za-z0-9 /()'._-]{0,70}):\s*(?P<definition>.+)$")
DASH_DEFINITION_RE = re.compile(r"^(?P<term>[A-Za-z_*?<>=(][A-Za-z0-9 _*?<>=(.)/+-]{0,70})\s+-\s+(?P<definition>.+)$")
NUMBERED_DEFINITION_RE = re.compile(r"^\d+\.\s*(?P<term>[A-Za-z][A-Za-z0-9 _()/*+-]{0,70})\s+-\s*(?P<definition>.+)$")
SYMBOL_DEFINITION_RE = re.compile(r"^(?P<term><>|<=|>=|=|<|>|\*|\?)\s*(?:=|-)?\s+(?P<definition>.+)$")
CODE_SECTION_HEADING_RE = re.compile(r"^--\s*(?P<title>[^:]+):\s*$")
RESULT_HEADING_RE = re.compile(r"^--\s*(?:Query\s+)?Results?:\s*$", re.I)
RELOAD_WATCH_ROOTS = (Path("app"), Path("tests"), Path("README.md"), Path("requirements.txt"))
RELOAD_SKIP_PARTS = {"__pycache__", ".pytest_cache", "translation-cache"}
HEX_DIGITS = "0123456789ABCDEF"
VISUAL_REFERENCE_RE = re.compile(r"^(?:figure|exhibit|diagram|chart)\s*[0-9A-Za-z.:-]*", re.I)
PDF_MATH_TRANSLATION = str.maketrans(
    {
        "\uf8ee": "\u23a1",
        "\uf8ef": "\u23a2",
        "\uf8f0": "\u23a3",
        "\uf8f9": "\u23a4",
        "\uf8fa": "\u23a5",
        "\uf8fb": "\u23a6",
        "\x02": "[",
        "\x03": "]",
    }
)
MATH_GLYPH_RE = re.compile(r"[\uf8ee\uf8ef\uf8f0\uf8f9\uf8fa\uf8fb\x02\x03\u23a1-\u23a6]")
MATH_EXAMPLE_RE = re.compile(r"^(?:Example|Solution)\s+\d+(?:\.\d+)?", re.I)
MATH_ASSIGNMENT_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_′']*\s*=")
MATH_DENSE_NUMBER_RE = re.compile(r"(?:[\u2212-]?\d+(?:\.\d+)?|\.\d+)")
MATH_DENSE_SYMBOL_RE = re.compile(r"[=\u00d7\u2212\u221a\u221e\u2192+\-/^()]|\b(?:sin|cos|tan|lim|arg|det|rank)\b", re.I)
SOURCE_ADMIN_BLOCK_RE = re.compile(
    r"^(?:learning objectives?|what\s+(?:are|were|will)\s+.*(?:objectives?|cover)|what\s+.*today\??|broadly,\s+where\s+(?:did|does)\s+this\s+unit\s+fit\??|how\s+were\s+you\s+assessed\??|where\s+to\s+next\??|coming\s+up\s+next|in\s+review|thanks\.?|good\s*luck!?|assessment task)\b",
    re.I,
)
SOURCE_OBJECTIVE_RE = re.compile(
    r"^(?:\d+(?:\.\d+)?\.?\s*)?(?:analyse|analyze|define|list|explain|discuss|describe|distinguish|identify|summari[sz]e|provide|revisit|outline|outlines|explore|focus|look)\b",
    re.I,
)
SOURCE_COURSE_LINE_RE = re.compile(r"^(?:INF|COS|MGT|MKT|MTH|MDA|BATE)\d{5}\b.*", re.I)
SOURCE_MONTH_RE = re.compile(r"^(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$", re.I)
SOURCE_PAGE_MARKER_RE = re.compile(r"^(?P<title>.+?)\s+(?P<number>\d{1,3})$")
SOURCE_REFERENCE_RE = re.compile(r"^(?:Image\s+Source|Source|References?)\s*:", re.I)
IMAGE_SRC_RE = re.compile(r"<img\s+[^>]*src=[\"'](?P<src>/static/content/[^\"']+)[\"']", re.I)
REFERENCE_SECTION_KEYS = {"original source files", "references", "source files"}
RECORDING_SECTION_KEYS = {"canvas recordings", "echo360 videos"}
SUBJECT_BLOCK_ORDER = ("IT", "Business", "Media")
SUBJECT_BLOCKS = {
    "Computer System": "IT",
    "Linear Algebra and Applications": "IT",
    "Data Management and Analytics": "IT",
    "Introduction to Programming": "IT",
    "Database Design Project": "IT",
    "Business Digitalisation": "Business",
    "Economics for Business Decision Making": "Business",
    "Contemporary Management Principles": "Business",
    "Marketing and the Consumer Experience": "Business",
    "Communicating with Data": "Media",
}
SUBJECT_ILLUSTRATIONS = {
    "Computer System": {"icon": "fa-microchip", "theme": "logic", "items": ["Boolean gates", "Logisim circuits", "ARM flow"]},
    "Linear Algebra and Applications": {"icon": "fa-table-cells", "theme": "math", "items": ["Matrix form", "Vector space", "Transform"]},
    "Data Management and Analytics": {"icon": "fa-chart-column", "theme": "data", "items": ["SQL joins", "ER model", "Analytics"]},
    "Introduction to Programming": {"icon": "fa-code", "theme": "code", "items": ["Variables", "Control flow", "Functions"]},
    "Marketing and the Consumer Experience": {"icon": "fa-bullhorn", "theme": "market", "items": ["4Ps", "Consumer insight", "Research"]},
    "Database Design Project": {"icon": "fa-database", "theme": "database", "items": ["Schema", "Queries", "Indexes"]},
    "Business Digitalisation": {"icon": "fa-network-wired", "theme": "business", "items": ["Processes", "Platforms", "Change"]},
    "Economics for Business Decision Making": {"icon": "fa-scale-balanced", "theme": "economics", "items": ["Demand", "Supply", "Decision"]},
    "Communicating with Data": {"icon": "fa-chart-pie", "theme": "media", "items": ["Data story", "Culture", "Visuals"]},
    "Contemporary Management Principles": {"icon": "fa-people-group", "theme": "management", "items": ["Planning", "Leading", "Control"]},
}
DEFAULT_SUBJECT_ILLUSTRATION = {"icon": "fa-book-open", "theme": "study", "items": ["Concept", "Practice", "Review"]}
SOURCE_BULLET_RE = re.compile(r"^[•\-]\s+")
SOURCE_NUMBERED_ITEM_RE = re.compile(r"^\(?\d+[).]\s+")
SOURCE_DEFINITION_RE = re.compile(r"\s[-–—]\s")
SOURCE_INTRO_MAP_RE = re.compile(
    r"^(?:Business Information Systems|Business Business Digitalisation|Issues\s+Issues|Industries and Sectors|Driving Forces and Competition|Business Models|Competencies|Business Processes|Investment\s*/\s*Innovation|Regul\s*at\s*i\s*on|Regulation and Law|Security and Governance|Sustainability and SDGs|Organisational change|Project Failure|Week\s+\d+|\d+\.\s+(?:Introduction|Digital Age|Think Like|The Tech Sector|Beyond ERP|IT Infrastructure|Data\s*&|SDLC|Agile|Liquid|Cybersecurity|Global|Wrap-Up)|Assignment\s+\d+)\b",
    re.I,
)
SOURCE_INTRO_ADMIN_PHRASES = (
    "go to",
    "canvas modules",
    "each week has",
    "available asynchronous",
    "lecture recordings",
    "off campus",
    "lab tutorial",
    "on campus",
    "attend one per week",
    "weekly content q and a assignments support",
    "online activities and self learning",
    "assignment work",
    "one reading per week",
    "discussion board",
    "how will we communicate",
    "canvas announcements",
    "discussion forum",
    "consultation times",
    "on campus sessions",
    "unit content",
    "unit progress",
    "quiz",
    "individual report",
    "assessment",
    "rubric",
    "grading system",
    "high distinction",
    "distinction",
    "credit",
    "pass",
    "refer canvas",
    "due date",
    "weight",
    "report site",
    "each column",
    "performance level",
    "each row",
    "criteria",
    "less than 50",
    "withdrew",
    "late submissions",
    "late submission penalty",
    "extensions",
    "documentation",
    "doctor certificate",
    "referencing",
    "plagiarism",
    "university policy",
    "harvard style",
    "assignments in this unit",
    "tutor",
    "librarian",
    "making a start",
    "business digitalisation",
    "yes",
)
BINARY_COUNT_ROWS = (
    (0, "0000", 11, "1011"),
    (1, "0001", 12, "1100"),
    (2, "0010", 13, "1101"),
    (3, "0011", 14, "1110"),
    (4, "0100", 15, "1111"),
    (5, "0101", 16, "10000"),
    (6, "0110", 17, "10001"),
    (7, "0111", 31, "11111"),
    (8, "1000", 32, "100000"),
    (9, "1001", 65, "1000001"),
    (10, "1010", "", ""),
)


def current_user(request: Request, db: Session) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return db.get(User, user_id)


def require_user(request: Request, db: Session) -> User:
    user = current_user(request, db)
    if not user:
        raise HTTPException(status_code=303, headers={"Location": "/auth/login"})
    return user


def require_admin(request: Request, db: Session) -> User:
    user = require_user(request, db)
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    return user


def render(request: Request, template: str, context: dict, db: Session) -> HTMLResponse:
    context["request"] = request
    context["current_user"] = current_user(request, db)
    context["static_token"] = get_reload_token()
    return templates.TemplateResponse(request, template, context)


def normalize_source_text(raw_text: str) -> str:
    text = unescape(raw_text).replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    cleaned_lines = []
    blank_pending = False
    for line in text.split("\n"):
        line = line.translate(PDF_MATH_TRANSLATION)
        cleaned = re.sub(r"[ \t\u2000-\u200b\u202f]+", " ", line).strip()
        cleaned = cleaned.replace("->", " -> ")
        cleaned = re.sub(r"^[>•]\s*", "• ", cleaned)
        cleaned = re.sub(r"^[–-]\s*", "- ", cleaned)
        if cleaned == "_start:":
            cleaned = ""
        if cleaned == "‹#›":
            cleaned = ""
        if re.match(r"^Slide\s+\d+$", cleaned, re.I):
            cleaned = ""
        if re.match(r"^(?:\d+\s+)?\d{1,2}/\d{1,2}/\d{2,4}\s+COS10004 Computer Systems(?:\s+\d+)?$", cleaned):
            cleaned = ""
        if re.match(r"^COS10004 Computer Systems\s+\d+$", cleaned):
            cleaned = ""
        if cleaned:
            if blank_pending and cleaned_lines:
                cleaned_lines.append("")
            cleaned_lines.append(cleaned)
            blank_pending = False
        else:
            blank_pending = bool(cleaned_lines)
    return "\n".join(cleaned_lines).strip()


def source_heading_level(line: str, index: int) -> int | None:
    if index == 0:
        return 2
    if len(line) > 90:
        return None
    letters = re.sub(r"[^A-Za-z]", "", line)
    if len(letters) < 4:
        return None
    if line.upper() == line and any(character.isalpha() for character in line):
        return 3
    if re.match(r"^(Lecture|Summary|Binary Counting|Number Systems|Analogue|Hexadecimal|Bit-Wise)", line, re.I):
        return 3
    return None


def render_table(headers: list[str], rows: list[list[str]], class_name: str = "source-table") -> str:
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    row_html = []
    for row in rows:
        row_html.append("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>")
    return f'<div class="source-table-wrap"><table class="{class_name}"><thead><tr>{header_html}</tr></thead><tbody>{"".join(row_html)}</tbody></table></div>'


def render_binary_counting_table() -> str:
    rows = [[str(left_decimal), left_binary, str(right_decimal), right_binary] for left_decimal, left_binary, right_decimal, right_binary in BINARY_COUNT_ROWS]
    return render_table(["Decimal", "Binary", "Decimal", "Binary"], rows, "source-table source-binary-table")


def render_hex_binary_table() -> str:
    rows = [[digit, format(index, "04b")] for index, digit in enumerate(HEX_DIGITS)]
    return render_table(["Hex", "Binary"], rows, "source-table source-compact-table")


def render_bit_weight_table(bits: list[str]) -> str:
    weights = ["128", "64", "32", "16", "8", "4", "2", "1"]
    labels = [f"Bit{index}" for index in range(7, -1, -1)]
    return render_table(["Weight", *weights], [["Bit", *labels], ["Value", *bits]], "source-table source-bit-table")


def render_radical(argument: str) -> str:
    value = re.sub(r"\s+", " ", argument).strip()
    if not value:
        return "√"
    label = escape(value, quote=True)
    body = escape(value)
    return f'<span class="math-radical" aria-label="square root of {label}"><span>{body}</span></span>'


def render_radicals_in_text(value: str) -> str:
    value = RADICAL_PAREN_RE.sub(lambda match: render_radical(match.group(1)), value)
    return RADICAL_SIMPLE_RE.sub(lambda match: render_radical(match.group(1)), value)


def render_inline_math_notation(content_html: str) -> str:
    parts = []
    skipped_tags = []
    for token in HTML_TOKEN_RE.split(content_html):
        if not token:
            continue
        if token.startswith("<"):
            parts.append(token)
            closing_match = HTML_END_TAG_RE.match(token)
            if closing_match:
                tag_name = closing_match.group(1).lower()
                if tag_name in skipped_tags:
                    skipped_tags = [tag for tag in skipped_tags if tag != tag_name]
                continue
            tag_match = HTML_TAG_NAME_RE.match(token)
            if tag_match:
                tag_name = tag_match.group(1).lower()
                if tag_name in MATH_RENDER_SKIP_TAGS and not HTML_SELF_CLOSING_RE.search(token):
                    skipped_tags.append(tag_name)
            continue
        parts.append(token if skipped_tags else render_radicals_in_text(token))
    return "".join(parts)


def clean_code_lines(value: str) -> list[str]:
    text = unescape(value).replace("\r\n", "\n").replace("\r", "\n")
    return [line.rstrip() for line in text.strip().split("\n")]


def split_pipe_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_ascii_table_header(lines: list[str], index: int) -> bool:
    return index + 1 < len(lines) and "|" in lines[index] and ASCII_RULE_RE.fullmatch(lines[index + 1].strip()) is not None


def collect_ascii_table(lines: list[str], index: int) -> tuple[str, int]:
    headers = split_pipe_row(lines[index])
    rows = []
    current = index + 2
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            break
        if "|" not in line:
            break
        cells = split_pipe_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append(cells[: len(headers)])
        current += 1
    return render_table(headers, rows, "source-table lesson-data-table"), current


def is_pipe_table(lines: list[str], index: int) -> bool:
    return index + 1 < len(lines) and "|" in lines[index] and "|" in lines[index + 1]


def collect_pipe_table(lines: list[str], index: int) -> tuple[str, int]:
    headers = split_pipe_row(lines[index])
    rows = []
    current = index + 1
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            break
        if "|" not in line:
            break
        cells = split_pipe_row(line)
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        rows.append(cells[: len(headers)])
        current += 1
    return render_table(headers, rows, "source-table lesson-data-table"), current


def collect_key_value_table(lines: list[str], index: int) -> tuple[str, int] | None:
    rows = []
    current = index
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            if rows:
                break
            continue
        match = KEY_VALUE_RE.match(line)
        if not match:
            break
        rows.append([match.group("term").strip(), match.group("definition").strip()])
        current += 1
    if len(rows) < 2:
        return None
    return render_table(["Term", "Meaning"], rows, "source-table lesson-definition-table"), current


def collect_colon_definition_table(lines: list[str], index: int) -> tuple[str, int] | None:
    rows = []
    current = index
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            if rows:
                break
            continue
        match = COLON_DEFINITION_RE.match(line)
        if not match:
            break
        rows.append([match.group("term").strip(), match.group("definition").strip()])
        current += 1
    if len(rows) < 2:
        return None
    return render_table(["Term", "Meaning"], rows, "source-table lesson-definition-table"), current


def collect_dash_definition_table(lines: list[str], index: int) -> tuple[str, int] | None:
    rows = []
    current = index
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            if rows:
                break
            continue
        match = NUMBERED_DEFINITION_RE.match(line) or DASH_DEFINITION_RE.match(line) or SYMBOL_DEFINITION_RE.match(line)
        if not match:
            break
        rows.append([match.group("term").strip(), match.group("definition").strip()])
        current += 1
    if len(rows) < 2:
        return None
    return render_table(["Item", "Meaning"], rows, "source-table lesson-definition-table"), current


def collect_primary_key_table(lines: list[str], index: int) -> tuple[str, int] | None:
    rows = []
    current = index
    last_label = ""
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            if rows:
                break
            continue
        match = KEY_CHOICE_RE.match(line)
        if match:
            label = match.group("label").strip()
            field = match.group("field").strip()
            reason = (match.group("reason") or "").strip("() ")
            rows.append([label, field, reason])
            last_label = label
            current += 1
            continue
        continuation = re.match(r"^(?P<field>[A-Za-z0-9_]+)\s*(?P<reason>\(.+\))$", line)
        if continuation and last_label:
            rows.append([last_label, continuation.group("field").strip(), continuation.group("reason").strip("() ")])
            current += 1
            continue
        break
    if not rows:
        return None
    return render_table(["Choice", "Field", "Reason"], rows, "source-table lesson-key-table"), current


def collect_relationship_type_table(lines: list[str], index: int) -> tuple[str, int] | None:
    rows = []
    current = index
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            if rows:
                break
            continue
        match = RELATION_TYPE_RE.match(line)
        if not match:
            break
        example = ""
        current += 1
        while current < len(lines):
            candidate = lines[current].strip()
            if not candidate:
                current += 1
                break
            if RELATION_TYPE_RE.match(candidate):
                break
            if candidate.lower().startswith("example:"):
                example = candidate.split(":", 1)[1].strip()
            elif example:
                example = f"{example} {candidate}".strip()
            else:
                example = candidate
            current += 1
        rows.append([match.group("name"), match.group("notation"), match.group("description"), example])
    if not rows:
        return None
    return render_table(["Relationship", "Notation", "Meaning", "Example"], rows, "source-table lesson-relationship-table"), current


def collect_schema_lines(lines: list[str], index: int) -> tuple[str, int] | None:
    rows = []
    current = index
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            if rows:
                break
            continue
        match = SCHEMA_LINE_RE.match(line)
        if not match:
            break
        rows.append([match.group("name").strip(), match.group("columns").strip()])
        current += 1
    if not rows:
        return None
    return render_table(["Table", "Columns"], rows, "source-table lesson-schema-table"), current


def render_relationship_map(lines: list[str]) -> str | None:
    text = "\n".join(lines).strip()
    if "(PK:" not in text or "\n    |" not in text:
        return None
    return f'<div class="lesson-diagram-block">{escape(text)}</div>'


def render_relation_line(line: str) -> str | None:
    if "-->" not in line and "->" not in line and "→" not in line:
        return None
    normalized = line.replace("-->", "→").replace("->", "→")
    parts = [part.strip() for part in normalized.split("→", 1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None
    target = parts[1]
    relationship = ""
    match = re.search(r"\(([^)]+)\)\s*$", target)
    if match:
        relationship = match.group(1)
        target = target[: match.start()].strip()
    return (
        '<div class="lesson-relation-row">'
        f'<span>{escape(parts[0])}</span><strong>→</strong><span>{escape(target)}</span>'
        f'{"<em>" + escape(relationship) + "</em>" if relationship else ""}'
        "</div>"
    )


def render_code_block(lines: list[str]) -> str:
    code_lines = list(lines)
    while code_lines and not code_lines[0].strip():
        code_lines.pop(0)
    while code_lines and not code_lines[-1].strip():
        code_lines.pop()
    if not code_lines:
        return ""
    return f"<pre><code>{escape(chr(10).join(code_lines))}</code></pre>"


def render_structured_section(inner_html: str, title: str = "") -> str:
    heading = f"<h3>{escape(title)}</h3>" if title else ""
    return f'<section class="lesson-structured-block">{heading}{inner_html}</section>'


def render_mixed_sql_code_block(lines: list[str]) -> str | None:
    parts = []
    code_lines = []
    structured_parts = 0
    current = 0

    def flush_code() -> None:
        nonlocal code_lines
        code_html = render_code_block(code_lines)
        if code_html:
            parts.append(code_html)
        code_lines = []

    while current < len(lines):
        line = lines[current].strip()
        heading_match = CODE_SECTION_HEADING_RE.match(line)
        if heading_match and current + 1 < len(lines):
            title = heading_match.group("title").strip()
            if RESULT_HEADING_RE.match(line):
                if is_ascii_table_header(lines, current + 1):
                    flush_code()
                    table_html, current = collect_ascii_table(lines, current + 1)
                    parts.append(render_structured_section(table_html, title))
                    structured_parts += 1
                    continue
                if is_pipe_table(lines, current + 1):
                    flush_code()
                    table_html, current = collect_pipe_table(lines, current + 1)
                    parts.append(render_structured_section(table_html, title))
                    structured_parts += 1
                    continue
            definitions = collect_dash_definition_table(lines, current + 1)
            if definitions:
                flush_code()
                table_html, current = definitions
                parts.append(render_structured_section(table_html, title))
                structured_parts += 1
                continue
        definitions = collect_dash_definition_table(lines, current)
        if definitions:
            flush_code()
            table_html, current = definitions
            parts.append(render_structured_section(table_html))
            structured_parts += 1
            continue
        if is_ascii_table_header(lines, current):
            flush_code()
            table_html, current = collect_ascii_table(lines, current)
            parts.append(render_structured_section(table_html))
            structured_parts += 1
            continue
        code_lines.append(lines[current])
        current += 1

    flush_code()
    if structured_parts == 0:
        return None
    return "".join(parts)


def render_structured_code_block(value: str) -> str | None:
    lines = clean_code_lines(value)
    if not lines:
        return None
    text = "\n".join(lines)
    if SQL_CODE_RE.search(text):
        mixed_sql = render_mixed_sql_code_block(lines)
        if mixed_sql:
            return mixed_sql
        if not any(is_ascii_table_header(lines, index) for index in range(len(lines))):
            return None
    relationship_map = render_relationship_map(lines)
    if relationship_map:
        return render_structured_section(relationship_map)
    parts = []
    structured_parts = 0
    current = 0
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            continue
        if line.endswith(":") and current + 1 < len(lines) and is_ascii_table_header(lines, current + 1):
            parts.append(f'<h3>{escape(line[:-1].strip())}</h3>')
            table_html, current = collect_ascii_table(lines, current + 1)
            parts.append(table_html)
            structured_parts += 1
            continue
        if line.endswith(":") and current + 1 < len(lines) and is_pipe_table(lines, current + 1):
            parts.append(f'<h3>{escape(line[:-1].strip())}</h3>')
            table_html, current = collect_pipe_table(lines, current + 1)
            parts.append(table_html)
            structured_parts += 1
            continue
        heading_match = CODE_SECTION_HEADING_RE.match(line)
        if heading_match and current + 1 < len(lines):
            definitions = collect_dash_definition_table(lines, current + 1)
            if definitions:
                parts.append(f'<h3>{escape(heading_match.group("title").strip())}</h3>')
                html, current = definitions
                parts.append(html)
                structured_parts += 1
                continue
        if is_ascii_table_header(lines, current):
            table_html, current = collect_ascii_table(lines, current)
            parts.append(table_html)
            structured_parts += 1
            continue
        primary_key = collect_primary_key_table(lines, current)
        if primary_key:
            html, current = primary_key
            parts.append(html)
            structured_parts += 1
            continue
        relationship_types = collect_relationship_type_table(lines, current)
        if relationship_types:
            html, current = relationship_types
            parts.append(html)
            structured_parts += 1
            continue
        schemas = collect_schema_lines(lines, current)
        if schemas:
            html, current = schemas
            parts.append(html)
            structured_parts += 1
            continue
        if is_pipe_table(lines, current):
            table_html, current = collect_pipe_table(lines, current)
            parts.append(table_html)
            structured_parts += 1
            continue
        key_values = collect_key_value_table(lines, current)
        if key_values:
            html, current = key_values
            parts.append(html)
            structured_parts += 1
            continue
        colon_definitions = collect_colon_definition_table(lines, current)
        if colon_definitions:
            html, current = colon_definitions
            parts.append(html)
            structured_parts += 1
            continue
        dash_definitions = collect_dash_definition_table(lines, current)
        if dash_definitions:
            html, current = dash_definitions
            parts.append(html)
            structured_parts += 1
            continue
        relation = render_relation_line(line)
        if relation:
            parts.append(relation)
            current += 1
            structured_parts += 1
            continue
        if "|" in line and ":" in line:
            label, row = [part.strip() for part in line.split(":", 1)]
            parts.append(render_table([label, "Fields"], [[label, row]], "source-table lesson-schema-table"))
            current += 1
            structured_parts += 1
            continue
        if line.endswith(":") and parts:
            parts.append(f'<h3>{escape(line[:-1].strip())}</h3>')
            current += 1
            continue
        return None
    if structured_parts == 0:
        return None
    return render_structured_section("".join(parts))


def render_lesson_code_blocks(content_html: str) -> str:
    def replace_code_block(match: re.Match) -> str:
        structured = render_structured_code_block(match.group("body"))
        return structured if structured else match.group(0)

    return PRE_CODE_RE.sub(replace_code_block, content_html)


def compact_source_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def source_contains(value: str, phrase: str) -> bool:
    return compact_source_text(phrase) in compact_source_text(value)


def is_source_admin_block_heading(line: str) -> bool:
    stripped = line.strip()
    return (
        bool(SOURCE_ADMIN_BLOCK_RE.match(stripped))
        or source_contains(stripped, "where do i find the content")
        or source_contains(stripped, "go to canvas modules")
        or source_contains(stripped, "is there a prescribed textbook")
        or source_contains(stripped, "how are classes structured each week")
        or source_contains(stripped, "do i need to attend")
        or source_contains(stripped, "assessment rubrics")
        or source_contains(stripped, "grading system")
    )


def is_source_intro_map_line(line: str) -> bool:
    stripped = line.strip()
    return bool(SOURCE_INTRO_MAP_RE.match(stripped)) or any(source_contains(stripped, phrase) for phrase in SOURCE_INTRO_ADMIN_PHRASES)


def is_source_admin_line(line: str, index: int) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    if stripped.lower() == "introduction":
        return True
    if re.fullmatch(r"\d{1,3}", stripped):
        return True
    if SOURCE_COURSE_LINE_RE.match(stripped):
        return True
    if SOURCE_MONTH_RE.match(stripped):
        return True
    if re.match(r"^\d{1,2}\s+[A-Z][A-Za-z]+\s+\d{4}$", stripped):
        return True
    if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", stripped):
        return True
    if re.search(r"@[\w.-]+", stripped):
        return True
    if re.match(r"^(?:presented by|presenter|chapter\s+\d+|lecture\s+\d+|part\s+\d+\s*[-–]|source:|ref:|refer canvas|assessment)\b", stripped, re.I):
        return True
    if index < 14 and re.match(r"^(?:Dr|Professor)\s+[A-Z][A-Za-z.'-]+", stripped):
        return True
    if index < 14 and " and " in stripped and re.fullmatch(r"[A-Z][A-Za-z.'-]+(?: [A-Z][A-Za-z.'-]+)+(?: and [A-Z][A-Za-z.'-]+(?: [A-Z][A-Za-z.'-]+)+)", stripped):
        return True
    if re.match(r"^\d+(?:\.\d+)+\s+", stripped) and SOURCE_OBJECTIVE_RE.match(stripped):
        return True
    if is_source_admin_block_heading(stripped):
        return True
    return False


def strip_source_page_number(line: str) -> str:
    if SOURCE_REFERENCE_RE.match(line):
        return SOURCE_PAGE_MARKER_RE.sub(r"\g<title>", line).strip()
    return line


def is_source_page_marker(line: str) -> bool:
    stripped = line.strip()
    if re.fullmatch(r"\d{1,3}", stripped):
        return True
    match = SOURCE_PAGE_MARKER_RE.match(stripped)
    if not match:
        return False
    title = match.group("title").strip()
    if re.search(r"\.{3,}", title):
        return False
    if re.match(r"^(?:Table|Figure|Exhibit|Source|Image Source|References?)\b", title, re.I):
        return False
    if len(re.findall(r"\d+", title)) >= 2:
        return False
    if len(title) > 82:
        return False
    return bool(re.search(r"[A-Za-z]", title)) and not bool(re.search(r"[.!:;]$", title))


def is_source_block_noise_line(line: str, index: int) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    if is_source_admin_line(stripped, index):
        return True
    if SOURCE_OBJECTIVE_RE.match(stripped):
        return True
    if is_source_intro_map_line(stripped):
        return True
    if source_contains(stripped, "canvas modules") or source_contains(stripped, "go to canvas") or source_contains(stripped, "available asynchronous"):
        return True
    if re.match(r"^each week has\b", stripped, re.I):
        return True
    if source_contains(stripped, "slides recordings weekly") or source_contains(stripped, "prescribed textbook"):
        return True
    if stripped.lower() == "no":
        return True
    if re.match(r"^lots to cover\b", stripped, re.I):
        return True
    return False


def looks_like_source_content_start(line: str, index: int) -> bool:
    stripped = line.strip()
    if not stripped or is_source_admin_line(stripped, index):
        return False
    if source_contains(stripped, "value chain") or VISUAL_REFERENCE_RE.match(stripped):
        return True
    if stripped.startswith(("• ", "- ")):
        return True
    if SOURCE_OBJECTIVE_RE.match(stripped) or is_source_intro_map_line(stripped):
        return False
    if source_heading_level(stripped, index):
        return True
    if re.match(r"^(?:what|why|how)\s+(?:is|are|does|do|can|will|were|was)\b", stripped, re.I) and not is_source_admin_block_heading(stripped):
        return True
    words = stripped.split()
    return len(words) <= 9 and len(stripped) <= 80 and not stripped.endswith(".") and bool(re.match(r"^[A-Z]", stripped))


def filter_source_lines(lines: list[str]) -> list[str]:
    filtered = []
    index = 0
    skip_block = False
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            if filtered and filtered[-1] and not skip_block:
                filtered.append("")
            index += 1
            continue
        if skip_block:
            if is_source_block_noise_line(line, index):
                index += 1
                continue
            if looks_like_source_content_start(line, index):
                skip_block = False
                continue
            index += 1
            continue
        if is_source_admin_block_heading(line):
            skip_block = True
            index += 1
            continue
        if is_source_page_marker(line):
            index += 1
            continue
        if is_source_admin_line(line, index):
            index += 1
            continue
        filtered.append(strip_source_page_number(line))
        index += 1
    while filtered and not filtered[0]:
        filtered.pop(0)
    while filtered and not filtered[-1]:
        filtered.pop()
    return filtered


def skip_source_intro_map(lines: list[str], index: int) -> int:
    while index < len(lines):
        line = lines[index].strip()
        if not line or is_source_intro_map_line(line):
            index += 1
            continue
        return index
    return index


def clean_visual_title(value: str) -> str:
    title = re.sub(r"\s+", " ", value).strip(" :-")
    return title[:120]


def clean_visual_items(lines: list[str], limit: int = 5) -> list[str]:
    items = []
    for line in lines:
        cleaned = clean_visual_title(re.sub(r"^[•-]\s*", "", line))
        if not cleaned or cleaned.isdigit() or cleaned.lower().startswith(("source:", "ref:")):
            continue
        if len(cleaned) < 3:
            continue
        items.append(cleaned)
        if len(items) == limit:
            break
    return items


def split_visual_flow_items(value: str) -> list[str]:
    parts = re.split(r"\s*(?:>|→|->|&gt;)\s*", value)
    return [clean_visual_title(part) for part in parts if clean_visual_title(part)]


def collect_visual_context(lines: list[str], start: int, limit: int = 8) -> list[str]:
    context = []
    index = start
    while index < len(lines) and len(context) < limit:
        line = lines[index].strip()
        if context and VISUAL_REFERENCE_RE.match(line):
            break
        if line:
            context.append(line)
        index += 1
    return context


def render_value_chain_diagram() -> str:
    support = ["Firm infrastructure", "Human resource management", "Technology development", "Procurement"]
    primary = ["Research and development", "Inbound logistics", "Operations", "Outbound logistics", "Marketing and sales", "Service"]
    support_html = "".join(f"<li>{escape(item)}</li>" for item in support)
    primary_html = "".join(f"<li>{escape(item)}</li>" for item in primary)
    return (
        '<figure class="source-visual source-value-chain" aria-label="Generic Value Chain diagram">'
        '<figcaption>Generic Value Chain</figcaption>'
        '<div class="value-chain-body">'
        '<div class="value-chain-label value-chain-support-label">Support activities</div>'
        f'<ol class="value-chain-support">{support_html}</ol>'
        '<div class="value-chain-label value-chain-primary-label">Primary activities</div>'
        f'<ol class="value-chain-primary">{primary_html}</ol>'
        '<div class="value-chain-margin value-chain-margin-top">Margin</div>'
        '<div class="value-chain-margin value-chain-margin-bottom">Margin</div>'
        "</div>"
        "</figure>"
    )


def render_flow_visual(title: str, items: list[str]) -> str:
    if len(items) < 2:
        return ""
    item_html = "".join(f"<li><span>{escape(item)}</span></li>" for item in items[:6])
    return (
        '<figure class="source-visual source-flow-visual">'
        f"<figcaption>{escape(clean_visual_title(title))}</figcaption>"
        f"<ol>{item_html}</ol>"
        "</figure>"
    )


def render_competitive_environment_visual(title: str) -> str:
    factors = ["Competitors", "New entrants", "Substitutes", "Suppliers", "Customers"]
    factor_html = "".join(f"<li>{escape(factor)}</li>" for factor in factors)
    return (
        '<figure class="source-visual source-network-visual">'
        f"<figcaption>{escape(clean_visual_title(title))}</figcaption>"
        '<div class="network-visual-body">'
        '<div class="network-core">Firm</div>'
        f"<ol>{factor_html}</ol>"
        "</div>"
        "</figure>"
    )


def render_generic_figure_visual(title: str, context_lines: list[str]) -> str:
    items = clean_visual_items(context_lines)
    if not items:
        return ""
    item_html = "".join(f"<li>{escape(item)}</li>" for item in items)
    return (
        '<figure class="source-visual source-exhibit-visual">'
        f"<figcaption>{escape(clean_visual_title(title))}</figcaption>"
        f"<ul>{item_html}</ul>"
        "</figure>"
    )


def render_visual_reference(line: str, lines: list[str], index: int) -> tuple[str, int] | None:
    if source_contains(line, "value chain"):
        return render_value_chain_diagram(), skip_source_intro_map(lines, index + 1)
    if not VISUAL_REFERENCE_RE.match(line):
        return None
    title = line
    next_index = index + 1
    if next_index < len(lines):
        next_line = lines[next_index].strip()
        if next_line and len(next_line) < 120 and not VISUAL_REFERENCE_RE.match(next_line):
            title = f"{title}: {next_line}"
            next_index += 1
    context = collect_visual_context(lines, next_index)
    combined = " ".join([title, *context])
    if source_contains(combined, "value chain"):
        return render_value_chain_diagram(), next_index
    flow_line = next((candidate for candidate in context if ">" in candidate or "->" in candidate or "→" in candidate), "")
    if flow_line:
        visual = render_flow_visual(title, split_visual_flow_items(flow_line))
        if visual:
            return visual, next_index
    if source_contains(combined, "competitive environment"):
        return render_competitive_environment_visual(title), next_index
    visual = render_generic_figure_visual(title, context)
    if visual:
        return visual, next_index
    return None


def normalize_source_math_line(line: str) -> str:
    return re.sub(r"\s+", " ", line.translate(PDF_MATH_TRANSLATION)).strip()


def is_source_math_example_line(line: str) -> bool:
    return bool(MATH_EXAMPLE_RE.match(line.strip()))


def is_source_math_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return False
    normalized = normalize_source_math_line(stripped)
    if re.search(r"\.{4,}\s*\d+$", normalized):
        return False
    if MATH_GLYPH_RE.search(stripped) or MATH_GLYPH_RE.search(normalized):
        return True
    if re.fullmatch(r"(?:\.{2,}|…)(?:\s+(?:\.{2,}|…)){1,}", normalized):
        return True
    if re.search(r"\b[a-zA-Z]{1,4}\d{1,2}\b", normalized) and len(normalized) <= 220:
        return True
    if MATH_ASSIGNMENT_RE.match(normalized) and len(normalized) <= 240:
        return True
    numbers = MATH_DENSE_NUMBER_RE.findall(normalized)
    letter_words = re.findall(r"[A-Za-z]{2,}", normalized)
    if len(numbers) >= 2 and len(normalized) <= 220 and not letter_words:
        return True
    return "=" in normalized and len(normalized) <= 240 and bool(MATH_DENSE_SYMBOL_RE.search(normalized))


def render_source_math_block(lines: list[str]) -> str:
    body = "\n".join(render_radicals_in_text(escape(normalize_source_math_line(line))) if line else "" for line in lines)
    return f'<pre class="source-math-block">{body}</pre>'


def collect_source_math_block(lines: list[str], index: int) -> tuple[list[str], int]:
    block_lines = []
    pending_blanks = []
    current = index
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            if block_lines:
                pending_blanks.append("")
            current += 1
            continue
        if not is_source_math_line(line):
            break
        block_lines.extend(pending_blanks)
        pending_blanks = []
        block_lines.append(line)
        current += 1
    return block_lines, current


def join_source_fragments(fragments: list[str]) -> str:
    text = " ".join(fragment.strip() for fragment in fragments if fragment.strip())
    text = re.sub(r"\s+", " ", text)
    if " . ." not in text:
        text = re.sub(r"\s+([,.;:?!)])", r"\1", text)
    text = re.sub(r"([(])\s+", r"\1", text)
    text = text.replace(" - ", " – ")
    return text.strip()


def is_source_reference_line(line: str) -> bool:
    stripped = line.strip()
    return bool(SOURCE_REFERENCE_RE.match(stripped) or re.match(r"^https?://", stripped, re.I))


def is_source_list_item(line: str) -> bool:
    stripped = line.strip()
    return bool(SOURCE_BULLET_RE.match(stripped) or SOURCE_NUMBERED_ITEM_RE.match(stripped))


def is_source_definition_line(line: str) -> bool:
    stripped = line.strip()
    if not SOURCE_DEFINITION_RE.search(stripped):
        return False
    if re.match(r"^(?:Source|Image Source|http)", stripped, re.I):
        return False
    return len(stripped) <= 150 and bool(re.match(r"^[A-Z0-9]", stripped))


def source_list_type(line: str) -> str:
    return "ol" if SOURCE_NUMBERED_ITEM_RE.match(line.strip()) else "ul"


def strip_source_list_marker(line: str) -> str:
    return SOURCE_NUMBERED_ITEM_RE.sub("", SOURCE_BULLET_RE.sub("", line.strip())).strip()


def source_is_short_fragment(line: str) -> bool:
    stripped = line.strip()
    if not stripped or is_source_reference_line(stripped) or is_source_list_item(stripped):
        return False
    if is_source_math_line(stripped):
        return False
    if len(stripped) > 48:
        return False
    if re.search(r"\.{3,}", stripped):
        return False
    return bool(re.search(r"[A-Za-z]", stripped))


def previous_source_is_blank(lines: list[str], index: int) -> bool:
    return index <= 0 or not lines[index - 1].strip()


def collect_source_heading_text(lines: list[str], index: int) -> tuple[str, int]:
    fragments = [lines[index].strip()]
    current = index + 1
    while current < len(lines) and len(fragments) < 4:
        candidate = lines[current].strip()
        if not candidate:
            break
        combined = join_source_fragments([*fragments, candidate])
        if len(combined) > 90 or not source_is_short_fragment(candidate):
            break
        previous = fragments[-1].strip().lower()
        should_join = previous.endswith((":", "of", "and", "to", "with", "for", "vs")) or candidate[:1].islower()
        should_join = should_join or (len(fragments) == 1 and index == 0)
        if not should_join:
            break
        fragments.append(candidate)
        current += 1
    return join_source_fragments(fragments), current


def is_source_context_heading(lines: list[str], index: int) -> bool:
    line = lines[index].strip()
    if source_heading_level(line, index):
        return True
    if not source_is_short_fragment(line):
        return False
    lowered = line.lower()
    if lowered in {"summary", "references", "lecture overview", "this week", "overview"}:
        return True
    if not previous_source_is_blank(lines, index):
        return False
    if re.match(r"^(?:At|The|This|These|We|It|Current|Related|From|Less|More|Various|Extracting|Insights|Focus)\b", line):
        return False
    next_index = index + 1
    while next_index < len(lines) and not lines[next_index].strip():
        next_index += 1
    if next_index >= len(lines):
        return True
    next_line = lines[next_index].strip()
    if line.endswith("?"):
        return True
    if line.lower().endswith((" of", " and", " to", " with", " for", " vs")):
        return True
    if len(line.split()) <= 4 and not line.endswith("."):
        return True
    if len(line.split()) <= 6 and len(line) <= 70 and next_line[:1].islower():
        return True
    return False


def collect_source_list(lines: list[str], index: int) -> tuple[str, int]:
    tag = source_list_type(lines[index])
    class_name = "source-numbered-list" if tag == "ol" else "source-list"
    items = []
    current = index
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            if current >= len(lines) or not is_source_list_item(lines[current].strip()):
                break
            continue
        if not is_source_list_item(line):
            break
        item_fragments = [strip_source_list_marker(line)]
        current += 1
        while current < len(lines):
            candidate = lines[current].strip()
            if not candidate:
                current += 1
                break
            if is_source_list_item(candidate) or is_source_context_heading(lines, current) or is_source_reference_line(candidate):
                break
            if tag == "ol" and item_fragments and re.match(r"^[A-Z]", candidate) and len(join_source_fragments(item_fragments)) > 34:
                break
            item_fragments.append(candidate)
            current += 1
        items.append(f"<li>{escape(join_source_fragments(item_fragments))}</li>")
    return f'<{tag} class="{class_name}">{"".join(items)}</{tag}>', current


def collect_source_definition_list(lines: list[str], index: int) -> tuple[str, int]:
    items = []
    current = index
    while current < len(lines):
        line = lines[current].strip()
        if not is_source_definition_line(line):
            break
        fragments = [line]
        current += 1
        while current < len(lines):
            candidate = lines[current].strip()
            if not candidate:
                current += 1
                break
            if is_source_definition_line(candidate) or is_source_list_item(candidate) or is_source_context_heading(lines, current):
                break
            fragments.append(candidate)
            current += 1
        statement = join_source_fragments(fragments)
        term, description = re.split(r"\s[-–—]\s", statement, maxsplit=1)
        items.append(f"<dt>{escape(term.strip())}</dt><dd>{escape(description.strip())}</dd>")
    return f'<dl class="source-definition-list">{"".join(items)}</dl>', current


def collect_source_paragraph(lines: list[str], index: int) -> tuple[str, int]:
    fragments = []
    current = index
    while current < len(lines):
        line = lines[current].strip()
        if not line:
            current += 1
            break
        if fragments and (
            is_source_context_heading(lines, current)
            or is_source_list_item(line)
            or is_source_definition_line(line)
            or is_source_reference_line(line)
            or is_source_math_line(line)
            or is_source_math_example_line(line)
            or render_visual_reference(line, lines, current)
            or line.lower() == "binary counting"
            or re.search(r"HEX\s*[–-]\s*BINARY\s*\(4 BITS TO A HEX DIGIT\)", line, re.I)
            or line.lower().startswith("8-bit example")
        ):
            break
        fragments.append(line)
        current += 1
    return join_source_fragments(fragments), current


def collect_source_overview(lines: list[str], index: int) -> tuple[str, int]:
    current = index + 1
    items = []
    while current < len(lines):
        while current < len(lines) and not lines[current].strip():
            current += 1
        if current >= len(lines):
            break
        line = lines[current].strip()
        if is_source_reference_line(line) or is_source_list_item(line) or is_source_math_line(line):
            break
        if line.lower() in {"references", "reference"}:
            break
        if not source_is_short_fragment(line):
            break
        item, next_index = collect_source_heading_text(lines, current)
        preview_index = next_index
        while preview_index < len(lines) and not lines[preview_index].strip():
            preview_index += 1
        following_preview, _ = collect_source_paragraph(lines, preview_index)
        if items and source_is_short_fragment(item) and len(following_preview) > 80:
            break
        if not item or len(item) > 130:
            break
        items.append(f"<li>{escape(item)}</li>")
        current = next_index
        if len(items) >= 8:
            break
    if not items:
        return "", index + 1
    return f'<ul class="source-overview-list">{"".join(items)}</ul>', current


def render_source_line(line: str, index: int) -> str:
    if is_source_math_example_line(line):
        return f'<div class="source-math-example">{escape(line)}</div>'
    level = source_heading_level(line, index)
    if level:
        return f"<h{level}>{escape(line)}</h{level}>"
    if line.startswith("=") or re.search(r"\b\d+\s*[*x]\s*\d+", line):
        return f'<div class="source-equation">{escape(line)}</div>'
    if re.match(r"^(e\.?g\.?|example|exercise)\b", line, re.I):
        return f'<div class="source-example">{escape(line)}</div>'
    return f"<p>{escape(line)}</p>"


def render_source_text(raw_text: str) -> str:
    lines = filter_source_lines(normalize_source_text(raw_text).splitlines())
    parts = ['<section class="source-text source-text-readable lesson-source">']
    index = 0
    current_heading = ""
    last_heading = ""
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if is_source_math_example_line(line):
            parts.append(f'<div class="source-math-example">{escape(line)}</div>')
            index += 1
            continue
        visual = render_visual_reference(line, lines, index)
        if visual:
            visual_html, next_index = visual
            parts.append(visual_html)
            index = next_index
            continue
        if line.lower() == "binary counting":
            parts.append("<h3>Binary Counting</h3>")
            parts.append(render_binary_counting_table())
            index += 1
            while index < len(lines) and not re.search(r"\bHEX|HEXADECIMAL\b", lines[index], re.I):
                index += 1
            continue
        if re.search(r"HEX\s*[–-]\s*BINARY\s*\(4 BITS TO A HEX DIGIT\)", line, re.I):
            parts.append("<h3>HEX - BINARY (4 Bits To A Hex Digit)</h3>")
            parts.append(render_hex_binary_table())
            index += 1
            continue
        if line.lower().startswith("8-bit example"):
            parts.append("<h3>8-Bit Example</h3>")
            lookahead = [line, *[candidate.strip() for candidate in lines[index + 1 : index + 6]]]
            bit_line = next((candidate for candidate in lookahead if re.fullmatch(r"(?:[01]\s+){7}[01]", candidate)), "")
            if bit_line:
                parts.append(render_bit_weight_table(bit_line.split()))
            index += 1
            continue
        if is_source_context_heading(lines, index):
            heading, next_index = collect_source_heading_text(lines, index)
            level = source_heading_level(line, index) or 3
            heading_key = compact_source_text(heading)
            if heading_key != last_heading:
                parts.append(f"<h{level}>{escape(heading)}</h{level}>")
            current_heading = heading_key
            last_heading = heading_key
            if heading.lower() in {"lecture overview", "this week", "summary"}:
                overview_html, overview_index = collect_source_overview(lines, next_index)
                if overview_html:
                    parts.append(overview_html)
                    index = overview_index
                    continue
            index = next_index
            continue
        if is_source_list_item(line):
            list_html, next_index = collect_source_list(lines, index)
            parts.append(list_html)
            index = next_index
            continue
        if is_source_definition_line(line):
            definition_html, next_index = collect_source_definition_list(lines, index)
            parts.append(definition_html)
            index = next_index
            continue
        if is_source_reference_line(line):
            reference_text, next_index = collect_source_paragraph(lines, index)
            parts.append(f'<p class="source-citation">{escape(reference_text)}</p>')
            index = next_index
            continue
        if is_source_math_line(line):
            if current_heading in {"references", "reference"}:
                reference_text, next_index = collect_source_paragraph(lines, index)
                parts.append(f'<p class="source-citation">{escape(reference_text)}</p>')
                index = next_index
                continue
            math_lines, next_index = collect_source_math_block(lines, index)
            parts.append(render_source_math_block(math_lines))
            index = next_index
            continue
        paragraph, next_index = collect_source_paragraph(lines, index)
        if paragraph:
            parts.append(render_source_line(paragraph, index))
        index = next_index
    parts.append("</section>")
    return "".join(parts)


def render_content_html(content_html: str) -> str:
    def replace_source_text(match: re.Match) -> str:
        return render_source_text(match.group("body"))

    source_html = SOURCE_TEXT_RE.sub(replace_source_text, content_html)
    structured_html = render_lesson_code_blocks(source_html)
    return render_inline_math_notation(structured_html)


def render_summary_text(lesson: Lesson) -> str:
    match = SOURCE_TEXT_RE.search(lesson.content_html)
    if not match:
        return lesson.summary
    lines = [line for line in normalize_source_text(match.group("body")).splitlines() if line.strip()]
    return " · ".join(lines[:2])


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def get_reload_token() -> str:
    import subprocess as _sp
    try:
        _git_hash = _sp.check_output(["git", "rev-parse", "--short", "HEAD"], stderr=_sp.DEVNULL, timeout=3).decode().strip()
    except Exception:
        _git_hash = "0"
    latest = 0
    total = 0
    for root in RELOAD_WATCH_ROOTS:
        if not root.exists():
            continue
        paths = [root] if root.is_file() else root.rglob("*")
        for path in paths:
            if not path.is_file() or RELOAD_SKIP_PARTS.intersection(path.parts):
                continue
            stat = path.stat()
            latest = max(latest, stat.st_mtime_ns)
            total += stat.st_size
    return f"{_git_hash}:{latest}:{total}"


def parse_options(options_text: str) -> str:
    options = [item.strip() for item in options_text.splitlines() if item.strip()]
    return json.dumps(options, ensure_ascii=False)


def is_reference_section(title: str) -> bool:
    return title.strip().casefold() in REFERENCE_SECTION_KEYS


def is_recording_section(title: str) -> bool:
    return title.strip().casefold() in RECORDING_SECTION_KEYS


def visible_section_expression():
    return ~func.lower(Section.title).in_(REFERENCE_SECTION_KEYS)


def get_subject_block(title: str) -> str:
    return SUBJECT_BLOCKS.get(title, "IT")


def find_subject_image(subject: Subject) -> str | None:
    for section in sorted(subject.sections, key=lambda item: item.position):
        if not is_reference_section(section.title):
            continue
        for lesson in sorted(section.lessons, key=lambda item: item.position):
            match = IMAGE_SRC_RE.search(lesson.content_html or "")
            if match:
                return match.group("src")
    for section in sorted(subject.sections, key=lambda item: item.position):
        for lesson in sorted(section.lessons, key=lambda item: item.position):
            match = IMAGE_SRC_RE.search(lesson.content_html or "")
            if match:
                return match.group("src")
    return None


def attach_subject_view_data(subject: Subject) -> Subject:
    subject.block_title = get_subject_block(subject.title)
    subject.image_url = find_subject_image(subject)
    subject.illustration = SUBJECT_ILLUSTRATIONS.get(subject.title, DEFAULT_SUBJECT_ILLUSTRATION)
    sorted_sections = sorted(subject.sections, key=lambda item: item.position)
    learning_sections = [section for section in sorted_sections if not is_reference_section(section.title)]
    subject.visible_sections = learning_sections or sorted_sections
    for section in subject.visible_sections:
        section.display_title = "Echo360 Videos" if is_recording_section(section.title) else "Lessons" if is_reference_section(section.title) else section.title
        section.visible_lessons = [
            lesson
            for lesson in sorted(section.lessons, key=lambda item: item.position)
            if lesson.is_published
        ]
    return subject


def group_subjects(subjects: list[Subject]) -> list[dict]:
    for subject in subjects:
        attach_subject_view_data(subject)
    blocks = []
    for block_title in SUBJECT_BLOCK_ORDER:
        block_subjects = [subject for subject in subjects if subject.block_title == block_title]
        if block_subjects:
            blocks.append({"title": block_title, "subjects": block_subjects})
    extras = [subject for subject in subjects if subject.block_title not in SUBJECT_BLOCK_ORDER]
    if extras:
        blocks.append({"title": "Other", "subjects": extras})
    return blocks


@app.get("/api/reload-token")
def reload_token():
    return JSONResponse({"token": get_reload_token()})


def get_subject_tree(db: Session) -> list[Subject]:
    subjects = (
        db.query(Subject)
        .options(joinedload(Subject.sections).joinedload(Section.lessons))
        .filter(Subject.is_published.is_(True))
        .order_by(Subject.position)
        .all()
    )
    subjects.sort(key=lambda subject: subject.position)
    for subject in subjects:
        subject.sections.sort(key=lambda section: section.position)
        for section in subject.sections:
            section.lessons.sort(key=lambda lesson: lesson.position)
        attach_subject_view_data(subject)
    return subjects


def get_first_lesson(db: Session) -> Lesson | None:
    return (
        db.query(Lesson)
        .join(Section)
        .join(Subject)
        .options(joinedload(Lesson.section).joinedload(Section.subject), joinedload(Lesson.exercises))
        .filter(Subject.is_published.is_(True), Lesson.is_published.is_(True), visible_section_expression())
        .order_by(Subject.position, Section.position, Lesson.position)
        .first()
    )


def get_replacement_lesson(lesson_id: int, db: Session) -> Lesson | None:
    legacy_lesson = db.get(Lesson, lesson_id)
    if not legacy_lesson:
        return None
    return (
        db.query(Lesson)
        .join(Lesson.section)
        .join(Section.subject)
        .options(joinedload(Lesson.section).joinedload(Section.subject), joinedload(Lesson.exercises))
        .filter(
            Lesson.id != legacy_lesson.id,
            Lesson.title == legacy_lesson.title,
            Lesson.is_published.is_(True),
            Subject.is_published.is_(True),
            visible_section_expression(),
        )
        .order_by(Subject.position, Section.position, Lesson.position)
        .first()
    ) or get_first_lesson(db)


def render_lesson_page(lesson: Lesson, request: Request, db: Session) -> HTMLResponse:
    user = current_user(request, db)
    lesson.exercises.sort(key=lambda exercise: exercise.position)
    subjects = get_subject_tree(db)
    progress = None
    attempts = []
    if user:
        progress = db.query(LessonProgress).filter_by(user_id=user.id, lesson_id=lesson.id).first()
        attempts = (
            db.query(ExerciseAttempt)
            .join(Exercise)
            .filter(ExerciseAttempt.user_id == user.id, Exercise.lesson_id == lesson.id)
            .order_by(ExerciseAttempt.created_at.desc())
            .all()
        )
    return render(
        request,
        "lesson.html",
        {
            "lesson": lesson,
            "subjects": subjects,
            "subject_blocks": group_subjects(subjects),
            "progress": progress,
            "attempts": attempts,
            "previous_lesson": get_previous_lesson(lesson, db),
            "next_lesson": get_next_lesson(lesson, db),
            "content_html": render_content_html(lesson.content_html),
            "summary_text": render_summary_text(lesson),
            "json": json,
        },
        db,
    )


@app.get("/api/lessons/{lesson_id}/translation")
def lesson_translation(lesson_id: int, request: Request, db: Session = Depends(get_db)):
    language = request.query_params.get("lang", "vi")
    if language not in {"en", "vi"}:
        raise HTTPException(status_code=400, detail="Unsupported language")
    lesson = (
        db.query(Lesson)
        .join(Section)
        .join(Subject)
        .filter(Lesson.id == lesson_id, Lesson.is_published.is_(True), Subject.is_published.is_(True))
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    payload = build_lesson_translation(
        lesson.id,
        lesson.title,
        render_summary_text(lesson),
        render_content_html(lesson.content_html),
        language,
    )
    return JSONResponse(
        {
            "language": payload["language"],
            "title": payload["title"],
            "summary": payload["summary"],
            "content_html": payload["content_html"],
        }
    )


def get_next_lesson(lesson: Lesson, db: Session) -> Lesson | None:
    return (
        db.query(Lesson)
        .join(Section)
        .filter(
            Section.subject_id == lesson.section.subject_id,
            Lesson.is_published.is_(True),
            visible_section_expression(),
            (Section.position > lesson.section.position)
            | ((Section.position == lesson.section.position) & (Lesson.position > lesson.position)),
        )
        .order_by(Section.position, Lesson.position)
        .first()
    )


def get_previous_lesson(lesson: Lesson, db: Session) -> Lesson | None:
    return (
        db.query(Lesson)
        .join(Section)
        .filter(
            Section.subject_id == lesson.section.subject_id,
            Lesson.is_published.is_(True),
            visible_section_expression(),
            (Section.position < lesson.section.position)
            | ((Section.position == lesson.section.position) & (Lesson.position < lesson.position)),
        )
        .order_by(Section.position.desc(), Lesson.position.desc())
        .first()
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    subjects = (
        db.query(Subject)
        .options(joinedload(Subject.sections).joinedload(Section.lessons))
        .filter(Subject.is_published.is_(True))
        .order_by(Subject.position)
        .all()
    )
    return render(request, "subjects.html", {"subjects": subjects, "subject_blocks": group_subjects(subjects)}, db)


@app.get("/auth/register", response_class=HTMLResponse)
def register_page(request: Request, db: Session = Depends(get_db)):
    return render(request, "auth/register.html", {"error": None}, db)


@app.post("/auth/register")
def register(
    request: Request,
    email: str = Form(...),
    display_name: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    normalized_email = email.strip().lower()
    existing = db.query(User).filter(User.email == normalized_email).first()
    if existing:
        return render(request, "auth/register.html", {"error": "Email already exists."}, db)
    user_count = db.query(func.count(User.id)).scalar() or 0
    user = User(
        email=normalized_email,
        display_name=display_name.strip(),
        password_hash=hash_password(password),
        role="admin" if user_count == 0 else "student",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    request.session["user_id"] = user.id
    return redirect("/dashboard")


@app.get("/auth/login", response_class=HTMLResponse)
def login_page(request: Request, db: Session = Depends(get_db)):
    return render(request, "auth/login.html", {"error": None}, db)


@app.post("/auth/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email.strip().lower()).first()
    if not user or not verify_password(password, user.password_hash):
        return render(request, "auth/login.html", {"error": "Email or password is incorrect."}, db)
    request.session["user_id"] = user.id
    return redirect("/dashboard")


@app.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/")


@app.get("/subjects", response_class=HTMLResponse)
def subjects_page(request: Request, db: Session = Depends(get_db)):
    subjects = (
        db.query(Subject)
        .options(joinedload(Subject.sections).joinedload(Section.lessons))
        .filter(Subject.is_published.is_(True))
        .order_by(Subject.position)
        .all()
    )
    return render(request, "subjects.html", {"subjects": subjects, "subject_blocks": group_subjects(subjects)}, db)


@app.get("/subjects/{subject_id}", response_class=HTMLResponse)
def subject_detail(subject_id: int, request: Request, db: Session = Depends(get_db)):
    subject = (
        db.query(Subject)
        .options(joinedload(Subject.sections).joinedload(Section.lessons))
        .filter(Subject.id == subject_id, Subject.is_published.is_(True))
        .first()
    )
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    subject.sections.sort(key=lambda section: section.position)
    for section in subject.sections:
        section.lessons.sort(key=lambda lesson: lesson.position)
    attach_subject_view_data(subject)
    return render(request, "subject_detail.html", {"subject": subject, "visible_sections": subject.visible_sections}, db)


@app.get("/lessons/{lesson_id}", response_class=HTMLResponse)
def lesson_detail(lesson_id: int, request: Request, db: Session = Depends(get_db)):
    lesson = (
        db.query(Lesson)
        .join(Section)
        .join(Subject)
        .options(joinedload(Lesson.section).joinedload(Section.subject), joinedload(Lesson.exercises))
        .filter(Lesson.id == lesson_id, Lesson.is_published.is_(True), Subject.is_published.is_(True))
        .first()
    )
    if not lesson:
        replacement = get_replacement_lesson(lesson_id, db)
        if replacement:
            return redirect(f"/lessons/{replacement.id}")
        return redirect("/subjects")
    return render_lesson_page(lesson, request, db)


@app.post("/exercises/{exercise_id}/attempts")
async def submit_attempt(exercise_id: int, request: Request, db: Session = Depends(get_db)):
    user = current_user(request, db)
    exercise = db.query(Exercise).options(joinedload(Exercise.lesson)).filter(Exercise.id == exercise_id).first()
    if not exercise:
        raise HTTPException(status_code=404, detail="Exercise not found")
    payload = await request.json()
    submitted_answer = str(payload.get("answer", "")).strip()
    score = float(payload.get("score", 0))
    result = str(payload.get("result", "submitted"))
    if exercise.exercise_type in {"multiple_choice", "short_answer"}:
        is_correct = submitted_answer.casefold() == exercise.answer.strip().casefold()
        score = 100 if is_correct else 0
        result = "passed" if is_correct else "failed"
    score = max(0, min(score, 100))
    if not user:
        return JSONResponse({"score": score, "result": result, "saved": False})
    attempt = ExerciseAttempt(
        user_id=user.id,
        exercise_id=exercise.id,
        submitted_answer=submitted_answer,
        score=score,
        result=result,
    )
    db.add(attempt)
    progress = db.query(LessonProgress).filter_by(user_id=user.id, lesson_id=exercise.lesson_id).first()
    if not progress:
        progress = LessonProgress(user_id=user.id, lesson_id=exercise.lesson_id)
        db.add(progress)
    progress.latest_score = score
    progress.is_completed = score >= 60
    progress.updated_at = datetime.utcnow()
    db.commit()
    return JSONResponse({"score": score, "result": result, "saved": True})


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    user = require_user(request, db)
    progress = (
        db.query(LessonProgress)
        .options(joinedload(LessonProgress.lesson))
        .filter(LessonProgress.user_id == user.id)
        .order_by(LessonProgress.updated_at.desc())
        .all()
    )
    attempts = (
        db.query(ExerciseAttempt)
        .options(joinedload(ExerciseAttempt.exercise))
        .filter(ExerciseAttempt.user_id == user.id)
        .order_by(ExerciseAttempt.created_at.desc())
        .limit(10)
        .all()
    )
    return render(request, "dashboard.html", {"progress": progress, "attempts": attempts}, db)


@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, db: Session = Depends(get_db)):
    require_admin(request, db)
    subjects = db.query(Subject).options(joinedload(Subject.sections)).order_by(Subject.position).all()
    lessons = db.query(Lesson).options(joinedload(Lesson.section).joinedload(Section.subject)).order_by(Lesson.id.desc()).all()
    exercises = db.query(Exercise).options(joinedload(Exercise.lesson)).order_by(Exercise.id.desc()).limit(20).all()
    return render(request, "admin/index.html", {"subjects": subjects, "lessons": lessons, "exercises": exercises}, db)


@app.post("/admin/subjects")
def admin_create_subject(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    position: int = Form(0),
    is_published: bool = Form(False),
    db: Session = Depends(get_db),
):
    require_admin(request, db)
    db.add(Subject(title=title.strip(), description=description.strip(), position=position, is_published=is_published))
    db.commit()
    return redirect("/admin")


@app.post("/admin/sections")
def admin_create_section(
    request: Request,
    subject_id: int = Form(...),
    title: str = Form(...),
    position: int = Form(0),
    db: Session = Depends(get_db),
):
    require_admin(request, db)
    db.add(Section(subject_id=subject_id, title=title.strip(), position=position))
    db.commit()
    return redirect("/admin")


@app.post("/admin/lessons")
def admin_create_lesson(
    request: Request,
    section_id: int = Form(...),
    title: str = Form(...),
    summary: str = Form(...),
    content_html: str = Form(...),
    widget_type: str = Form("none"),
    position: int = Form(0),
    is_published: bool = Form(False),
    db: Session = Depends(get_db),
):
    require_admin(request, db)
    db.add(
        Lesson(
            section_id=section_id,
            title=title.strip(),
            summary=summary.strip(),
            content_html=content_html.strip(),
            widget_type=widget_type.strip(),
            position=position,
            is_published=is_published,
        )
    )
    db.commit()
    return redirect("/admin")


@app.post("/admin/exercises")
def admin_create_exercise(
    request: Request,
    lesson_id: int = Form(...),
    title: str = Form(...),
    prompt: str = Form(...),
    exercise_type: str = Form(...),
    options_text: str = Form(""),
    answer: str = Form(""),
    starter_code: str = Form(""),
    test_code: str = Form(""),
    position: int = Form(0),
    db: Session = Depends(get_db),
):
    require_admin(request, db)
    db.add(
        Exercise(
            lesson_id=lesson_id,
            title=title.strip(),
            prompt=prompt.strip(),
            exercise_type=exercise_type,
            options_json=parse_options(options_text),
            answer=answer.strip(),
            starter_code=starter_code,
            test_code=test_code,
            position=position,
        )
    )
    db.commit()
    return redirect("/admin")


@app.post("/admin/subjects/{subject_id}/delete")
def admin_delete_subject(subject_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request, db)
    subject = db.get(Subject, subject_id)
    if subject:
        db.delete(subject)
        db.commit()
    return redirect("/admin")


@app.post("/admin/lessons/{lesson_id}/delete")
def admin_delete_lesson(lesson_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request, db)
    lesson = db.get(Lesson, lesson_id)
    if lesson:
        db.delete(lesson)
        db.commit()
    return redirect("/admin")


@app.post("/admin/exercises/{exercise_id}/delete")
def admin_delete_exercise(exercise_id: int, request: Request, db: Session = Depends(get_db)):
    require_admin(request, db)
    exercise = db.get(Exercise, exercise_id)
    if exercise:
        db.delete(exercise)
        db.commit()
    return redirect("/admin")


@app.get("/subjects/{subject_id}/practice", response_class=HTMLResponse)
def practice_mode(subject_id: int, request: Request, db: Session = Depends(get_db)):
    subject = (
        db.query(Subject)
        .options(joinedload(Subject.sections).joinedload(Section.lessons).joinedload(Lesson.exercises))
        .filter(Subject.id == subject_id, Subject.is_published.is_(True))
        .first()
    )
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    exercises = []
    for section in sorted(subject.sections, key=lambda s: s.position):
        if is_reference_section(section.title):
            continue
        for lesson in sorted(section.lessons, key=lambda l: l.position):
            if not lesson.is_published:
                continue
            for ex in sorted(lesson.exercises, key=lambda e: e.position):
                if ex.exercise_type != "multiple_choice":
                    continue
                exercises.append({
                    "id": ex.id,
                    "title": ex.title,
                    "prompt": ex.prompt,
                    "options": normalize_options(json.loads(ex.options_json) if ex.options_json else []),
                    "answer": ex.answer,
                    "lesson_title": lesson.title,
                    "section_title": section.title,
                })
    return render(
        request,
        "practice.html",
        {"subject": subject, "exercises_json": json.dumps(exercises, ensure_ascii=False)},
        db,
    )

