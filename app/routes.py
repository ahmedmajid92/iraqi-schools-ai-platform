import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, render_template, request, jsonify, session

from .db import insert_json, list_rows
from .services.lesson_planner import build_lesson_plan
from .services.quiz_generator import generate_quiz_from_text
from .services.ai_quiz import generate_quiz_smart
from .services.study_planner import build_study_plan
from .services.reading_analyzer import analyze_arabic_text
from .services.adaptive_quiz import AdaptiveQuizEngine, load_question_bank
from .services.file_extractor import extract_text_from_file

bp = Blueprint("main", __name__)

DATA_DIR = Path(__file__).parent / "data"

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def load_curriculum_seed() -> dict:
    p = DATA_DIR / "curriculum_seed.json"
    return json.loads(p.read_text(encoding="utf-8"))

@bp.get("/")
def index():
    curriculum = load_curriculum_seed()
    return render_template("index.html", curriculum=curriculum)

# ---------- File Upload ----------
@bp.post("/api/extract-text")
def api_extract_text():
    """Extract text from uploaded file (PDF, DOCX, TXT)."""
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "لم يتم رفع ملف."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"ok": False, "error": "لم يتم اختيار ملف."}), 400

    # Check file size (max 10MB)
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning

    if size > 10 * 1024 * 1024:  # 10MB
        return jsonify({"ok": False, "error": "حجم الملف كبير جدًا. الحد الأقصى 10 ميغابايت."}), 400

    success, result = extract_text_from_file(file, file.filename)

    if not success:
        return jsonify({"ok": False, "error": result}), 400

    return jsonify({"ok": True, "text": result})

# ---------- Teacher ----------
@bp.get("/teacher")
def teacher_page():
    curriculum = load_curriculum_seed()
    recent_quizzes = list_rows(current_app.config["DB_PATH"], "quiz_runs", limit=5)
    return render_template("teacher.html", curriculum=curriculum, recent_quizzes=recent_quizzes)

@bp.post("/api/teacher/lesson-plan")
def api_teacher_lesson_plan():
    payload = request.get_json(force=True)
    plan = build_lesson_plan(
        subject=payload.get("subject", "").strip(),
        grade=payload.get("grade", "").strip(),
        lesson_title=payload.get("lesson_title", "").strip(),
        duration_minutes=int(payload.get("duration_minutes", 45)),
        lesson_type=payload.get("lesson_type", "شرح/مفاهيم").strip(),
    )
    return jsonify({"ok": True, "plan": plan})

@bp.post("/api/teacher/quiz-generate")
def api_teacher_quiz_generate():
    payload = request.get_json(force=True)
    text = (payload.get("lesson_text") or "").strip()
    num_q = int(payload.get("num_questions", 10))
    grade = (payload.get("grade") or "").strip()
    subject = (payload.get("subject") or "").strip()

    if len(text) < 60:
        return jsonify({"ok": False, "error": "النص قصير جدًا. الرجاء لصق جزء أكبر من الدرس."}), 400

    # Use smart generator (AI with fallback to enhanced NLP)
    quiz = generate_quiz_smart(text=text, num_questions=num_q, grade=grade, subject=subject)

    # persist
    db_path = current_app.config["DB_PATH"]
    insert_json(db_path, "quiz_runs", now_iso(), "teacher_quiz", json.dumps(quiz, ensure_ascii=False))

    return jsonify({"ok": True, "quiz": quiz})

# ---------- Student ----------
@bp.get("/student")
def student_page():
    curriculum = load_curriculum_seed()
    recent_plans = list_rows(current_app.config["DB_PATH"], "study_plans", limit=5)
    return render_template("student.html", curriculum=curriculum, recent_plans=recent_plans)

@bp.post("/api/student/study-plan")
def api_student_study_plan():
    payload = request.get_json(force=True)
    title = (payload.get("title") or "خطة مذاكرة").strip()
    exam_date = (payload.get("exam_date") or "").strip()
    hours_per_day = float(payload.get("hours_per_day", 1.5))
    subjects = payload.get("subjects") or []
    topics_text = (payload.get("topics_text") or "").strip()

    plan = build_study_plan(
        title=title,
        exam_date_str=exam_date,
        hours_per_day=hours_per_day,
        subjects=subjects,
        topics_text=topics_text,
    )

    db_path = current_app.config["DB_PATH"]
    insert_json(db_path, "study_plans", now_iso(), title, json.dumps(plan, ensure_ascii=False))
    return jsonify({"ok": True, "plan": plan})

@bp.post("/api/student/reading-analyze")
def api_student_reading_analyze():
    payload = request.get_json(force=True)
    label = (payload.get("label") or "تحليل قراءة").strip()
    text = (payload.get("text") or "").strip()

    if len(text) < 80:
        return jsonify({"ok": False, "error": "النص قصير جدًا. الرجاء إدخال نص أطول للتحليل."}), 400

    result = analyze_arabic_text(text)

    db_path = current_app.config["DB_PATH"]
    insert_json(db_path, "reading_results", now_iso(), label, json.dumps(result, ensure_ascii=False))

    return jsonify({"ok": True, "result": result})

# ---------- Computer Lab ----------
@bp.get("/lab")
def lab_page():
    # init per session engine
    if "lab_state" not in session:
        session["lab_state"] = {
            "asked_ids": [],
            "score": 0,
            "correct": 0,
            "total": 0,
            "level": 2
        }
    return render_template("lab.html")

@bp.get("/api/lab/next-question")
def api_lab_next_question():
    bank = load_question_bank(str(DATA_DIR / "computer_lab_questions.json"))
    state = session.get("lab_state") or {"asked_ids": [], "score": 0, "correct": 0, "total": 0, "level": 2}
    engine = AdaptiveQuizEngine(bank)

    q = engine.next_question(state)
    if q is None:
        return jsonify({"ok": True, "done": True, "state": state})

    return jsonify({"ok": True, "done": False, "question": q, "state": state})

@bp.post("/api/lab/answer")
def api_lab_answer():
    payload = request.get_json(force=True)
    qid = payload.get("id")
    chosen = int(payload.get("choice_index", -1))

    bank = load_question_bank(str(DATA_DIR / "computer_lab_questions.json"))
    state = session.get("lab_state") or {"asked_ids": [], "score": 0, "correct": 0, "total": 0, "level": 2}

    engine = AdaptiveQuizEngine(bank)
    feedback, new_state = engine.apply_answer(state, qid, chosen)

    session["lab_state"] = new_state
    session.modified = True

    return jsonify({"ok": True, "feedback": feedback, "state": new_state})

@bp.post("/api/lab/reset")
def api_lab_reset():
    session["lab_state"] = {
        "asked_ids": [],
        "score": 0,
        "correct": 0,
        "total": 0,
        "level": 2
    }
    session.modified = True
    return jsonify({"ok": True})
