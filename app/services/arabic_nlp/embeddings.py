"""
Arabic word embeddings for semantic similarity.
Uses AraVec or other pre-trained Arabic embeddings with fallback to simple methods.
"""
import os
import functools
from typing import List, Tuple, Optional, Set
from pathlib import Path

# Lazy-loaded embedding model
_embedding_model = None
_model_loaded = False

# Path to embeddings data
DATA_DIR = Path(__file__).parent.parent.parent / "data" / "models" / "aravec"


def _load_embeddings():
    """Lazy-load Arabic word embedding model."""
    global _embedding_model, _model_loaded

    if _model_loaded:
        return _embedding_model

    _model_loaded = True

    # Try to load AraVec or similar model
    try:
        from gensim.models import KeyedVectors, Word2Vec

        # Strategy 1: Try loading as gensim native model (.mdl files from AraVec)
        mdl_paths = [
            DATA_DIR / "full_grams_cbow_300_wiki.mdl",
            DATA_DIR / "full_grams_sg_300_wiki.mdl",
            DATA_DIR / "full_grams_cbow_300_twitter.mdl",
            DATA_DIR / "wiki_300d.mdl",
            DATA_DIR / "aravec.mdl",
        ]

        # Check if .npy files exist without .mdl (incomplete download)
        npy_files = list(DATA_DIR.glob("*.npy"))
        if npy_files and not any(p.exists() for p in mdl_paths):
            print(f"Warning: Found .npy files but missing .mdl model file in {DATA_DIR}")
            print("Please download the complete AraVec model (including .mdl file)")

        for mdl_path in mdl_paths:
            if mdl_path.exists():
                try:
                    # AraVec models are saved as full Word2Vec models
                    model = Word2Vec.load(str(mdl_path))
                    _embedding_model = model.wv  # Extract KeyedVectors
                    print(f"Loaded AraVec model from {mdl_path}")
                    return _embedding_model
                except Exception as e:
                    print(f"Failed to load {mdl_path} as Word2Vec: {e}")
                    # Try loading as KeyedVectors directly
                    try:
                        _embedding_model = KeyedVectors.load(str(mdl_path))
                        print(f"Loaded KeyedVectors from {mdl_path}")
                        return _embedding_model
                    except Exception as e2:
                        print(f"Failed to load {mdl_path} as KeyedVectors: {e2}")
                        continue

        # Strategy 2: Try Word2Vec binary format (.bin files)
        bin_paths = [
            DATA_DIR / "wiki_300d.bin",
            DATA_DIR / "aravec.bin",
            DATA_DIR / "arabic_embeddings.bin",
        ]

        for bin_path in bin_paths:
            if bin_path.exists():
                try:
                    _embedding_model = KeyedVectors.load_word2vec_format(
                        str(bin_path), binary=True
                    )
                    print(f"Loaded embeddings from {bin_path}")
                    return _embedding_model
                except Exception as e:
                    print(f"Failed to load {bin_path}: {e}")
                    continue

        # Strategy 3: Try text format (.txt or .vec files)
        txt_paths = [
            DATA_DIR / "wiki_300d.txt",
            DATA_DIR / "wiki_300d.vec",
            DATA_DIR / "aravec.txt",
            DATA_DIR / "aravec.vec",
        ]
        for txt_path in txt_paths:
            if txt_path.exists():
                try:
                    _embedding_model = KeyedVectors.load_word2vec_format(
                        str(txt_path), binary=False
                    )
                    print(f"Loaded embeddings from {txt_path}")
                    return _embedding_model
                except Exception as e:
                    print(f"Failed to load {txt_path}: {e}")
                    continue

        # Strategy 4: Try loading any .npy file (numpy format)
        npy_paths = list(DATA_DIR.glob("*.npy"))
        for npy_path in npy_paths:
            try:
                _embedding_model = KeyedVectors.load(str(npy_path.with_suffix('')))
                print(f"Loaded embeddings from {npy_path}")
                return _embedding_model
            except Exception:
                continue

    except ImportError as e:
        print(f"Gensim not available: {e}")

    return None


