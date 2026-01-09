"""
AI-powered quiz generation with enhanced NLP fallback.
Uses OpenAI API (gpt-5-nano) as primary, Gemini as secondary fallback,
NLP as final fallback with pattern-based generation.
"""
import os
import re
import json
import random
from typing import Dict, List, Optional, Set

# Import from the new arabic_nlp package
from .arabic_nlp import (
    split_sentences,
    tokenize_arabic,
    remove_stopwords,
    DEFAULT_STOPWORDS,
    normalize_arabic,
    extract_lemma,
    extract_root,
    get_pos,
    PatternMatcher,
    get_semantic_distractors,
    is_embeddings_available,
    get_word_family,
    prepare_text_for_analysis,
)


def generate_quiz_smart(text: str, num_questions: int = 10, grade: str = "", subject: str = "") -> Dict:
    """
    Generate quiz using AI if available, otherwise use enhanced NLP.
    
    Priority:
    1. OpenAI API (gpt-5-nano) - Primary
    2. Gemini API - Secondary fallback  
    3. Qwen2.5 Local LLM - Third fallback (if ENABLE_LOCAL_LLM=1)
    4. Enhanced NLP (pattern-based) - Final fallback
    """
    # Try OpenAI first (primary)
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        try:
            from .openai_quiz import generate_with_openai
            result = generate_with_openai(text, num_questions, grade, subject)
            if result:
                return result
        except Exception as e:
            print(f"OpenAI generation failed: {e}")
    
    # Try Gemini as secondary fallback
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            result = _generate_with_gemini(text, num_questions, grade, subject, gemini_key)
            if result:
                return result
        except Exception as e:
            print(f"Gemini generation failed: {e}")
    
    # Try Qwen2.5 Local LLM if enabled
    if os.getenv("ENABLE_LOCAL_LLM") == "1":
        try:
            from .arabic_nlp import is_llm_available
            if is_llm_available():
                print("Using Qwen2.5 local LLM for quiz generation...")
                # Use the enhanced NLP which will utilize Qwen if available
                return _generate_enhanced_nlp(text, num_questions, grade, subject)
        except Exception as e:
            print(f"Qwen2.5 generation failed: {e}")

    # Final fallback to basic enhanced NLP (pattern-based, no LLM)
    print("Using basic NLP (pattern-based) for quiz generation...")
    return _generate_enhanced_nlp(text, num_questions, grade, subject)




def _generate_with_gemini(text: str, num_questions: int, grade: str, subject: str, api_key: str) -> Optional[Dict]:
    """Generate quiz using Google Gemini API."""
    try:
        from google import genai
    except ImportError:
        try:
            # Fallback to old package if new one not installed
            import google.generativeai as genai_old
            return _generate_with_gemini_legacy(text, num_questions, grade, subject, api_key, genai_old)
        except ImportError:
            return None

    # Initialize client with API key
    client = genai.Client(api_key=api_key)

    prompt = f"""أنت معلم خبير في إنشاء الاختبارات التعليمية.
بناءً على النص التالي، أنشئ {num_questions} أسئلة متنوعة ومناسبة للمستوى الدراسي.

المادة: {subject or 'غير محدد'}
الصف: {grade or 'غير محدد'}

النص:
{text[:4000]}

المطلوب:
أنشئ أسئلة متنوعة تشمل:
1. أسئلة اختيار من متعدد (4 خيارات)
2. أسئلة صح/خطأ
3. أسئلة أكمل الفراغ
4. أسئلة قصيرة

أرجع النتيجة بتنسيق JSON فقط بدون أي نص إضافي:
{{
  "questions": [
    {{
      "type": "اختيار من متعدد",
      "question": "نص السؤال",
      "choices": ["خيار 1", "خيار 2", "خيار 3", "خيار 4"],
      "answer_index": 0
    }},
    {{
      "type": "صح/خطأ",
      "question": "نص السؤال",
      "answer": "صح"
    }},
    {{
      "type": "أكمل الفراغ",
      "question": "الجملة مع _______",
      "answer": "الكلمة الناقصة"
    }},
    {{
      "type": "سؤال قصير",
      "question": "نص السؤال",
      "answer_hint": "تلميح للإجابة"
    }}
  ]
}}"""

    # Try multiple models in case one has quota exhausted
    models_to_try = ["gemini-2.0-flash-lite", "gemini-1.5-flash", "gemini-2.0-flash"]

    response_text = None
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            response_text = response.text.strip()
            break  # Success, exit loop
        except Exception as model_error:
            print(f"Model {model_name} failed: {model_error}")
            continue

    if not response_text:
        return None

    # Extract JSON from response
    try:
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
            questions = data.get("questions", [])

            # Determine difficulty
            difficulty = "متوسط"
            if grade and any(x in grade for x in ["الرابع", "الخامس", "السادس"]):
                difficulty = "متوسط/متقدم"

            return {
                "meta": {
                    "subject": subject or "غير محدد",
                    "grade": grade or "غير محدد",
                    "difficulty": difficulty,
                    "question_count": len(questions),
                    "generated_by": "AI (Gemini)"
                },
                "questions": questions,
                "notes": [
                    "تم توليد هذه الأسئلة باستخدام الذكاء الاصطناعي.",
                    "يُفضّل أن يراجعها المعلم قبل الاعتماد النهائي."
                ]
            }
    except Exception as e:
        print(f"Gemini JSON parsing error: {e}")

    return None


