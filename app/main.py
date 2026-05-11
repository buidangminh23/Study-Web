import json
from contextlib import asynccontextmanager
from datetime import datetime

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
from .seed import seed_data


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
app.add_middleware(SessionMiddleware, secret_key="study-web-local-secret", same_site="lax")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


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
    return templates.TemplateResponse(request, template, context)


def redirect(path: str) -> RedirectResponse:
    return RedirectResponse(path, status_code=303)


def parse_options(options_text: str) -> str:
    options = [item.strip() for item in options_text.splitlines() if item.strip()]
    return json.dumps(options, ensure_ascii=False)


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
    return subjects


def get_first_lesson(db: Session) -> Lesson | None:
    return (
        db.query(Lesson)
        .join(Section)
        .join(Subject)
        .options(joinedload(Lesson.section).joinedload(Section.subject), joinedload(Lesson.exercises))
        .filter(Subject.is_published.is_(True), Lesson.is_published.is_(True))
        .order_by(Subject.position, Section.position, Lesson.position)
        .first()
    )


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
            "progress": progress,
            "attempts": attempts,
            "previous_lesson": get_previous_lesson(lesson, db),
            "next_lesson": get_next_lesson(lesson, db),
            "json": json,
        },
        db,
    )


def get_next_lesson(lesson: Lesson, db: Session) -> Lesson | None:
    return (
        db.query(Lesson)
        .join(Section)
        .filter(
            Section.subject_id == lesson.section.subject_id,
            Lesson.is_published.is_(True),
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
            (Section.position < lesson.section.position)
            | ((Section.position == lesson.section.position) & (Lesson.position < lesson.position)),
        )
        .order_by(Section.position.desc(), Lesson.position.desc())
        .first()
    )


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    lesson = get_first_lesson(db)
    if not lesson:
        subjects = db.query(Subject).filter(Subject.is_published.is_(True)).order_by(Subject.position).all()
        return render(request, "index.html", {"subjects": subjects}, db)
    return render_lesson_page(lesson, request, db)


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
        return render(request, "auth/register.html", {"error": "Email đã tồn tại."}, db)
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
        return render(request, "auth/login.html", {"error": "Email hoặc mật khẩu không đúng."}, db)
    request.session["user_id"] = user.id
    return redirect("/dashboard")


@app.post("/auth/logout")
def logout(request: Request):
    request.session.clear()
    return redirect("/")


@app.get("/subjects", response_class=HTMLResponse)
def subjects_page(request: Request, db: Session = Depends(get_db)):
    subjects = db.query(Subject).filter(Subject.is_published.is_(True)).order_by(Subject.position).all()
    return render(request, "subjects.html", {"subjects": subjects}, db)


@app.get("/subjects/{subject_id}", response_class=HTMLResponse)
def subject_detail(subject_id: int, request: Request, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == subject_id, Subject.is_published.is_(True)).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
    lesson = (
        db.query(Lesson)
        .join(Section)
        .options(joinedload(Lesson.section).joinedload(Section.subject), joinedload(Lesson.exercises))
        .filter(Section.subject_id == subject.id, Lesson.is_published.is_(True))
        .order_by(Section.position, Lesson.position)
        .first()
    )
    if not lesson:
        return render(request, "subject_detail.html", {"subject": subject}, db)
    return render_lesson_page(lesson, request, db)


@app.get("/lessons/{lesson_id}", response_class=HTMLResponse)
def lesson_detail(lesson_id: int, request: Request, db: Session = Depends(get_db)):
    lesson = (
        db.query(Lesson)
        .options(joinedload(Lesson.section).joinedload(Section.subject), joinedload(Lesson.exercises))
        .filter(Lesson.id == lesson_id, Lesson.is_published.is_(True))
        .first()
    )
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
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
    widget_type: str = Form("variables"),
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
