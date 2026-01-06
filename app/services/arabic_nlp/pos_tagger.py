"""
Part-of-Speech tagging for Arabic text.
Uses CAMeL Tools with fallback to pattern-based heuristics.
"""
import re
import functools
from typing import List, Tuple, Optional, Set
from enum import Enum


class ArabicPOS(Enum):
    """Arabic Part-of-Speech tags."""
    NOUN = "اسم"
    VERB = "فعل"
    ADJ = "صفة"
    ADV = "ظرف"
    PREP = "حرف جر"
    CONJ = "حرف عطف"
    PRON = "ضمير"
    DET = "أداة تعريف"
    PARTICLE = "أداة"
    NUM = "عدد"
    PUNCT = "علامة ترقيم"
    UNKNOWN = "غير معروف"


# Lazy-loaded CAMeL tagger
_camel_tagger = None


def _get_camel_tagger():
    """Lazy-load CAMeL POS tagger."""
    global _camel_tagger
    if _camel_tagger is None:
        try:
            from camel_tools.tagger.default import DefaultTagger
            _camel_tagger = DefaultTagger.pretrained()
        except (ImportError, Exception):
            pass
    return _camel_tagger


# === Pattern-based POS Detection ===

# Verb patterns
VERB_PATTERNS = [
    # Past tense patterns
    re.compile(r'^(فعل|كتب|درس|قرأ|عمل|قال|ذهب|جاء|رأى|سمع|أخذ|وجد)'),
    re.compile(r'[يتنأ][\u0600-\u06FF]{2,}ون$'),  # Present plural masculine
    re.compile(r'[يتنأ][\u0600-\u06FF]{2,}ن$'),  # Present plural feminine
    re.compile(r'^[يتنأ][\u0600-\u06FF]+$'),  # Present tense
    re.compile(r'[\u0600-\u06FF]+وا$'),  # Past plural
    re.compile(r'[\u0600-\u06FF]+ت$'),  # Past feminine or 2nd person
]

# Common verb stems (high frequency)
COMMON_VERB_STEMS = {
    'يكون', 'تكون', 'كان', 'كانت', 'يكن',
    'يعمل', 'تعمل', 'عمل', 'عملت',
    'يقول', 'تقول', 'قال', 'قالت',
    'يجعل', 'تجعل', 'جعل', 'جعلت',
    'يأخذ', 'تأخذ', 'أخذ', 'أخذت',
    'يعطي', 'تعطي', 'أعطى', 'أعطت',
    'يجد', 'تجد', 'وجد', 'وجدت',
    'يرى', 'ترى', 'رأى', 'رأت',
    'يذهب', 'تذهب', 'ذهب', 'ذهبت',
    'يأتي', 'تأتي', 'أتى', 'أتت', 'جاء', 'جاءت',
    'يستخدم', 'تستخدم', 'استخدم', 'استخدمت',
    'يحتوي', 'تحتوي', 'احتوى', 'احتوت',
    'يتكون', 'تتكون', 'تكوّن', 'تكونت',
    'يتميز', 'تتميز', 'تميز', 'تميزت',
    'يعتبر', 'تعتبر', 'اعتبر', 'اعتبرت',
    'يؤدي', 'تؤدي', 'أدى', 'أدت',
    'يسبب', 'تسبب', 'سبب', 'سببت',
    'ينتج', 'تنتج', 'نتج', 'نتجت',
}

# Noun patterns
NOUN_SUFFIXES = {'ة', 'ات', 'ون', 'ين', 'ان', 'ية', 'اء', 'ي'}
NOUN_PATTERNS = [
    re.compile(r'^ال[\u0600-\u06FF]+'),  # Definite nouns
    re.compile(r'[\u0600-\u06FF]+ية$'),  # Nisba adjective/noun
    re.compile(r'[\u0600-\u06FF]+ات$'),  # Sound feminine plural
]

# Adjective patterns
ADJ_PATTERNS = [
    re.compile(r'^[\u0600-\u06FF]+ي$'),  # Nisba
    re.compile(r'^[\u0600-\u06FF]+ية$'),  # Nisba feminine
    re.compile(r'^(كبير|صغير|جديد|قديم|طويل|قصير|جميل|سريع|بطيء)'),
]

