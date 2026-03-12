"""
OpenAI-powered quiz generation with hybrid approach and cost optimization.
Uses gpt-5-nano with text truncation, smart chunking, and caching.
Falls back to local NLP if API unavailable.
"""
import os
import re
import json
import hashlib
import logging
from typing import Dict, List, Optional, Tuple
from app.env import get_env
from pathlib import Path

# Setup logging
logger = logging.getLogger(__name__)

# Cache setup
CACHE_DIR = Path(__file__).parent.parent.parent / "instance" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

try:
    import diskcache
    _cache = diskcache.Cache(str(CACHE_DIR / "openai_cache"))
    CACHE_AVAILABLE = True
except ImportError:
    _cache = None
    CACHE_AVAILABLE = False
    logger.warning("diskcache not installed - caching disabled")

# Constants
MAX_WORDS = 5000  # Maximum words to send to API
MAX_OUTPUT_TOKENS = 16000  # Max tokens for response
# GPT-4o-mini - Latest fast/cheap model
MODEL_NAME = get_env("OPENAI_MODEL", "gpt-4o-mini")
CACHE_TTL = 86400 * 7  # 7 days cache


def _get_openai_client():
    """Get OpenAI client if API key is available."""
    api_key = get_env("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key)
    except ImportError:
        logger.warning("openai package not installed")
        return None
    except Exception as e:
        logger.error(f"OpenAI client error: {e}")
        return None


def _count_words(text: str) -> int:
    """Count words in text (Arabic-aware)."""
    return len(text.split())


def _truncate_text(text: str, max_words: int = MAX_WORDS) -> str:
    """Truncate text to max words while preserving sentence boundaries."""
    words = text.split()
    if len(words) <= max_words:
        return text
    
    # Find last sentence boundary within limit
    truncated = " ".join(words[:max_words])
    last_period = max(truncated.rfind("."), truncated.rfind("。"), truncated.rfind("۔"))
    if last_period > len(truncated) * 0.7:  # Keep at least 70%
        truncated = truncated[:last_period + 1]
    
    return truncated


def _smart_chunk_text(text: str, max_words: int = MAX_WORDS) -> str:
    """
    Extract most relevant portions using TF-IDF scoring.
    This is the 2B cost optimization strategy.
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    import numpy as np
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    if len(paragraphs) <= 3:
        return _truncate_text(text, max_words)
    
    # Score paragraphs by TF-IDF importance
    try:
        vectorizer = TfidfVectorizer(max_features=100)
        tfidf_matrix = vectorizer.fit_transform(paragraphs)
        scores = np.asarray(tfidf_matrix.sum(axis=1)).flatten()
        
        # Always include first paragraph (intro) and last (conclusion)
        selected = [0, len(paragraphs) - 1]
        
        # Add highest scoring middle paragraphs
        middle_indices = list(range(1, len(paragraphs) - 1))
        middle_scores = [(i, scores[i]) for i in middle_indices]
        middle_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Select until we hit word limit
        result_words = _count_words(paragraphs[0]) + _count_words(paragraphs[-1])
        for idx, _ in middle_scores:
            para_words = _count_words(paragraphs[idx])
            if result_words + para_words > max_words:
                break
            selected.append(idx)
            result_words += para_words
        
        # Sort by original order and join
        selected.sort()
        return "\n\n".join(paragraphs[i] for i in selected)
    
    except Exception as e:
        logger.warning(f"Smart chunking failed: {e}, falling back to truncation")
        return _truncate_text(text, max_words)


def _get_cache_key(text: str, num_questions: int, grade: str, subject: str) -> str:
    """Generate cache key from request parameters."""
    content = f"{text}|{num_questions}|{grade}|{subject}"
    return hashlib.sha256(content.encode()).hexdigest()[:32]


def _get_cached_response(cache_key: str) -> Optional[Dict]:
    """Get cached response if available."""
    if not CACHE_AVAILABLE or _cache is None:
        return None
    try:
        return _cache.get(cache_key)
    except Exception:
        return None


def _cache_response(cache_key: str, response: Dict) -> None:
    """Cache response for future use."""
    if not CACHE_AVAILABLE or _cache is None:
        return
    try:
        _cache.set(cache_key, response, expire=CACHE_TTL)
    except Exception as e:
        logger.warning(f"Cache write failed: {e}")


def _build_quiz_prompt(text: str, num_questions: int, grade: str, subject: str) -> str:
    """Build optimized prompt for quiz generation."""
    return f"""أنت مساعد تعليمي متخصص في المناهج العراقية.
أنشئ {num_questions} سؤال اختيار من متعدد بناءً على النص التالي.

المرحلة: {grade or "الإعدادية"}
المادة: {subject or "عام"}

قواعد مهمة:
1. كل سؤال له 4 خيارات (أ، ب، ج، د)
2. إجابة واحدة صحيحة فقط
3. الأسئلة متنوعة (تعريفات، أسباب ونتائج، مقارنات، صح/خطأ محول)
4. مناسبة لمستوى الطالب العراقي
5. واضحة ومباشرة

النص:
{text}

أجب بصيغة JSON فقط:
{{
  "questions": [
    {{
      "question": "نص السؤال",
      "choices": ["أ) الخيار الأول", "ب) الخيار الثاني", "ج) الخيار الثالث", "د) الخيار الرابع"],
      "correct_index": 0,
      "explanation": "شرح مختصر للإجابة"
    }}
  ]
}}"""


def _parse_openai_response(response_text: str) -> Optional[Dict]:
    """Parse OpenAI response and extract quiz JSON."""
    if not response_text:
        logger.warning("Empty response from OpenAI")
        return None
    
    # Log raw response for debugging (safe for Windows)
    try:
        preview = response_text[:500]
        safe_preview = preview.encode('ascii', errors='ignore').decode('ascii')
        logger.info(f"Raw OpenAI response length: {len(response_text)} chars")
        print(f"[DEBUG] Response received, length: {len(response_text)} chars")
    except:
        pass
    
    # Clean response - remove markdown artifacts
    cleaned = response_text.strip()
    
    # Remove markdown code blocks
    if cleaned.startswith("```"):
        # Remove opening ``` (with optional language tag)
        cleaned = re.sub(r'^```(?:json)?\s*', '', cleaned)
        # Remove closing ```
        cleaned = re.sub(r'```\s*$', '', cleaned)
        cleaned = cleaned.strip()
    
    # Try direct JSON parse
    try:
        data = json.loads(cleaned)
        if "questions" in data:
            return data
    except json.JSONDecodeError as e:
        logger.debug(f"Direct JSON parse failed: {e}")
    
    # Try to find JSON object with questions array
    patterns = [
        r'\{[\s\S]*"questions"\s*:\s*\[[\s\S]*\]\s*\}',  # Full object with questions array
        r'\{\s*"questions"\s*:\s*\[.*?\]\s*\}',  # Compact version
    ]
    
    for pattern in patterns:
        match = re.search(pattern, response_text, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group(0))
                if "questions" in data:
                    return data
            except json.JSONDecodeError:
                continue
    
    # Try to extract individual question objects and build response
    question_pattern = r'\{[^{}]*"question"[^{}]*"choices"[^{}]*\}'
    questions_match = re.findall(question_pattern, response_text)
    if questions_match:
        questions = []
        for q_str in questions_match:
            try:
                q = json.loads(q_str)
                questions.append(q)
            except json.JSONDecodeError:
                continue
        if questions:
            return {"questions": questions}
    
    logger.warning(f"Failed to parse OpenAI response as JSON. Response type: {type(response_text)}")
    return None



def generate_with_openai(
    text: str,
    num_questions: int = 10,
    grade: str = "",
    subject: str = ""
) -> Optional[Dict]:
    """
    Generate quiz using OpenAI API with cost optimizations.
    
    Implements:
    - 2A: Text truncation (5K words)
    - 2B: Smart chunking with TF-IDF
    - 2C: Response caching
    
    Returns:
        Dict with quiz data or None if failed
    """
    client = _get_openai_client()
    if not client:
        return None
    
    # Check cache first (2C optimization)
    cache_key = _get_cache_key(text, num_questions, grade, subject)
    cached = _get_cached_response(cache_key)
    if cached:
        logger.info("Returning cached quiz response")
        cached["source"] = "openai_cached"
        return cached
    
    # Apply cost optimizations
    word_count = _count_words(text)
    if word_count > MAX_WORDS:
        # Use smart chunking for large texts (2A + 2B)
        processed_text = _smart_chunk_text(text, MAX_WORDS)
        logger.info(f"Text chunked: {word_count} -> {_count_words(processed_text)} words")
    else:
        processed_text = text
    
    # Build prompt
    prompt = _build_quiz_prompt(processed_text, num_questions, grade, subject)
    
    try:
        # Safe logging to avoid encoding errors on Windows
        try:
            print(f"[DEBUG] Calling OpenAI API with model: {MODEL_NAME}")
        except:
            pass  # Ignore print errors
            
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "أنت مساعد تعليمي متخصص في المناهج العراقية. أجب بصيغة JSON فقط."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=MAX_OUTPUT_TOKENS,
        )
        
        # Safe logging for response
        try:
            print(f"[DEBUG] OpenAI response received")
        except:
            pass
            
        response_text = response.choices[0].message.content
        
        # Safe logging for content length
        try:
            content_preview = response_text[:200] if response_text else 'EMPTY'
            # Remove Arabic characters for safe Windows console output
            safe_preview = content_preview.encode('ascii', errors='ignore').decode('ascii')
            print(f"[DEBUG] Response length: {len(response_text) if response_text else 0} chars")
        except:
            pass
        
        quiz_data = _parse_openai_response(response_text)
        
        if quiz_data and "questions" in quiz_data:
            quiz_data["source"] = "openai"
            quiz_data["model"] = MODEL_NAME
            quiz_data["word_count_original"] = word_count
            quiz_data["word_count_processed"] = _count_words(processed_text)
            
            # Cache successful response
            _cache_response(cache_key, quiz_data)
            
            return quiz_data
        
        logger.warning("OpenAI response did not contain valid quiz data")
        return None
        
    except Exception as e:
        # Safe error logging
        try:
            error_msg = str(e)
            # Remove Arabic/non-ASCII for safe Windows logging
            safe_error = error_msg.encode('ascii', errors='ignore').decode('ascii')
            logger.error(f"OpenAI API error: {safe_error}")
            print(f"[DEBUG] OpenAI exception: {safe_error}")
        except:
            logger.error("OpenAI API error (encoding issue in error message)")
            print("[DEBUG] OpenAI exception (encoding issue)")
        return None


def is_openai_available() -> bool:
    """Check if OpenAI API is configured and available."""
    return _get_openai_client() is not None


def get_token_estimate(text: str) -> int:
    """Estimate token count for text (rough approximation for Arabic)."""
    # Arabic typically uses ~1.5 tokens per word
    return int(_count_words(text) * 1.5)


def clear_cache() -> None:
    """Clear the quiz cache."""
    if CACHE_AVAILABLE and _cache is not None:
        _cache.clear()
        logger.info("Quiz cache cleared")
