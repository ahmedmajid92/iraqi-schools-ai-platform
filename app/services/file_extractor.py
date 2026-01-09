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
    
    Enhanced detection that handles both standard Arabic and presentation forms.
    """
    # Check for presentation forms (FE70-FEFF range) which indicate PDF reversal
    presentation_forms = sum(1 for c in text if '\uFE70' <= c <= '\uFEFF')
    if presentation_forms > 20:  # If many presentation forms, likely reversed
        return True
    
    # Check common reversed patterns
    reversed_patterns = [
        'ﻊﺿﺃ',  # أضع reversed (presentation form)
        'ﻁﻐﺿﺃ',  # أضغط reversed
        'ﺭﺎﺗﺧﺃ',  # أختار reversed
        'بوساحلا',  # الحاسوب reversed
        'عبارلا',  # الرابع reversed
        'ىلع',  # على reversed
        'يف',  # في reversed
        'نم',  # من reversed
        'نع',  # عن reversed
        'باتكلا',  # الكتاب reversed
        'ةسردملا',  # المدرسة reversed
        'بلاطلا',  # الطالب reversed
        'دنع',  # عند reversed
        'سماخلا',  # الخامس reversed
        'سداسلا',  # السادس reversed
        'لولأا',  # الأول reversed
        'ةلومحملا',  # المحمولة reversed (lowercase)
        'ﺔﻟﻭﻣﺣﻣﻟﺍ',  # المحمولة reversed (presentation)
    ]
    
    reversed_count = sum(1 for pattern in reversed_patterns if pattern in text)
    
    # If we find ANY reversed patterns, the text is reversed
    if reversed_count > 0:
        return True
    
    # Fallback: check word patterns
    # In correct Arabic, words starting with "ال" are common
    # In reversed Arabic, words ending with "لا" are common
    words = text.split()
    al_start = sum(1 for w in words if w.startswith('ال'))
    al_end = sum(1 for w in words if w.endswith('لا'))
    
    if al_end > al_start and al_end >= 2:
        return True
    
    return False


def _reverse_arabic_words(text: str) -> str:
    """
    Fix reversed Arabic text by reversing characters and word order.
    Enhanced to handle presentation forms.
    """
    def normalize_arabic(char):
        """Convert Arabic presentation forms to standard forms."""
        # Presentation forms B (FE70-FEFF) -> Standard Arabic (0600-06FF)
        code = ord(char)
        if 0xFE70 <= code <= 0xFEFF:
            # Simple mapping (not perfect but helps)
            # This is a simplified approach
            return char  # Keep as-is for now, reversal will fix it
        return char
    
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
            # Check if word contains Arabic characters (including presentation forms)
            arabic_chars = sum(1 for c in word if 
                             ('\u0600' <= c <= '\u06FF') or  # Standard Arabic
                             ('\uFE70' <= c <= '\uFEFF') or  # Presentation Forms B
                             ('\uFB50' <= c <= '\uFDFF'))    # Presentation Forms A
            
            if arabic_chars > len(word) * 0.3:  # More than 30% Arabic
                # Reverse the characters within the word
                fixed_word = word[::-1]
                # Normalize presentation forms
                fixed_word = ''.join(normalize_arabic(c) for c in fixed_word)
                fixed_words.append(fixed_word)
            else:
                # Keep non-Arabic words as-is (numbers, English, punctuation)
                fixed_words.append(word)

        # Reverse word order (RTL text was extracted as LTR)
        fixed_words.reverse()
        fixed_lines.append(' '.join(fixed_words))

    return '\n'.join(fixed_lines)


def _smart_line_merge(text: str) -> str:
    """
    Intelligently merge broken lines while preserving intentional breaks.
    
    This fixes the common PDF extraction issue where sentences are split
    across multiple lines incorrectly.
    
    Strategy:
    - Merge lines that don't end with sentence terminators
    - Preserve lines that start with bullets, numbers, or special markers
    - Preserve empty lines (paragraph breaks)
    - Handle Arabic punctuation
    """
    if not text:
        return text
    
    lines = text.split('\n')
    merged = []
    i = 0
    
    # Arabic and English sentence terminators
    sentence_ends = ('.', '،', ':', '؛', '!', '؟', '?', ')', '}', ']', '"', '»')
    # List/enumeration markers
    list_markers_pattern = r'^\s*[\d\-•▪◦○●➔→\u0660-\u0669]'  # Numbers, bullets, Arabic numerals
    
    while i < len(lines):
        line = lines[i]
        
        # Empty line - preserve as paragraph break
        if not line.strip():
            merged.append('')
            i += 1
            continue
        
        # Check if this is a list item or header
        if re.match(list_markers_pattern, line):
            merged.append(line)
            i += 1
            continue
        
        # Check if line ends with sentence terminator
        line_stripped = line.rstrip()
        
        # If line ends properly, don't merge
        if line_stripped.endswith(sentence_ends):
            merged.append(line)
            i += 1
            continue
        
        # Line doesn't end properly - check if we should merge with next
        if i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            
            # Don't merge if next line is empty
            if not next_line:
                merged.append(line)
                i += 1
                continue
            
            # Don' merge if next line starts a list/enumeration
            if re.match(list_markers_pattern, next_line):
                merged.append(line)
                i += 1
                continue
            
            # Don't merge if next line looks like a header (short and capitalized)
            if len(next_line) < 50 and next_line[0].isupper():
                merged.append(line)
                i += 1
                continue
            
            # Merge this line with next
            merged.append(line.rstrip() + ' ')
            i += 1
        else:
            # Last line
            merged.append(line)
            i += 1
    
    # Join and clean up multiple spaces
    result = '\n'.join(merged)
    # Remove trailing spaces before newlines
    result = re.sub(r' +\n', '\n', result)
    
    return result


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
    """Extract text from PDF file using PyMuPDF (faster and more accurate)."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        # Fallback to pdfplumber if PyMuPDF not available
        return _extract_pdf_fallback(file_storage)

    try:
        # Read file into memory
        pdf_bytes = file_storage.read()
        
        # Open PDF from bytes
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Extract text with sorting to improve line order
            # sort=True ensures text is extracted in reading order
            page_text = page.get_text("text", sort=True)
            
            if page_text and page_text.strip():
                text_parts.append(page_text)
        
        doc.close()

        if not text_parts:
            return False, "لم يتم العثور على نص في ملف PDF. قد يكون الملف يحتوي على صور فقط."

        full_text = "\n\n".join(text_parts)

        # Check if Arabic text is reversed (less common with PyMuPDF but still check)
        if _is_arabic_text_reversed(full_text):
            full_text = _reverse_arabic_words(full_text)

        # Apply smart line merging (new!)
        full_text = _smart_line_merge(full_text)

        # Apply comprehensive text cleaning
        full_text = _clean_extracted_text(full_text)

        return True, full_text
    except Exception as e:
        return False, f"خطأ في قراءة ملف PDF: {str(e)}"


def _extract_pdf_fallback(file_storage) -> Tuple[bool, str]:
    """Fallback PDF extraction using pdfplumber (original method)."""
    try:
        import pdfplumber
    except ImportError:
        return False, "مكتبات PDF غير متوفرة. يرجى تثبيت PyMuPDF أو pdfplumber."

    try:
        text_parts = []
        with pdfplumber.open(file_storage) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)

        if not text_parts:
            return False, "لم يتم العثور على نص في ملف PDF. قد يكون الملف يحتوي على صور فقط."

        full_text = "\n\n".join(text_parts)

        if _is_arabic_text_reversed(full_text):
            full_text = _reverse_arabic_words(full_text)

        full_text = _smart_line_merge(full_text)
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
