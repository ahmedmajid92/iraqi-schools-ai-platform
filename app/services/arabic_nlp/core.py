"""
Core Arabic NLP utilities.
Provides basic normalization, tokenization, and sentence splitting.
"""
import re
from typing import List, Set

# Diacritics pattern (tashkeel)
ARABIC_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u0652]")

# Punctuation pattern (non-Arabic, non-word chars)
PUNCT = re.compile(r"[^\w\u0600-\u06FF\s]+")

# Arabic token pattern (minimum 2 chars)
ARABIC_TOKEN = re.compile(r"[\u0600-\u06FF]{2,}")

# Extended character normalization map
NORMALIZATION_MAP = {
    # Alef variants -> Alef
    '\u0622': '\u0627',  # ALEF WITH MADDA ABOVE
    '\u0623': '\u0627',  # ALEF WITH HAMZA ABOVE
    '\u0625': '\u0627',  # ALEF WITH HAMZA BELOW
    '\u0671': '\u0627',  # ALEF WASLA
    '\u0672': '\u0627',  # ALEF WITH WAVY HAMZA ABOVE
    '\u0673': '\u0627',  # ALEF WITH WAVY HAMZA BELOW
    '\u0675': '\u0627',  # HIGH HAMZA ALEF
    # Ya variants -> Ya
    '\u0649': '\u064A',  # ALEF MAKSURA -> YEH
    '\u0626': '\u064A',  # YEH WITH HAMZA ABOVE -> YEH
    '\u06CC': '\u064A',  # FARSI YEH -> ARABIC YEH
    '\u06CD': '\u064A',  # YEH WITH TAIL
    # Waw variants -> Waw
    '\u0624': '\u0648',  # WAW WITH HAMZA ABOVE
    '\u06C6': '\u0648',  # OE
    '\u06C7': '\u0648',  # U
    '\u06C8': '\u0648',  # YU
    '\u06C9': '\u0648',  # KIRGHIZ YU
    # Ta marbuta -> Ha
    '\u0629': '\u0647',  # TEH MARBUTA -> HEH
    # Kaf variants
    '\u06A9': '\u0643',  # KEHEH -> KAF
    '\u06AA': '\u0643',  # SWASH KAF
}


def normalize_arabic(text: str) -> str:
    """
    Normalize Arabic text by removing diacritics and standardizing character variants.

    Operations:
    - Remove diacritics (tashkeel)
    - Normalize alef variants (أ إ آ ا) -> ا
    - Normalize ya variants (ى ئ) -> ي
    - Normalize waw variants (ؤ) -> و
    - Normalize ta marbuta (ة) -> ه
    - Normalize kaf variants -> ك

    Args:
        text: Arabic text to normalize

    Returns:
        Normalized text
    """
    # Remove diacritics
    text = ARABIC_DIACRITICS.sub("", text)

    # Apply character normalization
    for old, new in NORMALIZATION_MAP.items():
        text = text.replace(old, new)

    return text


def normalize_light(text: str) -> str:
    """
    Light normalization that preserves more information.
    Only removes diacritics and normalizes alef/ya variants.
    Keeps ta marbuta distinct from ha.
    """
    text = ARABIC_DIACRITICS.sub("", text)

    # Only normalize alef and ya variants
    light_map = {
        '\u0622': '\u0627', '\u0623': '\u0627', '\u0625': '\u0627',
        '\u0649': '\u064A', '\u0626': '\u064A',
        '\u0624': '\u0648',
    }
    for old, new in light_map.items():
        text = text.replace(old, new)

    return text


