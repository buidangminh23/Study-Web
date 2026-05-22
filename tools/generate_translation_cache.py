"""
Run this script locally to pre-generate Vietnamese translation cache for all lessons.
Usage: python tools/generate_translation_cache.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DATABASE_URL", "sqlite:///./study_web.db")

from app.database import SessionLocal, Base, engine
from app.models import Lesson, Section, Subject
from app.translation import build_lesson_translation
from app.main import render_summary_text, render_content_html

Base.metadata.create_all(bind=engine)

db = SessionLocal()

lessons = (
    db.query(Lesson)
    .join(Section)
    .join(Subject)
    .filter(Lesson.is_published.is_(True), Subject.is_published.is_(True))
    .all()
)

print(f"Found {len(lessons)} published lessons")

success = 0
failed = 0

for lesson in lessons:
    try:
        payload = build_lesson_translation(
            lesson.id,
            lesson.title,
            render_summary_text(lesson),
            render_content_html(lesson.content_html),
            "vi",
        )
        print(f"  [OK] {lesson.id}: {lesson.title[:60]}")
        success += 1
    except Exception as e:
        print(f"  [FAIL] {lesson.id}: {lesson.title[:60]} — {e}")
        failed += 1

db.close()
print(f"\nDone: {success} success, {failed} failed")
print("Now commit app/static/translation-cache/ and push to git.")
