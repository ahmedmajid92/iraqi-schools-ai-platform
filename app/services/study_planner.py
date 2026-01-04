from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

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

def _topics_from_text(subjects: List[str], topics_text: str) -> List[Dict]:
    """
    topics_text format:
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

    # spaced repetition review schedule per topic
    review_offsets = [1, 3, 7, 14]  # days after first study
    task_map = {(tsk.subject, tsk.title): tsk.day for tsk in tasks if tsk.kind == "درس"}

    for (sub, tp), first_day in task_map.items():
        for off in review_offsets:
            rd = first_day + timedelta(days=off)
            if rd <= exam:
                tasks.append(Task(day=rd, title=tp, kind="مراجعة", subject=sub))

    # sort tasks
    tasks.sort(key=lambda x: (x.day, 0 if x.kind == "درس" else 1, x.subject))

    # build calendar dict
    calendar = {}
    for i in range(days):
        d = start + timedelta(days=i)
        calendar[d.isoformat()] = []

    for t in tasks:
        calendar.setdefault(t.day.isoformat(), []).append({
            "subject": t.subject,
            "task": t.title,
            "kind": t.kind,
            "suggestion": "اكتبي 5 نقاط + 5 أسئلة سريعة" if t.kind == "مراجعة" else "فهم الفكرة + مثال + سؤالين"
        })

    # final review day
    calendar[exam.isoformat()].append({
        "subject": "مراجعة عامة",
        "task": "مراجعة شاملة + اختبار 20 دقيقة",
        "kind": "مراجعة",
        "suggestion": "حل أسئلة متنوعة + مراجعة الأخطاء فقط"
    })

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
        "tips": [
            "يفضل مذاكرة على فترتين قصيرتين بدل جلسة طويلة.",
            "في المراجعة: ركزي على الأخطاء وليس إعادة قراءة كل شيء.",
            "قبل الامتحان بيوم: نوم مبكر + مراجعة خفيفة."
        ]
    }
