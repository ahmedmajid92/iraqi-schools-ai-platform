# كيف يعالج النظام الملفات المرفوعة - File Processing Explained

## ✅ الإجابة المباشرة

**النظام يستخدم النص المستخرج (Extracted Text)، وليس File Search من OpenAI.**

---

## 📊 سير العمل (Workflow)

### الخطوة 1: تحميل الملف

```
المستخدم → يحمّل ملف (PDF/DOCX/TXT) → السيرفر
```

### الخطوة 2: استخراج النص

```javascript
// في teacher.html أو student.html
uploadFile('tFile', 'tLessonText')
  ↓
fetch('/api/extract-text', {file})  // POST request
  ↓
file_extractor.py → extract_text_from_file()
```

**ما يحدث في `file_extractor.py`:**

1. يقرأ الملف من memory
2. PDF → يستخدم `pdfplumber` لاستخراج النص
3. DOCX → يستخدم `python-docx` لاستخراج النص
4. TXT → يقرأ النص مباشرة
5. **يصحح النص العربي المعكوس** (مشكلة شائعة في PDF)
6. **ينظف النص** (يزيل أحرف Zero-width، مسافات غير مرئية، إلخ)
7. **يرجع النص النظيف** كـ string

### الخطوة 3: عرض النص في Textarea

```javascript
textarea.value = data.text; // النص يظهر في المربع
```

**الآن**: المستخدم يرى النص المستخرج ويمكنه تعديله!

### الخطوة 4: توليد الأسئلة

```javascript
// عند الضغط على "توليد الأسئلة"
teacherGenerateQuiz()
  ↓
POST /api/teacher/quiz-generate
Body: {
  lesson_text: "النص المستخرج",  // ← النص فقط، ليس الملف
  grade: "الخامس العلمي",
  subject: "الحاسوب"
}
```

### الخطوة 5: معالجة الطلب في السيرفر

```python
# في routes.py → api_teacher_quiz_generate()

text = payload.get("lesson_text")  # ← النص فقط

# يرسل النص إلى AI
quiz = generate_quiz_smart(text=text, ...)
```

### الخطوة 6: OpenAI API Call

```python
# في openai_quiz.py → generate_with_openai()

# تحسين التكلفة:
if word_count > MAX_WORDS:
    processed_text = _smart_chunk_text(text, MAX_WORDS)  # ← اقتطاع ذكي
else:
    processed_text = text

# بناء الـ prompt
prompt = f"""أنشئ {num_questions} سؤال...
النص:
{processed_text}  # ← النص فقط، ليس ملف
"""

# استدعاء OpenAI
response = client.chat.completions.create(
    model="gpt-5-nano-2025-08-07",
    messages=[
        {"role": "system", "content": "..."},
        {"role": "user", "content": prompt}  # ← النص في message
    ]
)
```

---

## 🔑 النقاط الأساسية

### ✅ ما يحدث:

1. **استخراج النص** من الملف (PDF → Text)
2. **إرسال النص** إلى OpenAI في الـ prompt
3. OpenAI **يقرأ النص** من message content
4. يولد الأسئلة بناءً على النص

### ❌ ما لا يحدث:

- ❌ **لا يتم** رفع الملف إلى OpenAI
- ❌ **لا يتم** استخدام File Search API
- ❌ **لا يتم** استخدام Assistants API
- ❌ **لا يتم** استخدام Vector Stores

---

## 📝 لماذا هذا الأسلوب؟

### المزايا:

1. ✅ **أبسط** - لا حاجة لـ Assistants API أو File Search
2. ✅ **أسرع** - لا حاجة لرفع الملف ومعالجته على OpenAI
3. ✅ **أرخص** - Chat Completion أرخص من Assistants + File Search
4. ✅ **تحكم أفضل** - يمكن تنظيف وتعديل النص قبل الإرسال
5. ✅ **يعمل مع Gemini أيضاً** - نفس الأسلوب يعمل مع كل AI

### تحسينات التكلفة المطبقة:

```python
# 1. اقتطاع النص (Max 5000 كلمة)
MAX_WORDS = 5000

# 2. اختيار ذكي للأجزاء المهمة (TF-IDF)
_smart_chunk_text(text, max_words)
  ↓
- يقسم النص لفقرات
- يحسب أهمية كل فقرة بـ TF-IDF
- يختار: أول فقرة + آخر فقرة + أهم الفقرات الوسطى
- يحافظ على حد 5000 كلمة

# 3. Cache (التخزين المؤقت)
- نفس النص + نفس عدد الأسئلة = يرجع من Cache
- مدة الـ Cache: 7 أيام
- توفير: لا حاجة لاستدعاء API مرة أخرى
```

---

## 🔄 مقارنة: Chat Completion vs File Search

| الميزة          | **Chat Completion** (المستخدم حالياً) | File Search API                  |
| --------------- | ------------------------------------- | -------------------------------- |
| **الطريقة**     | إرسال النص في message                 | رفع ملف + indexing               |
| **السرعة**      | سريع (فوري)                           | بطيء (يحتاج indexing)            |
| **التكلفة**     | منخفضة ($0.05/M input)                | عالية (رسوم إضافية للـ search)   |
| **الحد الأقصى** | ~5000 كلمة (قابل للتعديل)             | ملفات كبيرة                      |
| **التحكم**      | كامل (تنظيف + اقتطاع)                 | محدود                            |
| **التعقيد**     | بسيط                                  | معقد (Assistants + Vector Store) |

---

## 🎯 الخلاصة

### النظام الحالي:

```
ملف PDF/DOCX
  ↓ extract_text_from_file()
نص نظيف
  ↓ تعديل يدوي (اختياري)
نص نهائي
  ↓ generate_quiz_smart()
اختيار ذكي للأجزاء المهمة (5000 كلمة)
  ↓ OpenAI Chat Completion
إرسال النص في prompt
  ↓ GPT-5-Nano
توليد الأسئلة
```

### مثال عملي:

```python
# ملف PDF (10 صفحات، 8000 كلمة)
file.pdf
  ↓
"الحاسوب هو جهاز إلكتروني..."  # 8000 كلمة
  ↓ Smart Chunking
"الحاسوب هو جهاز... [أهم 5000 كلمة]"
  ↓ OpenAI
messages = [
  {"role": "user", "content": "أنشئ 10 أسئلة:\n الحاسوب هو..."}
]
  ↓
Questions Generated ✅
```

---

## 📌 ملخص تقني

| السؤال                       | الإجابة                                        |
| ---------------------------- | ---------------------------------------------- |
| **هل نستخدم File Search؟**   | ❌ لا                                          |
| **هل نرفع ملفات لـ OpenAI؟** | ❌ لا                                          |
| **ماذا نرسل لـ OpenAI؟**     | ✅ نص مستخرج في prompt                         |
| **كيف نعالج الملفات؟**       | ✅ نستخرج النص محلياً (pdfplumber/python-docx) |
| **أين يتم التنظيف؟**         | ✅ في السيرفر (file_extractor.py)              |
| **ما API المستخدم؟**         | ✅ Chat Completion (gpt-5-nano)                |

---

**🎉 النظام بسيط وفعال ورخيص!**
