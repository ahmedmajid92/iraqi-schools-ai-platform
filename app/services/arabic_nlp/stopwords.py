"""
Extended Arabic stopword list with categorization.
Contains 200+ common Arabic stopwords organized by grammatical category.
"""
from typing import Set, List, Optional

# === Pronouns (ضمائر) ===
PRONOUNS: Set[str] = {
    # Personal pronouns - separate
    "أنا", "أنت", "أنتِ", "أنتم", "أنتن", "أنتما",
    "هو", "هي", "هم", "هن", "هما",
    "نحن",
    # Object pronouns
    "إياي", "إياك", "إياكِ", "إياكم", "إياكن", "إياكما",
    "إياه", "إياها", "إياهم", "إياهن", "إياهما",
    "إيانا",
}

# === Prepositions (حروف الجر) ===
PREPOSITIONS: Set[str] = {
    "في", "من", "إلى", "الى", "على", "عن",
    "مع", "ل", "لـ", "ب", "بـ", "ك", "كـ",
    "حتى", "منذ", "مذ", "خلال", "عبر",
    "بين", "ضمن", "فوق", "تحت", "أمام", "خلف", "وراء",
    "حول", "ضد", "نحو", "عند", "لدى", "لدي",
    "دون", "بدون", "سوى", "عدا", "خلا", "حاشا",
    "قرب", "بعد", "قبل", "داخل", "خارج",
    "أثناء", "طوال", "إزاء", "تجاه", "حيال",
}

# === Conjunctions (حروف العطف والربط) ===
CONJUNCTIONS: Set[str] = {
    # Coordinating
    "و", "ف", "فـ", "ثم", "أو", "أم", "بل", "لا", "لكن",
    # Subordinating
    "أن", "إن", "أنّ", "إنّ", "لأن", "لأنّ",
    "كي", "لكي", "حتى", "إذا", "إذ", "لو", "لولا", "لوما",
    "كما", "كأن", "كأنّ", "كأنما", "لعل", "لعلّ",
    "مع أن", "مع أنّ", "رغم أن", "رغم أنّ",
    "بينما", "حين", "حينما", "عندما", "لما", "كلما",
    "حيث", "حيثما", "أينما", "متى", "متىما",
}

# === Demonstratives (أسماء الإشارة) ===
DEMONSTRATIVES: Set[str] = {
    "هذا", "هذه", "هذان", "هاتان", "هؤلاء",
    "ذلك", "تلك", "ذاك", "تيك",
    "ذانك", "تانك", "أولئك",
    "هنا", "هناك", "هنالك", "ثم", "ثمة", "ثمت",
}

# === Relative Pronouns (أسماء الموصول) ===
RELATIVES: Set[str] = {
    "الذي", "التي", "اللذان", "اللتان",
    "الذين", "اللاتي", "اللائي", "اللواتي",
    "ما", "من", "أي", "أيّ",
    "والذي", "والتي", "والذين", "واللاتي",
}

# === Interrogatives (أدوات الاستفهام) ===
INTERROGATIVES: Set[str] = {
    "ما", "ماذا", "من", "منذا",
    "كيف", "كيفما", "أين", "أينما",
    "متى", "متىما", "أيان", "أنى",
    "لماذا", "لم", "لِمَ", "علام", "عمّ", "فيم", "بم", "إلام",
    "هل", "أ", "أليس", "ألا",
    "كم", "أي", "أيّ",
}

# === Auxiliary Verbs (أفعال ناقصة وأدوات) ===
AUXILIARIES: Set[str] = {
    # كان وأخواتها
    "كان", "كانت", "كانوا", "كنّ", "كنت", "كنتم", "كنا",
    "يكون", "تكون", "أكون", "نكون", "يكونون", "تكونين",
    "ليس", "ليست", "ليسوا", "لسن", "لست", "لسنا",
    "أصبح", "أصبحت", "أصبحوا", "يصبح", "تصبح",
    "أمسى", "أمست", "يمسي", "تمسي",
    "أضحى", "أضحت", "يضحى", "تضحى",
    "ظل", "ظلت", "ظلوا", "يظل", "تظل",
    "بات", "باتت", "باتوا", "يبيت", "تبيت",
    "صار", "صارت", "صاروا", "يصير", "تصير",
    "مازال", "مازالت", "مازالوا", "لازال", "لازالت",
    "مادام", "مادامت", "مافتئ", "مافتئت",
    "ماانفك", "ماانفكت", "مابرح", "مابرحت",
}

# === Common Adverbs (ظروف شائعة) ===
ADVERBS: Set[str] = {
    # Time
    "الآن", "أمس", "غدا", "غداً", "اليوم", "البارحة",
    "دائما", "دائماً", "أبدا", "أبداً", "قط",
    "حالا", "حالاً", "فورا", "فوراً", "توا", "تواً",
    "سابقا", "سابقاً", "لاحقا", "لاحقاً",
    "أحيانا", "أحياناً", "نادرا", "نادراً", "غالبا", "غالباً",
    "مؤخرا", "مؤخراً", "أخيرا", "أخيراً", "أولا", "أولاً",
    # Manner
    "جدا", "جداً", "كثيرا", "كثيراً", "قليلا", "قليلاً",
    "سريعا", "سريعاً", "بطيئا", "بطيئاً",
    "تماما", "تماماً", "تقريبا", "تقريباً", "نسبيا", "نسبياً",
    "حقا", "حقاً", "فعلا", "فعلاً", "واقعا", "واقعاً",
    "معا", "معاً", "سويا", "سوياً", "وحده", "وحدها",
    "أيضا", "أيضاً", "كذلك", "هكذا", "كذا",
    # Place
    "هنا", "هناك", "ثم", "حيث", "فوق", "تحت", "أمام", "خلف",
    # Quantity
    "فقط", "فحسب", "بالكاد", "تقريبا", "حوالي", "نحو", "قرابة",
}