def _generate_with_gemini_legacy(text: str, num_questions: int, grade: str, subject: str, api_key: str, genai) -> Optional[Dict]:
    """Generate quiz using legacy Google Generative AI package."""
    genai.configure(api_key=api_key)

    # Try different model names
    model_names = ['gemini-2.0-flash', 'gemini-1.5-flash-latest', 'gemini-pro']
    model = None

    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            break
        except Exception:
            continue

    if not model:
        return None

    prompt = f"""أنت معلم خبير في إنشاء الاختبارات التعليمية.
بناءً على النص التالي، أنشئ {num_questions} أسئلة متنوعة ومناسبة للمستوى الدراسي.

المادة: {subject or 'غير محدد'}
الصف: {grade or 'غير محدد'}

النص:
{text[:4000]}

المطلوب:
أنشئ أسئلة متنوعة تشمل:
1. أسئلة اختيار من متعدد (4 خيارات)
2. أسئلة صح/خطأ
3. أسئلة أكمل الفراغ
4. أسئلة قصيرة

أرجع النتيجة بتنسيق JSON فقط بدون أي نص إضافي:
{{
  "questions": [
    {{
      "type": "اختيار من متعدد",
      "question": "نص السؤال",
      "choices": ["خيار 1", "خيار 2", "خيار 3", "خيار 4"],
      "answer_index": 0
    }}
  ]
}}"""

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
            questions = data.get("questions", [])

            difficulty = "متوسط"
            if grade and any(x in grade for x in ["الرابع", "الخامس", "السادس"]):
                difficulty = "متوسط/متقدم"

            return {
                "meta": {
                    "subject": subject or "غير محدد",
                    "grade": grade or "غير محدد",
                    "difficulty": difficulty,
                    "question_count": len(questions),
                    "generated_by": "AI (Gemini)"
                },
                "questions": questions,
                "notes": [
                    "تم توليد هذه الأسئلة باستخدام الذكاء الاصطناعي.",
                    "يُفضّل أن يراجعها المعلم قبل الاعتماد النهائي."
                ]
            }
    except Exception as e:
        print(f"Gemini Legacy API error: {e}")

    return None


