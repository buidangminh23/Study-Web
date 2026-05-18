import json
from pathlib import Path

from sqlalchemy.orm import Session

from .models import Exercise, Lesson, Section, Subject


CONTENT_DIR = Path(__file__).resolve().parent / "content" / "subjects"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_subject_folder(subject_dir: Path) -> dict:
    subject_meta = read_json(subject_dir / "subject.json")
    subject_data = {
        "title": subject_meta.get("title", subject_dir.name),
        "legacy_titles": subject_meta.get("legacy_titles", []),
        "description": subject_meta["description"],
        "is_published": subject_meta.get("is_published", True),
        "position": subject_meta.get("position", 0),
        "sections": [],
    }
    if "sections" in subject_meta:
        subject_data["sections"] = subject_meta["sections"]
        return subject_data
    for section_dir in sorted([item for item in subject_dir.iterdir() if item.is_dir()], key=lambda item: item.name):
        section_file = section_dir / "section.json"
        section_meta = read_json(section_file) if section_file.exists() else {}
        section_data = {
            "title": section_meta.get("title", section_dir.name),
            "position": section_meta.get("position", 0),
            "lessons": [],
        }
        lesson_files = sorted([item for item in section_dir.glob("*.json") if item.name != "section.json"], key=lambda item: item.name)
        for lesson_file in lesson_files:
            section_data["lessons"].append(read_json(lesson_file))
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


def seed_data(db: Session) -> None:
    for subject_data in load_subject_files():
        subject_titles = [subject_data["title"], *subject_data.get("legacy_titles", [])]
        subject = db.query(Subject).filter(Subject.title.in_(subject_titles)).first()
        if not subject:
            subject = Subject()
            db.add(subject)

        subject.title = subject_data["title"]
        subject.description = subject_data["description"]
        subject.is_published = subject_data.get("is_published", True)
        subject.position = subject_data.get("position", 0)
        db.flush()

        for section_position, section_data in enumerate(subject_data.get("sections", []), start=1):
            section_sort = section_data.get("position", section_position)
            section = (
                db.query(Section)
                .filter(Section.subject_id == subject.id, Section.position == section_sort)
                .first()
            )
            if not section:
                section = Section(subject_id=subject.id)
                db.add(section)

            section.title = section_data["title"]
            section.position = section_sort
            db.flush()

            for lesson_position, lesson_data in enumerate(section_data.get("lessons", []), start=1):
                lesson_sort = lesson_data.get("position", lesson_position)
                lesson = (
                    db.query(Lesson)
                    .filter(Lesson.section_id == section.id, Lesson.position == lesson_sort)
                    .first()
                )
                if not lesson:
                    lesson = Lesson(section_id=section.id)
                    db.add(lesson)

                lesson.title = lesson_data["title"]
                lesson.summary = lesson_data["summary"]
                lesson.content_html = lesson_data["content_html"]
                lesson.widget_type = lesson_data.get("widget_type") or "variables"
                lesson.position = lesson_sort
                lesson.is_published = lesson_data.get("is_published", True)
                db.flush()

                for exercise_position, exercise_data in enumerate(lesson_data.get("exercises", []), start=1):
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
                    exercise.options_json = json.dumps(
                        normalize_options(exercise_data.get("options", exercise_data.get("options_json", []))),
                        ensure_ascii=False,
                    )
                    exercise.answer = exercise_data.get("answer", "")
                    exercise.starter_code = exercise_data.get("starter_code", "")
                    exercise.test_code = exercise_data.get("test_code", "")
                    exercise.position = exercise_sort

    db.commit()
