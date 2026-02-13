"""
Arabic morphological analysis module.
Provides root extraction, lemmatization, and morphological feature analysis.

Uses CAMeL Tools when available, with fallback to PyArabic and simple heuristics.
"""
import functools
from typing import Dict, List, Optional, Tuple, Set

# Lazy-loaded analyzers
_camel_analyzer = None
_camel_db = None
_camel_disambiguator = None
_pyarabic_available = None


def _check_pyarabic() -> bool:
    """Check if PyArabic is available."""
    global _pyarabic_available
    if _pyarabic_available is None:
        try:
            import pyarabic.araby as araby
            _pyarabic_available = True
        except ImportError:
            _pyarabic_available = False
    return _pyarabic_available


def _get_camel_analyzer():
    """Lazy-load CAMeL morphological analyzer."""
    global _camel_analyzer, _camel_db
    if _camel_analyzer is None:
        try:
            from camel_tools.morphology.analyzer import Analyzer
            from camel_tools.morphology.database import MorphologyDB
            _camel_db = MorphologyDB.builtin_db()
            _camel_analyzer = Analyzer(_camel_db)
        except (ImportError, Exception):
            pass
    return _camel_analyzer


def _get_camel_disambiguator():
    """Lazy-load CAMeL disambiguator for context-aware analysis."""
    global _camel_disambiguator
    if _camel_disambiguator is None:
        try:
            from camel_tools.disambig.mle import MLEDisambiguator
            _camel_disambiguator = MLEDisambiguator.pretrained()
        except (ImportError, Exception):
            pass
    return _camel_disambiguator


# === Common Arabic Roots Database ===
# Most frequent trilateral roots in Arabic
COMMON_ROOTS: Set[str] = {
    # Knowledge & Learning
    'علم', 'درس', 'فهم', 'عرف', 'قرأ', 'كتب', 'حفظ', 'ذكر', 'فكر', 'نظر',
    # Actions
    'عمل', 'فعل', 'صنع', 'جعل', 'خلق', 'بنى', 'قام', 'جلس', 'مشى', 'ذهب',
    'جاء', 'أتى', 'رجع', 'خرج', 'دخل', 'نزل', 'صعد', 'وقف', 'سار', 'قاد',
    # Speaking & Communication
    'قول', 'كلم', 'نطق', 'سأل', 'جاب', 'خبر', 'شرح', 'وصف', 'بين', 'عبر',
    # Life & Existence
    'حيا', 'موت', 'ولد', 'نما', 'كبر', 'عاش', 'بقى', 'وجد', 'كان', 'صار',
    # Nature & Elements
    'ماء', 'نار', 'أرض', 'سماء', 'شمس', 'قمر', 'نجم', 'بحر', 'نهر', 'جبل',
    # Numbers & Counting
    'عدد', 'حسب', 'قسم', 'جمع', 'ضرب', 'طرح', 'زاد', 'نقص', 'كثر', 'قلل',
    # Time
    'وقت', 'زمن', 'يوم', 'سنة', 'شهر', 'ساع', 'دقق', 'ثان', 'قدم', 'حدث',
    # Body & Health
    'جسم', 'رأس', 'يدي', 'رجل', 'عين', 'أذن', 'قلب', 'صحة', 'مرض', 'شفى',
    # Emotions & States
    'حبب', 'كره', 'فرح', 'حزن', 'خوف', 'أمن', 'رضى', 'غضب', 'سعد', 'شقى',
    # Society & Relations
    'أهل', 'صحب', 'صدق', 'عدو', 'حكم', 'ملك', 'شعب', 'وطن', 'دول', 'مدن',
    # Science terms
    'كهرب', 'ذرر', 'حرر', 'ضوء', 'صوت', 'طاق', 'قوى', 'حرك', 'سرع', 'بطء',
}


