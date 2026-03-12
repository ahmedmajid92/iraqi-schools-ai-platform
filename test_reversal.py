import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
from app.services.file_extractor import _is_arabic_text_reversed, _reverse_arabic_words

sample_text = """
Computer بوساحلا / بارلاع اïدادعي

لصفلا :يناثلا ةنايص تايجمرب بوساحلا

تاءارجقا ئغجاجقا ئؤغعال طئاجو نجثلا
"""

with open('debug_output.txt', 'w', encoding='utf-8') as f:
    f.write(f"Is Reversed? {_is_arabic_text_reversed(sample_text)}\n")
    if _is_arabic_text_reversed(sample_text):
        f.write("Reversed output:\n")
        f.write(_reverse_arabic_words(sample_text))
