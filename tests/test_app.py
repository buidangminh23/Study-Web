import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed import load_subject_files


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Study Web" in response.text
    assert "subject-folder" in response.text


def test_subjects_seed_loads(client):
    response = client.get("/subjects")
    assert response.status_code == 200
    assert "Lập trình Python" in response.text


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"


def test_lesson_is_public(client):
    response = client.get("/lessons/1", follow_redirects=False)
    assert response.status_code == 200
    assert "Đăng nhập chỉ cần khi muốn lưu tiến độ" in response.text


def test_subject_content_loads_from_folder():
    subjects = load_subject_files()
    assert subjects[0]["title"] == "Lập trình Python"
    assert subjects[0]["sections"][0]["lessons"]
