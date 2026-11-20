"""Answer quality: the evaluation set, Amharic spelling, and no AI call when the course has nothing."""
import pytest
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


def test_amharic_question_is_translated_once_then_remembered(monkeypatch):
    """Every language is searched through an English version of the question, so the same question
    finds the same sections (and facts) in Amharic, Afaan Oromo and English. The translation is
    remembered: asking again costs only the answer."""
    monkeypatch.setenv("ABLEWAY_PROVIDERS", "gemini,offline")
    monkeypatch.setenv("GEMINI_API_KEYS", "test-key-not-real")
    from tutor import Tutor

    tutor = Tutor()
    gemini = next(p for p in tutor.chain if p.name == "gemini")
    monkeypatch.setattr(gemini, "status", lambda: {"available": True, "detail": ""})
    systems = []

    def fake(system, messages, **k):
        systems.append(system)
        return "How many days is the course?" if "translate" in system.lower() else "ኮርሱ 7 ቀን ነው [1]።"

    monkeypatch.setattr(gemini, "complete", fake)
    result = tutor.ask("ኮርሱ ስንት ቀን ነው?", "am")
    assert result["grounded"] is True
    assert sum("translate" in s.lower() for s in systems) == 1
    tutor._answer_cache.clear()  # not the answer cache: the translation must be remembered by itself
    tutor.ask("ኮርሱ ስንት ቀን ነው?", "am")
    assert sum("translate" in s.lower() for s in systems) == 1


def test_square_brackets_are_only_for_source_numbers():
    from tutor import parse_answer

    hits = [{"title": "Course Overview", "course": "", "url": "pages/x.html", "page": "pages/x.html", "text": ""}]
    answer = parse_answer("Imaammata [Late Policy] koorsii [1].", hits, "")["answer"]
    assert answer == "Imaammata (Late Policy) koorsii [1]."


@pytest.mark.parametrize("question, section", [
    ("Can I resubmit my homework?", "Course Overview"),
    ("Can I retake the exam?", "Evaluation Quizzes"),
    ("When is the homework due date?", "Course Overview"),
])
def test_everyday_words_find_the_course_words(monkeypatch, question, section):
    """Learners (and translations) say homework, exam, due date; the course says assignment, quiz, deadline."""
    monkeypatch.setenv("ABLEWAY_PROVIDERS", "offline")
    from tutor import Tutor

    answer = Tutor().ask(question, "en", cloud=False)
    assert answer["grounded"] and section in answer["citations"][0]["title"]


def test_every_source_carries_the_course_words(monkeypatch):
    """A source the page cannot show (for example a hidden course panel) is quoted in the chat instead."""
    monkeypatch.setenv("ABLEWAY_PROVIDERS", "offline")
    from tutor import Tutor

    tutor = Tutor()
    for question in ("What is the late submission policy?", "Can I resubmit an assignment?"):
        source = tutor.ask(question, "en", cloud=False)["citations"][0]
        assert source["snippet"] and source["snippet"].split()[0] != "WR"  # its own section, not the page top


def test_source_links_zoom_and_never_ring_the_wrong_place():
    from pathlib import Path

    script = (Path(__file__).resolve().parents[1] / "module" / "db-assistant.js").read_text(encoding="utf-8")
    assert "mimi-source-zoom" in script  # the zoom to the section
    assert "session.set('show-source'" in script  # a source on another page: go there, then show it
    assert "return null;" in script and "isShown(found)" in script  # never a fallback ring on a wrong place
