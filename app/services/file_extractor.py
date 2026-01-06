"""
File text extraction service.
Supports: PDF, Word (.docx), and plain text files.
"""
import os
import re
from typing import Tuple


def _is_arabic_text_reversed(text: str) -> bool:
    """
    Detect if Arabic text is reversed (characters in wrong order).

    This happens when PDF extraction reads RTL text incorrectly,
    producing text like "بوساحلا" instead of "الحاسوب".

    Detection method: Check if common Arabic words appear reversed.
    """
    # Common Arabic words and their reversed forms
    # If we find more reversed forms than normal forms, text is likely reversed
    common_words = [
        ('من', 'نم'),
        ('في', 'يف'),
        ('على', 'ىلع'),
        ('إلى', 'ىلإ'),
        ('الى', 'ىلا'),
        ('هذا', 'اذه'),
        ('هذه', 'هذه'),  # Palindrome, skip
        ('التي', 'يتلا'),
        ('الذي', 'يذلا'),
        ('كان', 'ناك'),
        ('عن', 'نع'),
        ('مع', 'عم'),
        ('بين', 'نيب'),
        ('كل', 'لك'),
        ('بعد', 'دعب'),
        ('قبل', 'لبق'),
        ('هو', 'وه'),
        ('هي', 'يه'),
        ('أن', 'نأ'),
        ('ان', 'نا'),
        ('لم', 'مل'),
        ('أو', 'وأ'),
        ('او', 'وا'),
        ('ما', 'ام'),
        ('عند', 'دنع'),
        ('حتى', 'ىتح'),
        ('لكن', 'نكل'),
        ('ثم', 'مث'),
        ('الماء', 'ءاملا'),
        ('العلم', 'ملعلا'),
        ('الكتاب', 'باتكلا'),
        ('المدرسة', 'ةسردملا'),
        ('الطالب', 'بلاطلا'),
    ]

    normal_count = 0
    reversed_count = 0

    for normal, reversed_form in common_words:
        if normal == reversed_form:  # Skip palindromes
            continue
        # Count occurrences
        normal_count += text.count(normal)
        reversed_count += text.count(reversed_form)

    # If we found significantly more reversed words, text is reversed
    # Use a threshold to avoid false positives
    if reversed_count > normal_count and reversed_count >= 3:
        return True

    return False


def _reverse_arabic_words(text: str) -> str:
    """
    Fix reversed Arabic text by reversing each word AND word order.

    This handles PDFs where Arabic text is extracted completely backwards:
    - Characters within each word are reversed
    - Word order within each line is reversed

    Example:
        Input:  "بوساحلا نع ةمدقم" (reversed)
        Output: "مقدمة عن الحاسوب" (correct)
    """
    lines = text.split('\n')
    fixed_lines = []

    for line in lines:
        if not line.strip():
            fixed_lines.append(line)
            continue

        # Split line into words
        words = line.split()
        fixed_words = []

        for word in words:
            # Check if word contains Arabic characters
            arabic_chars = sum(1 for c in word if '\u0600' <= c <= '\u06FF')

            if arabic_chars > len(word) * 0.5:  # More than 50% Arabic
                # Reverse the characters within the word
                fixed_words.append(word[::-1])
            else:
                # Keep non-Arabic words as-is (numbers, English, etc.)
                fixed_words.append(word)

        # Reverse word order (RTL text was extracted as LTR)
        fixed_words.reverse()
        fixed_lines.append(' '.join(fixed_words))

    return '\n'.join(fixed_lines)