@functools.lru_cache(maxsize=10000)
def extract_root(word: str) -> Optional[str]:
    """
    Extract the Arabic root from a word.

    Tries CAMeL Tools first, then PyArabic, then pattern-based heuristics.

    Args:
        word: Arabic word to analyze

    Returns:
        Root string (usually 3 letters) or None if not found
    """
    # Clean the word
    word = word.strip()
    if not word or len(word) < 2:
        return None

    # Try CAMeL Tools first
    analyzer = _get_camel_analyzer()
    if analyzer:
        try:
            analyses = analyzer.analyze(word)
            if analyses:
                # Get the most likely root
                root = analyses[0].get('root', None)
                if root and root != 'NTWS':  # NTWS means "no analysis"
                    return root
        except Exception:
            pass

    # Try PyArabic
    if _check_pyarabic():
        try:
            import pyarabic.araby as araby
            from pyarabic import stem

            # Use ISRI stemmer as approximation
            stemmer = stem.ArabicLightStemmer()
            stemmer.light_stem(word)
            root = stemmer.get_root()
            if root and len(root) >= 2:
                return root
        except Exception:
            pass

    # Fallback: Pattern-based heuristic
    return _extract_root_heuristic(word)


def _extract_root_heuristic(word: str) -> Optional[str]:
    """
    Simple heuristic-based root extraction.
    Removes common prefixes and suffixes to approximate the root.
    """
    from .core import normalize_arabic

    word = normalize_arabic(word)

    # Common prefixes to remove
    prefixes = ['ال', 'و', 'ف', 'ب', 'ك', 'ل', 'لل', 'وال', 'فال', 'بال', 'كال',
                'سي', 'ست', 'سن', 'سا', 'ي', 'ت', 'ن', 'ا', 'است', 'انف', 'افت']

    # Common suffixes to remove
    suffixes = ['ون', 'ين', 'ان', 'ات', 'ة', 'ه', 'ي', 'ها', 'هم', 'هن',
                'كم', 'كن', 'نا', 'تم', 'تن', 'وا', 'ا', 'ت', 'ية', 'ني', 'ك']

    # Remove prefixes
    for prefix in sorted(prefixes, key=len, reverse=True):
        if word.startswith(prefix) and len(word) > len(prefix) + 2:
            word = word[len(prefix):]
            break

    # Remove suffixes
    for suffix in sorted(suffixes, key=len, reverse=True):
        if word.endswith(suffix) and len(word) > len(suffix) + 2:
            word = word[:-len(suffix)]
            break

    # If we have 3-4 consonants left, that's likely the root
    if 2 <= len(word) <= 4:
        return word

    # Try to extract 3 consonants
    consonants = []
    for char in word:
        if char not in 'اوي':  # Skip weak letters
            consonants.append(char)
        if len(consonants) == 3:
            break

    if len(consonants) >= 2:
        return ''.join(consonants[:3])

    return None


@functools.lru_cache(maxsize=10000)
def extract_lemma(word: str) -> str:
    """
    Get the lemma (base/dictionary form) of an Arabic word.

    Args:
        word: Arabic word

    Returns:
        Lemma string (returns original word if lemmatization fails)
    """
    word = word.strip()
    if not word:
        return word

    # Try CAMeL Tools
    analyzer = _get_camel_analyzer()
    if analyzer:
        try:
            analyses = analyzer.analyze(word)
            if analyses:
                lemma = analyses[0].get('lex', None)
                if lemma:
                    return lemma
        except Exception:
            pass

    # Try PyArabic
    if _check_pyarabic():
        try:
            from pyarabic import stem
            stemmer = stem.ArabicLightStemmer()
            stemmer.light_stem(word)
            lemma = stemmer.get_stem()
            if lemma:
                return lemma
        except Exception:
            pass

    # Fallback: Return normalized word
    from .core import normalize_arabic
    return normalize_arabic(word)


