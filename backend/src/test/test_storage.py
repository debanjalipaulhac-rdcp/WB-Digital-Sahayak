"""
src/tests/test_storage.py
Tests for DynamoDB, S3 storage layer, Twilio builders, settings, and Bedrock fallback.
All tests use mocks — no real AWS calls, no cost.

Run: python src/tests/test_storage.py
"""
import sys, os, json, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# MUST be first — stubs boto3 and other externals before any project imports
from ..test.stub_externals import * # noqa: F401

from unittest.mock import MagicMock, patch


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DynamoDB — Profile
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestDynamoSaveProfile(unittest.TestCase):

    def _mock_table(self):
        t = MagicMock()
        t.put_item.return_value = {}
        return t

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_returns_true_on_success(self, mock_get):
        mock_get.return_value = self._mock_table()
        from src.storage.dynamo import save_profile
        self.assertTrue(save_profile("+91123", {"name": "Sulata"}))

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_item_has_correct_pk_and_sk(self, mock_get):
        t = self._mock_table()
        mock_get.return_value = t
        from src.storage.dynamo import save_profile
        save_profile("+919876543210", {"name": "Sulata"})
        item = t.put_item.call_args[1]["Item"]
        self.assertEqual(item["phone"], "+919876543210")
        self.assertEqual(item["sk"], "PROFILE")

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_ttl_is_set(self, mock_get):
        t = self._mock_table()
        mock_get.return_value = t
        from src.storage.dynamo import save_profile
        save_profile("+91123", {"name": "X"})
        self.assertIn("ttl", t.put_item.call_args[1]["Item"])

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_returns_false_on_exception(self, mock_get):
        t = self._mock_table()
        t.put_item.side_effect = Exception("DB down")
        mock_get.return_value = t
        from src.storage.dynamo import save_profile
        self.assertFalse(save_profile("+91123", {}))


class TestDynamoGetProfile(unittest.TestCase):

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_returns_profile_when_found(self, mock_get):
        t = MagicMock()
        t.get_item.return_value = {"Item": {"phone": "+91123", "sk": "PROFILE", "name": "Sulata", "age": 38}}
        mock_get.return_value = t
        from src.storage.dynamo import get_profile
        result = get_profile("+91123")
        self.assertIsNotNone(result)
        self.assertEqual(result["name"], "Sulata")
        self.assertNotIn("sk", result)   # sk must be stripped

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_returns_none_when_not_found(self, mock_get):
        t = MagicMock()
        t.get_item.return_value = {}
        mock_get.return_value = t
        from src.storage.dynamo import get_profile
        self.assertIsNone(get_profile("+91000"))

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_returns_none_on_exception(self, mock_get):
        t = MagicMock()
        t.get_item.side_effect = Exception("Network error")
        mock_get.return_value = t
        from src.storage.dynamo import get_profile
        self.assertIsNone(get_profile("+91000"))


class TestDynamoSession(unittest.TestCase):

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_save_stores_conversation_step(self, mock_get):
        t = MagicMock(); t.put_item.return_value = {}
        mock_get.return_value = t
        from src.storage.dynamo import save_session
        save_session("+91123", {"conversation_step": "AWAITING_DOCS", "scheme_id": "lakshmir_bhandar"})
        item = t.put_item.call_args[1]["Item"]
        self.assertEqual(item["conversation_step"], "AWAITING_DOCS")
        self.assertEqual(item["sk"], "SESSION")

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_session_ttl_is_24_hours(self, mock_get):
        import time
        t = MagicMock(); t.put_item.return_value = {}
        mock_get.return_value = t
        from src.storage.dynamo import save_session
        before = int(time.time())
        save_session("+91123", {"conversation_step": "START"})
        after  = int(time.time())
        item = t.put_item.call_args[1]["Item"]
        self.assertGreaterEqual(item["ttl"], before + 86400 - 2)
        self.assertLessEqual(item["ttl"],    after  + 86400 + 2)

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_get_returns_none_when_no_item(self, mock_get):
        t = MagicMock(); t.get_item.return_value = {}
        mock_get.return_value = t
        from src.storage.dynamo import get_session
        self.assertIsNone(get_session("+91123"))

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_clear_calls_delete_with_correct_key(self, mock_get):
        t = MagicMock(); t.delete_item.return_value = {}
        mock_get.return_value = t
        from src.storage.dynamo import clear_session
        self.assertTrue(clear_session("+919876543210"))
        t.delete_item.assert_called_once_with(Key={"phone": "+919876543210", "sk": "SESSION"})


