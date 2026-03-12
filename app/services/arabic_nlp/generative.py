"""
Qwen2.5-1.5B-Instruct based question generation for Arabic educational content.

This module provides generative AI capabilities for creating educational
questions in Arabic using Qwen2.5-1.5B-Instruct from Alibaba.

Model: Qwen/Qwen2.5-1.5B-Instruct (~3 GB)
- Instruction-tuned for following prompts
- Excellent multilingual support including Arabic
- Speed: 5-10 sec/question (CPU), 1-2 sec (GPU)

To enable, set environment variable:
    ENABLE_LOCAL_LLM=1
"""
import os
import re
from typing import List, Optional
from app.env import get_env

# Lazy-loaded model and tokenizer
_model = None
_tokenizer = None
_device = None
_load_attempted = False

MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

# Minimum ratio of Arabic characters required in output
MIN_ARABIC_RATIO = 0.6


def _is_enabled() -> bool:
    """Check if generative model is explicitly enabled via environment variable."""
    val = str(get_env("ENABLE_LOCAL_LLM", ""))
    return val.strip() in ("1", "true", "yes")


def _get_cache_dir() -> str:
    """Get the cache directory for model files."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cache_dir = os.path.join(base_dir, "..", "..", "data", "models", "qwen")
    os.makedirs(cache_dir, exist_ok=True)
    return cache_dir


def _load_model():
    """Lazy-load Qwen2.5 model and tokenizer."""
    global _model, _tokenizer, _device, _load_attempted

    if _load_attempted:
        return

    _load_attempted = True

    # Check if explicitly enabled
    if not _is_enabled():
        print("Local LLM (Qwen2.5) is DISABLED. Set ENABLE_LOCAL_LLM=1 to enable.")
        return

    try:
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM

        # Determine device
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading Qwen2.5-1.5B-Instruct on {_device}...")

        cache_dir = _get_cache_dir()

        # Load tokenizer
        _tokenizer = AutoTokenizer.from_pretrained(
            MODEL_NAME,
            cache_dir=cache_dir,
            trust_remote_code=True
        )

        # Load model with appropriate settings for CPU/GPU
        if _device == "cuda":
            _model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                cache_dir=cache_dir,
                torch_dtype=torch.float16,
                device_map="auto",
                trust_remote_code=True
            )
        else:
            # CPU: use float32 for compatibility
            _model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                cache_dir=cache_dir,
                torch_dtype=torch.float32,
                trust_remote_code=True
            ).to(_device)

        _model.eval()
        print("Qwen2.5-1.5B-Instruct loaded successfully!")

    except ImportError as e:
        print(f"Transformers/torch not installed: {e}")
        _model = None
        _tokenizer = None
    except Exception as e:
        print(f"Failed to load Qwen2.5 model: {e}")
        _model = None
        _tokenizer = None


def _is_valid_arabic_text(text: str) -> bool:
    """
    Validate that text is primarily Arabic and not garbage.

    Rejects:
    - Text with less than 60% Arabic characters
    - Text containing emojis
    - Text with too many repeated patterns
    - Text with excessive non-Arabic scripts
    """
    if not text or len(text) < 5:
        return False

    # Remove spaces and punctuation for character analysis
    clean_text = re.sub(r'[\s\u060C\u061B\u061F\u0640.,;:!?()[\]{}"\'-]+', '', text)

    if len(clean_text) == 0:
        return False

    # Count Arabic characters
    arabic_chars = sum(1 for c in clean_text if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F')
    arabic_ratio = arabic_chars / len(clean_text)

    if arabic_ratio < MIN_ARABIC_RATIO:
        return False

    # Check for emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U0001F900-\U0001F9FF"
        "]+",
        flags=re.UNICODE
    )
    if emoji_pattern.search(text):
        return False

    # Check for repeated garbage patterns
    words = text.split()
    if len(words) >= 3:
        word_counts = {}
        for word in words:
            word_lower = word.lower()
            word_counts[word_lower] = word_counts.get(word_lower, 0) + 1
        max_repetition = max(word_counts.values())
        if max_repetition > 3:
            return False

    return True


def _generate_with_chat(messages: List[dict], max_new_tokens: int = 128) -> Optional[str]:
    """Generate text using chat format."""
    if _model is None or _tokenizer is None:
        return None

    try:
        import torch

        # Format as chat
        text = _tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )

        inputs = _tokenizer(text, return_tensors="pt").to(_device)

        with torch.no_grad():
            outputs = _model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
                pad_token_id=_tokenizer.eos_token_id,
                eos_token_id=_tokenizer.eos_token_id,
            )

        # Decode only the new tokens
        response = _tokenizer.decode(
            outputs[0][inputs['input_ids'].shape[1]:],
            skip_special_tokens=True
        ).strip()

        return response

    except Exception as e:
        print(f"Generation failed: {e}")
        return None


def is_generative_available() -> bool:
    """
    Check if generative model dependencies are available AND enabled.

    Returns:
        True if transformers/torch are installed AND ENABLE_LOCAL_LLM=1
    """
    if not _is_enabled():
        return False

    try:
        import torch
        from transformers import AutoTokenizer
        return True
    except (ImportError, ValueError, Exception) as e:
        # ValueError can occur from huggingface-hub version mismatch
        # ImportError for missing dependencies
        # Catch all to prevent server crashes
        return False



def is_model_loaded() -> bool:
    """Check if the model is currently loaded in memory."""
    return _model is not None and _tokenizer is not None


def generate_question(context: str, answer: str = None) -> Optional[str]:
    """
    Generate a question from context using Qwen2.5.

    Args:
        context: The text to generate a question about (max ~500 chars recommended)
        answer: Optional answer to focus the question on

    Returns:
        Generated question string or None if generation fails
    """
    _load_model()
    if _model is None:
        return None

    # Build the prompt
    if answer:
        user_message = f"""أنت أستاذ عربي خبير. اقرأ النص التالي وأنشئ سؤالاً تعليمياً واحداً فقط.
