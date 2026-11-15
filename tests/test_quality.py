"""Answer quality: the evaluation set, Amharic spelling, and no AI call when the course has nothing."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))


def test_evaluation_set_offline_scores_full_marks():
    import evaluate

    passed, total, rows = evaluate.run(cloud=False)
    failed = [item["q"] for ok, item, _ in rows if not ok]
    assert passed == total, f"wrong source or not refused: {failed}"


def test_same_sound_letters_are_one_spelling():
    from retrieval import normalize_amharic

    assert normalize_amharic("ሥራ") == normalize_amharic("ስራ")
    assert normalize_amharic("ፀሐይ") == normalize_amharic("ጸሀይ")
    assert normalize_amharic("ዓለም") == normalize_amharic("አለም")
    assert normalize_amharic("ሃገር") == normalize_amharic("ሀገር")


def test_misheard_vowel_still_finds_the_word():
    from retrieval import expand_amharic

    glossary = {"ማስረከቢያ": "deadline"}
    assert expand_amharic("የማሰረከቢያ ቀኑ መቼ ነው?", glossary) == "deadline"  # ማሰ instead of ማስ


def test_no_model_call_when_course_has_nothing(monkeypatch):
    monkeypatch.setenv("ABLEWAY_PROVIDERS", "gemini,offline")
    monkeypatch.setenv("GEMINI_API_KEYS", "test-key-not-real")
    from tutor import Tutor

    tutor = Tutor()
    gemini = next(p for p in tutor.chain if p.name == "gemini")
    monkeypatch.setattr(gemini, "status", lambda: {"available": True, "detail": ""})
    calls = []
    monkeypatch.setattr(gemini, "complete", lambda *a, **k: calls.append(a) or "ok")
    result = tutor.ask("Who won the World Cup?", "en")
    assert calls == [] and result["grounded"] is False
    tutor.ask("Hello!", "en")  # a greeting needs no source: the model may answer it
    assert len(calls) == 1
