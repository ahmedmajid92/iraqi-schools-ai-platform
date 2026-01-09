import json
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, render_template, request, jsonify, session, Response, redirect, url_for, flash

from .db import insert_json, list_rows, get_row, get_user_stats, get_user_progress, create_user, get_user_by_username, get_user_by_id
from .services import auth
from .services.auth import login_required, teacher_required
from .services.lesson_planner import build_lesson_plan
from .services.quiz_generator import generate_quiz_from_text
from .services.ai_quiz import generate_quiz_smart
from .services.study_planner import build_study_plan
from .services.reading_analyzer import analyze_arabic_text
from .services.adaptive_quiz import AdaptiveQuizEngine, load_question_bank
from .services.file_extractor import extract_text_from_file
from .services.pdf_export import is_pdf_available, export_lesson_plan_pdf, export_quiz_pdf


bp = Blueprint("main", __name__)

DATA_DIR = Path(__file__).parent / "data"

# Input limits
MAX_FILE_SIZE_MB = 5
MAX_WORD_COUNT = 5000

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")

def count_words(text: str) -> int:
    """Count words in text."""
    return len(text.split())


def load_curriculum_seed() -> dict:
    p = DATA_DIR / "curriculum_seed.json"
    return json.loads(p.read_text(encoding="utf-8"))

@bp.get("/")
def index():
    curriculum = load_curriculum_seed()
    # Debug: Log session contents
    print(f"[DEBUG SESSION] user_id={session.get('user_id')}, role={session.get('role')}, grade={session.get('grade')}")
    return render_template("index.html", curriculum=curriculum)

# ---------- Authentication ----------
@bp.route("/login", methods=["GET", "POST"])
def login_page():
    """Login page and handler."""
    if request.method == "GET":
        # If already logged in, redirect to appropriate page
        if auth.is_logged_in():
            if auth.is_teacher():
                return redirect(url_for('main.teacher_page'))
            return redirect(url_for('main.student_page'))
        return render_template("login.html")
    
    # POST: Process login
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    
    if not username or not password:
        flash("يرجى إدخال اسم المستخدم وكلمة المرور", "error")
        return redirect(url_for('main.login_page'))
    
    # Get user from database
    db_path = current_app.config["DB_PATH"]
    user = get_user_by_username(db_path, username)
    
    if not user:
        flash("اسم المستخدم أو كلمة المرور غير صحيحة", "error")
        return redirect(url_for('main.login_page'))
    
    # Verify password
    if not auth.verify_password(password, user['password_hash']):
        flash("اسم المستخدم أو كلمة المرور غير صحيحة", "error")
        return redirect(url_for('main.login_page'))
    
    # Login successful
    auth.login_user(user)
    flash(f"مرحباً {user.get('display_name') or username}! 🎉", "success")
    
    # Redirect to appropriate page based on role
    next_page = request.args.get('next')
    if next_page:
        return redirect(next_page)
    
    if auth.is_teacher():
        return redirect(url_for('main.teacher_page'))
    return redirect(url_for('main.student_page'))


@bp.route("/signup", methods=["GET", "POST"])
def signup_page():
    """Signup page and handler."""
    if request.method == "GET":
        # If already logged in, redirect
        if auth.is_logged_in():
            return redirect(url_for('main.index'))
        return render_template("signup.html")
    
    # POST: Process signup
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    confirm_password = request.form.get("confirm_password", "").strip()
    display_name = request.form.get("display_name", "").strip()
    role = request.form.get("role", "student").strip()
    grade = request.form.get("grade", "").strip()
    
    # Validate username
    valid, error_msg = auth.validate_username(username)
    if not valid:
        flash(error_msg, "error")
        return redirect(url_for('main.signup_page'))
    
    # Validate password
    valid, error_msg = auth.validate_password(password)
    if not valid:
        flash(error_msg, "error")
        return redirect(url_for('main.signup_page'))
    
    # Check password confirmation
    if password != confirm_password:
        flash("كلمتا المرور غير متطابقتين", "error")
        return redirect(url_for('main.signup_page'))
    
    # Check if username already exists
    db_path = current_app.config["DB_PATH"]
    existing_user = get_user_by_username(db_path, username)
    if existing_user:
        flash("اسم المستخدم موجود بالفعل. يرجى اختيار اسم آخر", "error")
        return redirect(url_for('main.signup_page'))
    
    # Validate role
    if role not in ['student', 'teacher']:
        role = 'student'
    
    # Hash password and create user
    password_hash = auth.hash_password(password)
    user_id = create_user(
        db_path=db_path,
        username=username,
        password_hash=password_hash,
        role=role,
        display_name=display_name or None,
        grade=grade or None
    )
    
    # Get the created user and login
    user = get_user_by_id(db_path, user_id)
    auth.login_user(user)
    
    flash(f"تم إنشاء حسابك بنجاح! مرحباً {display_name or username} 🎉", "success")
    
    # Redirect based on role
    if role == 'teacher':
        return redirect(url_for('main.teacher_page'))
    return redirect(url_for('main.student_page'))


