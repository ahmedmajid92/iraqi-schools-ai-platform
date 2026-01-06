"""
Arabic grammatical patterns for question and answer extraction.
Enhanced pattern matching for educational content.
"""
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class QuestionType(Enum):
    """Types of questions that can be generated."""
    DEFINITION = "تعريف"
    CAUSE_EFFECT = "سبب ونتيجة"
    COMPARISON = "مقارنة"
    ENUMERATION = "تعداد"
    PROCESS = "عملية/خطوات"
    FACTUAL = "حقيقة"
    TRUE_FALSE = "صح/خطأ"
    MCQ = "اختيار من متعدد"
    FILL_BLANK = "أكمل الفراغ"
    SHORT_ANSWER = "إجابة قصيرة"


@dataclass
class PatternMatch:
    """Represents a matched pattern in text."""
    pattern_type: QuestionType
    sentence: str
    groups: Tuple[str, ...]
    start: int
    end: int
    confidence: float = 1.0


# === Definition Patterns (تعريفات) ===
# Note: Patterns use [\u0600-\u06FF]+ (no spaces) to match SINGLE WORDS only
# The _is_valid_term() method provides additional validation
DEFINITION_PATTERNS = [
    # X هو Y / X هي Y - match 1-2 words (no space in first part OR one space max)
    (r'([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+هو\s+(.{10,})', 'ما هو', QuestionType.DEFINITION),
    (r'([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+هي\s+(.{10,})', 'ما هي', QuestionType.DEFINITION),

    # يُعرَّف / تُعرَّف
    (r'يُعرَّف\s+([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+بأنه?\s+(.+)', 'عرّف', QuestionType.DEFINITION),
    (r'تُعرَّف\s+([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+بأنها?\s+(.+)', 'عرّفي', QuestionType.DEFINITION),
    (r'يعرف\s+([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+بأنه?\s+(.+)', 'عرّف', QuestionType.DEFINITION),
    (r'تعرف\s+([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+بأنها?\s+(.+)', 'عرّفي', QuestionType.DEFINITION),

    # المقصود بـ / يُقصد بـ
    (r'المقصود\s+ب([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+(.+)', 'ما المقصود بـ', QuestionType.DEFINITION),
    (r'يُقصد\s+ب([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+(.+)', 'ما المقصود بـ', QuestionType.DEFINITION),
    (r'يقصد\s+ب([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+(.+)', 'ما المقصود بـ', QuestionType.DEFINITION),
    (r'المراد\s+ب([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+(.+)', 'ما المراد بـ', QuestionType.DEFINITION),

    # نعني بـ / يعني
    (r'نعني\s+ب([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+(.+)', 'ماذا نعني بـ', QuestionType.DEFINITION),
    (r'([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+يعني\s+(.+)', 'ما معنى', QuestionType.DEFINITION),
    (r'([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+تعني\s+(.+)', 'ما معنى', QuestionType.DEFINITION),

    # يُسمى / تُسمى
    (r'يُسمى\s+(.{5,30}?)\s+ب?([\u0600-\u06FF]+)', 'ما اسم', QuestionType.DEFINITION),
    (r'تُسمى\s+(.{5,30}?)\s+ب?([\u0600-\u06FF]+)', 'ما اسم', QuestionType.DEFINITION),
    (r'يسمى\s+(.{5,30}?)\s+ب?([\u0600-\u06FF]+)', 'ما اسم', QuestionType.DEFINITION),
    (r'تسمى\s+(.{5,30}?)\s+ب?([\u0600-\u06FF]+)', 'ما اسم', QuestionType.DEFINITION),

    # عبارة عن
    (r'([\u0600-\u06FF]+(?:\s+[\u0600-\u06FF]+)?)\s+عبارة\s+عن\s+(.+)', 'ما هو', QuestionType.DEFINITION),
]