@functools.lru_cache(maxsize=5000)
def get_morphological_features(word: str) -> Dict:
    """
    Extract morphological features from an Arabic word.

    Returns dict with keys:
    - root: Trilateral root
    - lemma: Base form
    - pos: Part of speech
    - gender: Masculine/Feminine
    - number: Singular/Dual/Plural
    - person: 1st/2nd/3rd
    - definiteness: Definite/Indefinite
    - has_prefix: Boolean
    - has_suffix: Boolean
    """
    features = {
        'root': None,
        'lemma': word,
        'pos': None,
        'gender': None,
        'number': None,
        'person': None,
        'definiteness': None,
        'has_prefix': False,
        'has_suffix': False,
    }

    word = word.strip()
    if not word:
        return features

    # Try CAMeL Tools for full analysis
    analyzer = _get_camel_analyzer()
    if analyzer:
        try:
            analyses = analyzer.analyze(word)
            if analyses:
                a = analyses[0]  # Take most likely analysis
                features['root'] = a.get('root')
                features['lemma'] = a.get('lex', word)
                features['pos'] = a.get('pos')

                # Map CAMeL features
                gen = a.get('gen')
                if gen:
                    features['gender'] = 'مذكر' if gen == 'm' else 'مؤنث' if gen == 'f' else None

                num = a.get('num')
                if num:
                    num_map = {'s': 'مفرد', 'd': 'مثنى', 'p': 'جمع'}
                    features['number'] = num_map.get(num)

                per = a.get('per')
                if per:
                    per_map = {'1': 'متكلم', '2': 'مخاطب', '3': 'غائب'}
                    features['person'] = per_map.get(per)

                stt = a.get('stt')
                if stt:
                    features['definiteness'] = 'معرفة' if stt == 'd' else 'نكرة' if stt == 'i' else None

                # Check for prefixes/suffixes
                features['has_prefix'] = bool(a.get('prc0') or a.get('prc1') or a.get('prc2'))
                features['has_suffix'] = bool(a.get('enc0') or a.get('suf'))

                return features
        except Exception:
            pass

    # Fallback: Simple heuristics
    features['root'] = extract_root(word)
    features['lemma'] = extract_lemma(word)

    # Simple prefix/suffix detection
    from .core import normalize_arabic
    norm_word = normalize_arabic(word)

    # Check for definite article
    if norm_word.startswith('ال'):
        features['definiteness'] = 'معرفة'
        features['has_prefix'] = True
    else:
        features['definiteness'] = 'نكرة'

    # Check common prefixes
    prefixes = ['و', 'ف', 'ب', 'ك', 'ل', 'س']
    for p in prefixes:
        if norm_word.startswith(p) and len(norm_word) > 3:
            features['has_prefix'] = True
            break

    # Check common suffixes
    if norm_word.endswith(('ون', 'ين', 'ات', 'ان')):
        features['number'] = 'جمع'
        features['has_suffix'] = True
    elif norm_word.endswith('ه') and len(norm_word) > 2:
        features['has_suffix'] = True
    elif norm_word.endswith(('ها', 'هم', 'هن', 'كم', 'نا')):
        features['has_suffix'] = True

    # Simple gender detection
    if norm_word.endswith('ه'):  # Normalized ta-marbuta
        features['gender'] = 'مؤنث'
    elif norm_word.endswith('ات'):
        features['gender'] = 'مؤنث'
        features['number'] = 'جمع'

    return features


