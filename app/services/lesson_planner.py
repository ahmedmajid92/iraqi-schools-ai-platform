from typing import Dict, List

LESSON_TEMPLATES = {
    "شرح/مفاهيم": {
        "phases": [
            ("تمهيد", 5, "سؤال محفّز مرتبط بحياة الطالبات + مراجعة سريعة"),
            ("عرض المفاهيم", 15, "شرح مختصر + أمثلة من واقع المدرسة/البيت"),
            ("نشاط صفّي", 15, "عمل مجموعات صغيرة + ورقة نشاط قصيرة"),
            ("تطبيق/تقويم سريع", 7, "سؤالين (اختيار/صح-خطأ) + مناقشة"),
            ("خاتمة وواجب", 3, "ملخص نقطي + واجب متدرج")
        ],
        "assessment": ["سؤال اختيار من متعدد", "سؤال صح/خطأ", "سؤال قصير"]
    },
    "حل مسائل": {
        "phases": [
            ("تمهيد", 5, "مراجعة قاعدة أو قانون"),
            ("مثال محلول", 12, "شرح خطوات الحل على السبورة"),
            ("تدريب موجّه", 15, "حل تمرينين مع الطالبات"),
            ("تطبيق فردي", 10, "تمرين قصير لكل طالبة"),
            ("خاتمة وواجب", 3, "واجب: 4 مسائل (سهل-متوسط-صعب)")
        ],
        "assessment": ["تمرين قصير", "ملاحظة أخطاء شائعة", "واجب منزلي"]
    },
    "قراءة وفهم": {
        "phases": [
            ("تمهيد", 5, "توقعات من العنوان + مفردات أساسية"),
            ("قراءة موجّهة", 12, "قراءة فقرة + أسئلة أثناء القراءة"),
            ("تحليل", 15, "استخراج الفكرة الرئيسة + أدلة"),
            ("نشاط", 10, "تلخيص 3 أسطر + كلمة جديدة"),
            ("خاتمة وواجب", 3, "واجب: تلخيص + 3 مفردات")
        ],
        "assessment": ["تلخيص", "أسئلة فهم", "مفردات"]
    }
}

def build_lesson_plan(subject: str, grade: str, lesson_title: str, duration_minutes: int, lesson_type: str) -> Dict:
    tmpl = LESSON_TEMPLATES.get(lesson_type, LESSON_TEMPLATES["شرح/مفاهيم"])

    # scale phase minutes to match duration
    phases = tmpl["phases"]
    total = sum(m for _, m, _ in phases)
    factor = duration_minutes / max(total, 1)

    scaled_phases = []
    acc = 0
    for i, (name, minutes, desc) in enumerate(phases):
        if i == len(phases) - 1:
            m = max(1, duration_minutes - acc)
        else:
            m = max(1, int(round(minutes * factor)))
        acc += m
        scaled_phases.append({"name": name, "minutes": m, "desc": desc})

    objectives = [
        "أن يشرح الطالب المفهوم/الفكرة بأسلوبه.",
        "أن يعطي مثالاً من واقعه يوضح الفكرة.",
        "أن يجيب عن أسئلة تقويم قصيرة بدقة."
    ]

    differentiation = [
        "طلاب بحاجة دعم: أسئلة مباشرة + أمثلة إضافية.",
        "طلاب متفوقون: سؤال توسّع أو تطبيق أعلى مستوى."
    ]

    homework = [
        "تلخيص 5 نقاط من الدرس (أو حل 3-5 أسئلة).",
        "تحضير سؤال واحد للدرس القادم."
    ]

    return {
        "meta": {
            "subject": subject or "—",
            "grade": grade or "—",
            "lesson_title": lesson_title or "—",
            "duration_minutes": duration_minutes,
            "lesson_type": lesson_type
        },
        "objectives": objectives,
        "phases": scaled_phases,
        "assessment": tmpl["assessment"],
        "differentiation": differentiation,
        "homework": homework
    }
