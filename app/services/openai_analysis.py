"""
AI-powered Arabic text analysis for student mode.
Uses OpenAI/Gemini for enhanced analysis with NLP fallback.
"""
import os
import json
import re
from typing import Dict, Optional


def analyze_with_ai(text: str, label: str = "تحليل") -> Optional[Dict]:
    """
    Analyze Arabic text using AI (OpenAI first, then Gemini fallback).
    
    Returns:
        Dict with analysis results or None if failed
    """
    # Try OpenAI first
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        result = _analyze_with_openai(text, label, openai_key)
        if result:
            return result
    
    # Try Gemini as fallback
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        result = _analyze_with_gemini(text, label, gemini_key)
        if result:
            return result
    
    return None


def _analyze_with_openai(text: str, label: str, api_key: str) -> Optional[Dict]:
    """Analyze text using OpenAI gpt-4o-mini."""
    try:
        from openai import OpenAI
        
        client = OpenAI(api_key=api_key)
        
        prompt = f"""أنت معلم لغة عربية خبير. حلل النص التالي وأعطني:

1. مستوى الصعوبة (سهل/متوسط/صعب)
2. عدد الجمل
3. عدد الكلمات
4. متوسط الكلمات لكل جملة
5. متوسط الأحرف لكل كلمة
6. قائمة بـ 5-10 كلمات قد تكون صعبة على الطالب
7. ملخص نقطي (3-5 نقاط رئيسية)
8. ملاحظات وتوصيات للطالب

النص:
{text[:3000]}

أرجع النتيجة بصيغة JSON فقط:
{{
  "difficulty": "متوسط",
  "metrics": {{
    "sentences": 10,
    "words": 150,
    "avg_words_per_sentence": 15.0,
    "avg_chars_per_word": 5.2
  }},
  "difficult_words": ["كلمة1", "كلمة2"],
  "summary_bullets": ["نقطة 1", "نقطة 2"],
  "notes": ["ملاحظة 1", "ملاحظة 2"]
}}"""

        response = client.chat.completions.create(
            model="gpt-5-mini",
            messages=[
                {"role": "system", "content": "أنت معلم لغة عربية. أجب بصيغة JSON فقط."},
                {"role": "user", "content": prompt}
            ],
            max_completion_tokens=2000,
        )
        
        response_text = response.choices[0].message.content
        
        # Parse JSON
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
            data["source"] = "openai"
            data["model"] = "gpt-5-mini"
            return data
        
        return None
        
    except Exception as e:
        print(f"OpenAI analysis error: {e}")
        return None


def _analyze_with_gemini(text: str, label: str, api_key: str) -> Optional[Dict]:
    """Analyze text using Google Gemini."""
    try:
        from google import genai
        
        client = genai.Client(api_key=api_key)
        
        prompt = f"""أنت معلم لغة عربية خبير. حلل النص التالي وأعطني:

1. مستوى الصعوبة (سهل/متوسط/صعب)
2. عدد الجمل
3. عدد الكلمات  
4. متوسط الكلمات لكل جملة
5. متوسط الأحرف لكل كلمة
6. قائمة بـ 5-10 كلمات قد تكون صعبة على الطالب
7. ملخص نقطي (3-5 نقاط رئيسية)
8. ملاحظات وتوصيات للطالب

النص:
{text[:3000]}

أرجع النتيجة بصيغة JSON فقط:
{{
  "difficulty": "متوسط",
  "metrics": {{
    "sentences": 10,
    "words": 150,
    "avg_words_per_sentence": 15.0,
    "avg_chars_per_word": 5.2
  }},
  "difficult_words": ["كلمة1", "كلمة2"],
  "summary_bullets": ["نقطة 1", "نقطة 2"],
  "notes": ["ملاحظة 1", "ملاحظة 2"]
}}"""

        response = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=prompt
        )
        
        response_text = response.text.strip()
        
        # Parse JSON
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
            data["source"] = "gemini"
            data["model"] = "gemini-2.0-flash-lite"
            return data
        
        return None
        
    except ImportError:
        # Try legacy package
        try:
            import google.generativeai as genai_old
            return _analyze_with_gemini_legacy(text, label, api_key, genai_old)
        except ImportError:
            return None
    except Exception as e:
        print(f"Gemini analysis error: {e}")
        return None


def _analyze_with_gemini_legacy(text: str, label: str, api_key: str, genai) -> Optional[Dict]:
    """Analyze text using legacy Gemini package."""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""أنت معلم لغة عربية خبير. حلل النص التالي وأعطني تحليلاً شاملاً بصيغة JSON.

النص:
{text[:3000]}

أرجع JSON فقط مع: difficulty, metrics, difficult_words, summary_bullets, notes"""

        response = model.generate_content(prompt)
        response_text = response.text.strip()
        
        json_match = re.search(r'\{[\s\S]*\}', response_text)
        if json_match:
            data = json.loads(json_match.group())
            data["source"] = "gemini"
            return data
        
        return None
    except Exception as e:
        print(f"Gemini legacy error: {e}")
        return None