# === Curated Word Families ===
# Real Arabic words grouped by root for generating quality distractors
CURATED_WORD_FAMILIES: Dict[str, List[str]] = {
    # Knowledge & Learning
    'علم': ['علم', 'عالم', 'أستاذ', 'تعليم', 'علوم', 'عليم', 'معلومة', 'تعلم', 'معلومات'],
    'درس': ['درس', 'دراسة', 'مدرسة', 'مدرس', 'دارس', 'تدريس', 'دروس'],
    'فهم': ['فهم', 'فاهم', 'مفهوم', 'تفاهم', 'فهيم', 'استفهام'],
    'عرف': ['عرف', 'معرفة', 'تعريف', 'معروف', 'عارف', 'اعتراف'],
    'قرأ': ['قراءة', 'قارئ', 'مقروء', 'قرآن', 'اقرأ'],
    'كتب': ['كتاب', 'كاتب', 'مكتوب', 'كتابة', 'مكتبة', 'كتب', 'مكاتب'],
    'حفظ': ['حفظ', 'حافظ', 'محفوظ', 'حفاظ', 'تحفيظ'],
    'ذكر': ['ذكر', 'ذاكرة', 'تذكر', 'مذكور', 'ذكرى', 'تذكير'],
    'فكر': ['فكر', 'فكرة', 'تفكير', 'مفكر', 'أفكار'],
    'نظر': ['نظر', 'نظرة', 'نظرية', 'منظر', 'ناظر', 'انتظار'],

    # Actions
    'عمل': ['عمل', 'عامل', 'معمل', 'عملية', 'أعمال', 'معامل'],
    'فعل': ['فعل', 'فاعل', 'مفعول', 'فعال', 'أفعال', 'تفاعل'],
    'صنع': ['صنع', 'صناعة', 'مصنع', 'صانع', 'مصنوع'],
    'بنى': ['بناء', 'مبنى', 'بنية', 'باني', 'مباني'],
    'خلق': ['خلق', 'خالق', 'مخلوق', 'خلاق', 'أخلاق'],

    # Speaking & Communication
    'قول': ['قول', 'قائل', 'مقولة', 'أقوال', 'قال'],
    'كلم': ['كلمة', 'كلام', 'متكلم', 'تكلم', 'كلمات'],
    'سأل': ['سؤال', 'سائل', 'مسؤول', 'أسئلة', 'تساؤل'],
    'جاب': ['جواب', 'إجابة', 'مجيب', 'أجاب'],
    'شرح': ['شرح', 'شارح', 'شروح', 'توضيح'],
    'وصف': ['وصف', 'صفة', 'موصوف', 'واصف', 'صفات'],

    # Nature & Science
    'ماء': ['ماء', 'مياه', 'مائي', 'مائية'],
    'نار': ['نار', 'ناري', 'نيران', 'حريق'],
    'أرض': ['أرض', 'أرضي', 'أراضي'],
    'شمس': ['شمس', 'شمسي', 'شمسية'],
    'قمر': ['قمر', 'قمري', 'أقمار'],
    'نجم': ['نجم', 'نجوم', 'نجمة'],
    'بحر': ['بحر', 'بحري', 'بحار', 'بحرية'],
    'نهر': ['نهر', 'أنهار', 'نهري'],
    'جبل': ['جبل', 'جبال', 'جبلي'],

    # Numbers & Math
    'عدد': ['عدد', 'أعداد', 'عددي', 'تعداد', 'معدود'],
    'حسب': ['حساب', 'حاسب', 'محسوب', 'احتساب', 'حاسوب'],
    'قسم': ['قسم', 'قسمة', 'أقسام', 'تقسيم', 'قسمي'],
    'جمع': ['جمع', 'جامع', 'مجموع', 'جمعية', 'مجموعة'],
    'ضرب': ['ضرب', 'ضارب', 'مضروب', 'ضربة'],

    # Time
    'وقت': ['وقت', 'أوقات', 'توقيت', 'مؤقت'],
    'زمن': ['زمن', 'زمني', 'أزمنة', 'زمان'],
    'يوم': ['يوم', 'يومي', 'أيام', 'يومية'],
    'سنة': ['سنة', 'سنوي', 'سنوات', 'سنين'],

    # Body & Health
    'جسم': ['جسم', 'أجسام', 'جسدي', 'جسيم'],
    'صحة': ['صحة', 'صحي', 'صحية', 'تصحيح'],
    'مرض': ['مرض', 'مريض', 'أمراض', 'مرضي'],
    'قلب': ['قلب', 'قلبي', 'قلوب'],

    # Science & Technology
    'كهرب': ['كهرباء', 'كهربي', 'كهربائي', 'كهربائية'],
    'ذرر': ['ذرة', 'ذري', 'ذرات', 'ذرية'],
    'طاق': ['طاقة', 'طاقات', 'طاقوي'],
    'قوى': ['قوة', 'قوي', 'قوى', 'تقوية'],
    'حرك': ['حركة', 'حركي', 'متحرك', 'تحريك'],
    'سرع': ['سرعة', 'سريع', 'تسريع', 'إسراع'],
    'ضوء': ['ضوء', 'أضواء', 'ضوئي', 'إضاءة'],
    'صوت': ['صوت', 'أصوات', 'صوتي'],
    'حرر': ['حرارة', 'حراري', 'حار', 'ساخن'],

    # Society
    'حكم': ['حكم', 'حاكم', 'محكوم', 'حكومة', 'أحكام'],
    'ملك': ['ملك', 'مملكة', 'ملكي', 'ملوك'],
    'شعب': ['شعب', 'شعبي', 'شعوب'],
    'وطن': ['وطن', 'وطني', 'أوطان', 'مواطن'],
    'دول': ['دولة', 'دولي', 'دول'],
    'مدن': ['مدينة', 'مدني', 'مدن'],

    # Religion & Values
    'صلا': ['صلاة', 'مصلي', 'صلوات'],
    'عبد': ['عبادة', 'عابد', 'معبد', 'عبد'],
    'إيمن': ['إيمان', 'مؤمن', 'أمان', 'آمن'],
}