# Preposition set
PREPOSITIONS = {
    'في', 'من', 'إلى', 'الى', 'على', 'عن', 'مع', 'ب', 'ل', 'ك',
    'حتى', 'منذ', 'خلال', 'عبر', 'بين', 'ضمن', 'فوق', 'تحت',
    'أمام', 'خلف', 'حول', 'نحو', 'عند', 'لدى', 'دون', 'بدون',
}

# Conjunction set
CONJUNCTIONS = {
    'و', 'ف', 'ثم', 'أو', 'أم', 'بل', 'لكن', 'إن', 'أن',
    'لأن', 'كي', 'حتى', 'إذا', 'لو', 'كما', 'بينما', 'حين',
}

# Pronoun set
PRONOUNS = {
    'أنا', 'أنت', 'أنتِ', 'أنتم', 'أنتن', 'نحن',
    'هو', 'هي', 'هم', 'هن', 'هما',
    'هذا', 'هذه', 'ذلك', 'تلك', 'هؤلاء', 'أولئك',
    'الذي', 'التي', 'الذين', 'اللاتي',
}

# Particle set
PARTICLES = {
    'قد', 'لقد', 'سوف', 'لن', 'لم', 'ما', 'لا', 'إلا',
    'هل', 'أ', 'ليس', 'ليست', 'نعم', 'كلا', 'بلى',
}

# Adverb set
ADVERBS = {
    'جدا', 'جداً', 'كثيرا', 'كثيراً', 'قليلا', 'قليلاً',
    'دائما', 'دائماً', 'أبدا', 'أبداً', 'فقط', 'أيضا', 'أيضاً',
    'الآن', 'غدا', 'أمس', 'هنا', 'هناك', 'حيث',
    'معا', 'معاً', 'سريعا', 'سريعاً', 'تماما', 'تماماً',
}


@functools.lru_cache(maxsize=10000)
def get_pos(word: str) -> ArabicPOS:
    """
    Get the Part-of-Speech tag for a single word.

    Args:
        word: Arabic word

    Returns:
        ArabicPOS enum value
    """
    word = word.strip()
    if not word:
        return ArabicPOS.UNKNOWN

    # Try CAMeL Tools first
    tagger = _get_camel_tagger()
    if tagger:
        try:
            # Tag single word in sentence context
            tags = tagger.tag([word])
            if tags:
                return _map_camel_pos(tags[0])
        except Exception:
            pass

    # Fallback to rule-based
    return _get_pos_heuristic(word)


def _map_camel_pos(camel_tag: str) -> ArabicPOS:
    """Map CAMeL POS tag to our ArabicPOS enum."""
    tag = camel_tag.upper()

    if tag.startswith('NOUN') or tag.startswith('N'):
        return ArabicPOS.NOUN
    elif tag.startswith('VERB') or tag.startswith('V'):
        return ArabicPOS.VERB
    elif tag.startswith('ADJ') or tag.startswith('A'):
        return ArabicPOS.ADJ
    elif tag.startswith('ADV'):
        return ArabicPOS.ADV
    elif tag.startswith('PREP') or tag.startswith('P'):
        return ArabicPOS.PREP
    elif tag.startswith('CONJ') or tag.startswith('C'):
        return ArabicPOS.CONJ
    elif tag.startswith('PRON'):
        return ArabicPOS.PRON
    elif tag.startswith('DET'):
        return ArabicPOS.DET
    elif tag.startswith('PART'):
        return ArabicPOS.PARTICLE
    elif tag.startswith('NUM'):
        return ArabicPOS.NUM
    elif tag.startswith('PUNCT'):
        return ArabicPOS.PUNCT
    else:
        return ArabicPOS.UNKNOWN


