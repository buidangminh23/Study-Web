import json
import re
from html import unescape
from pathlib import Path

from sqlalchemy.orm import Session

from .models import Exercise, Lesson, Section, Subject


CONTENT_DIR = Path(__file__).resolve().parent / "content" / "subjects"
REMOVED_SUBJECT_TITLES = {"Python Programming", "Lập trình Python", "Boolean Algebra and Logisim"}
HIDDEN_SOURCE_ARCHIVE_SUBJECTS = {
    "Business Digitalisation",
    "Communicating with Data",
    "Contemporary Management Principles",
    "Data Management and Analytics",
    "Economics for Business Decision Making",
    "Marketing and the Consumer Experience",
}
HIDDEN_SECTION_TITLES_BY_SUBJECT = {
    "Introduction to Programming": {"Core Programming Concepts"},
}
SOURCE_ARCHIVE_SECTION_TITLE = "Original Source Files"
SOURCE_TEXT_RE = re.compile(
    r"<pre(?P<attrs>[^>]*)class=[\"'][^\"']*\bsource-text\b[^\"']*[\"'][^>]*>(?P<body>.*?)</pre>",
    re.IGNORECASE | re.DOTALL,
)
HTML_HEADING_RE = re.compile(r"<h[1-3][^>]*>(?P<body>.*?)</h[1-3]>", re.IGNORECASE | re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")
COURSE_CODE_RE = re.compile(r"^(?:INF|COS|MGT|MKT|MTH|MDA|ECO|BATE)\d{5}\b", re.IGNORECASE)
SOURCE_WEEK_PREFIX_RE = re.compile(r"^Week\s+\d+\s+(?:PPTX|Lecture\s+PDF|PDF|PPT|slides?|slide\s+deck)\s*:\s*", re.IGNORECASE)
SOURCE_FILE_WORD_RE = re.compile(r"\b(?:PPTX|PDF|slide\s+deck|lecture\s+pdf|slides?)\b", re.IGNORECASE)
TITLE_TEXT_FIXES = {
    "Liter acy": "Literacy",
    "Intr oduction": "Introduction",
    "Infog r a phics": "Infographics",
    "Jour nalism": "Journalism",
    "Histor y": "History",
    "Develop ment": "Development",
    "Manag ement": "Management",
    "Exper ience": "Experience",
    "Consum er": "Consumer",
    "Mar ket": "Market",
    "For ces": "Forces",
    "Supp ly": "Supply",
}
TITLE_WRAP_ENDINGS = (":", "&", "and", "of", "to", "with", "for", "the", "a", "an", "getting", "conditional", "indexed", "programmable")


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_title_text(value: str) -> str:
    text = unescape(value)
    text = HTML_TAG_RE.sub(" ", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"[\u2000-\u200b\u202f]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" :-|")
    text = text.replace(" - ", " – ")
    for old, new in TITLE_TEXT_FIXES.items():
        text = text.replace(old, new)
    return text


def clean_knowledge_title(value: str) -> str:
    title = clean_title_text(value)
    title = re.sub(r"(?<=[a-z])Lecture\b", " Lecture", title)
    title = re.sub(r"\b(?:Liter|Infog|Intr|Jour|Histor|Anal)\s+([a-z])", lambda match: match.group(0).replace(" ", ""), title)
    title = SOURCE_WEEK_PREFIX_RE.sub("", title)
    title = re.sub(r"^Week\s+\d+\s*[-:]\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^(?:INF|COS|MGT|MKT|MTH|MDA|ECO)\d{5}[-\s]*", "", title, flags=re.IGNORECASE)
    if re.search(r"\bLecture\s+\d", title, re.IGNORECASE):
        title = re.sub(r"^.*?\b(Lecture\s+\d)", r"\1", title, flags=re.IGNORECASE)
    title = re.sub(r"^Lecture\s+\d+(?:\.\d+)?\s*(?:[-–—]?\s*Part\s+\d+\s*)?[-–—]?\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^\d{4}\s+L\d+\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^L\d+\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^Part\s+\d+\s*[-–—]?\s*", "", title, flags=re.IGNORECASE)
    title = re.sub(r"^BATE\d+e\s+C\d+\s*", "Chapter ", title, flags=re.IGNORECASE)
    title = re.sub(r"\b(?:Short|Edit)\b$", "", title, flags=re.IGNORECASE).strip()
    title = re.sub(r"\s+", " ", title).strip(" :-|")
    if ":" in title:
        left, right = [part.strip() for part in title.split(":", 1)]
        if SOURCE_FILE_WORD_RE.search(left) or re.match(r"^Week\s+\d+\b", left, re.IGNORECASE):
            title = right
    return title[:160] if title else ""


def is_source_title_noise(line: str) -> bool:
    stripped = clean_title_text(line)
    if not stripped:
        return True
    if stripped.lower() in {"contents", "references", "slide", "source file"}:
        return True
    if re.fullmatch(r"\d{1,3}", stripped):
        return True
    if re.fullmatch(r"Slide\s+\d+", stripped, re.IGNORECASE):
        return True
    if re.match(r"^(?:Chapter\s+\d+|[0-9]+(?:st|nd|rd|th)\s+edition|Learning Objectives?)\b", stripped, re.IGNORECASE):
        return True
    if re.match(r"^\d+(?:\.\d+)?\s+(?:Identify|Discuss|Explain|Describe|Use|Analyse|Analyze|Define|List)\b", stripped, re.IGNORECASE):
        return True
    if re.match(r"^\d{1,2}/\d{1,2}/\d{2,4}$", stripped):
        return True
    if COURSE_CODE_RE.match(stripped) and "lecture" not in stripped.lower():
        return True
    if re.match(r"^(?:Dr|Professor|Presented by|Presenter)\b", stripped, re.IGNORECASE):
        return True
    if re.match(r"^(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}$", stripped, re.IGNORECASE):
        return True
    return False


def collect_source_title(lines: list[str], index: int) -> str:
    fragments = [clean_title_text(lines[index])]
    current = index + 1
    while current < len(lines) and len(fragments) < 4:
        candidate = clean_title_text(lines[current])
        if is_source_title_noise(candidate):
            break
        joined = clean_title_text(" ".join([*fragments, candidate]))
        previous = fragments[-1].lower()
        if len(joined) > 120:
            break
        if previous.endswith(TITLE_WRAP_ENDINGS) or candidate.startswith("&") or candidate[:1].islower():
            fragments.append(candidate)
            current += 1
            continue
        break
    return clean_knowledge_title(" ".join(fragments))


def infer_source_text_title(content_html: str) -> str:
    match = SOURCE_TEXT_RE.search(content_html)
    if not match:
        return ""
    raw_text = unescape(match.group("body")).replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    lines = [clean_title_text(line) for line in raw_text.splitlines()]
    lines = [line for line in lines if line]
    for index, line in enumerate(lines[:80]):
        if is_source_title_noise(line):
            continue
        if re.fullmatch(r"Week\s+\d+", line, re.IGNORECASE) and index + 1 < len(lines):
            for next_index in range(index + 1, min(index + 8, len(lines))):
                if not is_source_title_noise(lines[next_index]):
                    return collect_source_title(lines, next_index)
        if line.lower().startswith("week ") and line.endswith(":") and index + 1 < len(lines):
            return clean_knowledge_title(f"{line} {lines[index + 1]}")
        title = collect_source_title(lines, index)
        if title:
            return title
    return ""


def infer_knowledge_title(lesson_data: dict) -> str:
    explicit = clean_knowledge_title(lesson_data.get("knowledge_title", ""))
    if explicit:
        return explicit
    content_html = lesson_data.get("content_html", "")
    heading_match = HTML_HEADING_RE.search(content_html)
    if heading_match:
        title = clean_knowledge_title(heading_match.group("body"))
        if title:
            return title
    source_title = infer_source_text_title(content_html)
    if source_title:
        return source_title
    return clean_knowledge_title(lesson_data.get("title", "")) or lesson_data.get("title", "")


def normalize_lesson_title(lesson_data: dict) -> dict:
    normalized = dict(lesson_data)
    normalized["title"] = infer_knowledge_title(normalized)
    return normalized


def normalize_section_lessons(section_data: dict) -> dict:
    normalized = dict(section_data)
    normalized["lessons"] = [normalize_lesson_title(lesson) for lesson in section_data.get("lessons", [])]
    return normalized


def should_load_section_dir(subject_title: str, section_dir: Path) -> bool:
    if section_dir.name in HIDDEN_SECTION_TITLES_BY_SUBJECT.get(subject_title, set()):
        return False
    return not (
        section_dir.name == SOURCE_ARCHIVE_SECTION_TITLE
        and subject_title in HIDDEN_SOURCE_ARCHIVE_SUBJECTS
    )


def load_subject_folder(subject_dir: Path) -> dict:
    subject_meta = read_json(subject_dir / "subject.json")
    subject_title = subject_meta.get("title", subject_dir.name)
    subject_data = {
        "title": subject_title,
        "legacy_titles": subject_meta.get("legacy_titles", []),
        "description": subject_meta["description"],
        "is_published": subject_meta.get("is_published", True),
        "position": subject_meta.get("position", 0),
        "sections": [],
    }
    if "sections" in subject_meta:
        subject_data["sections"] = [normalize_section_lessons(section) for section in subject_meta["sections"]]
        return subject_data
    section_dirs = sorted(
        [item for item in subject_dir.iterdir() if item.is_dir() and should_load_section_dir(subject_title, item)],
        key=lambda item: item.name,
    )
    for section_position, section_dir in enumerate(section_dirs, start=1):
        section_file = section_dir / "section.json"
        section_meta = read_json(section_file) if section_file.exists() else {}
        section_data = {
            "title": section_meta.get("title", section_dir.name),
            "position": section_meta.get("position", section_position),
            "lessons": [],
        }
        lesson_files = sorted([item for item in section_dir.glob("*.json") if item.name != "section.json"], key=lambda item: item.name)
        for lesson_file in lesson_files:
            section_data["lessons"].append(normalize_lesson_title(read_json(lesson_file)))
        subject_data["sections"].append(section_data)
    return subject_data


def load_subject_files() -> list[dict]:
    subjects = []
    for subject_dir in sorted([item for item in CONTENT_DIR.iterdir() if item.is_dir()], key=lambda item: item.name):
        subject_file = subject_dir / "subject.json"
        if subject_file.exists():
            subjects.append(load_subject_folder(subject_dir))
    return subjects


def normalize_options(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        try:
            return normalize_options(json.loads(text))
        except json.JSONDecodeError:
            return [item.strip() for item in text.splitlines() if item.strip()]
    return [str(value)]


def normalize_exercise_data(exercise_data: dict, exercise_position: int) -> dict:
    prompt = exercise_data.get("prompt") or exercise_data.get("question") or ""
    title = exercise_data.get("title") or prompt[:80] or f"Exercise {exercise_position}"
    exercise_type = exercise_data.get("exercise_type") or exercise_data.get("type") or "multiple_choice"
    return {
        "title": title,
        "prompt": prompt,
        "exercise_type": exercise_type,
        "options": exercise_data.get("options", exercise_data.get("options_json", [])),
        "answer": exercise_data.get("answer", ""),
        "starter_code": exercise_data.get("starter_code", ""),
        "test_code": exercise_data.get("test_code", ""),
        "position": exercise_data.get("position", exercise_position),
    }


def find_section(db: Session, subject_id: int, title: str, position: int) -> Section | None:
    section = db.query(Section).filter(Section.subject_id == subject_id, Section.title == title).first()
    if section:
        return section
    return db.query(Section).filter(Section.subject_id == subject_id, Section.position == position).first()


def find_lesson(db: Session, section_id: int, title: str, position: int) -> Lesson | None:
    lesson = db.query(Lesson).filter(Lesson.section_id == section_id, Lesson.position == position).first()
    if lesson:
        return lesson
    return db.query(Lesson).filter(Lesson.section_id == section_id, Lesson.title == title).first()


def seed_data(db: Session) -> None:
    loaded_titles = set()
    for subject_data in load_subject_files():
        subject_titles = [subject_data["title"], *subject_data.get("legacy_titles", [])]
        loaded_titles.update(subject_titles)
        subject = db.query(Subject).filter(Subject.title.in_(subject_titles)).first()
        if not subject:
            subject = Subject()
            db.add(subject)

        subject.title = subject_data["title"]
        subject.description = subject_data["description"]
        subject.is_published = subject_data.get("is_published", True)
        subject.position = subject_data.get("position", 0)
        db.flush()

        active_section_ids = set()
        for section_position, section_data in enumerate(subject_data.get("sections", []), start=1):
            section_sort = section_data.get("position", section_position)
            section = find_section(db, subject.id, section_data["title"], section_sort)
            if not section:
                section = Section(subject_id=subject.id)
                db.add(section)

            section.title = section_data["title"]
            section.position = section_sort
            db.flush()
            active_section_ids.add(section.id)

            active_lesson_ids = set()
            for lesson_position, lesson_data in enumerate(section_data.get("lessons", []), start=1):
                lesson_sort = lesson_data.get("position", lesson_position)
                lesson = find_lesson(db, section.id, lesson_data["title"], lesson_sort)
                if not lesson:
                    lesson = Lesson(section_id=section.id)
                    db.add(lesson)

                lesson.title = lesson_data["title"]
                lesson.summary = lesson_data["summary"]
                lesson.content_html = lesson_data["content_html"]
                lesson.widget_type = "none"
                lesson.position = lesson_sort
                lesson.is_published = lesson_data.get("is_published", True)
                db.flush()
                active_lesson_ids.add(lesson.id)

                for exercise_position, raw_exercise_data in enumerate(lesson_data.get("exercises", []), start=1):
                    exercise_data = normalize_exercise_data(raw_exercise_data, exercise_position)
                    exercise_sort = exercise_data.get("position", exercise_position)
                    exercise = (
                        db.query(Exercise)
                        .filter(Exercise.lesson_id == lesson.id, Exercise.position == exercise_sort)
                        .first()
                    )
                    if not exercise:
                        exercise = Exercise(lesson_id=lesson.id)
                        db.add(exercise)

                    exercise.title = exercise_data["title"]
                    exercise.prompt = exercise_data["prompt"]
                    exercise.exercise_type = exercise_data["exercise_type"]
                    exercise.options_json = json.dumps(normalize_options(exercise_data.get("options", [])), ensure_ascii=False)
                    exercise.answer = exercise_data.get("answer", "")
                    exercise.starter_code = exercise_data.get("starter_code", "")
                    exercise.test_code = exercise_data.get("test_code", "")
                    exercise.position = exercise_sort
            for stale_lesson in db.query(Lesson).filter(Lesson.section_id == section.id).all():
                if stale_lesson.id not in active_lesson_ids:
                    db.delete(stale_lesson)

        for stale_section in db.query(Section).filter(Section.subject_id == subject.id).all():
            if stale_section.id not in active_section_ids:
                db.delete(stale_section)

    for title in REMOVED_SUBJECT_TITLES - loaded_titles:
        subject = db.query(Subject).filter(Subject.title == title).first()
        if subject:
            subject.is_published = False
            for section in subject.sections:
                for lesson in section.lessons:
                    lesson.widget_type = "none"

    db.commit()