# === Cause-Effect Patterns (السبب والنتيجة) ===
CAUSE_EFFECT_PATTERNS = [
    # لأن / بسبب / نتيجة
    (r'(.{10,})\s+لأن\s+(.+)', 'لماذا', QuestionType.CAUSE_EFFECT),
    (r'(.{10,})\s+لأنّ\s+(.+)', 'لماذا', QuestionType.CAUSE_EFFECT),
    (r'(.{10,})\s+بسبب\s+(.+)', 'ما سبب', QuestionType.CAUSE_EFFECT),
    (r'(.{10,})\s+نتيجة\s+(.+)', 'ما نتيجة', QuestionType.CAUSE_EFFECT),
    (r'(.{10,})\s+نتيجة\s+ل(.+)', 'ما نتيجة', QuestionType.CAUSE_EFFECT),

    # يؤدي إلى / تؤدي إلى
    (r'([\u0600-\u06FF\s]+?)\s+يؤدي\s+إلى\s+(.+)', 'ما نتيجة', QuestionType.CAUSE_EFFECT),
    (r'([\u0600-\u06FF\s]+?)\s+تؤدي\s+إلى\s+(.+)', 'ما نتيجة', QuestionType.CAUSE_EFFECT),
    (r'([\u0600-\u06FF\s]+?)\s+يؤدي\s+الى\s+(.+)', 'ما نتيجة', QuestionType.CAUSE_EFFECT),
    (r'([\u0600-\u06FF\s]+?)\s+تؤدي\s+الى\s+(.+)', 'ما نتيجة', QuestionType.CAUSE_EFFECT),

    # ينتج عن / تنتج عن
    (r'ينتج\s+عن\s+([\u0600-\u06FF\s]+?)\s+(.+)', 'ماذا ينتج عن', QuestionType.CAUSE_EFFECT),
    (r'تنتج\s+عن\s+([\u0600-\u06FF\s]+?)\s+(.+)', 'ماذا ينتج عن', QuestionType.CAUSE_EFFECT),

    # مما أدى / مما يؤدي
    (r'(.+?)\s+مما\s+أدى\s+إلى\s+(.+)', 'ما نتيجة', QuestionType.CAUSE_EFFECT),
    (r'(.+?)\s+مما\s+يؤدي\s+إلى\s+(.+)', 'ما نتيجة', QuestionType.CAUSE_EFFECT),

    # نظراً لـ / بناءً على
    (r'(.+?)\s+نظراً\s+ل(.+)', 'علل', QuestionType.CAUSE_EFFECT),
    (r'(.+?)\s+نظرا\s+ل(.+)', 'علل', QuestionType.CAUSE_EFFECT),
    (r'(.+?)\s+بناءً\s+على\s+(.+)', 'ما أساس', QuestionType.CAUSE_EFFECT),

    # وذلك لأن / ويرجع ذلك إلى
    (r'(.+?)\s+وذلك\s+لأن\s+(.+)', 'علل', QuestionType.CAUSE_EFFECT),
    (r'(.+?)\s+ويرجع\s+ذلك\s+إلى\s+(.+)', 'ما سبب', QuestionType.CAUSE_EFFECT),

    # يسبب / تسبب
    (r'([\u0600-\u06FF\s]+?)\s+يسبب\s+(.+)', 'ما الذي يسببه', QuestionType.CAUSE_EFFECT),
    (r'([\u0600-\u06FF\s]+?)\s+تسبب\s+(.+)', 'ما الذي تسببه', QuestionType.CAUSE_EFFECT),
]