@bp.get("/logout")
def logout_page():
    """Logout handler."""
    auth.logout_user()
    flash("تم تسجيل الخروج بنجاح", "info")
    return redirect(url_for('main.index'))

# ---------- Dashboard ----------
@bp.get("/dashboard")
@login_required
def dashboard_page():
    """Progress dashboard page."""
    return render_template("dashboard.html")

@bp.get("/api/dashboard/stats")
def api_dashboard_stats():
    """Get user statistics for dashboard."""
    db_path = current_app.config["DB_PATH"]
    
    # For now, use session-based stats (can be upgraded to user-based later)
    lab_state = session.get("lab_state")
    
    # Build stats from session data
    stats = {
        "total_quizzes": 0,
        "total_questions_answered": 0,
        "correct_answers": 0,
        "accuracy": 0,
        "subjects": {},
        "recent_activity": [],
        "lab_progress": None
    }
    
    # Get lab progress from session
    if lab_state:
        stats["lab_progress"] = {
            "total_questions": lab_state.get("total", 0),
            "correct_answers": lab_state.get("correct", 0),
            "total_points": lab_state.get("points", 0),
            "best_streak": lab_state.get("best_streak", 0),
            "badges_json": json.dumps(lab_state.get("badges", []))
        }
        stats["total_questions_answered"] = lab_state.get("total", 0)
        stats["correct_answers"] = lab_state.get("correct", 0)
        if stats["total_questions_answered"] > 0:
            stats["accuracy"] = round(stats["correct_answers"] / stats["total_questions_answered"] * 100, 1)
    
    # Get recent quiz runs
    recent_quizzes = list_rows(db_path, "quiz_runs", limit=5)
    stats["total_quizzes"] = len(recent_quizzes)
    
    return jsonify({"ok": True, "stats": stats})

# ---------- File Upload ----------
@bp.post("/api/extract-text")
def api_extract_text():
    """Extract text from uploaded file (PDF, DOCX, TXT)."""
    if 'file' not in request.files:
        return jsonify({"ok": False, "error": "لم يتم رفع ملف."}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"ok": False, "error": "لم يتم اختيار ملف."}), 400

    # Check file size (max 5MB)
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning

    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if size > max_bytes:
        return jsonify({"ok": False, "error": f"حجم الملف كبير جدًا. الحد الأقصى {MAX_FILE_SIZE_MB} ميغابايت."}), 400

    success, result = extract_text_from_file(file, file.filename)

    if not success:
        return jsonify({"ok": False, "error": result}), 400

    # Check word count
    word_count = count_words(result)
    if word_count > MAX_WORD_COUNT:
        return jsonify({
            "ok": False, 
            "error": f"النص طويل جدًا ({word_count} كلمة). الحد الأقصى {MAX_WORD_COUNT} كلمة. يرجى استخدام محاضرة واحدة فقط."
        }), 400

    return jsonify({"ok": True, "text": result, "word_count": word_count})


# ---------- Teacher ----------
@bp.get("/teacher")
@teacher_required
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

    # Check word count limit
    word_count = count_words(text)
    if word_count > MAX_WORD_COUNT:
        return jsonify({
            "ok": False, 
            "error": f"النص طويل جدًا ({word_count} كلمة). الحد الأقصى {MAX_WORD_COUNT} كلمة."
        }), 400

    # Use smart generator (AI with fallback to enhanced NLP)
    quiz = generate_quiz_smart(text=text, num_questions=num_q, grade=grade, subject=subject)

    # persist
    db_path = current_app.config["DB_PATH"]
    insert_json(db_path, "quiz_runs", now_iso(), "teacher_quiz", json.dumps(quiz, ensure_ascii=False))

    return jsonify({"ok": True, "quiz": quiz})


# ---------- Student ----------
@bp.get("/student")
@login_required
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
# Grade-based settings for difficulty and timer
GRADE_SETTINGS = {
    "الرابع العلمي": {"level": 1, "timer": 25, "difficulty": "سهل"},
    "الخامس العلمي": {"level": 2, "timer": 20, "difficulty": "متوسط"},
    "السادس العلمي": {"level": 3, "timer": 20, "difficulty": "صعب"},
}

