import json
from pathlib import Path

from sqlalchemy.orm import Session

from .models import Exercise, Lesson, Section, Subject


CONTENT_DIR = Path(__file__).resolve().parent / "content" / "subjects"


def load_subject_files() -> list[dict]:
    subjects = []
    for subject_file in sorted(CONTENT_DIR.glob("*/subject.json")):
        subjects.append(json.loads(subject_file.read_text(encoding="utf-8")))
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