# === Comparison Patterns (المقارنة) ===
COMPARISON_PATTERNS = [
    # الفرق بين
    (r'الفرق\s+بين\s+([\u0600-\u06FF\s]+?)\s+و([\u0600-\u06FF\s]+)', 'ما الفرق بين', QuestionType.COMPARISON),

    # يختلف عن
    (r'([\u0600-\u06FF\s]+?)\s+يختلف\s+عن\s+([\u0600-\u06FF\s]+?)\s+في\s+(.+)', 'قارن بين', QuestionType.COMPARISON),
    (r'([\u0600-\u06FF\s]+?)\s+تختلف\s+عن\s+([\u0600-\u06FF\s]+?)\s+في\s+(.+)', 'قارن بين', QuestionType.COMPARISON),

    # أكثر / أقل
    (r'([\u0600-\u06FF\s]+?)\s+أكثر\s+([\u0600-\u06FF\s]+?)\s+من\s+([\u0600-\u06FF\s]+)', 'قارن', QuestionType.COMPARISON),
    (r'([\u0600-\u06FF\s]+?)\s+أقل\s+([\u0600-\u06FF\s]+?)\s+من\s+([\u0600-\u06FF\s]+)', 'قارن', QuestionType.COMPARISON),

    # بينما / في حين
    (r'بينما\s+(.+?)[،,]\s*(.+)', 'قارن', QuestionType.COMPARISON),
    (r'في\s+حين\s+(.+?)[،,]\s*(.+)', 'قارن', QuestionType.COMPARISON),

    # على عكس / بخلاف
    (r'([\u0600-\u06FF\s]+?)\s+على\s+عكس\s+([\u0600-\u06FF\s]+)', 'قارن', QuestionType.COMPARISON),
    (r'([\u0600-\u06FF\s]+?)\s+بخلاف\s+([\u0600-\u06FF\s]+)', 'قارن', QuestionType.COMPARISON),

    # مقارنة بـ
    (r'([\u0600-\u06FF\s]+?)\s+مقارنة\s+ب([\u0600-\u06FF\s]+)', 'قارن', QuestionType.COMPARISON),

    # يشبه / تشبه
    (r'([\u0600-\u06FF\s]+?)\s+يشبه\s+([\u0600-\u06FF\s]+?)\s+في\s+(.+)', 'ما أوجه التشابه بين', QuestionType.COMPARISON),
    (r'([\u0600-\u06FF\s]+?)\s+تشبه\s+([\u0600-\u06FF\s]+?)\s+في\s+(.+)', 'ما أوجه التشابه بين', QuestionType.COMPARISON),
]