الإجابة المطلوبة هي: {answer}

النص: {context[:500]}

اكتب السؤال فقط بدون أي شرح أو مقدمة:"""
    else:
        user_message = f"""أنت أستاذ عربي خبير. اقرأ النص التالي وأنشئ سؤالاً تعليمياً واحداً فقط.

النص: {context[:500]}

اكتب السؤال فقط بدون أي شرح أو مقدمة:"""

    messages = [
        {"role": "system", "content": "أنت مساعد تعليمي عربي. تجيب بالعربية فقط وبشكل مختصر."},
        {"role": "user", "content": user_message}
    ]

    response = _generate_with_chat(messages, max_new_tokens=100)

    if not response:
        return None

    # Clean up response
    question = response.strip()

    # Remove common prefixes the model might add
    prefixes_to_remove = [
        "السؤال:", "السؤال هو:", "سؤال:", "س:",
        "Question:", "Q:", "هنا السؤال:",
    ]
    for prefix in prefixes_to_remove:
        if question.startswith(prefix):
            question = question[len(prefix):].strip()

    # Validate
    if not _is_valid_arabic_text(question):
        print(f"Rejected invalid question: {question[:50]}...")
        return None

    if len(question) < 10:
        return None

    # Ensure it ends with question mark
    if not question.endswith('؟') and not question.endswith('?'):
        question += '؟'

    return question


def generate_questions_batch(contexts: List[str], num_per_context: int = 1) -> List[str]:
    """Generate questions for multiple contexts."""
    _load_model()
    if _model is None:
        return []

    questions = []
    for context in contexts:
        for _ in range(num_per_context):
            q = generate_question(context)
            if q:
                questions.append(q)

    return questions


def generate_mcq_distractors(correct_answer: str, context: str, num: int = 3) -> List[str]:
    """
    Generate plausible wrong answers (distractors) for MCQ.

    Args:
        correct_answer: The correct answer
        context: The context/passage
        num: Number of distractors to generate

    Returns:
        List of distractor strings
    """
    _load_model()
    if _model is None:
        return []

    user_message = f"""أنت أستاذ عربي تنشئ اختبارات.
الإجابة الصحيحة هي: {correct_answer}
السياق: {context[:200]}

أنشئ {num} إجابات خاطئة ولكن معقولة (مشتتات) لسؤال اختيار من متعدد.
اكتب كل إجابة في سطر منفصل، بدون ترقيم:"""

    messages = [
        {"role": "system", "content": "أنت مساعد تعليمي. تجيب بالعربية فقط."},
        {"role": "user", "content": user_message}
    ]

    response = _generate_with_chat(messages, max_new_tokens=150)

    if not response:
        return []

    # Parse distractors from response
    distractors = []
    seen = {correct_answer.strip().lower()}

    lines = response.strip().split('\n')
    for line in lines:
        # Clean the line
        distractor = line.strip()

        # Remove numbering if present
        distractor = re.sub(r'^[\d\-\.\)]+\s*', '', distractor)
        distractor = distractor.strip()

        if not distractor:
            continue
        if distractor.lower() in seen:
            continue
        if not _is_valid_arabic_text(distractor):
            continue
        if len(distractor) < 2:
            continue

        distractors.append(distractor)
        seen.add(distractor.lower())

        if len(distractors) >= num:
            break

    return distractors[:num]


def paraphrase_question(question: str) -> str:
    """
    Paraphrase/improve an existing question.

    Args:
        question: Original question

    Returns:
        Paraphrased question or original if paraphrasing fails
    """
    _load_model()
    if _model is None:
        return question

    user_message = f"""أعد صياغة هذا السؤال بطريقة مختلفة مع الحفاظ على المعنى:
{question}

اكتب السؤال المُعاد صياغته فقط:"""

    messages = [
        {"role": "system", "content": "أنت مساعد لغوي عربي."},
        {"role": "user", "content": user_message}
    ]

    response = _generate_with_chat(messages, max_new_tokens=100)

    if not response:
        return question

    paraphrased = response.strip()

    if not _is_valid_arabic_text(paraphrased):
        return question

    if len(paraphrased) < 10 or paraphrased == question:
        return question

    if not paraphrased.endswith('؟') and not paraphrased.endswith('?'):
        paraphrased += '؟'

    return paraphrased


def summarize_for_question(text: str, max_length: int = 100) -> str:
    """
    Summarize text to extract key information for question generation.

    Args:
        text: Long text to summarize
        max_length: Maximum length of summary

    Returns:
        Summarized text or original if summarization fails
    """
    _load_model()
    if _model is None or len(text) <= max_length:
        return text[:max_length] if len(text) > max_length else text

    user_message = f"""لخّص النص التالي في جملة أو جملتين:
{text[:500]}

الملخص:"""

    messages = [
        {"role": "system", "content": "أنت مساعد للتلخيص. تجيب بالعربية."},
        {"role": "user", "content": user_message}
    ]

    response = _generate_with_chat(messages, max_new_tokens=max_length)

    if not response:
        return text[:max_length]

    summary = response.strip()

    if not _is_valid_arabic_text(summary):
        return text[:max_length]

    return summary if summary else text[:max_length]


def unload_model():
    """Unload the model from memory to free up RAM."""
    global _model, _tokenizer, _device, _load_attempted

    if _model is not None:
        del _model
        _model = None

    if _tokenizer is not None:
        del _tokenizer
        _tokenizer = None

    _load_attempted = False

    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass

    print("Qwen2.5 model unloaded from memory")
