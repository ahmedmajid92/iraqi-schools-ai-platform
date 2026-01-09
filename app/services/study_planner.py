"""
Subject-specific study planner for Iraqi schools.
Provides customized review schedules and suggestions per subject category.
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional
import json
from pathlib import Path


# Subject category configurations (loaded from curriculum_seed.json)
SUBJECT_CONFIGS = {
    # STEM subjects
    "الحاسوب": {
        "category": "stem",
        "review_days": [1, 3, 5, 10],
        "study_suggestion": "فهم المفاهيم + تطبيق عملي على الحاسوب",
        "review_suggestion": "حل تمارين عملية + مراجعة الأوامر والخطوات",
        "exam_tips": [
            "ركز على الجزء العملي والتطبيقات",
            "راجع أسئلة الوزارية السابقة",
            "تدرب على كتابة الأكواد والخوارزميات"
        ]
    },
    "الأحياء": {
        "category": "stem",
        "review_days": [1, 3, 5, 10],
        "study_suggestion": "ارسم مخططات + حفظ التعريفات + فهم العمليات",
        "review_suggestion": "مراجعة الرسوم البيانية + حل أسئلة وزارية",
        "exam_tips": [
            "احفظ التعريفات والمصطلحات العلمية",
            "ارسم المخططات والرسوم التوضيحية",
            "ركز على أسئلة المقارنة والعلل"
        ]
    },
    # Languages
    "اللغة العربية": {
        "category": "languages",
        "review_days": [1, 2, 4, 7],
        "study_suggestion": "حفظ النصوص + فهم القواعد النحوية + التطبيق",
        "review_suggestion": "مراجعة القواعد + إعراب جمل + كتابة تعبير",
        "exam_tips": [
            "احفظ القطع المطلوبة والشواهد",
            "تدرب على الإعراب والبلاغة",
            "راجع أسئلة الفهم والاستيعاب"
        ]
    },
    "اللغة الإنكليزية": {
        "category": "languages",
        "review_days": [1, 2, 4, 7],
        "study_suggestion": "حفظ المفردات + قراءة النصوص + تطبيق القواعد",
        "review_suggestion": "مراجعة Grammar + Solutions للأسئلة + Vocabulary",
        "exam_tips": [
            "احفظ المفردات والتعابير الجديدة",
            "تدرب على قواعد الـ Grammar",
            "اقرأ النصوص وطبق أسئلة الفهم"
        ]
    },
    # Humanities
    "التاريخ": {
        "category": "humanities",
        "review_days": [1, 4, 8, 14],
        "study_suggestion": "فهم الأحداث + ربط التواريخ + حفظ الشخصيات",
        "review_suggestion": "تلخيص الأحداث + مراجعة التواريخ المهمة",
        "exam_tips": [
            "احفظ التواريخ والأحداث المهمة",
            "اربط الأحداث ببعضها",
            "ركز على أسئلة العلل والمقارنات"
        ]
    },
    "الجغرافية": {
        "category": "humanities",
        "review_days": [1, 4, 8, 14],
        "study_suggestion": "قراءة الخرائط + حفظ المصطلحات + فهم الظواهر",
        "review_suggestion": "مراجعة الخرائط + حل أسئلة على المواقع والمناخ",
        "exam_tips": [
            "ادرس الخرائط جيداً",
            "احفظ الإحصائيات والأرقام المهمة",
            "افهم العلاقة بين الظواهر الجغرافية"
        ]
    },
    # Religious Studies
    "الإسلامية": {
        "category": "religious",
        "review_days": [1, 2, 5, 10],
        "study_suggestion": "حفظ الآيات والأحاديث + فهم الأحكام + التطبيق",
        "review_suggestion": "تسميع + مراجعة الأحكام + حل أسئلة",
        "exam_tips": [
            "تأكد من صحة حفظ الآيات والأحاديث",
            "افهم معاني المفردات القرآنية",
            "راجع الأحكام الشرعية والفقهية"
        ]
    }
}

# Default config for unknown subjects
DEFAULT_CONFIG = {
    "category": "general",
    "review_days": [1, 3, 7, 14],
    "study_suggestion": "فهم الفكرة + مثال + سؤالين",
    "review_suggestion": "اكتب 5 نقاط + 5 أسئلة سريعة",
    "exam_tips": ["راجع الأسئلة المهمة", "حل نماذج سابقة"]
}


@dataclass
class Task:
    day: date
    title: str
    kind: str  # "درس" or "مراجعة"
    subject: str


def _parse_date(s: str) -> Optional[date]:
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def _today() -> date:
    return date.today()


def _get_subject_config(subject: str) -> Dict:
    """Get subject-specific configuration."""
    return SUBJECT_CONFIGS.get(subject, DEFAULT_CONFIG)


def _topics_from_text(subjects: List[str], topics_text: str) -> List[Dict]:
    """
    Parse topics text format:
    مادة: موضوع 1
    مادة: موضوع 2
    or
    موضوع مستقل (سيتم توزيعه على أول مادة)
    """
    lines = [ln.strip() for ln in (topics_text or "").splitlines() if ln.strip()]
    topics = []
    if not lines:
        # fallback: create 5 units per subject
        for sub in subjects:
            for i in range(1, 6):
                topics.append({"subject": sub, "topic": f"وحدة {i}"})
        return topics

    fallback_subject = subjects[0] if subjects else "مادة"
    for ln in lines:
        if ":" in ln:
            sub, tp = ln.split(":", 1)
            sub = sub.strip() or fallback_subject
            tp = tp.strip()
            if tp:
                topics.append({"subject": sub, "topic": tp})
        else:
            topics.append({"subject": fallback_subject, "topic": ln})
    return topics


def build_study_plan(
    title: str,
    exam_date_str: str,
    hours_per_day: float,
    subjects: List[str],
    topics_text: str
) -> Dict:
    """
    Build a study plan with subject-specific schedules and suggestions.
    
    Features:
    - Different review schedules per subject category
    - Subject-appropriate study suggestions
    - Iraqi exam-focused tips
    """
    exam = _parse_date(exam_date_str)
    if not exam:
        # default: 14 days from today
        exam = _today() + timedelta(days=14)

    start = _today()
    if exam <= start:
        exam = start + timedelta(days=7)

    days = (exam - start).days + 1

    # capacity: 30-min blocks
    blocks_per_day = max(1, int(round(hours_per_day * 2)))

    topics = _topics_from_text(subjects, topics_text)

    tasks: List[Task] = []
    # distribute new lessons across days
    day_cursor = start
    b = 0

    for t in topics:
        tasks.append(Task(day=day_cursor, title=t["topic"], kind="درس", subject=t["subject"]))
        b += 1
        if b >= blocks_per_day:
            b = 0
            day_cursor = min(exam, day_cursor + timedelta(days=1))

    # Subject-specific spaced repetition review schedules
    task_map = {(tsk.subject, tsk.title): tsk.day for tsk in tasks if tsk.kind == "درس"}

    for (sub, tp), first_day in task_map.items():
        config = _get_subject_config(sub)
        review_days = config.get("review_days", [1, 3, 7, 14])
        
        for off in review_days:
            rd = first_day + timedelta(days=off)
            if rd <= exam:
                tasks.append(Task(day=rd, title=tp, kind="مراجعة", subject=sub))

    # sort tasks
    tasks.sort(key=lambda x: (x.day, 0 if x.kind == "درس" else 1, x.subject))

    # build calendar dict with subject-specific suggestions
    calendar = {}
    for i in range(days):
        d = start + timedelta(days=i)
        calendar[d.isoformat()] = []

    for t in tasks:
        config = _get_subject_config(t.subject)
        suggestion = config.get("review_suggestion" if t.kind == "مراجعة" else "study_suggestion", "")
        
        calendar.setdefault(t.day.isoformat(), []).append({
            "subject": t.subject,
            "task": t.title,
            "kind": t.kind,
            "suggestion": suggestion
        })

    # final review day
    calendar[exam.isoformat()].append({
        "subject": "مراجعة عامة",
        "task": "مراجعة شاملة + اختبار تجريبي",
        "kind": "مراجعة",
        "suggestion": "حل أسئلة وزارية متنوعة + مراجعة الأخطاء فقط"
    })

    # Collect all exam tips for included subjects
    all_tips = [
        "يفضل المذاكرة على فترتين قصيرتين بدل جلسة طويلة.",
        "في المراجعة: ركز على الأخطاء وليس إعادة قراءة كل شيء.",
        "قبل الامتحان بيوم: نوم مبكر + مراجعة خفيفة."
    ]
    
    subject_tips = {}
    for sub in subjects:
        config = _get_subject_config(sub)
        tips = config.get("exam_tips", [])
        if tips:
            subject_tips[sub] = tips

    return {
        "meta": {
            "title": title,
            "start_date": start.isoformat(),
            "exam_date": exam.isoformat(),
            "hours_per_day": hours_per_day,
            "blocks_per_day": blocks_per_day,
            "subjects": subjects
        },
        "calendar": calendar,
        "tips": all_tips,
        "subject_tips": subject_tips
    }
