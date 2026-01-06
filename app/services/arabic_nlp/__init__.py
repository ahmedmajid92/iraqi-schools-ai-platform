"""
Arabic NLP Package for Iraq Education AI Assistant.

This package provides comprehensive Arabic text processing capabilities:
- Text normalization and tokenization
- Extended stopword filtering (200+ words)
- Morphological analysis (root extraction, lemmatization)
- Part-of-speech tagging
- Grammar pattern matching for question generation
- Word embeddings for semantic similarity

All modules use lazy loading for heavy dependencies (CAMeL Tools, AraVec)
and provide graceful fallbacks when these are not available.

Usage:
    from app.services.arabic_nlp import (
        normalize_arabic,
        tokenize_arabic,
        split_sentences,
        remove_stopwords,
        extract_root,
        extract_lemma,
        get_pos,
        PatternMatcher,
    )

    # Basic text processing
    text = "النص العربي للتحليل"
    normalized = normalize_arabic(text)
    tokens = tokenize_arabic(text)
    sentences = split_sentences(text)

    # Stopword removal
    filtered = remove_stopwords(tokens)

    # Morphological analysis
    root = extract_root("كتاب")  # Returns: كتب
    lemma = extract_lemma("الكتب")  # Returns: كتاب

    # POS tagging
    pos = get_pos("يكتب")  # Returns: ArabicPOS.VERB

    # Pattern matching for questions
    matcher = PatternMatcher()
    definitions = matcher.find_definitions(text)
"""

# === Core Text Processing ===
from .core import (
    normalize_arabic,
    normalize_light,
    split_sentences,
    tokenize_arabic,
    tokenize_with_positions,
    is_arabic,
    remove_tatweel,
    clean_text,
    prepare_text_for_analysis,
)

# === Stopwords ===
from .stopwords import (
    DEFAULT_STOPWORDS,
    ALL_STOPWORDS,
    get_stopwords,
    remove_stopwords,
    is_stopword,
    # Category sets (for advanced usage)
    PRONOUNS,
    PREPOSITIONS,
    CONJUNCTIONS,
    DEMONSTRATIVES,
    RELATIVES,
    INTERROGATIVES,
    AUXILIARIES,
    ADVERBS,
    NEGATION,
    AFFIRMATION,
)

# === Morphological Analysis ===
from .morphology import (
    extract_root,
    extract_lemma,
    get_morphological_features,
    get_word_family,
    is_same_root,
    get_morphological_complexity,
    stem_arabic,
    analyze_sentence,
    group_by_root,
)

# === Part-of-Speech Tagging ===
from .pos_tagger import (
    ArabicPOS,
    get_pos,
    tag_sentence,
    extract_nouns,
    extract_verbs,
    extract_adjectives,
    extract_content_words,
    is_content_word,
    is_function_word,
    get_pos_distribution,
    filter_by_pos,
    get_nouns_and_adjectives,
)

# === Pattern Matching ===
from .patterns import (
    QuestionType,
    PatternMatch,
    PatternMatcher,
    DEFINITION_PATTERNS,
    CAUSE_EFFECT_PATTERNS,
    COMPARISON_PATTERNS,
    ENUMERATION_PATTERNS,
    PROCESS_PATTERNS,
    FACTUAL_KEYWORDS,
)

# === Word Embeddings ===
from .embeddings import (
    get_similar_words,
    word_similarity,
    get_semantic_distractors,
    get_word_vector,
    is_embeddings_available,
    get_vocabulary_size,
    words_in_vocabulary,
    compute_text_similarity,
    find_odd_one_out,
)

# Version
__version__ = "2.0.0"

# All public exports
__all__ = [
    # Core
    "normalize_arabic",
    "normalize_light",
    "split_sentences",
    "tokenize_arabic",
    "tokenize_with_positions",
    "is_arabic",
    "remove_tatweel",
    "clean_text",
    "prepare_text_for_analysis",
    # Stopwords
    "DEFAULT_STOPWORDS",
    "ALL_STOPWORDS",
    "get_stopwords",
    "remove_stopwords",
    "is_stopword",
    "PRONOUNS",
    "PREPOSITIONS",
    "CONJUNCTIONS",
    "DEMONSTRATIVES",
    "RELATIVES",
    "INTERROGATIVES",
    "AUXILIARIES",
    "ADVERBS",
    "NEGATION",
    "AFFIRMATION",
    # Morphology
    "extract_root",
    "extract_lemma",
    "get_morphological_features",
    "get_word_family",
    "is_same_root",
    "get_morphological_complexity",
    "stem_arabic",
    "analyze_sentence",
    "group_by_root",
    # POS
    "ArabicPOS",
    "get_pos",
    "tag_sentence",
    "extract_nouns",
    "extract_verbs",
    "extract_adjectives",
    "extract_content_words",
    "is_content_word",
    "is_function_word",
    "get_pos_distribution",
    "filter_by_pos",
    "get_nouns_and_adjectives",
    # Patterns
    "QuestionType",
    "PatternMatch",
    "PatternMatcher",
    "DEFINITION_PATTERNS",
    "CAUSE_EFFECT_PATTERNS",
    "COMPARISON_PATTERNS",
    "ENUMERATION_PATTERNS",
    "PROCESS_PATTERNS",
    "FACTUAL_KEYWORDS",
    # Embeddings
    "get_similar_words",
    "word_similarity",
    "get_semantic_distractors",
    "get_word_vector",
    "is_embeddings_available",
    "get_vocabulary_size",
    "words_in_vocabulary",
    "compute_text_similarity",
    "find_odd_one_out",
]
