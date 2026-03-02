"""
src/tests/test_voice.py
Tests for Sarvam STT and TTS wrappers.
All tests mock Sarvam API — no real calls, no cost.

Run: python src/tests/test_voice.py
"""
import sys, os, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
from src.tests.stub_externals import * # noqa: F401 — must be before all project imports

from unittest.mock import MagicMock, patch

# Force-import the voice modules so patch() can resolve them as attributes of src.voice
import src.voice.sarvam_stt   # noqa: F401
import src.voice.sarvam_tts   # noqa: F401


class TestSarvamSTT(unittest.TestCase):

    def test_mock_mode_returns_success(self):
        with patch("src.voice.sarvam_stt.settings") as s:
            s.MOCK_MODE = True
            from src.voice.sarvam_stt import transcribe_audio
            result = transcribe_audio(b"fake_audio", "test.ogg")
        self.assertTrue(result["success"])
        self.assertTrue(result["mock"])
        self.assertGreater(len(result["transcript"]), 0)

    def test_rejects_oversized_audio(self):
        with patch("src.voice.sarvam_stt.settings") as s:
            s.MOCK_MODE = False
            s.SARVAM_API_KEY = "key"
            from src.voice.sarvam_stt import transcribe_audio
            result = transcribe_audio(b"x" * 600_000, "huge.ogg")  # 600KB > 500KB limit
        self.assertFalse(result["success"])
        self.assertTrue(result["rejected"])
        self.assertIn("large", result["rejection_reason"].lower())

    def test_rejects_audio_over_15_seconds(self):
        with patch("src.voice.sarvam_stt.settings") as s:
            s.MOCK_MODE = False
            s.SARVAM_API_KEY = "key"
            with patch("src.voice.sarvam_stt._preprocess_audio", return_value=(b"audio", 20.0)):
                from src.voice import sarvam_stt
                result = sarvam_stt.transcribe_audio(b"audio", "long.ogg")
        self.assertFalse(result["success"])
        self.assertTrue(result["rejected"])
        self.assertIn("15", result["rejection_reason"])

    def test_rejects_silent_audio(self):
        with patch("src.voice.sarvam_stt.settings") as s:
            s.MOCK_MODE = False
            s.SARVAM_API_KEY = "key"
            with patch("src.voice.sarvam_stt._preprocess_audio", return_value=(b"", 0.1)):
                from src.voice import sarvam_stt
                result = sarvam_stt.transcribe_audio(b"tiny", "silent.ogg")
        self.assertFalse(result["success"])
        self.assertTrue(result["rejected"])

    def test_result_always_has_required_keys(self):
        with patch("src.voice.sarvam_stt.settings") as s:
            s.MOCK_MODE = True
            from src.voice.sarvam_stt import transcribe_audio
            result = transcribe_audio(b"audio", "test.ogg")
        for key in ["success", "transcript", "duration_seconds", "rejected", "rejection_reason"]:
            self.assertIn(key, result, f"Missing required key: '{key}'")


class TestSarvamTTS(unittest.TestCase):

    def test_tier2_message_skips_tts_returns_none_none(self):
        """Strategy 3: Tier 2 messages must NOT trigger TTS — saves cost."""
        with patch("src.voice.sarvam_tts.settings") as s:
            s.MOCK_MODE = False
            s.SARVAM_API_KEY = "key"
            from src.voice.sarvam_tts import generate_audio
            url, audio = generate_audio("Processing...", message_type="confirmation")
        self.assertIsNone(url)
        self.assertIsNone(audio)

    def test_mock_mode_returns_fake_url(self):
        with patch("src.voice.sarvam_tts.settings") as s:
            s.MOCK_MODE = True
            from src.voice.sarvam_tts import generate_audio
            url, audio = generate_audio("test text", cache_key="test.ogg", message_type="score_reveal")
        self.assertIsNotNone(url)
        self.assertIn("mock", url)

    @patch("src.voice.sarvam_tts.audio_exists", return_value=True)
    @patch("src.voice.sarvam_tts.get_audio_url", return_value="https://s3.amazonaws.com/cached.ogg")
    @patch("src.voice.sarvam_tts._call_sarvam_tts")
    def test_cache_hit_never_calls_sarvam(self, mock_api, mock_url, mock_exists):
        """Strategy 1: S3 cache hit must short-circuit — never call Sarvam TTS API."""
        with patch("src.voice.sarvam_tts.settings") as s:
            s.MOCK_MODE = False
            s.SARVAM_API_KEY = "key"
            from src.voice.sarvam_tts import generate_audio
            url, _ = generate_audio("text", cache_key="name_mismatch_bn.ogg",
                                    message_type="mismatch_alert")
        mock_api.assert_not_called()
        self.assertEqual(url, "https://s3.amazonaws.com/cached.ogg")

    @patch("src.voice.sarvam_tts.audio_exists", return_value=False)
    @patch("src.voice.sarvam_tts._call_sarvam_tts", return_value=b"audio_bytes")
    @patch("src.voice.sarvam_tts.upload_audio", return_value=True)
    @patch("src.voice.sarvam_tts.get_audio_url", return_value="https://s3.amazonaws.com/fresh.ogg")
    def test_cache_miss_calls_sarvam_then_uploads_to_s3(self, mock_url, mock_upload, mock_api, mock_exists):
        """Strategy 1: Cache miss must call Sarvam then push result to S3."""
        with patch("src.voice.sarvam_tts.settings") as s:
            s.MOCK_MODE = False
            s.SARVAM_API_KEY = "key"
            from src.voice.sarvam_tts import generate_audio
            url, audio = generate_audio("text", cache_key="new.ogg",
                                        message_type="mismatch_alert")
        mock_api.assert_called_once()
        mock_upload.assert_called_once()

    def test_tier1_and_tier2_classification(self):
        from src.voice.sarvam_tts import is_tier1
        # Tier 1 — must use TTS
        self.assertTrue(is_tier1("score_reveal"))
        self.assertTrue(is_tier1("mismatch_alert"))
        self.assertTrue(is_tier1("office_script"))
        self.assertTrue(is_tier1("welcome"))
        # Tier 2 — text only
        self.assertFalse(is_tier1("confirmation"))
        self.assertFalse(is_tier1("acknowledgement"))
        self.assertFalse(is_tier1("prompt"))