# === Negation Particles (أدوات النفي) ===
NEGATION: Set[str] = {
    "لا", "لم", "لن", "ما", "لات", "إن",  # إن النافية
    "ليس", "ليست", "ليسوا", "لسن", "لست", "لسنا",
    "غير", "بدون", "عدم", "سوى",
    "لما",  # لم + ما
}

# === Affirmation & Emphasis (أدوات التوكيد) ===
AFFIRMATION: Set[str] = {
    "إن", "إنّ", "أن", "أنّ",
    "قد", "لقد",
    "نعم", "بلى", "أجل", "إي",
    "حقا", "حقاً", "فعلا", "فعلاً", "بالفعل",
    "بالتأكيد", "طبعا", "طبعاً", "يقينا", "يقيناً",
    "لا شك", "لاشك", "بلاشك",
}

# === Exception Particles (أدوات الاستثناء) ===
EXCEPTION: Set[str] = {
    "إلا", "غير", "سوى", "خلا", "عدا", "حاشا",
    "ما خلا", "ما عدا", "ليس", "لا يكون",
}

# === Condition Particles (أدوات الشرط) ===
CONDITION: Set[str] = {
    "إن", "إذا", "لو", "لولا", "لوما",
    "من", "ما", "مهما", "متى", "أين", "أينما",
    "حيثما", "كيفما", "أي", "أنى", "أيان",
}

# === Common Nouns Acting as Function Words ===
FUNCTION_NOUNS: Set[str] = {
    "كل", "جميع", "بعض", "معظم", "أغلب", "أكثر", "أقل",
    "نفس", "ذات", "عين", "كلا", "كلتا",
    "غير", "سوى", "مثل", "شبه", "نحو", "حوالي",
    "خاصة", "عامة", "خصوصا", "عموما",
    "أول", "آخر", "ثان", "ثالث",
    "شيء", "أمر", "حال", "نوع", "شكل",
    "طريق", "طريقة", "سبيل", "وجه", "نحو",
    "حين", "وقت", "أثناء", "خلال",
    "بداية", "نهاية", "أساس", "صدد",
}

# === Common Verbs Acting as Function Words ===
FUNCTION_VERBS: Set[str] = {
    # Modal-like
    "يمكن", "تمكن", "أمكن", "استطاع", "يستطيع",
    "يجب", "وجب", "ينبغي",
    "يريد", "أراد", "يرغب", "رغب",
    # Aspectual
    "بدأ", "يبدأ", "شرع", "أخذ", "جعل",
    "انتهى", "توقف", "استمر", "ظل", "بقي",
    # Reporting
    "قال", "يقول", "ذكر", "يذكر", "أشار",
    "أوضح", "بين", "يبين", "أفاد", "يفيد",
}

# === Combined Default Stopwords ===
DEFAULT_STOPWORDS: Set[str] = (
    PRONOUNS |
    PREPOSITIONS |
    CONJUNCTIONS |
    DEMONSTRATIVES |
    RELATIVES |
    INTERROGATIVES |
    AUXILIARIES |
    ADVERBS |
    NEGATION |
    AFFIRMATION |
    EXCEPTION |
    CONDITION |
    FUNCTION_NOUNS
)

# === All Stopwords (including function verbs) ===
ALL_STOPWORDS: Set[str] = DEFAULT_STOPWORDS | FUNCTION_VERBS


def get_stopwords(
    categories: Optional[List[str]] = None,
    include_verbs: bool = False
) -> Set[str]:
    """
    Get stopwords, optionally filtered by category.

    Args:
        categories: List of category names to include. If None, returns default set.
                   Valid categories: 'pronouns', 'prepositions', 'conjunctions',
                   'demonstratives', 'relatives', 'interrogatives', 'auxiliaries',
                   'adverbs', 'negation', 'affirmation', 'exception', 'condition',
                   'function_nouns', 'function_verbs'
        include_verbs: Whether to include function verbs in default set

    Returns:
        Set of stopwords
    """
    if categories is None:
        return ALL_STOPWORDS if include_verbs else DEFAULT_STOPWORDS

    category_map = {
        'pronouns': PRONOUNS,
        'prepositions': PREPOSITIONS,
        'conjunctions': CONJUNCTIONS,
        'demonstratives': DEMONSTRATIVES,
        'relatives': RELATIVES,
        'interrogatives': INTERROGATIVES,
        'auxiliaries': AUXILIARIES,
        'adverbs': ADVERBS,
        'negation': NEGATION,
        'affirmation': AFFIRMATION,
        'exception': EXCEPTION,
        'condition': CONDITION,
        'function_nouns': FUNCTION_NOUNS,
        'function_verbs': FUNCTION_VERBS,
    }

    result = set()
    for cat in categories:
        if cat in category_map:
            result |= category_map[cat]

    return result


def remove_stopwords(
    tokens: List[str],
    stopwords: Optional[Set[str]] = None,
    min_length: int = 2
) -> List[str]:
    """
    Remove stopwords from a list of tokens.

    Args:
        tokens: List of tokens to filter
        stopwords: Set of stopwords to remove. If None, uses DEFAULT_STOPWORDS.
        min_length: Minimum token length to keep (default 2)

    Returns:
        Filtered list of tokens
    """
    sw = stopwords if stopwords is not None else DEFAULT_STOPWORDS
    return [w for w in tokens if w not in sw and len(w) >= min_length]


def is_stopword(word: str, stopwords: Optional[Set[str]] = None) -> bool:
    """Check if a word is a stopword."""
    sw = stopwords if stopwords is not None else DEFAULT_STOPWORDS
    return word in sw