@bp.get("/lab")
@login_required
def lab_page():
    # Restrict to scientific branches only (not for teachers)
    user_grade = session.get("grade", "")
    user_role = session.get("role", "student")
    allowed_grades = ["الرابع العلمي", "الخامس العلمي", "السادس العلمي"]
    
    if user_role != "teacher" and user_grade not in allowed_grades:
        flash("مختبر الحاسوب متاح فقط لطلاب الفروع العلمية (الرابع/الخامس/السادس العلمي)", "warning")
        return redirect(url_for("main.student"))
    
    # Get grade settings for timer and level
    grade_settings = GRADE_SETTINGS.get(user_grade, {"level": 2, "timer": 20, "difficulty": "متوسط"})
    
    # init per session engine with gamification state
    if "lab_state" not in session:
        session["lab_state"] = {
            "asked_ids": [],
            "score": 0,
            "correct": 0,
            "total": 0,
            "level": grade_settings["level"],
            "points": 0,
            "current_streak": 0,
            "best_streak": 0,
            "badges": []
        }
    return render_template("lab.html", grade_settings=grade_settings, user_grade=user_grade)

@bp.get("/api/lab/next-question")
def api_lab_next_question():
    bank = load_question_bank(str(DATA_DIR / "computer_lab_questions.json"))
    state = session.get("lab_state") or {
        "asked_ids": [], "score": 0, "correct": 0, "total": 0, 
        "level": 2, "points": 0, "current_streak": 0, "best_streak": 0, "badges": []
    }
    engine = AdaptiveQuizEngine(bank)

    q = engine.next_question(state)
    if q is None:
        return jsonify({"ok": True, "done": True, "state": state})

    # Save updated state (asked_ids updated)
    session["lab_state"] = state
    session.modified = True

    return jsonify({"ok": True, "done": False, "question": q, "state": state})

@bp.post("/api/lab/answer")
def api_lab_answer():
    payload = request.get_json(force=True)
    qid = payload.get("id")
    chosen_answer = payload.get("chosen_answer", "")  # Get the actual answer text chosen
    time_taken = payload.get("time_taken_seconds")

    bank = load_question_bank(str(DATA_DIR / "computer_lab_questions.json"))
    state = session.get("lab_state") or {
        "asked_ids": [], "score": 0, "correct": 0, "total": 0,
        "level": 2, "points": 0, "current_streak": 0, "best_streak": 0, "badges": []
    }

    # Find the question to get the correct answer
    question = next((q for q in bank if q['id'] == qid), None)
    if question:
        correct_answer = question['choices'][question['answer_index']]
        # Check if chosen answer matches correct answer
        chosen_index = question['answer_index'] if chosen_answer == correct_answer else -1
    else:
        chosen_index = -1

    engine = AdaptiveQuizEngine(bank)
    feedback, new_state = engine.apply_answer(state, qid, chosen_index, time_taken)

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
        "level": 2,
        "points": 0,
        "current_streak": 0,
        "best_streak": 0,
        "badges": []
    }
    session.modified = True
    return jsonify({"ok": True})


# ---------- PDF Export ----------
@bp.post("/api/export/lesson-plan")
def api_export_lesson_plan():
    """Export lesson plan to PDF."""
    if not is_pdf_available():
        return jsonify({"ok": False, "error": "تصدير PDF غير متوفر. يرجى تثبيت reportlab."}), 500
    
    payload = request.get_json(force=True)
    plan = payload.get("plan")
    
    if not plan:
        return jsonify({"ok": False, "error": "لا توجد خطة درس للتصدير."}), 400
    
    try:
        pdf_bytes = export_lesson_plan_pdf(plan)
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': 'attachment; filename=lesson_plan.pdf'}
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"فشل التصدير: {str(e)}"}), 500


@bp.post("/api/export/quiz")
def api_export_quiz():
    """Export quiz to PDF."""
    if not is_pdf_available():
        return jsonify({"ok": False, "error": "تصدير PDF غير متوفر. يرجى تثبيت reportlab."}), 500
    
    payload = request.get_json(force=True)
    quiz = payload.get("quiz")
    include_answers = payload.get("include_answers", True)
    
    if not quiz:
        return jsonify({"ok": False, "error": "لا يوجد اختبار للتصدير."}), 400
    
    try:
        pdf_bytes = export_quiz_pdf(quiz, include_answers=include_answers)
        return Response(
            pdf_bytes,
            mimetype='application/pdf',
            headers={'Content-Disposition': 'attachment; filename=quiz.pdf'}
        )
    except Exception as e:
        return jsonify({"ok": False, "error": f"فشل التصدير: {str(e)}"}), 500


@bp.get("/api/limits")
def api_get_limits():
    """Get current input limits for the frontend."""
    return jsonify({
        "ok": True,
        "limits": {
            "max_file_size_mb": MAX_FILE_SIZE_MB,
            "max_word_count": MAX_WORD_COUNT
        }
    })