class EnhancedQuizGenerator:
    """
    Quiz generator using morphological analysis, pattern matching,
    and semantic similarity for improved question quality.
    """

    def __init__(self):
        self.pattern_matcher = PatternMatcher()
        self.used_sentences: Set[str] = set()
        self._used_generative = False

    def _get_generator_name(self) -> str:
        """Get the name of the generator used."""
        if self._used_generative:
            return "Enhanced NLP 2.0 + Qwen2.5"
        return "Enhanced NLP 2.0"

    def generate(self, text: str, num_questions: int, grade: str = "", subject: str = "") -> Dict:
        """Generate quiz with enhanced NLP techniques."""
        # Note: No fixed seed - allows different quizzes each time

        # Prepare and clean text before analysis
        text = prepare_text_for_analysis(text)

        sentences = split_sentences(text)
        tokens = remove_stopwords(tokenize_arabic(text), DEFAULT_STOPWORDS)

        questions = []

        # === Phase 1: Pattern-based question generation ===

        # 1. Extract patterns using PatternMatcher (text already cleaned)
        all_patterns = self.pattern_matcher.find_all_patterns(text)

        # 2. Generate definition questions
        for defn in all_patterns['definitions'][:3]:
            if len(questions) >= num_questions:
                break
            q = self._make_definition_question(defn)
            if q and defn['sentence'] not in self.used_sentences:
                questions.append(q)
                self.used_sentences.add(defn['sentence'])

        # 3. Generate cause-effect questions
        for ce in all_patterns['cause_effects'][:2]:
            if len(questions) >= num_questions:
                break
            q = self._make_cause_effect_question(ce)
            if q and ce['sentence'] not in self.used_sentences:
                questions.append(q)
                self.used_sentences.add(ce['sentence'])

        # 4. Generate enumeration questions
        for enum in all_patterns['enumerations'][:2]:
            if len(questions) >= num_questions:
                break
            q = self._make_enumeration_question(enum)
            if q:
                questions.append(q)

        # 5. Generate comparison questions
        for comp in all_patterns['comparisons'][:1]:
            if len(questions) >= num_questions:
                break
            q = self._make_comparison_question(comp)
            if q and comp['sentence'] not in self.used_sentences:
                questions.append(q)
                self.used_sentences.add(comp['sentence'])

        # 6. Generate True/False from factual sentences
        for fact in all_patterns['factual'][:3]:
            if len(questions) >= num_questions:
                break
            q = self._make_true_false_question(fact)
            if q and fact['sentence'] not in self.used_sentences:
                questions.append(q)
                self.used_sentences.add(fact['sentence'])

        # === Phase 1.5: Generative Model Questions (Qwen2.5) ===
        if len(questions) < num_questions:
            try:
                from .arabic_nlp import is_generative_available, generate_question

                if is_generative_available():
                    # Get sentences not yet used
                    unused_sentences = [s for s in sentences if s not in self.used_sentences and len(s) >= 30]

                    for sent in unused_sentences[:5]:  # Try up to 5 sentences
                        if len(questions) >= num_questions:
                            break

                        generated_q = generate_question(sent)
                        if generated_q and len(generated_q) > 10:
                            questions.append({
                                "type": "سؤال قصير",
                                "question": generated_q,
                                "answer_hint": sent
                            })
                            self.used_sentences.add(sent)
                            self._used_generative = True
            except ImportError:
                pass  # Generative model not available

        # === Phase 2: Term-based MCQ generation ===
        remaining = num_questions - len(questions)
        if remaining > 0:
            mcqs = self._generate_semantic_mcqs(text, sentences, tokens, remaining)
            questions.extend(mcqs)

        # === Phase 3: Fill-in-blank questions ===
        remaining = num_questions - len(questions)
        if remaining > 0:
            fill_blanks = self._generate_fill_blanks(sentences, tokens, remaining)
            questions.extend(fill_blanks)

        # Shuffle and limit
        random.shuffle(questions)
        questions = questions[:num_questions]

        # Determine difficulty
        difficulty = "متوسط"
        if grade and any(x in grade for x in ["الرابع", "الخامس", "السادس"]):
            difficulty = "متوسط/متقدم"

        return {
            "meta": {
                "subject": subject or "غير محدد",
                "grade": grade or "غير محدد",
                "difficulty": difficulty,
                "question_count": len(questions),
                "generated_by": self._get_generator_name()
            },
            "questions": questions,
            "notes": [
                "تم توليد هذه الأسئلة باستخدام تحليل لغوي متقدم.",
                "يشمل التحليل: الأنماط النحوية، التحليل الصرفي، والتشابه الدلالي.",
                "يُفضّل أن يراجعها المعلم قبل الاعتماد النهائي."
            ]
        }

    def _make_definition_question(self, defn: Dict) -> Optional[Dict]:
        """Create a question from a definition pattern."""
        term = defn.get('term', '')
        if len(term) < 3:
            return None

        return {
            "type": "سؤال قصير",
            "question": f"{defn['question_prefix']} {term}؟",
            "answer_hint": defn['sentence']
        }

    def _make_cause_effect_question(self, ce: Dict) -> Optional[Dict]:
        """Create a question from a cause-effect pattern."""
        effect = ce.get('effect', '')
        if len(effect) < 10:
            return None

        # Clean up the effect text
        effect = effect.strip()
        if effect.endswith('،') or effect.endswith(','):
            effect = effect[:-1]

        return {
            "type": "سؤال قصير",
            "question": f"{ce['question_prefix']} {effect}؟",
            "answer_hint": ce['sentence']
        }

    def _make_enumeration_question(self, enum: Dict) -> Optional[Dict]:
        """Create a question from an enumeration pattern."""
        topic = enum.get('topic', '')
        if len(topic) < 3:
            return None

        return {
            "type": "سؤال قصير",
            "question": f"{enum['question_prefix']} {topic}",
            "answer_hint": enum.get('items', '')
        }

    def _make_comparison_question(self, comp: Dict) -> Optional[Dict]:
        """Create a question from a comparison pattern."""
        item1 = comp.get('item1', '')
        item2 = comp.get('item2', '')
        if len(item1) < 2 or len(item2) < 2:
            return None

        return {
            "type": "سؤال قصير",
            "question": f"{comp['question_prefix']} {item1} و{item2}؟",
            "answer_hint": comp['sentence']
        }

    def _make_true_false_question(self, fact: Dict) -> Optional[Dict]:
        """Create a True/False question from a factual sentence."""
        sent = fact.get('sentence', '')
        if len(sent) < 20:
            return None

        # 50% chance TRUE, 50% chance FALSE
        if random.random() < 0.5:
            return {
                "type": "صح/خطأ",
                "question": f"صح أم خطأ: {sent}",
                "answer": "صح"
            }
        else:
            # Try to create a false statement
            false_sent = self._create_false_statement(sent)
            if false_sent and false_sent != sent:
                return {
                    "type": "صح/خطأ",
                    "question": f"صح أم خطأ: {false_sent}",
                    "answer": "خطأ"
                }
            else:
                # Fallback to TRUE if we can't create a false statement
                return {
                    "type": "صح/خطأ",
                    "question": f"صح أم خطأ: {sent}",
                    "answer": "صح"
                }

    def _create_false_statement(self, sentence: str) -> Optional[str]:
        """
        Create a false statement from a true sentence.

        Strategies:
        1. Negate verbs (يتكون → لا يتكون)
        2. Swap quantities (أكثر ↔ أقل, كل → بعض)
        3. Replace numbers with wrong numbers
        """
        # Strategy 1: Negate verbs
        negation_patterns = [
            (r'\bيتكون\b', 'لا يتكون'),
            (r'\bتتكون\b', 'لا تتكون'),
            (r'\bيحتوي\b', 'لا يحتوي'),
            (r'\bتحتوي\b', 'لا تحتوي'),
            (r'\bيستخدم\b', 'لا يستخدم'),
            (r'\bتستخدم\b', 'لا تستخدم'),
            (r'\bيعتبر\b', 'لا يعتبر'),
            (r'\bتعتبر\b', 'لا تعتبر'),
            (r'\bيمكن\b', 'لا يمكن'),
            (r'\bتمكن\b', 'لا تمكن'),
            (r'\bيجب\b', 'لا يجب'),
            (r'\bيساعد\b', 'لا يساعد'),
            (r'\bتساعد\b', 'لا تساعد'),
            (r'\bيؤدي\b', 'لا يؤدي'),
            (r'\bتؤدي\b', 'لا تؤدي'),
            (r'\bيوجد\b', 'لا يوجد'),
            (r'\bتوجد\b', 'لا توجد'),
            (r'\bيعمل\b', 'لا يعمل'),
            (r'\bتعمل\b', 'لا تعمل'),
        ]

        for pattern, replacement in negation_patterns:
            if re.search(pattern, sentence):
                return re.sub(pattern, replacement, sentence, count=1)

        # Strategy 2: Swap quantities
        quantity_swaps = [
            (r'\bأكثر\b', 'أقل'),
            (r'\bأقل\b', 'أكثر'),
            (r'\bكل\b', 'بعض'),
            (r'\bجميع\b', 'بعض'),
            (r'\bدائماً\b', 'أحياناً'),
            (r'\bدائما\b', 'أحيانا'),
            (r'\bفقط\b', 'أيضاً'),
            (r'\bالأكبر\b', 'الأصغر'),
            (r'\bالأصغر\b', 'الأكبر'),
            (r'\bالأول\b', 'الأخير'),
            (r'\bالأخير\b', 'الأول'),
        ]

        for pattern, replacement in quantity_swaps:
            if re.search(pattern, sentence):
                return re.sub(pattern, replacement, sentence, count=1)

        # Strategy 3: If sentence contains a number, change it
        number_match = re.search(r'\b(\d+)\b', sentence)
        if number_match:
            num = int(number_match.group(1))
            # Change the number to something different but plausible
            wrong_num = num + random.choice([-2, -1, 1, 2, 3])
            if wrong_num <= 0:
                wrong_num = num + random.randint(1, 5)
            return sentence.replace(str(num), str(wrong_num), 1)

        # Could not create a false statement
        return None

    def _generate_semantic_mcqs(self, text: str, sentences: List[str], tokens: List[str], count: int) -> List[Dict]:
        """Generate MCQs with semantically-related distractors."""
        questions = []

        # Extract key terms using lemmatization
        lemma_to_tokens: Dict[str, List[str]] = {}
        for token in tokens:
            if len(token) >= 4:
                lemma = extract_lemma(token)
                if lemma not in lemma_to_tokens:
                    lemma_to_tokens[lemma] = []
                lemma_to_tokens[lemma].append(token)

        # Count frequencies (by lemma)
        lemma_freq = {lemma: len(tokens_list) for lemma, tokens_list in lemma_to_tokens.items()}

        # Get top terms by frequency
        top_lemmas = sorted(lemma_freq.items(), key=lambda x: -x[1])[:20]

        for lemma, freq in top_lemmas:
            if len(questions) >= count:
                break
            if freq < 2:
                continue

            # Get a representative token
            term = lemma_to_tokens[lemma][0]

            # Find sentence containing this term
            target_sent = None
            for sent in sentences:
                if term in sent or lemma in normalize_arabic(sent):
                    if sent not in self.used_sentences:
                        target_sent = sent
                        break

            if not target_sent:
                continue

            # Generate distractors
            distractors = self._get_smart_distractors(term, tokens, 3)
            if len(distractors) < 3:
                continue

            # Create MCQ with varied, specific templates
            choices = [term] + distractors[:3]
            random.shuffle(choices)

            # Use diverse question templates
            mcq_templates = [
                f"ما المصطلح الذي يصف: {target_sent[:50]}...؟",
                f"اختر الكلمة المناسبة: {target_sent[:50]}...؟",
                f"أي المصطلحات التالية ورد في النص: {target_sent[:50]}...؟",
                f"ما الكلمة الصحيحة لإكمال المعنى: {target_sent[:50]}...؟",
            ]
            question_text = random.choice(mcq_templates)

            questions.append({
                "type": "اختيار من متعدد",
                "question": question_text,
                "choices": choices,
                "answer_index": choices.index(term)
            })
            self.used_sentences.add(target_sent)

        return questions

    def _get_smart_distractors(self, correct_answer: str, context_tokens: List[str], num: int) -> List[str]:
        """
        Get smart distractors using multiple strategies:
        0. Generative model (Qwen2.5 - if available)
        1. Semantic similarity (embeddings)
        2. Same-root words
        3. POS-matched context words
        4. Frequency fallback
        """
        distractors: List[str] = []
        correct_normalized = normalize_arabic(correct_answer)
        correct_lemma = extract_lemma(correct_answer)
        used: Set[str] = {correct_normalized, correct_lemma}

        # Strategy 0: Generative model distractors (Qwen2.5)
        try:
            from .arabic_nlp import is_generative_available, generate_mcq_distractors

            if is_generative_available():
                context_text = " ".join(context_tokens[:30])
                generated = generate_mcq_distractors(correct_answer, context_text, num)
                for word in generated:
                    norm = normalize_arabic(word)
                    if norm not in used and len(word) >= 2:
                        distractors.append(word)
                        used.add(norm)
                        self._used_generative = True
                        if len(distractors) >= num:
                            return distractors
        except ImportError:
            pass

        # Strategy 1: Semantic distractors (if embeddings available)
        if is_embeddings_available():
            semantic = get_semantic_distractors(correct_answer, context_tokens[:50], num)
            for word in semantic:
                norm = normalize_arabic(word)
                if norm not in used:
                    distractors.append(word)
                    used.add(norm)
                    if len(distractors) >= num:
                        return distractors

        # Strategy 2: Root-based distractors
        if len(distractors) < num:
            root = extract_root(correct_answer)
            if root:
                family = get_word_family(root, limit=5)
                for word in family:
                    norm = normalize_arabic(word)
                    if norm not in used and word != correct_answer:
                        distractors.append(word)
                        used.add(norm)
                        if len(distractors) >= num:
                            return distractors

        # Strategy 3: POS-matched distractors from context
        if len(distractors) < num:
            correct_pos = get_pos(correct_answer)
            for token in context_tokens:
                if get_pos(token) == correct_pos:
                    norm = normalize_arabic(token)
                    if norm not in used and len(token) >= 3:
                        distractors.append(token)
                        used.add(norm)
                        if len(distractors) >= num:
                            return distractors

        # Strategy 4: Frequency-based fallback (similar length)
        if len(distractors) < num:
            target_len = len(correct_answer)
            for token in context_tokens:
                if abs(len(token) - target_len) <= 3:
                    norm = normalize_arabic(token)
                    if norm not in used and len(token) >= 3:
                        distractors.append(token)
                        used.add(norm)
                        if len(distractors) >= num:
                            return distractors

        return distractors

    def _generate_fill_blanks(self, sentences: List[str], tokens: List[str], count: int) -> List[Dict]:
        """Generate fill-in-the-blank questions."""
        questions = []

        # Get important terms (by frequency and length)
        term_freq: Dict[str, int] = {}
        for token in tokens:
            if len(token) >= 4:
                term_freq[token] = term_freq.get(token, 0) + 1

        important_terms = [t for t, f in sorted(term_freq.items(), key=lambda x: -x[1])[:15]]

        for sent in sentences:
            if len(questions) >= count:
                break
            if sent in self.used_sentences:
                continue
            if len(sent) < 30:
                continue

            # Find an important term in this sentence
            sent_tokens = tokenize_arabic(sent)
            for term in important_terms:
                if term in sent_tokens:
                    # Create blank
                    blanked = sent.replace(term, "_______", 1)
                    if blanked != sent:
                        questions.append({
                            "type": "أكمل الفراغ",
                            "question": f"أكمل الفراغ:\n{blanked}",
                            "answer": term
                        })
                        self.used_sentences.add(sent)
                        break

        return questions


def _generate_enhanced_nlp(text: str, num_questions: int, grade: str, subject: str) -> Dict:
    """Generate quiz using enhanced NLP patterns (no API)."""
    generator = EnhancedQuizGenerator()
    return generator.generate(text, num_questions, grade, subject)
