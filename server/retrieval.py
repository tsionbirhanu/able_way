"""Keyword search (BM25) over the extracted course chunks.

Pure Python and fully offline. The course content is in English, so an Amharic question is
first expanded with English terms from data/glossary_am.json; when an AI provider is
available the tutor also translates the question before searching (see tutor.py).
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"

STOPWORDS = set(
    """a an and are as at be but by can do does for from has have how i if in is it its me my of on or
    our so than that the their them then there these they this to was we were what when where which
    who why will with you your about tell please explain""".split()
)

ETHIOPIC = re.compile(r"[ሀ-᎟ⶀ-⷟]")


def is_amharic(text: str) -> bool:
    return bool(ETHIOPIC.search(text))


def stem(word: str) -> str:
    """Very light English stemming so that 'deadlines' finds 'deadline'."""
    if word.isdigit() or len(word) <= 3:
        return word
    for suffix, replacement in (("ies", "y"), ("sses", "ss"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            return word[: len(word) - len(suffix)] + replacement
    return word


def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [stem(w) for w in words if w not in STOPWORDS]


class Index:
    K1 = 1.4
    B = 0.75

    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.docs: list[dict[str, int]] = []
        self.lengths: list[int] = []
        df: dict[str, int] = {}
        for chunk in chunks:
            # The title is counted three times: a match on the heading is a strong signal.
            words = tokenize(chunk["title"]) * 3 + tokenize(chunk["text"])
            counts: dict[str, int] = {}
            for w in words:
                counts[w] = counts.get(w, 0) + 1
            self.docs.append(counts)
            self.lengths.append(len(words))
            for w in counts:
                df[w] = df.get(w, 0) + 1
        n = len(chunks) or 1
        self.avg_len = (sum(self.lengths) / n) or 1
        self.idf = {w: math.log(1 + (n - d + 0.5) / (d + 0.5)) for w, d in df.items()}

    def search(self, query: str, k: int = 5, corpus: str | None = None) -> list[dict]:
        """Return up to k chunks, best first, each with a 'score'. Empty when nothing in the
        content shares a meaningful word with the query."""
        terms = tokenize(query)
        if not terms:
            return []
        scored = []
        for i, counts in enumerate(self.docs):
            if corpus and self.chunks[i].get("corpus") != corpus:
                continue
            score = 0.0
            for term in set(terms):
                tf = counts.get(term, 0)
                if not tf:
                    continue
                norm = tf + self.K1 * (1 - self.B + self.B * self.lengths[i] / self.avg_len)
                score += self.idf[term] * tf * (self.K1 + 1) / norm
            if score > 0:
                scored.append((score, i))
        scored.sort(reverse=True)
        return [{**self.chunks[i], "score": round(score, 3)} for score, i in scored[:k]]


def coverage(index: "Index", query: str, hits: list[dict]) -> float:
    """Share of the query's words found in at least one of the hits (0..1). An off-topic
    question can still score well on one shared word ("world cup" finds "world"), but only a
    real course question has most of its words in the course."""
    terms = set(tokenize(query))
    if not terms or not hits:
        return 0.0
    position = {c["id"]: i for i, c in enumerate(index.chunks)}
    docs = [index.docs[position[h["id"]]] for h in hits if h.get("id") in position]
    def found(term: str) -> bool:
        if any(term in d for d in docs):
            return True
        # "resubmit" and "resubmission": the same word family, which the light stemmer keeps apart.
        return len(term) >= 6 and any(w.startswith(term[:6]) for d in docs for w in d)

    return sum(1 for t in terms if found(t)) / len(terms)


def load_chunks() -> list[dict]:
    """All chunk files in data/: chunks.json from extract.py, plus any chunks_*.json that
    teammates add (for example a jobs corpus with "corpus": "jobs")."""
    chunks: list[dict] = []
    for path in sorted(DATA.glob("chunks*.json")):
        chunks.extend(json.loads(path.read_text(encoding="utf-8")))
    return chunks


def load_glossary(lang: str = "am") -> dict[str, str]:
    path = DATA / f"glossary_{lang}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


# ------------------------------------------------------------------ Afaan Oromo
# The course is in English. A word list per language turns the learner's words into English search
# words, so questions in these languages are understood with no AI at all, as Amharic ones are.

def expand_words(question: str, glossary: dict[str, str], lang: str) -> str:
    """English search terms for the words of the question found in the word list. Afaan Oromo is
    written in Latin letters; the apostrophe (hudhaa) is often left out when typing."""
    plain, key = f" {question.lower().replace(chr(39), '').replace('’', '')} ", lambda w: w.lower().replace("'", "")
    found = []
    # Longest first, and a match is taken out of the text: "hojii manaa" (assignment) is not also "hojii".
    for word, english in sorted(glossary.items(), key=lambda item: -len(item[0])):
        stem = key(word)
        # Short words must stand alone ("ai", "va"); longer ones are stems ("galch" in "galchuu").
        pattern = rf"(?<!\w){re.escape(stem)}(?!\w)" if len(stem) <= 3 else re.escape(stem)
        if re.search(pattern, plain):
            found.append(english)
            plain = re.sub(pattern, " ", plain)
    return " ".join(found)


# Amharic letters (fidel) are a consonant plus one of seven vowel orders: ሰ ሱ ሲ ሳ ሴ ስ ሶ are all "s".
# Unicode keeps each consonant's orders together in a row of eight code points from U+1200.
_ROW = 8
# Letters that sound the same and are written either way (ሀ/ሐ/ኀ, ሰ/ሠ, አ/ዐ, ጸ/ፀ): so "ሥራ" and
# "ስራ", or "ፀሐይ" and "ጸሀይ", are one word. Each pair maps a whole row onto its usual spelling.
_SAME_SOUND = {0x1210: 0x1200, 0x1280: 0x1200, 0x1220: 0x1230, 0x12D0: 0x12A0, 0x1340: 0x1338}


def normalize_amharic(text: str) -> str:
    """One spelling for letters that sound the same; ሃ/ሓ/ኃ and ኣ/ዓ written as ሀ and አ."""
    out = []
    for ch in text:
        cp = ord(ch)
        base = cp - (cp - 0x1200) % _ROW if 0x1200 <= cp <= 0x137F else None
        if base in _SAME_SOUND and cp - base < 7:
            cp = _SAME_SOUND[base] + (cp - base)
            base = _SAME_SOUND[base]
        if base in (0x1200, 0x12A0) and cp - base == 3:  # ሃ -> ሀ, ኣ -> አ (the same sound)
            cp = base
        out.append(chr(cp))
    return "".join(out)


def consonants(text: str) -> str:
    """The consonant skeleton: every letter in its sixth (vowel-less) order, so a vowel misheard by
    speech recognition, or another form of the same word (ማስረከብ, ማስረከቢያ), still matches."""
    out = []
    for ch in normalize_amharic(text):
        cp = ord(ch)
        if 0x1200 <= cp <= 0x137F and (cp - 0x1200) % _ROW < 7:
            cp = cp - (cp - 0x1200) % _ROW + 5
        out.append(chr(cp))
    return "".join(out)


def expand_amharic(question: str, glossary: dict[str, str]) -> str:
    """English search terms for the Amharic words we recognise in the question: by spelling (with
    same-sound letters treated as one), else, for longer words, by consonant skeleton."""
    plain, skeleton = normalize_amharic(question), consonants(question)
    found = []
    for amharic, english in glossary.items():
        if normalize_amharic(amharic) in plain or (len(amharic) >= 3 and consonants(amharic) in skeleton):
            found.append(english)
    return " ".join(found)
