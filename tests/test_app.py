import json
import re

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.main import render_content_html
from app.database import SessionLocal
from app.models import Lesson
from app.models import Section
from app.models import Subject
from app.seed import CONTENT_DIR
from app.seed import SOURCE_ARCHIVE_SECTION_TITLE
from app.seed import infer_source_text_title
from app.seed import load_subject_files
from app.seed import normalize_exercise_data
from app import translation


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
    assert "Python Programming" not in response.text
    assert "Introduction to Programming" in response.text
    assert "Boolean Algebra and Logisim" not in response.text
    assert "Computer System" in response.text


def test_dashboard_requires_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/auth/login"


def test_lesson_is_public(client):
    db = SessionLocal()
    try:
        lesson = (
            db.query(Lesson)
            .join(Lesson.section)
            .join(Section.subject)
            .filter(Subject.is_published.is_(True), Lesson.is_published.is_(True))
            .order_by(Subject.position, Section.position, Lesson.position)
            .first()
        )
        lesson_id = lesson.id
    finally:
        db.close()
    response = client.get(f"/lessons/{lesson_id}", follow_redirects=False)
    assert response.status_code == 200
    assert "lesson-content" in response.text
    assert "Practice</h2>" not in response.text
    assert "Submit answer" not in response.text
    assert "pyodide.js" not in response.text
    assert "widget-panel" not in response.text
    assert "lesson-widgets.js" not in response.text