def get_similar_words(word: str, top_n: int = 10) -> List[Tuple[str, float]]:
    """
    Find semantically similar words using embeddings.

    Args:
        word: Arabic word
        top_n: Number of similar words to return

    Returns:
        List of (word, similarity_score) tuples, sorted by similarity
    """
    model = _load_embeddings()

    if model is None:
        return []

    # Normalize the word
    from .core import normalize_arabic
    norm_word = normalize_arabic(word)

    try:
        # Try original word first
        if word in model:
            return model.most_similar(word, topn=top_n)
        # Try normalized
        if norm_word in model:
            return model.most_similar(norm_word, topn=top_n)
        # Try without diacritics
        if norm_word != word and norm_word in model:
            return model.most_similar(norm_word, topn=top_n)
    except KeyError:
        pass

    return []


def word_similarity(word1: str, word2: str) -> float:
    """
    Compute semantic similarity between two words.

    Args:
        word1: First Arabic word
        word2: Second Arabic word

    Returns:
        Similarity score between -1 and 1 (higher = more similar)
    """
    model = _load_embeddings()

    if model is None:
        # Fallback: simple character overlap
        return _simple_similarity(word1, word2)

    from .core import normalize_arabic
    w1 = normalize_arabic(word1)
    w2 = normalize_arabic(word2)

    try:
        # Try to compute similarity
        if w1 in model and w2 in model:
            return model.similarity(w1, w2)
    except KeyError:
        pass

    return _simple_similarity(word1, word2)


def _simple_similarity(word1: str, word2: str) -> float:
    """
    Simple character-based similarity fallback.
    Uses Jaccard similarity on character n-grams.
    """
    from .core import normalize_arabic

    w1 = normalize_arabic(word1)
    w2 = normalize_arabic(word2)

    if w1 == w2:
        return 1.0

    # Get character bigrams
    def get_ngrams(s: str, n: int = 2) -> Set[str]:
        return set(s[i:i+n] for i in range(len(s) - n + 1))

    ngrams1 = get_ngrams(w1)
    ngrams2 = get_ngrams(w2)

    if not ngrams1 or not ngrams2:
        return 0.0

    # Jaccard similarity
    intersection = len(ngrams1 & ngrams2)
    union = len(ngrams1 | ngrams2)

    return intersection / union if union > 0 else 0.0


def get_semantic_distractors(
    correct_answer: str,
    context_words: Optional[List[str]] = None,
    num_distractors: int = 3,
    min_similarity: float = 0.3,
    max_similarity: float = 0.85
) -> List[str]:
    """
    Generate semantically plausible but incorrect distractors for MCQs.

    Finds words that are related (similar) but not too similar to the correct answer.
    This creates challenging but fair distractors.

    Args:
        correct_answer: The correct answer word
        context_words: Optional list of words from the same context (avoid using these)
        num_distractors: Number of distractors to generate
        min_similarity: Minimum similarity threshold (below = unrelated)
        max_similarity: Maximum similarity threshold (above = too similar/correct)

    Returns:
        List of distractor words
    """
    context_words = set(context_words or [])
    context_words.add(correct_answer)

    from .core import normalize_arabic
    norm_answer = normalize_arabic(correct_answer)
    context_normalized = {normalize_arabic(w) for w in context_words}

    distractors = []

    # Strategy 1: Embeddings-based (best quality)
    model = _load_embeddings()
    if model:
        try:
            # Get more candidates than needed
            similar = get_similar_words(correct_answer, top_n=20)
            for word, sim in similar:
                # Filter by similarity range
                if min_similarity <= sim <= max_similarity:
                    # Not in context
                    if normalize_arabic(word) not in context_normalized:
                        distractors.append(word)
                        if len(distractors) >= num_distractors:
                            break
        except Exception:
            pass

    # Strategy 2: Root-based distractors
    if len(distractors) < num_distractors:
        from .morphology import extract_root, get_word_family

        root = extract_root(correct_answer)
        if root:
            family = get_word_family(root, limit=10)
            for word in family:
                if normalize_arabic(word) not in context_normalized:
                    if word not in distractors:
                        distractors.append(word)
                        if len(distractors) >= num_distractors:
                            break

    # Strategy 3: POS-matched from context
    if len(distractors) < num_distractors and context_words:
        from .pos_tagger import get_pos

        answer_pos = get_pos(correct_answer)
        for ctx_word in context_words:
            if ctx_word != correct_answer:
                if get_pos(ctx_word) == answer_pos:
                    if normalize_arabic(ctx_word) not in context_normalized:
                        if ctx_word not in distractors:
                            distractors.append(ctx_word)
                            if len(distractors) >= num_distractors:
                                break

    return distractors[:num_distractors]


