"""Azure AI Speech provider: request shape and reply handling, with the network replaced by a fake.

Run with:  python -m pytest -q server/tests
"""

import io
import json
import os
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import speech  # noqa: E402


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class AzureVoice(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AZURE_SPEECH_KEY": "test-key", "AZURE_SPEECH_REGION": "westeurope"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_amharic_uses_the_female_mekdes_voice_and_escapes_text(self):
        sent = {}

        def fake_urlopen(request, timeout=0):
            sent["url"] = request.full_url
            sent["headers"] = dict(request.header_items())
            sent["body"] = request.data.decode("utf-8")
            return FakeResponse(b"ID3fake-mp3")

        with mock.patch.object(speech.urllib.request, "urlopen", fake_urlopen):
            audio, mime = speech.AzureTTS().synthesize("ሰላም <ተማሪ> & ጓደኛ", "am")
        self.assertEqual((audio, mime), (b"ID3fake-mp3", "audio/mpeg"))
        self.assertEqual(sent["url"], "https://westeurope.tts.speech.microsoft.com/cognitiveservices/v1")
        self.assertEqual(sent["headers"]["Ocp-apim-subscription-key"], "test-key")
        self.assertIn("name='am-ET-MekdesNeural'", sent["body"])
        self.assertIn("xml:lang='am-ET'", sent["body"])
        self.assertIn("&lt;ተማሪ&gt; &amp; ጓደኛ", sent["body"])

    def test_not_available_without_settings(self):
        with mock.patch.dict(os.environ, {"AZURE_SPEECH_KEY": ""}):
            self.assertFalse(speech.AzureTTS().status()["available"])

    def test_quota_error_pauses_the_provider(self):
        def fake_urlopen(request, timeout=0):
            raise urllib.error.HTTPError(request.full_url, 429, "Too Many Requests", {"Retry-After": "30"}, io.BytesIO(b""))

        tts = speech.AzureTTS()
        with mock.patch.object(speech.urllib.request, "urlopen", fake_urlopen):
            with self.assertRaises(speech.SpeechError):
                tts.synthesize("Hello", "en")
        self.assertFalse(tts.status()["available"])


class AzureHearing(unittest.TestCase):
    def setUp(self):
        self.env = mock.patch.dict(os.environ, {"AZURE_SPEECH_KEY": "test-key", "AZURE_SPEECH_REGION": "westeurope"})
        self.env.start()

    def tearDown(self):
        self.env.stop()

    def test_amharic_turn_is_sent_to_the_am_et_recogniser(self):
        sent = {}

        def fake_urlopen(request, timeout=0):
            sent["url"] = request.full_url
            sent["type"] = request.get_header("Content-type")
            return FakeResponse(json.dumps({"RecognitionStatus": "Success", "DisplayText": "አንድ።"}).encode("utf-8"))

        with mock.patch.object(speech.urllib.request, "urlopen", fake_urlopen):
            text = speech.Speech().transcribe(b"RIFFfake", "audio/wav", "am")
        self.assertEqual(text, "አንድ።")
        self.assertIn("language=am-ET", sent["url"])
        self.assertIn("samplerate=16000", sent["type"])

    def test_silence_is_an_empty_turn(self):
        def fake_urlopen(request, timeout=0):
            return FakeResponse(json.dumps({"RecognitionStatus": "InitialSilenceTimeout"}).encode("utf-8"))

        with mock.patch.object(speech.urllib.request, "urlopen", fake_urlopen):
            self.assertEqual(speech.Speech().transcribe(b"RIFFfake", "audio/wav", "en"), "")

    def test_status_reports_hearing_ready(self):
        self.assertTrue(speech.Speech().status()["stt"])


if __name__ == "__main__":
    unittest.main()
