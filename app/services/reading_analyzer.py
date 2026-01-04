from typing import Dict, List
from .arabic_nlp import split_sentences, tokenize_arabic, remove_stopwords, DEFAULT_STOPWORDS, normalize_arabic

def analyze_arabic_text(text: str) -> Dict:
    sents = split_sentences(text)
    tokens = remove_stopwords(tokenize_arabic(text), DEFAULT_STOPWORDS)
    if not tokens:
        return {
            "difficulty": "غير محدد",
            "metrics": {},
            "difficult_words": [],
            "notes": ["لم يتمكن النظام من استخراج كلمات كافية للتحليل."]
        }

    word_count = len(tokens)
    sent_count = max(1, len(sents))
    avg_words_per_sent = word_count / sent_count

    char_lens = [len(w) for w in tokens]
    avg_chars_per_word = sum(char_lens) / len(char_lens)

    unique = set(tokens)
    ttr = len(unique) / max(1, word_count)  # type-token ratio

    # Heuristic score (smaller => easier)
    score = 0.4 * avg_words_per_sent + 0.3 * avg_chars_per_word + 0.3 * (1.0 - ttr) * 20

    if score <= 10.5:
        difficulty = "سهل"
    elif score <= 15.5:
        difficulty = "متوسط"
    else:
        difficulty = "صعب"

    # difficult words: long + rare (appear once)
    freq = {}
    for w in tokens:
        freq[w] = freq.get(w, 0) + 1

    candidates = [w for w in unique if len(w) >= 6 and freq.get(w, 0) == 1]
    candidates.sort(key=lambda w: (-len(w), w))
    difficult_words = candidates[:12]

    # summary bullets (extractive)
    bullets = []
    for s in sents[:8]:
        if len(s) >= 25:
            bullets.append(s.strip())
        if len(bullets) >= 5:
            break

    return {
        "difficulty": difficulty,
        "metrics": {
            "sentences": len(sents),
            "words": word_count,
            "avg_words_per_sentence": round(avg_words_per_sent, 2),
            "avg_chars_per_word": round(avg_chars_per_word, 2),
            "lexical_diversity_ttr": round(ttr, 3),
            "score": round(score, 2)
        },
        "difficult_words": difficult_words,
        "summary_bullets": bullets,
        "notes": [
            "التصنيف تقريبي لمساعدة المعلمة/الطالبة على اختيار نص مناسب.",
            "الكلمات الصعبة هنا تعتمد على الطول والندرة داخل النص نفسه."
        ]
    }