def _clean_extracted_text(text: str) -> str:
    """
    Clean extracted text by removing artifacts and normalizing whitespace.

    This is critical for Arabic text processing - raw PDF extraction often
    produces text with zero-width characters, excessive whitespace, and
    other artifacts that break NLP analysis.
    """
    if not text:
        return text

    # 1. Remove zero-width characters that break text processing
    zero_width_chars = [
        '\u200b',  # Zero-width space
        '\u200c',  # Zero-width non-joiner
        '\u200d',  # Zero-width joiner
        '\u200e',  # Left-to-right mark
        '\u200f',  # Right-to-left mark
        '\ufeff',  # Byte order mark
        '\u00ad',  # Soft hyphen
        '\u2060',  # Word joiner
        '\u2061',  # Function application
        '\u2062',  # Invisible times
        '\u2063',  # Invisible separator
        '\u2064',  # Invisible plus
    ]
    for char in zero_width_chars:
        text = text.replace(char, '')

    # 2. Normalize various space types to regular space
    space_chars = [
        '\u00a0',  # Non-breaking space
        '\u2000',  # En quad
        '\u2001',  # Em quad
        '\u2002',  # En space
        '\u2003',  # Em space
        '\u2004',  # Three-per-em space
        '\u2005',  # Four-per-em space
        '\u2006',  # Six-per-em space
        '\u2007',  # Figure space
        '\u2008',  # Punctuation space
        '\u2009',  # Thin space
        '\u200a',  # Hair space
        '\u202f',  # Narrow no-break space
        '\u205f',  # Medium mathematical space
        '\u3000',  # Ideographic space
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

    # 6. Collapse 3+ consecutive newlines to double newline (preserve paragraphs)
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 7. Remove lines that are only punctuation or whitespace
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # Keep line if it has at least one letter (Arabic or Latin)
        if re.search(r'[\u0600-\u06FF\u0750-\u077Fa-zA-Z]', line):
            cleaned_lines.append(line)
        elif line.strip() == '':
            # Keep empty lines (paragraph breaks)
            cleaned_lines.append('')
    text = '\n'.join(cleaned_lines)

    # 8. Final cleanup - remove leading/trailing whitespace
    text = text.strip()

    return text


def extract_text_from_file(file_storage, filename: str) -> Tuple[bool, str]:
    """
    Extract text from uploaded file.

    Args:
        file_storage: Flask FileStorage object
        filename: Original filename

    Returns:
        Tuple of (success: bool, text_or_error: str)
    """
    ext = os.path.splitext(filename)[1].lower()

    try:
        if ext == '.txt':
            return _extract_txt(file_storage)
        elif ext == '.pdf':
            return _extract_pdf(file_storage)
        elif ext == '.docx':
            return _extract_docx(file_storage)
        else:
            return False, f"نوع الملف غير مدعوم: {ext}. الأنواع المدعومة: PDF, DOCX, TXT"
    except Exception as e:
        return False, f"خطأ في قراءة الملف: {str(e)}"

def _extract_txt(file_storage) -> Tuple[bool, str]:
    """Extract text from plain text file."""
    try:
        content = file_storage.read()
        # Try UTF-8 first, then fallback to other encodings
        for encoding in ['utf-8', 'utf-8-sig', 'cp1256', 'iso-8859-6']:
            try:
                text = content.decode(encoding)
                # Apply text cleaning
                text = _clean_extracted_text(text)
                return True, text
            except UnicodeDecodeError:
                continue
        return False, "تعذر قراءة ترميز الملف النصي."
    except Exception as e:
        return False, f"خطأ في قراءة الملف النصي: {str(e)}"

def _extract_pdf(file_storage) -> Tuple[bool, str]:
    """Extract text from PDF file using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        return False, "مكتبة pdfplumber غير مثبتة. قم بتشغيل: pip install pdfplumber"

    try:
        text_parts = []
        with pdfplumber.open(file_storage) as pdf:
            for page in pdf.pages:
                # Extract text without layout mode - it causes excessive whitespace
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        if not text_parts:
            return False, "لم يتم العثور على نص في ملف PDF. قد يكون الملف يحتوي على صور فقط."

        full_text = "\n\n".join(text_parts)

        # Check if Arabic text is reversed (common PDF extraction issue)
        if _is_arabic_text_reversed(full_text):
            full_text = _reverse_arabic_words(full_text)

        # Apply comprehensive text cleaning
        full_text = _clean_extracted_text(full_text)

        return True, full_text
    except Exception as e:
        return False, f"خطأ في قراءة ملف PDF: {str(e)}"

def _extract_docx(file_storage) -> Tuple[bool, str]:
    """Extract text from Word document using python-docx."""
    try:
        from docx import Document
    except ImportError:
        return False, "مكتبة python-docx غير مثبتة. قم بتشغيل: pip install python-docx"

    try:
        doc = Document(file_storage)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]

        if not paragraphs:
            return False, "لم يتم العثور على نص في ملف Word."

        full_text = "\n\n".join(paragraphs)

        # Apply comprehensive text cleaning
        full_text = _clean_extracted_text(full_text)

        return True, full_text
    except Exception as e:
        return False, f"خطأ في قراءة ملف Word: {str(e)}"
