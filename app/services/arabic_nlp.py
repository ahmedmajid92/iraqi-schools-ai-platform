import re
from typing import List, Set

ARABIC_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u0652]")
PUNCT = re.compile(r"[^\w\u0600-\u06FF\s]+")

DEFAULT_STOPWORDS: Set[str] = {
    "في","من","إلى","على","عن","أن","إن","كان","كانت","هو","هي","هم","هن","هذا","هذه","ذلك","تلك",
    "هناك","هنا","ثم","أو","و","ف","كما","لكن","لأن","حتى","مع","ضمن","بين","بعد","قبل","كل","أي",
    "إذا","إذ","قد","لا","لم","لن","ما","ماذا","لماذا","كيف","حيث","عند","عندما","إلا","بل","مثل",
    "الى","عليه","عليها","فيه","فيها","به","بها","له","لها","والتي","الذي","التي","الذين","اللاتي",
    "وقد","كما","أيضا","أيضاً","جدا","جداً"
}

def normalize_arabic(text: str) -> str:
    text = ARABIC_DIACRITICS.sub("", text)
    text = text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    text = text.replace("ى", "ي").replace("ة", "ه")
    text = text.replace("ؤ", "و").replace("ئ", "ي")
    return text

def split_sentences(text: str) -> List[str]:
    t = text.replace("؟", "?").replace("؛", ";")
    parts = re.split(r"[\.!\?\n;]+", t)
    sents = [p.strip() for p in parts if p.strip()]
    return sents

def tokenize_arabic(text: str) -> List[str]:
    t = normalize_arabic(text)
    t = PUNCT.sub(" ", t)
    tokens = re.findall(r"[\u0600-\u06FF]{2,}", t)
    return tokens

def remove_stopwords(tokens: List[str], stopwords: Set[str] = None) -> List[str]:
    sw = stopwords or DEFAULT_STOPWORDS
    return [w for w in tokens if w not in sw and len(w) >= 2]
