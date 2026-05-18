import json
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import Subject
from app.seed import CONTENT_DIR
from app.seed import load_subject_files


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Study Web" in response.text
    assert "subject-card" in response.text


def test_subjects_seed_loads(client):
    response = client.get("/subjects")
    assert response.status_code == 200
    assert "Python Programming" in response.text
    assert "Boolean Algebra and Logisim" in response.text


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"


def test_lesson_is_public(client):
    response = client.get("/lessons/1", follow_redirects=False)
    assert response.status_code == 200
    assert "lesson-content" in response.text
    assert "Practice</h2>" not in response.text
    assert "Submit answer" not in response.text
    assert "pyodide.js" not in response.text


def test_practice_mode_remains_available(client):
    db = SessionLocal()
    try:
        subject = db.query(Subject).filter(Subject.title == "Python Programming").one()
    finally:
        db.close()
    response = client.get(f"/subjects/{subject.id}/practice", follow_redirects=False)
    assert response.status_code == 200
    assert "Practice Mode" in response.text
    assert "EXERCISES" in response.text
    match = re.search(r"const EXERCISES = (.*?);\s*const SUBMIT_URL", response.text, re.S)
    assert match
    exercises = json.loads(match.group(1))
    assert exercises
    assert isinstance(exercises[0]["options"], list)
    assert exercises[0]["options"]


def test_subject_detail_shows_course_overview(client):
    db = SessionLocal()
    try:
        subject = db.query(Subject).filter(Subject.title == "Python Programming").one()
    finally:
        db.close()
    response = client.get(f"/subjects/{subject.id}", follow_redirects=False)
    assert response.status_code == 200
    assert "Course" in response.text
    assert "Variables and Data Types" in response.text
    assert "Log in only if you want to save progress" not in response.text


def test_subject_content_loads_from_folder():
    subjects = load_subject_files()
    subjects_by_title = {subject["title"]: subject for subject in subjects}
    assert "Python Programming" in subjects_by_title
    assert "Boolean Algebra and Logisim" in subjects_by_title
    assert subjects_by_title["Python Programming"]["sections"][0]["lessons"]
    assert subjects_by_title["Boolean Algebra and Logisim"]["sections"][0]["lessons"]
    assert (CONTENT_DIR / "Lập trình Python").is_dir()
    assert (CONTENT_DIR / "Lập trình Python" / "Python cơ bản" / "01-bien-va-kieu-du-lieu.json").is_file()
    assert (CONTENT_DIR / "Boolean Algebra and Logisim").is_dir()
    assert (
        CONTENT_DIR
        / "Boolean Algebra and Logisim"
        / "Digital Logic Foundations"
        / "01-gates-and-boolean-algebra.json"
    ).is_file()