def get_word_vector(word: str) -> Optional[List[float]]:
    """
    Get the embedding vector for a word.

    Args:
        word: Arabic word

    Returns:
        List of floats (embedding vector) or None if not found
    """
    model = _load_embeddings()
    if model is None:
        return None

    from .core import normalize_arabic
    norm = normalize_arabic(word)

    try:
        if word in model:
            return model[word].tolist()
        if norm in model:
            return model[norm].tolist()
    except KeyError:
        pass

    return None


def is_embeddings_available() -> bool:
    """Check if embeddings are loaded and available."""
    model = _load_embeddings()
    return model is not None


def get_vocabulary_size() -> int:
    """Get the size of the embedding vocabulary."""
    model = _load_embeddings()
    if model is None:
        return 0
    return len(model.key_to_index) if hasattr(model, 'key_to_index') else len(model.vocab)


def words_in_vocabulary(words: List[str]) -> List[str]:
    """Filter words to only those in the embedding vocabulary."""
    model = _load_embeddings()
    if model is None:
        return []

    from .core import normalize_arabic
    result = []
    for word in words:
        norm = normalize_arabic(word)
        if word in model or norm in model:
            result.append(word)
    return result


def compute_text_similarity(text1: str, text2: str) -> float:
    """
    Compute similarity between two texts using average word embeddings.

    Args:
        text1: First Arabic text
        text2: Second Arabic text

    Returns:
        Similarity score between 0 and 1
    """
    from .core import tokenize_arabic
    from .stopwords import remove_stopwords

    tokens1 = remove_stopwords(tokenize_arabic(text1))
    tokens2 = remove_stopwords(tokenize_arabic(text2))

    if not tokens1 or not tokens2:
        return 0.0

    model = _load_embeddings()
    if model is None:
        # Fallback to Jaccard
        set1 = set(tokens1)
        set2 = set(tokens2)
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        return intersection / union if union > 0 else 0.0

    # Get vectors for each text
    def get_avg_vector(tokens):
        vectors = []
        from .core import normalize_arabic
        for token in tokens:
            norm = normalize_arabic(token)
            try:
                if token in model:
                    vectors.append(model[token])
                elif norm in model:
                    vectors.append(model[norm])
            except KeyError:
                continue
        if not vectors:
            return None
        import numpy as np
        return np.mean(vectors, axis=0)

    vec1 = get_avg_vector(tokens1)
    vec2 = get_avg_vector(tokens2)

    if vec1 is None or vec2 is None:
        return 0.0

    # Cosine similarity
    import numpy as np
    dot = np.dot(vec1, vec2)
    norm1 = np.linalg.norm(vec1)
    norm2 = np.linalg.norm(vec2)

    if norm1 == 0 or norm2 == 0:
        return 0.0

    return float(dot / (norm1 * norm2))


def find_odd_one_out(words: List[str]) -> Optional[str]:
    """
    Find the word that doesn't belong in a group.
    Useful for generating "which one doesn't belong" questions.

    Args:
        words: List of Arabic words

    Returns:
        The word that is least similar to the others, or None
    """
    if len(words) < 3:
        return None

    model = _load_embeddings()
    if model is None:
        return None

    try:
        # Use gensim's doesnt_match if available
        from .core import normalize_arabic
        norm_words = [normalize_arabic(w) for w in words]
        vocab_words = [w for w in norm_words if w in model]

        if len(vocab_words) >= 3:
            odd = model.doesnt_match(vocab_words)
            # Map back to original
            idx = norm_words.index(odd)
            return words[idx]
    except Exception:
        pass

    return None