def get_word_family(root: str, limit: int = 10) -> List[str]:
    """
    Get common words derived from the same root.

    Uses curated word families for common roots to ensure quality
    (no nonsense generated words).

    Args:
        root: Arabic root (usually 3 letters)
        limit: Maximum number of words to return

    Returns:
        List of related real Arabic words, or empty list if root not found
    """
    if not root or len(root) < 2:
        return []

    from .core import normalize_arabic
    root_normalized = normalize_arabic(root)

    # Try exact match first
    if root in CURATED_WORD_FAMILIES:
        return CURATED_WORD_FAMILIES[root][:limit]

    # Try normalized version
    if root_normalized in CURATED_WORD_FAMILIES:
        return CURATED_WORD_FAMILIES[root_normalized][:limit]

    # Try matching first 2-3 characters for partial matches
    for stored_root, words in CURATED_WORD_FAMILIES.items():
        if len(root) >= 2 and len(stored_root) >= 2:
            if root[:2] == stored_root[:2]:
                return words[:limit]

    # No match found - return empty list instead of generating nonsense
    return []


def is_same_root(word1: str, word2: str) -> bool:
    """Check if two words share the same root."""
    root1 = extract_root(word1)
    root2 = extract_root(word2)
    if root1 and root2:
        return root1 == root2
    return False


def get_morphological_complexity(word: str) -> float:
    """
    Calculate morphological complexity score for a word.

    Returns:
        Float between 0 and 1 (higher = more complex)
    """
    features = get_morphological_features(word)
    score = 0.0

    # Has prefix adds complexity
    if features['has_prefix']:
        score += 0.25

    # Has suffix adds complexity
    if features['has_suffix']:
        score += 0.25

    # Long words are more complex
    word_len = len(word)
    if word_len >= 7:
        score += 0.25
    elif word_len >= 5:
        score += 0.1

    # Plural forms are slightly more complex
    if features['number'] == 'جمع':
        score += 0.15

    # No root found suggests unusual form
    if not features['root']:
        score += 0.1

    return min(1.0, score)


def stem_arabic(word: str) -> str:
    """
    Apply Arabic stemming to a word.
    Returns the stem (may be shorter than lemma).
    """
    if _check_pyarabic():
        try:
            from pyarabic import stem
            stemmer = stem.ArabicLightStemmer()
            stemmer.light_stem(word)
            result = stemmer.get_stem()
            if result:
                return result
        except Exception:
            pass

    # Fallback to lemma
    return extract_lemma(word)


def analyze_sentence(sentence: str) -> List[Dict]:
    """
    Analyze all words in a sentence.

    Returns:
        List of morphological feature dicts for each word
    """
    from .core import tokenize_arabic

    tokens = tokenize_arabic(sentence, normalize=False)
    return [get_morphological_features(token) for token in tokens]


def group_by_root(words: List[str]) -> Dict[str, List[str]]:
    """
    Group a list of words by their roots.

    Args:
        words: List of Arabic words

    Returns:
        Dict mapping roots to lists of words
    """
    groups: Dict[str, List[str]] = {}

    for word in words:
        root = extract_root(word)
        if root:
            if root not in groups:
                groups[root] = []
            groups[root].append(word)
        else:
            # Unknown roots go to special key
            if '_unknown' not in groups:
                groups['_unknown'] = []
            groups['_unknown'].append(word)

    return groups
