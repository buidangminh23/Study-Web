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


def seed_data(db: Session) -> None:
    for subject_data in load_subject_files():
        existing_subject = db.query(Subject).filter(Subject.title == subject_data["title"]).first()
        if existing_subject:
            continue

        subject = Subject(
            title=subject_data["title"],
            description=subject_data["description"],
            is_published=subject_data.get("is_published", True),
            position=subject_data.get("position", 0),
        )
        db.add(subject)
        db.flush()

        for section_position, section_data in enumerate(subject_data.get("sections", []), start=1):
            section = Section(
                subject_id=subject.id,
                title=section_data["title"],
                position=section_data.get("position", section_position),
            )
            db.add(section)
            db.flush()

            for lesson_position, lesson_data in enumerate(section_data.get("lessons", []), start=1):
                lesson = Lesson(
                    section_id=section.id,
                    title=lesson_data["title"],
                    summary=lesson_data["summary"],
                    content_html=lesson_data["content_html"],
                    widget_type=lesson_data.get("widget_type", "variables"),
                    position=lesson_data.get("position", lesson_position),
                    is_published=lesson_data.get("is_published", True),
                )
                db.add(lesson)
                db.flush()

                for exercise_position, exercise_data in enumerate(lesson_data.get("exercises", []), start=1):
                    db.add(
                        Exercise(
                            lesson_id=lesson.id,
                            title=exercise_data["title"],
                            prompt=exercise_data["prompt"],
                            exercise_type=exercise_data["exercise_type"],
                            options_json=json.dumps(exercise_data.get("options", []), ensure_ascii=False),
                            answer=exercise_data.get("answer", ""),
                            starter_code=exercise_data.get("starter_code", ""),
                            test_code=exercise_data.get("test_code", ""),
                            position=exercise_data.get("position", exercise_position),
                        )
                    )

    db.commit()
