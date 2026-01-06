"""
Arabic text difficulty analyzer with enhanced linguistic features.
Provides comprehensive readability scoring for educational content.
"""
import json
from typing import Dict, List, Optional, Set
from pathlib import Path

# Import from the new arabic_nlp package
from .arabic_nlp import (
    split_sentences,
    tokenize_arabic,
    remove_stopwords,
    DEFAULT_STOPWORDS,
    normalize_arabic,
    extract_lemma,
    extract_root,
    get_morphological_complexity,
    get_pos,
    is_content_word,
)

# Path to frequency data
FREQUENCY_FILE = Path(__file__).parent.parent / "data" / "resources" / "arabic_frequency.json"

# Lazy-loaded frequency data
_frequency_data: Optional[Dict[str, int]] = None


def _load_frequency_data() -> Dict[str, int]:
    """Load Arabic word frequency data."""
    global _frequency_data
    if _frequency_data is None:
        try:
            with open(FREQUENCY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Filter out metadata keys
                _frequency_data = {k: v for k, v in data.items()
                                   if not k.startswith('_')}
        except (FileNotFoundError, json.JSONDecodeError):
            _frequency_data = {}
    return _frequency_data


def get_word_frequency_rank(word: str) -> int:
    """
    Get the frequency rank of a word (lower = more common).
    Returns 5000 if word not found (treated as rare).
    """
    freq_data = _load_frequency_data()
    normalized = normalize_arabic(word)

    # Try exact match
    if word in freq_data:
        return freq_data[word]
    if normalized in freq_data:
        return freq_data[normalized]

    # Try lemma
    lemma = extract_lemma(word)
    if lemma in freq_data:
        return freq_data[lemma]

    # Word not found - treat as rare
    return 5000


def calculate_vocabulary_frequency_score(tokens: List[str]) -> float:
    """
    Calculate vocabulary frequency score.
    Lower score = more common vocabulary = easier text.

    Returns:
        Float between 0 and 1 (higher = harder vocabulary)
    """
    if not tokens:
        return 0.5

    freq_data = _load_frequency_data()
    if not freq_data:
        return 0.5  # Fallback if no frequency data

    scores = []
    for token in tokens:
        rank = get_word_frequency_rank(token)
        # Normalize rank to 0-1 scale (log scale)
        # Rank 1 = 0, Rank 5000 = 1
        import math
        normalized_score = min(1.0, math.log10(rank + 1) / math.log10(5001))
        scores.append(normalized_score)

    return sum(scores) / len(scores) if scores else 0.5


def calculate_morphological_complexity_score(tokens: List[str]) -> float:
    """
    Calculate average morphological complexity of tokens.

    Returns:
        Float between 0 and 1 (higher = more complex)
    """
    if not tokens:
        return 0.0

    complexities = [get_morphological_complexity(token) for token in tokens[:100]]  # Limit for performance
    return sum(complexities) / len(complexities) if complexities else 0.0


def calculate_syntactic_complexity_score(sentences: List[str]) -> float:
    """
    Calculate syntactic complexity based on sentence structure.

    Returns:
        Float between 0 and 1 (higher = more complex)
    """
    if not sentences:
        return 0.0

    scores = []
    for sent in sentences[:20]:  # Limit for performance
        # Count clause markers
        clause_markers = ['الذي', 'التي', 'الذين', 'حيث', 'لأن', 'إذا', 'عندما', 'بينما']
        clause_count = sum(1 for marker in clause_markers if marker in sent)

        # Count punctuation (indicates complex structure)
        punct_count = sent.count('،') + sent.count(',') + sent.count(':') + sent.count('؛')

        # Sentence length factor
        words = tokenize_arabic(sent)
        length_factor = min(1.0, len(words) / 30)  # Normalize to 30 words

        # Combine factors
        sent_score = min(1.0, (clause_count * 0.15 + punct_count * 0.1 + length_factor * 0.3))
        scores.append(sent_score)

    return sum(scores) / len(scores) if scores else 0.0


def calculate_technical_density_score(tokens: List[str], freq_data: Optional[Dict] = None) -> float:
    """
    Calculate density of technical/domain-specific terms.

    Returns:
        Float between 0 and 1 (higher = more technical)
    """
    if not tokens:
        return 0.0

    # Words with rank > 2000 are considered more technical/specialized
    freq_data = freq_data or _load_frequency_data()
    technical_count = 0

    for token in tokens:
        rank = get_word_frequency_rank(token)
        if rank > 2000:
            technical_count += 1

    return min(1.0, technical_count / max(1, len(tokens)))


def identify_difficult_words(text: str, limit: int = 15) -> List[Dict]:
    """
    Identify difficult words with explanations.

    Returns:
        List of dicts with word info and difficulty reasons
    """
    tokens = remove_stopwords(tokenize_arabic(text), DEFAULT_STOPWORDS)

    # Count frequencies in text
    text_freq = {}
    for token in tokens:
        text_freq[token] = text_freq.get(token, 0) + 1

    difficult = []
    seen_lemmas: Set[str] = set()

    for token in set(tokens):
        lemma = extract_lemma(token)

        # Skip if we've already seen this lemma
        if lemma in seen_lemmas:
            continue

        reasons = []
        difficulty_score = 0.0

        # 1. Low corpus frequency
        rank = get_word_frequency_rank(token)
        if rank > 3000:
            reasons.append("كلمة نادرة الاستخدام")
            difficulty_score += 0.3
        elif rank > 1500:
            reasons.append("كلمة غير شائعة")
            difficulty_score += 0.15

        # 2. Long word
        if len(token) >= 8:
            reasons.append("كلمة طويلة")
            difficulty_score += 0.2
        elif len(token) >= 6:
            difficulty_score += 0.1

        # 3. Morphological complexity
        morph_complexity = get_morphological_complexity(token)
        if morph_complexity >= 0.5:
            reasons.append("تركيب صرفي معقد")
            difficulty_score += 0.2

        # 4. Technical term (appears once and is not common)
        if text_freq.get(token, 0) == 1 and rank > 1000:
            reasons.append("مصطلح تخصصي")
            difficulty_score += 0.15

        # 5. Content word check (nouns/verbs are more important)
        if is_content_word(token):
            difficulty_score += 0.05

        # Only include if sufficiently difficult
        if difficulty_score >= 0.4 and reasons:
            seen_lemmas.add(lemma)
            difficult.append({
                'word': token,
                'lemma': lemma,
                'root': extract_root(token),
                'reasons': reasons,
                'score': round(difficulty_score, 2),
                'frequency_rank': rank
            })

    # Sort by difficulty score
    difficult.sort(key=lambda x: -x['score'])
    return difficult[:limit]


def analyze_arabic_text(text: str) -> Dict:
    """
    Comprehensive Arabic text difficulty analysis.

    Returns a dictionary with:
    - difficulty: Overall difficulty rating (سهل/متوسط/صعب)
    - metrics: Detailed numerical metrics
    - difficulty_factors: Breakdown of difficulty components
    - difficult_words: List of challenging vocabulary
    - summary_bullets: Key sentences from the text
    - notes: Analysis notes
    """
    sentences = split_sentences(text)
    tokens = remove_stopwords(tokenize_arabic(text), DEFAULT_STOPWORDS)

    if not tokens:
        return {
            "difficulty": "غير محدد",
            "metrics": {},
            "difficulty_factors": {},
            "difficult_words": [],
            "summary_bullets": [],
            "notes": ["لم يتمكن النظام من استخراج كلمات كافية للتحليل."]
        }

    # === Basic Metrics ===
    word_count = len(tokens)
    sent_count = max(1, len(sentences))
    avg_words_per_sent = word_count / sent_count

    char_lens = [len(w) for w in tokens]
    avg_chars_per_word = sum(char_lens) / len(char_lens)

    unique_tokens = set(tokens)
    ttr = len(unique_tokens) / max(1, word_count)  # Type-Token Ratio

    # === Enhanced Difficulty Factors ===

    # 1. Sentence length factor (normalized 0-1)
    sentence_length_score = min(1.0, avg_words_per_sent / 25)

    # 2. Word length factor (normalized 0-1)
    word_length_score = min(1.0, (avg_chars_per_word - 3) / 5)

    # 3. Vocabulary diversity (inverted TTR - lower diversity = easier)
    diversity_score = 1.0 - ttr

    # 4. Vocabulary frequency score
    vocab_freq_score = calculate_vocabulary_frequency_score(tokens)

    # 5. Morphological complexity
    morph_score = calculate_morphological_complexity_score(tokens[:100])

    # 6. Syntactic complexity
    syntax_score = calculate_syntactic_complexity_score(sentences)

    # 7. Technical density
    tech_score = calculate_technical_density_score(tokens)

    # === Weighted Final Score ===
    # Weights tuned for Arabic educational content
    final_score = (
        0.18 * sentence_length_score +
        0.12 * word_length_score +
        0.10 * diversity_score +
        0.25 * vocab_freq_score +       # Vocabulary frequency is most important
        0.15 * morph_score +
        0.12 * syntax_score +
        0.08 * tech_score
    )

    # Scale to 0-20 for compatibility with old thresholds
    scaled_score = final_score * 20

    # === Difficulty Classification ===
    if scaled_score <= 8:
        difficulty = "سهل"
        difficulty_description = "مناسب للمراحل الابتدائية"
    elif scaled_score <= 13:
        difficulty = "متوسط"
        difficulty_description = "مناسب للمراحل المتوسطة"
    else:
        difficulty = "صعب"
        difficulty_description = "مناسب للمراحل الإعدادية والثانوية"

    # === Difficult Words ===
    difficult_words_data = identify_difficult_words(text, limit=12)
    difficult_words = [d['word'] for d in difficult_words_data]

    # === Summary Bullets (extractive) ===
    bullets = []
    for s in sentences[:10]:
        if len(s) >= 25:
            bullets.append(s.strip())
        if len(bullets) >= 5:
            break

    # === POS Distribution (for insights) ===
    pos_counts = {}
    for token in tokens[:200]:  # Limit for performance
        pos = get_pos(token)
        pos_name = pos.value
        pos_counts[pos_name] = pos_counts.get(pos_name, 0) + 1

    return {
        "difficulty": difficulty,
        "difficulty_description": difficulty_description,
        "metrics": {
            "sentences": len(sentences),
            "words": word_count,
            "unique_words": len(unique_tokens),
            "avg_words_per_sentence": round(avg_words_per_sent, 2),
            "avg_chars_per_word": round(avg_chars_per_word, 2),
            "lexical_diversity_ttr": round(ttr, 3),
            "score": round(scaled_score, 2)
        },
        "difficulty_factors": {
            "sentence_length": round(sentence_length_score, 3),
            "word_length": round(word_length_score, 3),
            "vocabulary_diversity": round(diversity_score, 3),
            "vocabulary_frequency": round(vocab_freq_score, 3),
            "morphological_complexity": round(morph_score, 3),
            "syntactic_complexity": round(syntax_score, 3),
            "technical_density": round(tech_score, 3)
        },
        "pos_distribution": pos_counts,
        "difficult_words": difficult_words,
        "difficult_words_details": difficult_words_data[:8],  # Detailed info for top 8
        "summary_bullets": bullets,
        "notes": [
            "التصنيف يعتمد على تحليل لغوي متقدم للنص.",
            f"درجة الصعوبة الإجمالية: {round(scaled_score, 1)} من 20",
            "الكلمات الصعبة محددة بناءً على التردد والتعقيد الصرفي."
        ]
    }


def get_readability_summary(text: str) -> str:
    """
    Get a brief Arabic readability summary.

    Returns:
        A one-line summary of text difficulty
    """
    analysis = analyze_arabic_text(text)
    difficulty = analysis['difficulty']
    word_count = analysis['metrics'].get('words', 0)
    score = analysis['metrics'].get('score', 0)

    return f"مستوى الصعوبة: {difficulty} | عدد الكلمات: {word_count} | الدرجة: {score}/20"


def compare_texts_difficulty(text1: str, text2: str) -> Dict:
    """
    Compare difficulty of two texts.

    Returns:
        Dict with comparison results
    """
    analysis1 = analyze_arabic_text(text1)
    analysis2 = analyze_arabic_text(text2)

    score1 = analysis1['metrics'].get('score', 0)
    score2 = analysis2['metrics'].get('score', 0)

    if score1 < score2:
        easier = "النص الأول"
        harder = "النص الثاني"
    elif score2 < score1:
        easier = "النص الثاني"
        harder = "النص الأول"
    else:
        easier = "متساويان"
        harder = "متساويان"

    return {
        "text1_difficulty": analysis1['difficulty'],
        "text1_score": score1,
        "text2_difficulty": analysis2['difficulty'],
        "text2_score": score2,
        "easier_text": easier,
        "harder_text": harder,
        "score_difference": round(abs(score1 - score2), 2)
    }