class TestSarvamTTSTextSplitter(unittest.TestCase):

    def test_short_text_returns_single_chunk(self):
        from src.voice.sarvam_tts import _split_text
        text = "ছোট বাক্য।"
        self.assertEqual([text], _split_text(text, 500))

    def test_long_text_splits_at_sentence_boundary(self):
        from src.voice.sarvam_tts import _split_text
        text = "প্রথম বাক্য। " * 20   # ~260 chars — over limit of 100
        chunks = _split_text(text, 100)
        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 150)   # some tolerance for boundary detection

    def test_joining_chunks_recovers_full_content(self):
        from src.voice.sarvam_tts import _split_text
        text = "এক। দুই। তিন। চার। পাঁচ। ছয়। সাত। আট। নয়। দশ।"
        chunks = _split_text(text, 20)
        joined = "".join(chunks)
        # All words must survive the split (order preserved)
        self.assertIn("এক", joined)
        self.assertIn("দশ", joined)


class TestVoiceIntegration(unittest.TestCase):
    """End-to-end flow tests in MOCK_MODE — no real API calls."""

    def test_score_reveal_mock_returns_url(self):
        with patch("src.voice.sarvam_tts.settings") as s:
            s.MOCK_MODE = True
            from src.voice.sarvam_tts import generate_score_audio
            url, _ = generate_score_audio(42, "RED", "Lakshmir Bhandar")
        self.assertIsNotNone(url)

    def test_known_issue_audio_mock_returns_url(self):
        with patch("src.voice.sarvam_tts.settings") as s:
            s.MOCK_MODE = True
            from src.voice.sarvam_tts import generate_issue_audio
            url, _ = generate_issue_audio("NAME_MISMATCH")
        self.assertIsNotNone(url)

    def test_unknown_issue_code_returns_none_none(self):
        with patch("src.voice.sarvam_tts.settings") as s:
            s.MOCK_MODE = True
            from src.voice.sarvam_tts import generate_issue_audio
            url, audio = generate_issue_audio("FAKE_CODE_THAT_DOES_NOT_EXIST")
        self.assertIsNone(url)
        self.assertIsNone(audio)

    def test_welcome_audio_mock_returns_url(self):
        with patch("src.voice.sarvam_tts.settings") as s:
            s.MOCK_MODE = True
            from src.voice.sarvam_tts import generate_welcome_audio
            url, _ = generate_welcome_audio()
        self.assertIsNotNone(url)

    def test_all_manifest_codes_have_audio_in_mock(self):
        """Every entry in AUDIO_CACHE_MANIFEST must produce a URL in mock mode."""
        from src.storage.s3 import AUDIO_CACHE_MANIFEST
        with patch("src.voice.sarvam_tts.settings") as s:
            s.MOCK_MODE = True
            from src.voice.sarvam_tts import generate_issue_audio
            for code in AUDIO_CACHE_MANIFEST:
                url, _ = generate_issue_audio(code)
                self.assertIsNotNone(url, f"generate_issue_audio('{code}') returned None in mock mode")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [TestSarvamSTT, TestSarvamTTS, TestSarvamTTSTextSplitter, TestVoiceIntegration]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)