def split_sentences(text: str) -> List[str]:
    """
    Split Arabic text into sentences.

    Handles:
    - Arabic question mark (؟)
    - Arabic semicolon (؛)
    - Standard punctuation (. ! ?)
    - Newlines as sentence boundaries
    - Protects common abbreviations from false splits

    Args:
        text: Text to split

    Returns:
        List of sentences (minimum 10 characters)
    """
    # Protect common Arabic abbreviations from splitting
    abbreviations = [
        ('د.', 'ABBR_DR'),      # Doctor
        ('أ.', 'ABBR_PROF'),    # Professor
        ('م.', 'ABBR_ENG'),     # Engineer
        ('ص.', 'ABBR_PAGE'),    # Page
        ('ج.', 'ABBR_PART'),    # Part
        ('هـ.', 'ABBR_HIJRI'),  # Hijri date
        ('ق.م.', 'ABBR_BC'),    # Before Christ
        ('ب.م.', 'ABBR_AD'),    # Anno Domini
    ]

    t = text
    for abbr, placeholder in abbreviations:
        t = t.replace(abbr, placeholder)

    # Handle ellipsis
    t = t.replace('...', 'ELLIPSIS').replace('…', 'ELLIPSIS')

    # Normalize Arabic punctuation
    t = t.replace("؟", "?").replace("؛", ";")

    # Split on sentence-ending punctuation
    parts = re.split(r"[\.!\?\n;]+", t)

    # Restore abbreviations and clean
    sentences = []
    for p in parts:
        p = p.strip()
        if not p:
            continue

        # Restore abbreviations
        for abbr, placeholder in abbreviations:
            p = p.replace(placeholder, abbr)
        p = p.replace('ELLIPSIS', '...')

        # Only include sentences with meaningful content (min 10 chars)
        if len(p) >= 10:
            sentences.append(p)

    return sentences


def tokenize_arabic(text: str, normalize: bool = True) -> List[str]:
    """
    Tokenize Arabic text into words.

    Args:
        text: Text to tokenize
        normalize: Whether to apply normalization (default True)

    Returns:
        List of Arabic tokens (minimum 2 characters)
    """
    if normalize:
        text = normalize_arabic(text)

    # Remove punctuation
    text = PUNCT.sub(" ", text)

    # Extract Arabic tokens
    tokens = ARABIC_TOKEN.findall(text)

    return tokens


def tokenize_with_positions(text: str) -> List[tuple]:
    """
    Tokenize text and return tokens with their positions.

    Returns:
        List of (token, start, end) tuples
    """
    results = []
    for match in ARABIC_TOKEN.finditer(text):
        results.append((match.group(), match.start(), match.end()))
    return results


def is_arabic(text: str) -> bool:
    """Check if text contains primarily Arabic characters."""
    arabic_chars = len(re.findall(r"[\u0600-\u06FF]", text))
    total_chars = len(re.findall(r"\S", text))
    return total_chars > 0 and (arabic_chars / total_chars) > 0.5


def remove_tatweel(text: str) -> str:
    """Remove tatweel (kashida) stretching character."""
    return text.replace('\u0640', '')


def clean_text(text: str) -> str:
    """
    Clean Arabic text by removing extra whitespace and normalizing.
    """
    # Remove tatweel
    text = remove_tatweel(text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    # Normalize Arabic text
    text = normalize_arabic(text)

    return text.strip()


def prepare_text_for_analysis(text: str) -> str:
    """
    Prepare text for NLP analysis by cleaning and normalizing.

    This function should be called before pattern matching, quiz generation,
    or any other NLP analysis. It performs comprehensive cleaning while
    preserving paragraph structure.

    Operations:
    1. Remove zero-width characters
    2. Normalize whitespace within lines (preserve paragraph breaks)
    3. Remove tatweel (kashida)
    4. Apply light normalization (alef/ya only, preserve ta-marbuta)

    Args:
        text: Raw text (e.g., from PDF extraction)

    Returns:
        Cleaned and normalized text ready for NLP analysis
    """
    if not text:
        return text

    # 1. Remove zero-width characters
    zero_width_chars = [
        '\u200b', '\u200c', '\u200d', '\u200e', '\u200f',
        '\ufeff', '\u00ad', '\u2060', '\u2061', '\u2062',
        '\u2063', '\u2064',
    ]
    for char in zero_width_chars:
        text = text.replace(char, '')

    # 2. Normalize various space types to regular space
    space_chars = [
        '\u00a0', '\u2000', '\u2001', '\u2002', '\u2003',
        '\u2004', '\u2005', '\u2006', '\u2007', '\u2008',
        '\u2009', '\u200a', '\u202f', '\u205f', '\u3000',
    ]
    for char in space_chars:
        text = text.replace(char, ' ')

    # 3. Normalize tabs to spaces
    text = text.replace('\t', ' ')

    # 4. Collapse multiple spaces within lines to single space
    text = re.sub(r'[ ]{2,}', ' ', text)

    # 5. Strip whitespace from each line
    lines = text.split('\n')
    lines = [line.strip() for line in lines]
    text = '\n'.join(lines)

    # 6. Collapse 3+ consecutive newlines to double newline
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 7. Remove tatweel (kashida)
    text = remove_tatweel(text)

    # 8. Apply light normalization (preserve ta-marbuta for pattern matching)
    text = normalize_light(text)

    return text.strip()
