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


def load_glossary() -> dict[str, str]:
    path = DATA / "glossary_am.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def expand_amharic(question: str, glossary: dict[str, str]) -> str:
    """English search terms for the Amharic words we recognise in the question."""
    found = [english for amharic, english in glossary.items() if amharic in question]
    return " ".join(found)