def _get_pos_heuristic(word: str) -> ArabicPOS:
    """Rule-based POS tagging fallback."""
    from .core import normalize_arabic

    # Normalize for matching
    norm = normalize_arabic(word)

    # Check closed classes first (high precision)
    if word in PREPOSITIONS or norm in PREPOSITIONS:
        return ArabicPOS.PREP

    if word in CONJUNCTIONS or norm in CONJUNCTIONS:
        return ArabicPOS.CONJ

    if word in PRONOUNS or norm in PRONOUNS:
        return ArabicPOS.PRON

    if word in PARTICLES or norm in PARTICLES:
        return ArabicPOS.PARTICLE

    if word in ADVERBS or norm in ADVERBS:
        return ArabicPOS.ADV

    # Check for verbs
    if word in COMMON_VERB_STEMS or norm in COMMON_VERB_STEMS:
        return ArabicPOS.VERB

    for pattern in VERB_PATTERNS:
        if pattern.search(norm):
            return ArabicPOS.VERB

    # Check for adjectives
    for pattern in ADJ_PATTERNS:
        if pattern.search(norm):
            return ArabicPOS.ADJ

    # Check for nouns
    for pattern in NOUN_PATTERNS:
        if pattern.search(word):  # Use original for ال detection
            return ArabicPOS.NOUN

    # Default: assume noun (most common open class)
    if len(word) >= 3:
        return ArabicPOS.NOUN

    return ArabicPOS.UNKNOWN


def tag_sentence(sentence: str) -> List[Tuple[str, ArabicPOS]]:
    """
    Tag all words in a sentence with POS.

    Args:
        sentence: Arabic sentence

    Returns:
        List of (word, POS) tuples
    """
    from .core import tokenize_arabic

    tokens = tokenize_arabic(sentence, normalize=False)

    # Try CAMeL for full sentence (better context)
    tagger = _get_camel_tagger()
    if tagger:
        try:
            tags = tagger.tag(tokens)
            return [(tokens[i], _map_camel_pos(tags[i]))
                    for i in range(len(tokens))]
        except Exception:
            pass

    # Fallback: tag word by word
    return [(token, get_pos(token)) for token in tokens]


def extract_nouns(sentence: str) -> List[str]:
    """Extract only nouns from a sentence."""
    tagged = tag_sentence(sentence)
    return [word for word, pos in tagged if pos == ArabicPOS.NOUN]


def extract_verbs(sentence: str) -> List[str]:
    """Extract only verbs from a sentence."""
    tagged = tag_sentence(sentence)
    return [word for word, pos in tagged if pos == ArabicPOS.VERB]


def extract_adjectives(sentence: str) -> List[str]:
    """Extract only adjectives from a sentence."""
    tagged = tag_sentence(sentence)
    return [word for word, pos in tagged if pos == ArabicPOS.ADJ]


def extract_content_words(sentence: str) -> List[str]:
    """Extract content words (nouns, verbs, adjectives) from a sentence."""
    content_pos = {ArabicPOS.NOUN, ArabicPOS.VERB, ArabicPOS.ADJ}
    tagged = tag_sentence(sentence)
    return [word for word, pos in tagged if pos in content_pos]


def is_content_word(word: str) -> bool:
    """Check if a word is a content word (noun, verb, adjective)."""
    pos = get_pos(word)
    return pos in {ArabicPOS.NOUN, ArabicPOS.VERB, ArabicPOS.ADJ}


def is_function_word(word: str) -> bool:
    """Check if a word is a function word (preposition, conjunction, etc.)."""
    pos = get_pos(word)
    return pos in {ArabicPOS.PREP, ArabicPOS.CONJ, ArabicPOS.PRON,
                   ArabicPOS.DET, ArabicPOS.PARTICLE}


def get_pos_distribution(text: str) -> dict:
    """
    Get the distribution of POS tags in a text.

    Returns:
        Dict mapping POS to count
    """
    from .core import tokenize_arabic

    tokens = tokenize_arabic(text, normalize=False)
    distribution = {}

    for token in tokens:
        pos = get_pos(token)
        pos_name = pos.value
        distribution[pos_name] = distribution.get(pos_name, 0) + 1

    return distribution


def filter_by_pos(tokens: List[str], allowed_pos: Set[ArabicPOS]) -> List[str]:
    """Filter tokens to only include specified POS types."""
    return [token for token in tokens if get_pos(token) in allowed_pos]


def get_nouns_and_adjectives(sentence: str) -> List[str]:
    """Extract nouns and adjectives (useful for key terms)."""
    tagged = tag_sentence(sentence)
    return [word for word, pos in tagged
            if pos in {ArabicPOS.NOUN, ArabicPOS.ADJ}]