def test_legacy_unpublished_lesson_redirects_to_published_replacement(client):
    db = SessionLocal()
    try:
        current_lesson = (
            db.query(Lesson)
            .join(Lesson.section)
            .join(Section.subject)
            .filter(Subject.is_published.is_(True), Lesson.is_published.is_(True))
            .order_by(Subject.position, Section.position, Lesson.position)
            .first()
        )
        legacy_subject = Subject(
            title="Legacy Hidden Course",
            description="Hidden course",
            is_published=False,
            position=999,
        )
        legacy_section = Section(title="Legacy Hidden Section", position=1)
        legacy_lesson = Lesson(
            title=current_lesson.title,
            summary="Legacy lesson",
            content_html="<p>Legacy lesson</p>",
            widget_type="none",
            position=1,
            is_published=True,
        )
        legacy_subject.sections.append(legacy_section)
        legacy_section.lessons.append(legacy_lesson)
        db.add(legacy_subject)
        db.commit()
        legacy_subject_id = legacy_subject.id
        legacy_lesson_id = legacy_lesson.id
        current_lesson_id = current_lesson.id
    finally:
        db.close()
    try:
        response = client.get(f"/lessons/{legacy_lesson_id}", follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"] == f"/lessons/{current_lesson_id}"
    finally:
        db = SessionLocal()
        try:
            created_subject = db.get(Subject, legacy_subject_id)
            if created_subject:
                db.delete(created_subject)
                db.commit()
        finally:
            db.close()


def test_missing_lesson_redirects_to_courses(client):
    response = client.get("/lessons/999999", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/subjects"


def test_reload_token_endpoint(client):
    response = client.get("/api/reload-token")
    assert response.status_code == 200
    assert response.json()["token"]


def test_source_text_renders_binary_tables():
    html = render_content_html(
        '<pre class="source-text">BINARY NUMBERS\n\n8-bit example 128 64 32 16 8 4 2 1\nBit7 Bit6 Bit5 Bit4 Bit3 Bit2 Bit1 Bit0\n1 0 1 0 1 0 1 1\n\nBinary Counting\nDecimal Binary Decimal Binary\n0 0000 11 1011\n8 31\n9 32\n10 65\n\nHEX - BINARY (4 BITS TO A HEX DIGIT)</pre>'
    )
    assert "source-bit-table" in html
    assert "<td>Value</td><td>1</td><td>0</td><td>1</td><td>0</td><td>1</td><td>0</td><td>1</td><td>1</td>" in html
    assert "source-binary-table" in html
    assert "<td>8</td><td>1000</td><td>32</td><td>100000</td>" in html
    assert "source-compact-table" in html
    assert "<td>F</td><td>1111</td>" in html


def test_source_text_renders_visual_diagrams():
    html = render_content_html(
        '<pre class="source-text">Business overview\n\nVa l u e C h a i n s\n\nFigure 6.1\nDesigning a customer-driven marketing strategy - the four steps:\nSegmentation > Targeting > Differentiation > Positioning\n\nExhibit 2.4 The Competitive Environment\nCompetitors\nNew Entrants\nSuppliers\nCustomers</pre>'
    )
    assert "source-value-chain" in html
    assert "Firm infrastructure" in html
    assert "Marketing and sales" in html
    assert "source-flow-visual" in html
    assert "Segmentation" in html
    assert "Positioning" in html
    assert "source-network-visual" in html
    assert "New entrants" in html


def test_source_text_renders_math_blocks():
    html = render_content_html(
        '<pre class="source-text">Contents\n1.1 Definitions . . . . . . . . . . . . . . . . . 5\nExample 1.1\n   1 \n1 2 −5  5  C = 4.3 −3.15 2.7 17.5\nA =  0 3 2  B = −6 0 3 −2.58 −12.75\n−1 5 0 7\nA general matrix with m rows and n columns can be denoted by\nA=[aik]m×n = a31 a32 a33 ··· a3n</pre>'
    )
    assert "source-math-example" in html
    assert "source-math-block" in html
    assert '<p>1.1 Definitions . . . . . . . . . . . . . . . . . 5</p>' in html
    assert 'source-math-block">1.1 Definitions' not in html
    assert "⎡" in html
    assert "A=[aik]m×n" in html


def test_source_text_removes_admin_intro_content():
    html = render_content_html(
        '<pre class="source-text">Introduction\n\nINF10024 Business Digitalisation\nMark Dale and Rohan Bennett\nFebruary 2023\n\nWhat are the objectives for today?\n1. Provide a brief review of the unit\n2. Revisit the core concepts\n\nVa l u e C h a i n s\nBusiness Processes Services and service delivery Big data\nGo to:\nCanvas &gt; Modules\nLecture Recordings\n\nWhat are information systems?\nData, processes, people, technology and management work together.</pre>'
    )
    assert "INF10024 Business Digitalisation" not in html
    assert "Mark Dale and Rohan Bennett" not in html
    assert "February 2023" not in html
    assert "Provide a brief review" not in html
    assert "Business Processes Services" not in html
    assert "Canvas" not in html
    assert "Lecture Recordings" not in html
    assert "source-value-chain" in html
    assert "What are information systems?" in html
    assert "Data, processes, people" in html


def test_source_text_combines_wrapped_slide_lines():
    html = render_content_html(
        '<pre class="source-text">Week 1:\nWhat is data?\n\nMDA10012: Communicating with Data\n\nDr Kyle Moore\n\nLecture Overview\n\nWhat is data?\n\nWhy study data? How to study\ndata?\n\nThinking about data and concepts\n\nWhat is data? 2\n\nWhat is data?\n\nAt its most basic level, data are\nmeasurements or observations\ncollected as information for\nreference or analysis.\n• Wisdom - well informed decisions and effective action based\non understanding of the underlying knowledge.\n1) Data is everywhere\n2) Data is valuable\n3) Data literacy skills are becoming\nincreasingly essential to modern work\nData has been flagged as useful.</pre>'
    )
    assert "MDA10012" not in html
    assert "Dr Kyle Moore" not in html
    assert "What is data? 2" not in html
    assert "source-overview-list" in html
    assert "Why study data? How to study data?" in html
    assert "measurements or observations collected as information for reference or analysis." in html
    assert "well informed decisions and effective action based on understanding of the underlying knowledge." in html
    assert "Data literacy skills are becoming increasingly essential to modern work" in html
    assert "Data has been flagged as useful." in html


def test_source_titles_use_knowledge_headings():
    assert infer_source_text_title('<pre class="source-text">Week 5:\nData as a\nConcept\n\nMDA10012: Communicating with Data</pre>') == "Data as a Concept"
    assert infer_source_text_title('<pre class="source-text">COS10004 Computer Systems\nLecture 7.1 ARM Assembly Programming: Getting\nReady\n\nDr Chris McCarthy</pre>') == "ARM Assembly Programming: Getting Ready"
    assert infer_source_text_title('<pre class="source-text">Conditional\nBranching\nLecture 8.3\n\nConditionals in programming languages</pre>') == "Conditional Branching"
    assert infer_source_text_title('<pre class="source-text">2/2/2023\nECO10005-Economics for Business Decision Making\nMarket Forces (Demand & Supply)</pre>') == "Market Forces (Demand & Supply)"


def test_square_roots_render_as_radicals():
    html = render_content_html('<div class="formula-box">|a| = √(4+9+25) = <strong>√38</strong></div>')
    assert 'class="math-radical"' in html
    assert '<span>4+9+25</span>' in html
    assert '<span>38</span>' in html
    assert "√38" not in html


def test_square_roots_inside_code_stay_literal():
    html = render_content_html("<pre><code>SELECT √38</code></pre>")
    assert "SELECT √38" in html


def test_database_definition_code_blocks_render_as_tables():
    html = render_content_html(
        "<pre><code>Table  = a collection of related records\nRow    = one record\nColumn = one attribute/field</code></pre>"
    )
    assert "lesson-structured-block" in html
    assert "lesson-definition-table" in html
    assert "<pre" not in html
    assert "<td>Table</td><td>a collection of related records</td>" in html


def test_database_ascii_tables_render_as_html_tables():
    html = render_content_html(
        "<pre><code>Rating table (Primary Key = ratingCode):\nratingCode | ratingName | description\n--------------------------------------\nG | General | Suitable for all ages\nPG | Parental Guidance | Recommended for 15+</code></pre>"
    )
    assert "lesson-structured-block" in html
    assert "Rating table (Primary Key = ratingCode)" in html
    assert "<th>ratingCode</th>" in html
    assert "<td>PG</td><td>Parental Guidance</td><td>Recommended for 15+</td>" in html
    assert "<pre" not in html


def test_database_schema_and_normal_form_blocks_render_as_tables():
    schema_html = render_content_html(
        "<pre><code>Actor table:    actorNo | firstName | surname | gender\nMovie table:    movieNo | title | relyear | runtime | ratingCode\nCasting table:  castId (PK) | actorNo (FK) | movieNo (FK)\n\nEach row in Casting represents ONE actor in ONE movie:\ncastId | actorNo | movieNo\n1      | 51329   | 82693</code></pre>"
    )
    assert schema_html.count("lesson-structured-block") == 1
    assert "lesson-schema-table" in schema_html
    assert "<th>castId</th><th>actorNo</th><th>movieNo</th>" in schema_html
    assert "<pre" not in schema_html
    normal_form_html = render_content_html(
        "<pre><code>1NF: Atomic values — no repeating groups\n2NF: No partial dependencies\n3NF: No transitive dependencies</code></pre>"
    )
    assert "lesson-definition-table" in normal_form_html
    assert "<td>1NF</td><td>Atomic values — no repeating groups</td>" in normal_form_html
    assert "<pre" not in normal_form_html


def test_database_relationship_map_renders_as_diagram_block():
    html = render_content_html(
        "<pre><code>Rating (PK: ratingCode)\n    |\n    | 1:N\n    |\nMovie (PK: movieNo)\n    |\n    | N:1\n    |\nActor (PK: actorNo)</code></pre>"
    )
    assert "lesson-diagram-block" in html
    assert "Rating (PK: ratingCode)" in html
    assert "<pre" not in html


def test_sql_code_blocks_remain_code_blocks():
    html = render_content_html("<pre><code>SELECT title FROM Movie WHERE relyear = 2015;</code></pre>")
    assert "<pre><code>SELECT title FROM Movie WHERE relyear = 2015;</code></pre>" in html
    assert "lesson-structured-block" not in html


def test_sql_result_tables_split_from_query_code():
    html = render_content_html(
        "<pre><code>-- Get movie title WITH its rating name:\n"
        "SELECT m.title, r.ratingName\n"
        "FROM   Movie m\n"
        "INNER JOIN Rating r ON m.ratingCode = r.ratingCode;\n\n"
        "-- Result:\n"
        "title                     | ratingName\n"
        "-----------------------------------------\n"
        "The Hunger Games          | Parental Guidance\n"
        "Silver Linings Playbook   | Mature Accompanied (15+)</code></pre>"
    )
    assert html.count("<pre><code>") == 1
    assert "lesson-structured-block" in html
    assert "<h3>Result</h3>" in html
    assert "<th>title</th><th>ratingName</th>" in html
    assert "<td>The Hunger Games</td><td>Parental Guidance</td>" in html
    assert "-- Result:" not in html


def test_sql_reference_lists_render_as_tables():
    operators_html = render_content_html(
        "<pre><code>-- Exact match:\n"
        "SELECT title FROM Movie WHERE relyear = 2015;\n\n"
        "-- Comparison operators:\n"
        "=   equal\n"
        "<>  not equal\n"
        ">   greater than\n"
        "<   less than\n"
        ">=  greater than or equal\n"
        "<=  less than or equal</code></pre>"
    )
    assert "lesson-structured-block" in operators_html
    assert "<h3>Comparison operators</h3>" in operators_html
    assert "<td>&gt;=</td><td>greater than or equal</td>" in operators_html
    assert "<td>&lt;</td><td>less than</td>" in operators_html
    order_html = render_content_html(
        "<pre><code>1. FROM    - identify tables\n"
        "2. JOIN    - combine tables\n"
        "3. WHERE   - filter individual rows\n"
        "4. GROUP BY - group rows</code></pre>"
    )
    assert "lesson-definition-table" in order_html
    assert "<td>GROUP BY</td><td>group rows</td>" in order_html
    assert "<pre" not in order_html


def test_practice_mode_remains_available(client):
    db = SessionLocal()
    try:
        subject = db.query(Subject).filter(Subject.title == "Introduction to Programming").one()
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


def test_language_toggle_and_vietnamese_lesson_content(client):
    db = SessionLocal()
    try:
        lesson = (
            db.query(Lesson)
            .join(Section)
            .join(Subject)
            .filter(
                Subject.title == "Introduction to Programming",
                Section.title == "Programming Fundamentals",
                Lesson.title == "Variables and Data Types",
            )
            .one()
        )
        lesson_id = lesson.id
    finally:
        db.close()
    response = client.get(f"/lessons/{lesson_id}")
    assert response.status_code == 200
    assert 'data-language-choice="en"' in response.text
    assert 'data-language-choice="vi"' in response.text
    assert f'data-lesson-id="{lesson_id}"' in response.text
    assert 'data-title-vi="Biến và Kiểu Dữ liệu"' in response.text
    assert 'data-lang="en"' in response.text
    assert 'data-lang="vi"' in response.text
    assert "Toán tử số học" in response.text
    assert "Phạm vi biến" in response.text
    assert "/static/js/language-toggle.js" in response.text


def test_generated_translation_preserves_code_and_caches(monkeypatch, tmp_path):
    monkeypatch.setattr(translation, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(translation, "translate_texts", lambda texts, target_language: [f"{target_language.upper()}:{text}" for text in texts])
    payload = translation.build_lesson_translation(
        999,
        "Database Table",
        "Primary key summary",
        "<h2>Hello World</h2><p>Database table and primary key.</p><pre><code>SELECT * FROM Movie;</code></pre>",
    )
    cached = translation.build_lesson_translation(
        999,
        "Database Table",
        "Primary key summary",
        "<h2>Hello World</h2><p>Database table and primary key.</p><pre><code>SELECT * FROM Movie;</code></pre>",
        "vi",
    )
    assert payload["title"] == "VI:Database Table"
    assert "VI:Hello World" in payload["content_html"]
    assert "<code>SELECT * FROM Movie;</code>" in payload["content_html"]
    assert cached == payload


def test_generated_english_translation_only_changes_vietnamese_text(monkeypatch, tmp_path):
    monkeypatch.setattr(translation, "CACHE_DIR", tmp_path)
    monkeypatch.setattr(translation, "translate_texts", lambda texts, target_language: [f"{target_language.upper()}:{text}" for text in texts])
    payload = translation.build_lesson_translation(
        1000,
        "Database là gì?",
        "Cấu trúc tables và rows",
        "<h2>Database là gì?</h2><p>Tập hợp data theo tables.</p><p>Primary Key stays English.</p><pre><code>SELECT * FROM Movie;</code></pre>",
        "en",
    )
    assert payload["language"] == "en"
    assert payload["title"] == "EN:Database là gì?"
    assert "EN:Database là gì?" in payload["content_html"]
    assert "EN:Tập hợp data theo tables." in payload["content_html"]
    assert "Primary Key stays English." in payload["content_html"]
    assert "<code>SELECT * FROM Movie;</code>" in payload["content_html"]


def test_mixed_vietnamese_translation_changes_english_segments_only():
    payload = translation.translate_texts(
        [
            "Database là gì?",
            "Thuật ngữ Column (Attribute/Field)",
            "Cells chứa single values (atomic)",
            "Đại diện cho một entity duy nhất",
            "Column names là unique",
            "Lưu một loại thông tin cụ thể",
        ],
        "vi",
    )
    assert payload[0] == "Cơ sở dữ liệu là gì?"
    assert payload[1] == "Thuật ngữ Cột (thuộc tính/trường)"
    assert payload[2] == "Ô chứa giá trị đơn (nguyên tử)"
    assert payload[3] == "Đại diện cho một thực thể duy nhất"
    assert payload[4] == "Tên cột là duy nhất"
    assert payload[5] == "Lưu một loại thông tin cụ thể"


def test_subject_detail_shows_course_overview(client):
    db = SessionLocal()
    try:
        subject = db.query(Subject).filter(Subject.title == "Introduction to Programming").one()
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
    assert "Python Programming" not in subjects_by_title
    assert "Boolean Algebra and Logisim" not in subjects_by_title
    assert not (CONTENT_DIR / "Lập trình Python").exists()
    assert not (CONTENT_DIR / "Boolean Algebra and Logisim").exists()
    computer_system = subjects_by_title["Computer System"]
    computer_sections = {section["title"]: section for section in computer_system["sections"]}
    assert computer_sections["Digital Logic Foundations"]["position"] == 0
    assert computer_sections["Digital Logic Foundations"]["lessons"]
    assert (
        CONTENT_DIR
        / "Computer System"
        / "Digital Logic Foundations"
        / "01-gates-and-boolean-algebra.json"
    ).is_file()
    programming = subjects_by_title["Introduction to Programming"]
    section_titles = [section["title"] for section in programming["sections"]]
    assert "Programming Fundamentals" in section_titles
    assert "Weekly Programming Topics" in section_titles
    assert "Core Programming Concepts" not in section_titles
    fundamentals = next(section for section in programming["sections"] if section["title"] == "Programming Fundamentals")
    assert fundamentals["position"] == 1
    assert fundamentals["lessons"][0]["title"] == "Variables and Data Types"
    weekly_programming = next(section for section in programming["sections"] if section["title"] == "Weekly Programming Topics")
    assert weekly_programming["position"] == 2
    assert len(weekly_programming["lessons"]) == 12
    assert weekly_programming["lessons"][0]["title"] == "Procedures, Functions and Structure Charts"
    assert weekly_programming["lessons"][-1]["title"] == "Testing, Tools and Projects"
    linear_algebra = subjects_by_title["Linear Algebra and Applications"]
    linear_sections = {section["title"]: section["position"] for section in linear_algebra["sections"]}
    assert linear_sections["Matrices"] == 1
    assert linear_sections["Vectors"] == 2
    assert linear_sections["Linear Geometry"] == 3
    assert linear_sections["Linear Transformations"] == 4
    assert linear_sections["Complex Numbers"] == 5
    source_section = next(section for section in linear_algebra["sections"] if section["title"] == "Original Source Files")
    assert source_section["position"] == 90
    assert source_section["lessons"][0]["title"] == "Linear Algebra and Applications"
    assert (CONTENT_DIR / "Linear Algebra and Applications" / "Original Source Files" / "01-mth10013.json").is_file()


def test_new_exercise_schema_is_normalized():
    exercise = normalize_exercise_data(
        {
            "type": "multiple_choice",
            "question": "Which value is a float?",
            "options": ["42", "3.14", "True"],
            "answer": "3.14",
        },
        1,
    )
    assert exercise["title"] == "Which value is a float?"
    assert exercise["prompt"] == "Which value is a float?"
    assert exercise["exercise_type"] == "multiple_choice"
    assert exercise["options"] == ["42", "3.14", "True"]


def test_database_design_project_source_files_include_visuals():
    subjects = load_subject_files()
    database_project = next(subject for subject in subjects if subject["title"] == "Database Design Project")
    source_section = next(section for section in database_project["sections"] if section["title"] == "Original Source Files")
    assert source_section["position"] == 90
    assert len(source_section["lessons"]) == 11
    first_lesson = source_section["lessons"][0]
    assert first_lesson["title"] == "Adding and Manipulating the Data"
    assert "source-slide-gallery" in first_lesson["content_html"]
    assert "source-text" in first_lesson["content_html"]
    assert "slide-002.webp" in first_lesson["content_html"]
    assert (
        CONTENT_DIR.parent.parent
        / "static"
        / "content"
        / "database-design-project"
        / "week-7-adding-and-manipulating-data-pptx"
        / "slide-002.webp"
    ).is_file()


def test_business_and_media_subjects_use_curated_sections():
    subjects = load_subject_files()
    subjects_by_title = {subject["title"]: subject for subject in subjects}
    expected_sections = {
        "Business Digitalisation": {
            "Information Systems Foundations",
            "How We Do Information Systems",
            "Future of Information Systems",
        },
        "Economics for Business Decision Making": {"Microeconomics", "Macroeconomics"},
        "Contemporary Management Principles": {
            "Management Foundations",
            "Strategy and Structure",
            "People and Organisations",
            "Leading and Changing",
        },
        "Marketing and the Consumer Experience": {"Marketing Fundamentals"},
        "Communicating with Data": {"Understanding Data", "Data Visualization and Communication"},
    }
    for subject_title, required_sections in expected_sections.items():
        section_titles = {section["title"] for section in subjects_by_title[subject_title]["sections"]}
        assert SOURCE_ARCHIVE_SECTION_TITLE not in section_titles
        assert required_sections.issubset(section_titles)
        assert all(section["lessons"] for section in subjects_by_title[subject_title]["sections"])