class TestDynamoSaveResult(unittest.TestCase):

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_returns_sk_string_starting_with_result(self, mock_get):
        t = MagicMock(); t.put_item.return_value = {}
        mock_get.return_value = t
        from src.storage.dynamo import save_result
        sk = save_result("+91123", "lakshmir_bhandar", {"score": 42, "band": "RED", "issues": [], "roadmap": []})
        self.assertTrue(sk.startswith("RESULT#"))

    @patch("src.storage.dynamo.get_dynamodb_table")
    def test_issues_stored_as_json_string(self, mock_get):
        t = MagicMock(); t.put_item.return_value = {}
        mock_get.return_value = t
        from src.storage.dynamo import save_result
        issues = [{"type": "fatal", "code": "NAME_MISMATCH", "score_deduction": 35}]
        save_result("+91123", "lakshmir_bhandar", {"score": 40, "band": "RED", "issues": issues, "roadmap": []})
        item = t.put_item.call_args[1]["Item"]
        self.assertIsInstance(item["issues"], str)
        self.assertEqual(json.loads(item["issues"])[0]["code"], "NAME_MISMATCH")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# S3 — Audio Cache
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestS3AudioCache(unittest.TestCase):

    @patch("src.storage.s3.get_s3_client")
    def test_audio_exists_true_when_found(self, mock_s3_fn):
        s3 = MagicMock(); s3.head_object.return_value = {"ContentLength": 1234}
        mock_s3_fn.return_value = s3
        from src.storage.s3 import audio_exists
        self.assertTrue(audio_exists("name_mismatch_bn.ogg"))

    @patch("src.storage.s3.get_s3_client")
    def test_audio_exists_false_when_404(self, mock_s3_fn):
        from botocore.exceptions import ClientError
        s3 = MagicMock()
        s3.head_object.side_effect = ClientError({"Error": {"Code": "404", "Message": "Not Found"}}, "HeadObject")
        mock_s3_fn.return_value = s3
        from src.storage.s3 import audio_exists
        self.assertFalse(audio_exists("nonexistent.ogg"))

    @patch("src.storage.s3.get_s3_client")
    def test_upload_returns_true_on_success(self, mock_s3_fn):
        s3 = MagicMock(); s3.put_object.return_value = {}
        mock_s3_fn.return_value = s3
        from src.storage.s3 import upload_audio
        self.assertTrue(upload_audio(b"audio", "test.ogg"))

    @patch("src.storage.s3.get_s3_client")
    def test_upload_returns_false_on_exception(self, mock_s3_fn):
        s3 = MagicMock(); s3.put_object.side_effect = Exception("S3 down")
        mock_s3_fn.return_value = s3
        from src.storage.s3 import upload_audio
        self.assertFalse(upload_audio(b"audio", "test.ogg"))

    @patch("src.storage.s3.get_s3_client")
    def test_get_audio_url_returns_https_url(self, mock_s3_fn):
        s3 = MagicMock()
        s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/file.ogg?sig=abc"
        mock_s3_fn.return_value = s3
        from src.storage.s3 import get_audio_url
        url = get_audio_url("name_mismatch_bn.ogg")
        self.assertIsNotNone(url)
        self.assertTrue(url.startswith("https://"))

    @patch("src.storage.s3.get_s3_client")
    def test_get_audio_url_returns_none_on_exception(self, mock_s3_fn):
        s3 = MagicMock(); s3.generate_presigned_url.side_effect = Exception("Signing failed")
        mock_s3_fn.return_value = s3
        from src.storage.s3 import get_audio_url
        self.assertIsNone(get_audio_url("test.ogg"))

    @patch("src.storage.s3.audio_exists", return_value=True)
    @patch("src.storage.s3.get_audio_url", return_value="https://s3.amazonaws.com/cached.ogg")
    def test_get_or_generate_cache_hit_never_calls_tts(self, mock_url, mock_exists):
        from src.storage.s3 import get_or_generate_audio
        fake_tts = MagicMock()
        url = get_or_generate_audio("name_mismatch_bn.ogg", "Bengali text", fake_tts)
        self.assertEqual(url, "https://s3.amazonaws.com/cached.ogg")
        fake_tts.assert_not_called()

    @patch("src.storage.s3.audio_exists", return_value=False)
    @patch("src.storage.s3.upload_audio", return_value=True)
    @patch("src.storage.s3.get_audio_url", return_value="https://s3.amazonaws.com/fresh.ogg")
    def test_get_or_generate_cache_miss_calls_tts(self, mock_url, mock_upload, mock_exists):
        from src.storage.s3 import get_or_generate_audio
        fake_tts = MagicMock(return_value=b"audio_bytes")
        url = get_or_generate_audio("new.ogg", "Bengali text", fake_tts)
        fake_tts.assert_called_once_with("Bengali text")
        self.assertEqual(url, "https://s3.amazonaws.com/fresh.ogg")

    @patch("src.storage.s3.audio_exists", return_value=False)
    def test_get_or_generate_no_tts_func_returns_none(self, mock_exists):
        from src.storage.s3 import get_or_generate_audio
        self.assertIsNone(get_or_generate_audio("x.ogg", "text", tts_func=None))

    def test_manifest_has_all_critical_codes(self):
        from src.storage.s3 import AUDIO_CACHE_MANIFEST
        for code in ["NAME_MISMATCH", "DORMANT_ACCOUNT", "AADHAAR_UNLINKED", "WELCOME"]:
            self.assertIn(code, AUDIO_CACHE_MANIFEST,
                          f"'{code}' missing from AUDIO_CACHE_MANIFEST — demo will fail")

    def test_manifest_all_entries_have_text_and_ogg_filename(self):
        from src.storage.s3 import AUDIO_CACHE_MANIFEST
        for code, (text, filename) in AUDIO_CACHE_MANIFEST.items():
            self.assertGreater(len(text), 0,      f"{code}: Bengali text is empty")
            self.assertTrue(filename.endswith(".ogg"), f"{code}: filename must end in .ogg")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Twilio message builders
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestTwilioMessageBuilders(unittest.TestCase):

    def test_score_message_green_has_emoji_and_score(self):
        from ..config.twilio_client import build_score_message
        msg = build_score_message(90, "GREEN", "Lakshmir Bhandar")
        self.assertIn("🟢", msg)
        self.assertIn("90", msg)

    def test_score_message_red_has_emoji_and_score(self):
        from ..config.twilio_client import build_score_message
        msg = build_score_message(20, "RED", "Lakshmir Bhandar")
        self.assertIn("🔴", msg)
        self.assertIn("20", msg)

    def test_issue_message_empty_shows_tick(self):
        from ..config.twilio_client import build_issue_message
        self.assertIn("✅", build_issue_message([]))

    def test_issue_message_fatal_shows_warning(self):
        from ..config.twilio_client import build_issue_message
        msg = build_issue_message([{"type": "fatal", "code": "NAME_MISMATCH", "message": "Name mismatch on Aadhaar and Bank"}])
        self.assertIn("⚠️", msg)
        self.assertIn("Name mismatch", msg)

    def test_roadmap_empty_returns_empty_string(self):
        from ..config.twilio_client import build_roadmap_message
        self.assertEqual("", build_roadmap_message([]))

    def test_roadmap_shows_numbered_steps(self):
        from ..config.twilio_client import build_roadmap_message
        msg = build_roadmap_message([
            {"step": 1, "where": "Bank Branch", "what": "Fix name", "what_bn": "নাম ঠিক করুন"},
            {"step": 2, "where": "BDO Office", "what": "Submit", "what_bn": "জমা দিন"},
        ])
        self.assertIn("1️⃣", msg)
        self.assertIn("2️⃣", msg)
        self.assertIn("Bank Branch", msg)

    def test_format_whatsapp_10_digit(self):
        from ..config.twilio_client import format_whatsapp_number
        self.assertEqual("whatsapp:+919876543210", format_whatsapp_number("9876543210"))

    def test_format_whatsapp_already_formatted(self):
        from ..config.twilio_client import format_whatsapp_number
        self.assertEqual("whatsapp:+919876543210", format_whatsapp_number("whatsapp:+919876543210"))

    def test_format_whatsapp_with_plus(self):
        from ..config.twilio_client import format_whatsapp_number
        self.assertEqual("whatsapp:+919876543210", format_whatsapp_number("+919876543210"))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Settings
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestSettings(unittest.TestCase):

    def test_loads_without_crash(self):
        from ..config.settings import settings
        self.assertIsNotNone(settings)

    def test_default_region_is_mumbai(self):
        from ..config.settings import settings
        self.assertEqual("ap-south-1", settings.AWS_REGION)

    def test_schemes_json_exists(self):
        from ..config.settings import settings
        self.assertTrue(os.path.exists(settings.SCHEMES_JSON_PATH),
                        f"schemes.json not found at {settings.SCHEMES_JSON_PATH}")

    def test_scripts_json_exists(self):
        from ..config.settings import settings
        self.assertTrue(os.path.exists(settings.SCRIPTS_JSON_PATH),
                        f"scripts.json not found at {settings.SCRIPTS_JSON_PATH}")

    def test_repr_does_not_leak_secrets(self):
        from ..config.settings import settings
        r = repr(settings)
        self.assertNotIn("sk_live", r)
        self.assertIn("MISSING", r)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Bedrock fallback (no real AWS call)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestBedrockFallback(unittest.TestCase):

    def test_fallback_green_bn_contains_name_and_score(self):
        from ..config.bedrock_client import _fallback_explanation
        text = _fallback_explanation(90, "GREEN", [], "Lakshmir Bhandar", "Sulata", "bn")
        self.assertIn("Sulata", text)
        self.assertIn("90", text)

    def test_fallback_red_mentions_fatal_count(self):
        from ..config.bedrock_client import _fallback_explanation
        issues = [{"type": "fatal"}, {"type": "fatal"}]
        text = _fallback_explanation(20, "RED", issues, "Lakshmir Bhandar", "Sulata", "bn")
        self.assertIn("2", text)

    def test_fallback_en_contains_name_and_score(self):
        from ..config.bedrock_client import _fallback_explanation
        text = _fallback_explanation(85, "GREEN", [], "Swasthya Sathi", "Priya", "en")
        self.assertIn("Priya", text)
        self.assertIn("85", text)

    def test_generate_explanation_returns_non_empty_string_without_aws(self):
        """With no AWS creds, must fall back to template — never crash or return empty."""
        from ..config.bedrock_client import generate_explanation
        result = generate_explanation(
            score=42, band="RED",
            issues=[{"type": "fatal", "code": "NAME_MISMATCH", "message": "Name mismatch"}],
            scheme_name="Lakshmir Bhandar", profile_name="Sulata", lang="bn"
        )
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 10)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [TestDynamoSaveProfile, TestDynamoGetProfile, TestDynamoSession,
                TestDynamoSaveResult, TestS3AudioCache, TestTwilioMessageBuilders,
                TestSettings, TestBedrockFallback]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)