import random
from typing import Dict, List, Optional

from sklearn.feature_extraction.text import TfidfVectorizer

from .arabic_nlp import split_sentences, tokenize_arabic, remove_stopwords, DEFAULT_STOPWORDS, normalize_arabic

def _arabic_tokenizer(text: str) -> List[str]:
    tokens = tokenize_arabic(text)
    tokens = remove_stopwords(tokens, DEFAULT_STOPWORDS)
    return tokens

def _top_terms(text: str, k: int = 18) -> List[str]:
    norm = normalize_arabic(text)
    vectorizer = TfidfVectorizer(
        tokenizer=_arabic_tokenizer,
        lowercase=False,
        ngram_range=(1, 2),
        max_features=2000
    )
    X = vectorizer.fit_transform([norm])
    feats = vectorizer.get_feature_names_out()
    scores = X.toarray()[0]
    pairs = sorted(zip(feats, scores), key=lambda x: x[1], reverse=True)
    terms = [t for t, s in pairs if s > 0][:k]
    # remove very short / noisy
    cleaned = []
    for t in terms:
        if len(t.replace(" ", "")) >= 4:
            cleaned.append(t)
    return cleaned[:k]

def _find_sentence_with_term(sentences: List[str], term: str) -> Optional[str]:
    term_norm = normalize_arabic(term)
    for s in sentences:
        if term_norm in normalize_arabic(s):
            return s.strip()
    return None

def _make_mcq(term: str, distractors: List[str]) -> Dict:
    choices = [term] + distractors[:3]
    random.shuffle(choices)
    answer_index = choices.index(term)
    q = {
        "type": "اختيار من متعدد",
        "question": f"أي خيار يعبّر عن المفهوم/المصطلح التالي: «{term}»؟",
        "choices": choices,
        "answer_index": answer_index
    }
    return q

def _make_fill_blank(sentence: str, term: str) -> Dict:
    # simple replace first occurrence
    s = sentence
    idx = normalize_arabic(s).find(normalize_arabic(term))
    if idx == -1:
        blanked = sentence
    else:
        # approximate replace by raw term if present
        blanked = sentence.replace(term, "_______", 1)
        if blanked == sentence:
            blanked = normalize_arabic(sentence).replace(normalize_arabic(term), "_______", 1)
    return {
        "type": "أكمل الفراغ",
        "question": f"أكمل الفراغ في الجملة التالية:\n{blanked}",
        "answer": term
    }

def _make_true_false(sentence: str) -> Dict:
    return {
        "type": "صح/خطأ",
        "question": f"صح أم خطأ:\n{sentence}",
        "answer": "صح"
    }

def _make_short_answer(term: str, sentence: str) -> Dict:
    return {
        "type": "سؤال قصير",
        "question": f"اشرح/عرّف باختصار: «{term}». (استعن بالدرس)",
        "answer_hint": sentence
    }

def generate_quiz_from_text(text: str, num_questions: int = 10, grade: str = "", subject: str = "") -> Dict:
    random.seed(42)

    sentences = split_sentences(text)
    terms = _top_terms(text, k=max(18, num_questions * 2))

    # create distractor pool
    pool = [t for t in terms if len(t) >= 3]
    random.shuffle(pool)

    questions = []
    used_terms = set()

    # prefer definition-like sentences for short answers
    def_like = [s for s in sentences if any(x in s for x in ["هو", "هي", "يعرف", "تعرف", "يعني", "المقصود"])]
    random.shuffle(def_like)

    # build mix: fill-blank + mcq + true/false + short
    while len(questions) < num_questions and terms:
        term = terms.pop(0)
        if term in used_terms:
            continue
        used_terms.add(term)

        sent = _find_sentence_with_term(sentences, term) or (random.choice(sentences) if sentences else f"المصطلح: {term}")

        # choose question type
        if len(questions) % 4 == 0:
            # fill blank
            questions.append(_make_fill_blank(sent, term))
        elif len(questions) % 4 == 1:
            # mcq
            d = [x for x in pool if x != term and abs(len(x) - len(term)) <= 6]
            questions.append(_make_mcq(term, d[:3] if len(d) >= 3 else pool[:3]))
        elif len(questions) % 4 == 2:
            # true/false from a real sentence
            questions.append(_make_true_false(sent))
        else:
            # short answer: use definition sentence if possible
            hint = def_like.pop(0) if def_like else sent
            questions.append(_make_short_answer(term, hint))

    # difficulty heuristic
    difficulty = "متوسط"
    if grade and any(x in grade for x in ["الرابع", "الخامس", "السادس"]):
        difficulty = "متوسط/متقدم"

    return {
        "meta": {
            "subject": subject or "غير محدد",
            "grade": grade or "غير محدد",
            "difficulty": difficulty,
            "question_count": len(questions)
        },
        "questions": questions,
        "notes": [
            "هذه أسئلة مساعدة مبنية على نص الدرس. يُفضّل أن تراجعها المعلمة قبل الاعتماد النهائي.",
            "قسم (صح/خطأ) هنا يعرض جمل صحيحة من النص لتقويم سريع داخل الصف."
        ]
    }
