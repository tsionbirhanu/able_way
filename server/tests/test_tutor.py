"""Run with:  python -m unittest discover -s server/tests

No network and no AI model needed: the model-backed path is exercised with a scripted fake.
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from providers import OfflineProvider, Provider, ProviderError  # noqa: E402
from tutor import NOT_FOUND, Tutor, parse_answer  # noqa: E402


class FakeModel(Provider):
    name, label = "fake", "Fake model"

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def status(self):
        return {"available": True, "detail": ""}

    def complete(self, system, messages, max_tokens=16000):
        self.calls.append({"system": system, "messages": messages})
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


class Offline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tutor = Tutor(chain=[OfflineProvider()])

    def test_faq_in_english(self):
        r = self.tutor.ask("Is the VA profession shrinking?", "en")
        self.assertTrue(r["grounded"])
        self.assertIn("evolving", r["answer"])
        self.assertEqual(r["citations"][0]["url"], "pages/concept-with-navigation.html")

    def test_faq_in_amharic_is_answered_in_amharic(self):
        r = self.tutor.ask("ምናባዊ ረዳት ማለት ምን ማለት ነው", "am")
        self.assertTrue(r["grounded"])
        self.assertRegex(r["answer"], "[ሀ-፿]")
        self.assertEqual(r["provider"], "offline")

    def test_simple_mode_uses_the_simple_answer(self):
        normal = self.tutor.ask("What is the late policy for WR 100?", "en")
        simple = self.tutor.ask("What is the late policy for WR 100?", "en", simple=True)
        self.assertLess(len(simple["answer"]), len(normal["answer"]))

    def test_unprepared_question_quotes_the_course(self):
        r = self.tutor.ask("How do I verify that sources actually exist?", "en")
        self.assertTrue(r["grounded"])
        self.assertIn("Week 9", r["citations"][0]["title"])

    def test_amharic_keywords_reach_english_content(self):
        r = self.tutor.ask("ስለ ቅዠት እና ምንጭ ማረጋገጥ ንገረኝ", "am")
        self.assertTrue(r["grounded"])
        self.assertIn("Week 9", r["citations"][0]["title"])

    def test_off_topic_is_refused(self):
        for question, lang in (("What is the capital of France?", "en"), ("የኢትዮጵያ ዋና ከተማ ማን ናት?", "am")):
            r = self.tutor.ask(question, lang)
            self.assertFalse(r["grounded"], question)
            self.assertEqual(r["citations"], [])


class WithModel(unittest.TestCase):
    def test_citations_are_checked_and_renumbered(self):
        model = FakeModel(["Resubmission is allowed once [3]. A 15% reduction applies [3][1]. Invented [9]."])
        r = Tutor(chain=[model, OfflineProvider()]).ask("Can I resubmit an assignment in WR 100?")
        self.assertEqual(r["provider"], "fake")
        self.assertNotIn("[9]", r["answer"])
        self.assertIn("[1]. A 15% reduction applies [1][2].", r["answer"])
        self.assertEqual([c["n"] for c in r["citations"]], [1, 2])
        sent = model.calls[0]["messages"][-1]["content"]
        self.assertIn("[1] ", sent)
        self.assertIn("Question: Can I resubmit", sent)

    def test_not_found_marker(self):
        model = FakeModel([f"{NOT_FOUND} That is not in your course material [1]."])
        r = Tutor(chain=[model, OfflineProvider()]).ask("What is the capital of France?")
        self.assertFalse(r["grounded"])
        self.assertEqual(r["citations"], [])
        self.assertNotIn("[", r["answer"])

    def test_amharic_question_is_translated_before_search(self):
        # A question the Amharic word list does not know ("What does that rule say?") is translated
        # by the model first; one it does know skips that call (tests/test_quality.py).
        model = FakeModel(["late policy deadline WR 100", "መልስ [1]።"])
        r = Tutor(chain=[model, OfflineProvider()]).ask("ያ ደንብ ምን ይላል?", "am", simple=True)
        self.assertEqual(len(model.calls), 2)
        self.assertIn("Amharic", model.calls[1]["system"])
        self.assertIn("simple mode", model.calls[1]["system"])
        self.assertTrue(r["grounded"])

    def test_falls_back_to_offline_when_the_model_fails(self):
        model = FakeModel([ProviderError("down")])
        r = Tutor(chain=[model, OfflineProvider()]).ask("Is the VA profession shrinking?")
        self.assertEqual(r["provider"], "offline")
        self.assertTrue(r["grounded"])

    def test_parse_handles_comma_lists(self):
        hits = [{"title": "A", "url": "a", "text": "x"}, {"title": "B", "url": "b", "text": "y"}]
        r = parse_answer("Both [2, 1].", hits, fallback="none")
        self.assertEqual(r["answer"], "Both [1][2].")
        self.assertEqual([c["title"] for c in r["citations"]], ["B", "A"])


if __name__ == "__main__":
    unittest.main()


class OffTopic(unittest.TestCase):
    def test_one_shared_word_is_not_an_answer(self):
        r = Tutor(chain=[OfflineProvider()]).ask("Who won the football world cup?", "en")
        self.assertFalse(r["grounded"])
        self.assertEqual(r["citations"], [])


class Jobs(unittest.TestCase):
    def test_job_question_is_answered_from_the_listings(self):
        for question, lang in (("What jobs are open for me, and how do I apply?", "en"),
                               ("ለእኔ የሚሆኑ ክፍት ሥራዎች የትኞቹ ናቸው? እንዴትስ ማመልከት እችላለሁ?", "am")):
            r = Tutor(chain=[OfflineProvider()]).ask(question, lang)
            self.assertTrue(r["grounded"], question)
            self.assertTrue(r["citations"][0]["url"].endswith("jobs.html") or "jobs" in r["citations"][0]["url"], r["citations"])

    def test_course_question_still_uses_the_course(self):
        r = Tutor(chain=[OfflineProvider()]).ask("Can I resubmit an assignment?", "en")
        self.assertIn("Resubmission", r["citations"][0]["title"])


class AnswerCache(unittest.TestCase):
    def test_the_same_question_does_not_call_the_ai_twice(self):
        model = FakeModel(["Resubmission is allowed once [1]."])  # only one reply: a second call would fail
        tutor = Tutor(chain=[model, OfflineProvider()])
        first = tutor.ask("Can I resubmit an assignment in WR 100?")
        second = tutor.ask("can I resubmit an assignment in WR 100")
        self.assertEqual(len(model.calls), 1)
        self.assertTrue(second.get("cached"))
        self.assertEqual(first["answer"], second["answer"])

    def test_follow_up_questions_are_not_cached(self):
        model = FakeModel(["One [1].", "Two [1]."])
        tutor = Tutor(chain=[model, OfflineProvider()])
        history = [{"role": "user", "content": "Tell me about resubmission"}]
        tutor.ask("Can I resubmit an assignment in WR 100?", history=history)
        tutor.ask("Can I resubmit an assignment in WR 100?", history=history)
        self.assertEqual(len(model.calls), 2)