# === Enumeration Patterns (التعداد) ===
ENUMERATION_PATTERNS = [
    # أولاً، ثانياً، ثالثاً
    (r'(أولاً|أولا)[:\s]+(.+)', 'list_item', QuestionType.ENUMERATION),
    (r'(ثانياً|ثانيا)[:\s]+(.+)', 'list_item', QuestionType.ENUMERATION),
    (r'(ثالثاً|ثالثا)[:\s]+(.+)', 'list_item', QuestionType.ENUMERATION),
    (r'(رابعاً|رابعا)[:\s]+(.+)', 'list_item', QuestionType.ENUMERATION),
    (r'(خامساً|خامسا)[:\s]+(.+)', 'list_item', QuestionType.ENUMERATION),

    # Numbered lists
    (r'(\d+)[.)\-:]\s*(.+)', 'numbered_item', QuestionType.ENUMERATION),

    # Arabic letter lists
    (r'([أبتثجحخ])[.)\-:]\s*(.+)', 'lettered_item', QuestionType.ENUMERATION),

    # Bullet points
    (r'[•\-\*]\s*(.+)', 'bullet_item', QuestionType.ENUMERATION),

    # من أهم / من أبرز
    (r'من\s+أهم\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'اذكر أهم', QuestionType.ENUMERATION),
    (r'من\s+أبرز\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'اذكر أبرز', QuestionType.ENUMERATION),

    # تتكون من / يتكون من
    (r'([\u0600-\u06FF\s]+?)\s+يتكون\s+من\s+(.+)', 'مما يتكون', QuestionType.ENUMERATION),
    (r'([\u0600-\u06FF\s]+?)\s+تتكون\s+من\s+(.+)', 'مما تتكون', QuestionType.ENUMERATION),

    # تشمل / يشمل
    (r'([\u0600-\u06FF\s]+?)\s+يشمل\s+(.+)', 'ماذا يشمل', QuestionType.ENUMERATION),
    (r'([\u0600-\u06FF\s]+?)\s+تشمل\s+(.+)', 'ماذا تشمل', QuestionType.ENUMERATION),

    # أنواع / أقسام
    (r'أنواع\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'اذكر أنواع', QuestionType.ENUMERATION),
    (r'أقسام\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'اذكر أقسام', QuestionType.ENUMERATION),

    # خصائص / صفات / مميزات
    (r'خصائص\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'اذكر خصائص', QuestionType.ENUMERATION),
    (r'صفات\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'اذكر صفات', QuestionType.ENUMERATION),
    (r'مميزات\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'اذكر مميزات', QuestionType.ENUMERATION),
]

# === Process/Steps Patterns (العمليات والخطوات) ===
PROCESS_PATTERNS = [
    # خطوات
    (r'خطوات\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'اذكر خطوات', QuestionType.PROCESS),

    # مراحل
    (r'مراحل\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'اذكر مراحل', QuestionType.PROCESS),

    # لكي / حتى
    (r'لكي\s+(.+?)\s+يجب\s+(.+)', 'كيف', QuestionType.PROCESS),
    (r'حتى\s+(.+?)\s+يجب\s+(.+)', 'كيف', QuestionType.PROCESS),

    # يتم عن طريق
    (r'يتم\s+([\u0600-\u06FF\s]+?)\s+عن\s+طريق\s+(.+)', 'كيف يتم', QuestionType.PROCESS),
    (r'تتم\s+([\u0600-\u06FF\s]+?)\s+عن\s+طريق\s+(.+)', 'كيف تتم', QuestionType.PROCESS),

    # طريقة / كيفية
    (r'طريقة\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'ما طريقة', QuestionType.PROCESS),
    (r'كيفية\s+([\u0600-\u06FF\s]+?)[:\s]+(.+)', 'كيف', QuestionType.PROCESS),

    # يُصنع / تُصنع
    (r'([\u0600-\u06FF\s]+?)\s+يُصنع\s+من\s+(.+)', 'كيف يُصنع', QuestionType.PROCESS),
    (r'([\u0600-\u06FF\s]+?)\s+تُصنع\s+من\s+(.+)', 'كيف تُصنع', QuestionType.PROCESS),
]

# === Factual Keywords (للأسئلة الحقائقية) ===
FACTUAL_KEYWORDS = [
    'يتكون', 'تتكون', 'يحتوي', 'تحتوي',
    'يتميز', 'تتميز', 'يستخدم', 'تستخدم',
    'يعتبر', 'تعتبر', 'يمثل', 'تمثل',
    'يشمل', 'تشمل', 'يضم', 'تضم',
    'يبلغ', 'تبلغ', 'يصل', 'تصل',
    'ينقسم', 'تنقسم', 'يتضمن', 'تتضمن',
    'يقع', 'تقع', 'يوجد', 'توجد',
    'يعمل', 'تعمل', 'يساعد', 'تساعد',
    'يؤثر', 'تؤثر', 'يرتبط', 'ترتبط',
]


class PatternMatcher:
    """
    Enhanced pattern matching for Arabic educational content.
    Extracts question-worthy patterns from text.
    """

    def __init__(self, use_morphology: bool = False):
        """
        Initialize pattern matcher.

        Args:
            use_morphology: Whether to use morphological analysis (requires CAMeL)
        """
        self.use_morphology = use_morphology
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regex patterns for efficiency."""
        self._definition_re = [(re.compile(p, re.UNICODE), q, t)
                               for p, q, t in DEFINITION_PATTERNS]
        self._cause_effect_re = [(re.compile(p, re.UNICODE), q, t)
                                 for p, q, t in CAUSE_EFFECT_PATTERNS]
        self._comparison_re = [(re.compile(p, re.UNICODE), q, t)
                               for p, q, t in COMPARISON_PATTERNS]
        self._enumeration_re = [(re.compile(p, re.UNICODE), q, t)
                                for p, q, t in ENUMERATION_PATTERNS]
        self._process_re = [(re.compile(p, re.UNICODE), q, t)
                            for p, q, t in PROCESS_PATTERNS]

    def find_definitions(self, text: str) -> List[Dict]:
        """
        Extract definition sentences with terms and definitions.

        Returns:
            List of dicts with keys: 'term', 'definition', 'sentence', 'question_prefix'
        """
        results = []
        sentences = self._split_sentences(text)
        seen_terms = set()  # Avoid duplicate terms

        for sent in sentences:
            for pattern, question_prefix, _ in self._definition_re:
                match = pattern.search(sent)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        term = self._clean_term(groups[0])
                        definition = groups[1].strip()

                        # Validate the term is a proper single word or short phrase
                        if not self._is_valid_term(term):
                            continue

                        # Skip if we've already seen this term
                        if term in seen_terms:
                            continue

                        if len(definition) >= 10:
                            seen_terms.add(term)
                            results.append({
                                'term': term,
                                'definition': definition,
                                'sentence': sent.strip(),
                                'question_prefix': question_prefix,
                                'type': QuestionType.DEFINITION.value
                            })
                    break  # One match per sentence

        return results

    def find_cause_effects(self, text: str) -> List[Dict]:
        """
        Extract cause-effect relationships.

        Returns:
            List of dicts with keys: 'cause', 'effect', 'sentence', 'question_prefix'
        """
        results = []
        sentences = self._split_sentences(text)

        for sent in sentences:
            for pattern, question_prefix, _ in self._cause_effect_re:
                match = pattern.search(sent)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        # Order depends on pattern (some are effect-cause, some cause-effect)
                        part1 = groups[0].strip()
                        part2 = groups[1].strip()
                        if len(part1) >= 10 and len(part2) >= 5:
                            results.append({
                                'effect': part1,
                                'cause': part2,
                                'sentence': sent.strip(),
                                'question_prefix': question_prefix,
                                'type': QuestionType.CAUSE_EFFECT.value
                            })
                    break

        return results

    def find_comparisons(self, text: str) -> List[Dict]:
        """
        Extract comparison statements.

        Returns:
            List of dicts with keys: 'item1', 'item2', 'aspect', 'sentence', 'question_prefix'
        """
        results = []
        sentences = self._split_sentences(text)

        for sent in sentences:
            for pattern, question_prefix, _ in self._comparison_re:
                match = pattern.search(sent)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        item1 = groups[0].strip()
                        item2 = groups[1].strip()
                        aspect = groups[2].strip() if len(groups) > 2 else ""
                        if len(item1) >= 2 and len(item2) >= 2:
                            results.append({
                                'item1': item1,
                                'item2': item2,
                                'aspect': aspect,
                                'sentence': sent.strip(),
                                'question_prefix': question_prefix,
                                'type': QuestionType.COMPARISON.value
                            })
                    break

        return results

    def find_enumerations(self, text: str) -> List[Dict]:
        """
        Extract enumerated lists and their topics.

        Returns:
            List of dicts with keys: 'topic', 'items', 'sentence', 'question_prefix'
        """
        results = []
        sentences = self._split_sentences(text)

        # Track enumeration sequences
        current_topic = None
        current_items = []

        for i, sent in enumerate(sentences):
            for pattern, marker, _ in self._enumeration_re:
                match = pattern.search(sent)
                if match:
                    groups = match.groups()

                    if marker in ['list_item', 'numbered_item', 'lettered_item', 'bullet_item']:
                        # This is a list item
                        item_text = groups[-1].strip() if groups else sent.strip()
                        current_items.append(item_text)

                        # Check if previous sentence has topic
                        if current_topic is None and i > 0:
                            current_topic = sentences[i - 1].strip()
                    else:
                        # This is a topic-item pattern
                        if len(groups) >= 2:
                            results.append({
                                'topic': groups[0].strip(),
                                'items': groups[1].strip(),
                                'sentence': sent.strip(),
                                'question_prefix': marker,
                                'type': QuestionType.ENUMERATION.value
                            })
                    break

        # Finalize any collected enumeration
        if current_items and current_topic:
            results.append({
                'topic': current_topic,
                'items': '، '.join(current_items[:5]),  # Limit to 5 items
                'sentence': current_topic,
                'question_prefix': 'اذكر',
                'type': QuestionType.ENUMERATION.value
            })

        return results

    def find_processes(self, text: str) -> List[Dict]:
        """
        Extract process/steps descriptions.

        Returns:
            List of dicts with keys: 'process', 'steps', 'sentence', 'question_prefix'
        """
        results = []
        sentences = self._split_sentences(text)

        for sent in sentences:
            for pattern, question_prefix, _ in self._process_re:
                match = pattern.search(sent)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        process = groups[0].strip()
                        steps = groups[1].strip()
                        if len(process) >= 3 and len(steps) >= 10:
                            results.append({
                                'process': process,
                                'steps': steps,
                                'sentence': sent.strip(),
                                'question_prefix': question_prefix,
                                'type': QuestionType.PROCESS.value
                            })
                    break

        return results

    def find_factual_sentences(self, text: str) -> List[Dict]:
        """
        Find sentences containing factual statements.

        Returns:
            List of dicts with keys: 'sentence', 'keyword'
        """
        results = []
        sentences = self._split_sentences(text)

        for sent in sentences:
            for keyword in FACTUAL_KEYWORDS:
                if keyword in sent and len(sent) >= 20:
                    results.append({
                        'sentence': sent.strip(),
                        'keyword': keyword,
                        'type': QuestionType.FACTUAL.value
                    })
                    break

        return results

    def find_all_patterns(self, text: str) -> Dict[str, List[Dict]]:
        """
        Find all pattern types in text.

        Returns:
            Dict with keys for each pattern type
        """
        return {
            'definitions': self.find_definitions(text),
            'cause_effects': self.find_cause_effects(text),
            'comparisons': self.find_comparisons(text),
            'enumerations': self.find_enumerations(text),
            'processes': self.find_processes(text),
            'factual': self.find_factual_sentences(text),
        }

    def suggest_question_type(self, sentence: str) -> Optional[QuestionType]:
        """
        Suggest the best question type for a given sentence.

        Args:
            sentence: The sentence to analyze

        Returns:
            Suggested QuestionType or None
        """
        # Check each pattern type
        for pattern, _, qtype in self._definition_re:
            if pattern.search(sentence):
                return qtype

        for pattern, _, qtype in self._cause_effect_re:
            if pattern.search(sentence):
                return qtype

        for pattern, _, qtype in self._comparison_re:
            if pattern.search(sentence):
                return qtype

        for pattern, _, qtype in self._enumeration_re:
            if pattern.search(sentence):
                return qtype

        for pattern, _, qtype in self._process_re:
            if pattern.search(sentence):
                return qtype

        # Check for factual keywords
        for keyword in FACTUAL_KEYWORDS:
            if keyword in sentence:
                return QuestionType.FACTUAL

        return None

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences with text preparation."""
        from .core import prepare_text_for_analysis

        # Clean and normalize text first
        text = prepare_text_for_analysis(text)

        # Normalize Arabic punctuation
        t = text.replace("؟", "?").replace("؛", ";").replace("،", ",")
        # Split on sentence-ending punctuation
        parts = re.split(r"[\.!\?\n;]+", t)
        return [p.strip() for p in parts if p.strip() and len(p.strip()) >= 10]

    def _is_valid_term(self, term: str) -> bool:
        """
        Validate that a term is a proper single word or short phrase.

        Rejects:
        - Terms with < 2 characters
        - Terms with > 2 words (too long)
        - Terms with < 70% Arabic characters

        Args:
            term: The term to validate

        Returns:
            True if valid, False otherwise
        """
        if not term:
            return False

        term = term.strip()

        # Reject very short terms
        if len(term) < 2:
            return False

        # Count words (split on whitespace)
        words = term.split()
        if len(words) > 2:
            # Allow compound terms up to 2 words only
            return False

        # Check Arabic character ratio
        arabic_chars = sum(1 for c in term if '\u0600' <= c <= '\u06FF')
        total_chars = len(term.replace(' ', ''))
        if total_chars == 0:
            return False

        arabic_ratio = arabic_chars / total_chars
        if arabic_ratio < 0.7:
            return False

        return True

    def _clean_term(self, term: str) -> str:
        """Clean and normalize a term."""
        if not term:
            return term

        # Remove leading/trailing whitespace
        term = term.strip()

        # Remove excessive internal whitespace
        term = ' '.join(term.split())

        return term
