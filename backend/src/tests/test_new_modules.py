"""
src/tests/test_new_modules.py
==============================
Tests for the 3 modules that existed but had no tests:
  - src/ai/recommendations.py   (3-mode engine)
  - src/ai/language_detector.py (Bengali/English detection)
  - src/voice/response_router.py (audio routing rules)

These are the modules that were "done" but unverified.
Run: python -m unittest src/tests/test_new_modules.py -v
"""
import sys, os, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))
import src.tests.stub_externals  # noqa — must be first
import src.ai.recommendations
import src.ai.language_detector
import src.voice.response_router

from unittest.mock import patch


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Language Detector
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestLanguageDetector(unittest.TestCase):

    def _d(self, text):
        from src.ai.language_detector import detect_language
        return detect_language(text)

    # Bengali Unicode script
    def test_bengali_unicode_returns_bn(self):
        self.assertEqual("bn", self._d("আমার বয়স ৩৮"))

    def test_bengali_unicode_mixed_returns_bn(self):
        self.assertEqual("bn", self._d("আমার wife এর জন্য scheme"))

    def test_bengali_unicode_short_returns_bn(self):
        self.assertEqual("bn", self._d("হ্যাঁ"))

    # Romanized Bengali
    def test_romanized_ami_returns_bn(self):
        self.assertEqual("bn", self._d("ami 38 bochor"))

    def test_romanized_apnar_returns_bn(self):
        self.assertEqual("bn", self._d("apnar scheme ache?"))

    def test_romanized_bdo_returns_bn(self):
        self.assertEqual("bn", self._d("bdo office jabo"))

    def test_romanized_gram_returns_bn(self):
        self.assertEqual("bn", self._d("gram panchayat e jete hobe"))

    # English
    def test_english_returns_en(self):
        self.assertEqual("en", self._d("My age is 38"))

    def test_english_question_returns_en(self):
        self.assertEqual("en", self._d("what is my readiness score"))

    def test_english_scheme_query_returns_en(self):
        self.assertEqual("en", self._d("I need health insurance for my family"))

    # Edge cases
    def test_empty_defaults_to_bn(self):
        self.assertEqual("bn", self._d(""))

    def test_numbers_only_defaults_to_bn(self):
        self.assertEqual("bn", self._d("38"))

    def test_mixed_mostly_bengali_returns_bn(self):
        # More Bengali signal than English
        self.assertEqual("bn", self._d("আমি hospital এ যাব কারণ my mother is sick"))

    def test_get_response_lang_uses_session_preference(self):
        from src.ai.language_detector import get_response_lang
        # Session has explicit lang → use it even if text says otherwise
        result = get_response_lang("My age is 38", session={"lang": "bn"})
        self.assertEqual("bn", result)

    def test_get_response_lang_detects_when_no_session(self):
        from src.ai.language_detector import get_response_lang
        result = get_response_lang("My age is 38", session={})
        self.assertEqual("en", result)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Response Router
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestResponseRouter(unittest.TestCase):

    def _should(self, profile, session=None):
        """Call should_send_audio with MOCK_MODE=False, restore after."""
        from src.voice.response_router import should_send_audio
        from src.config.settings import settings as s
        orig = s.MOCK_MODE
        s.MOCK_MODE = False
        try:
            return should_send_audio(profile, session or {})
        finally:
            s.MOCK_MODE = orig

    # Rule 1: Voice input → always audio
    def test_voice_input_always_gets_audio(self):
        self.assertTrue(self._should(
            {"age": 25, "gender": "male", "caste": "general"},
            {"last_input_was_voice": True}
        ))

    def test_text_input_young_male_general_gets_text(self):
        self.assertFalse(self._should(
            {"age": 25, "gender": "male", "caste": "general"},
            {"last_input_was_voice": False}
        ))

    # Rule 2: Female 30+
    def test_female_30_gets_audio(self):
        self.assertTrue(self._should({"age": 30, "gender": "female", "caste": "general"}))

    def test_female_38_sulata_gets_audio(self):
        # Sulata MUST get audio — this is the primary demo user
        self.assertTrue(self._should({"age": 38, "gender": "female", "caste": "sc"}))

    def test_female_29_does_not_trigger_rule2(self):
        # 29 < 30 — rule 2 doesn't apply, but check if another rule catches it
        result = self._should({"age": 29, "gender": "female", "caste": "general"})
        # Not necessarily False (SC/ST rule might catch it), but general female 29 → text
        self.assertFalse(result)

    # Rule 3: SC/ST 20+
    def test_sc_20_gets_audio(self):
        self.assertTrue(self._should({"age": 20, "gender": "male", "caste": "sc"}))

    def test_st_25_gets_audio(self):
        self.assertTrue(self._should({"age": 25, "gender": "male", "caste": "st"}))

    def test_obc_20_does_not_trigger_sc_st_rule(self):
        # OBC is not SC/ST — check OBC rural rule separately
        result = self._should({"age": 20, "gender": "male", "caste": "obc", "district": "Kolkata"})
        self.assertFalse(result)  # urban OBC → text

    # Rule 4: Male 45+
    def test_male_45_gets_audio(self):
        self.assertTrue(self._should({"age": 45, "gender": "male", "caste": "general"}))

    def test_male_44_does_not_trigger_rule4(self):
        self.assertFalse(self._should({"age": 44, "gender": "male", "caste": "general"}))

    # Rule 5: OBC rural
    def test_obc_rural_jalpaiguri_gets_audio(self):
        self.assertTrue(self._should({
            "age": 30, "gender": "male", "caste": "obc", "district": "Jalpaiguri"
        }))

    def test_obc_urban_kolkata_does_not_trigger_rural_rule(self):
        self.assertFalse(self._should({
            "age": 30, "gender": "male", "caste": "obc", "district": "Kolkata"
        }))

    # MOCK_MODE
    def test_mock_mode_always_returns_false(self):
        from src.voice.response_router import should_send_audio
        from src.config.settings import settings as s
        orig = s.MOCK_MODE
        s.MOCK_MODE = True
        try:
            result = should_send_audio(
                {"age": 38, "gender": "female", "caste": "sc"},
                {"last_input_was_voice": True}
            )
        finally:
            s.MOCK_MODE = orig
        self.assertFalse(result)

    # format_whatsapp_response
    def test_format_response_audio_when_eligible(self):
        from src.voice.response_router import format_whatsapp_response
        from src.config.settings import settings as s
        orig = s.MOCK_MODE
        s.MOCK_MODE = False
        try:
            result = format_whatsapp_response(
                text="Your score is 42",
                text_bn="আপনার score 42",
                audio_url="https://s3.../score.ogg",
                profile={"age": 38, "gender": "female", "caste": "sc"},
                session={},
                lang="bn"
            )
        finally:
            s.MOCK_MODE = orig
        self.assertTrue(result["send_audio"])
        self.assertIsNotNone(result["audio_url"])
        self.assertEqual("আপনার score 42", result["text"])

    def test_format_response_text_when_not_eligible(self):
        from src.voice.response_router import format_whatsapp_response
        from src.config.settings import settings as s
        orig = s.MOCK_MODE
        s.MOCK_MODE = False
        try:
            result = format_whatsapp_response(
                text="Your score is 85",
                text_bn=None,
                audio_url="https://s3.../score.ogg",
                profile={"age": 25, "gender": "male", "caste": "general"},
                session={},
                lang="en"
            )
        finally:
            s.MOCK_MODE = orig
        self.assertFalse(result["send_audio"])
        self.assertIsNone(result["audio_url"])
        self.assertEqual("Your score is 85", result["text"])

    def test_format_response_no_audio_url_means_text_only(self):
        from src.voice.response_router import format_whatsapp_response
        from src.config.settings import settings as s
        orig = s.MOCK_MODE
        s.MOCK_MODE = False
        try:
            result = format_whatsapp_response(
                text="Your score",
                text_bn="আপনার score",
                audio_url=None,
                profile={"age": 38, "gender": "female", "caste": "sc"},
                session={},
            )
        finally:
            s.MOCK_MODE = orig
        self.assertFalse(result["send_audio"])

    def test_explain_routing_decision_returns_string(self):
        from src.voice.response_router import explain_routing_decision
        result = explain_routing_decision(
            {"age": 38, "gender": "female", "caste": "sc"}, {}
        )
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 5)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Recommendations Engine — 3 modes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class TestRecommendationsProfileBased(unittest.TestCase):
    """Mode 1: profile → which schemes can this person apply for?"""

    def test_female_38_sc_gets_lakshmir_bhandar(self):
        from src.ai.recommendations import profile_based
        recs = profile_based({"age": 38, "gender": "female", "caste": "sc"})
        ids = [r["scheme_id"] for r in recs]
        self.assertIn("lakshmir_bhandar", ids)

    def test_everyone_gets_swasthya_sathi(self):
        from src.ai.recommendations import profile_based
        recs = profile_based({"age": 30, "gender": "male", "caste": "general"})
        ids = [r["scheme_id"] for r in recs]
        self.assertIn("swasthya_sathi", ids)

    def test_govt_employee_gets_empty_list(self):
        from src.ai.recommendations import profile_based
        recs = profile_based({"age": 38, "gender": "female", "is_govt_employee": True})
        self.assertEqual([], recs, "Govt employees are ineligible for all cash schemes")

    def test_tax_payer_gets_empty_list(self):
        from src.ai.recommendations import profile_based
        recs = profile_based({"age": 38, "gender": "female", "pays_income_tax": True})
        self.assertEqual([], recs)

    def test_male_does_not_get_lakshmir_bhandar(self):
        from src.ai.recommendations import profile_based
        recs = profile_based({"age": 38, "gender": "male", "caste": "general"})
        ids = [r["scheme_id"] for r in recs]
        self.assertNotIn("lakshmir_bhandar", ids, "Lakshmir Bhandar is female-only")

    def test_under_age_excluded(self):
        from src.ai.recommendations import profile_based
        # Age 20 is below Lakshmir Bhandar min (25)
        recs = profile_based({"age": 20, "gender": "female", "caste": "general"})
        ids = [r["scheme_id"] for r in recs]
        self.assertNotIn("lakshmir_bhandar", ids)

    def test_exclude_scheme_id_works(self):
        from src.ai.recommendations import profile_based
        recs = profile_based(
            {"age": 38, "gender": "female", "caste": "sc"},
            exclude_scheme_id="lakshmir_bhandar"
        )
        ids = [r["scheme_id"] for r in recs]
        self.assertNotIn("lakshmir_bhandar", ids)

    def test_output_has_required_fields(self):
        from src.ai.recommendations import profile_based
        recs = profile_based({"age": 38, "gender": "female", "caste": "sc"})
        for r in recs:
            for field in ["scheme_id", "scheme_name", "reason", "matched_by", "confidence"]:
                self.assertIn(field, r, f"Rec missing field: '{field}'")


class TestRecommendationsContextBased(unittest.TestCase):
    """Mode 2: viewing scheme X → suggest related Y, Z"""

    def test_viewing_lakshmir_with_daughter_suggests_kanyashree(self):
        from src.ai.recommendations import context_based
        recs = context_based("lakshmir_bhandar", profile={"has_daughter": True, "gender": "female"})
        ids = [r["scheme_id"] for r in recs]
        self.assertIn("kanyashree", ids)

    def test_viewing_lakshmir_always_suggests_swasthya_sathi(self):
        from src.ai.recommendations import context_based
        recs = context_based("lakshmir_bhandar", profile={"gender": "female"})
        ids = [r["scheme_id"] for r in recs]
        self.assertIn("swasthya_sathi", ids)

    def test_current_scheme_not_in_results(self):
        from src.ai.recommendations import context_based
        recs = context_based("lakshmir_bhandar")
        ids = [r["scheme_id"] for r in recs]
        self.assertNotIn("lakshmir_bhandar", ids, "Should never recommend the current scheme")

    def test_unknown_scheme_returns_empty(self):
        from src.ai.recommendations import context_based
        recs = context_based("NONEXISTENT_SCHEME_XYZ")
        self.assertEqual([], recs)

    def test_no_daughter_does_not_get_kanyashree(self):
        from src.ai.recommendations import context_based
        recs = context_based("lakshmir_bhandar", profile={
            "gender": "female", "has_daughter": False, "has_school_child": False
        })
        ids = [r["scheme_id"] for r in recs]
        # kanyashree trigger requires has_daughter or is_enrolled_in_school
        self.assertNotIn("kanyashree", ids)


class TestRecommendationsQueryBased(unittest.TestCase):
    """Mode 3: freeform query → vector/keyword search"""

    def test_hospital_query_finds_swasthya_sathi(self):
        from src.ai.recommendations import query_based
        # embed() will fail (no AWS) → keyword fallback
        recs = query_based("hospital free treatment sick mother")
        ids = [r["scheme_id"] for r in recs]
        self.assertIn("swasthya_sathi", ids)

    def test_woman_scheme_finds_lakshmir(self):
        from src.ai.recommendations import query_based
        recs = query_based("scheme for my wife monthly cash")
        ids = [r["scheme_id"] for r in recs]
        self.assertIn("lakshmir_bhandar", ids)

    def test_empty_query_returns_empty_or_defaults(self):
        # Empty query: vector_search returns [] (empty text)
        # keyword_fallback then returns default schemes (not empty)
        # This is correct behaviour — an empty query shows all options
        from src.ai.recommendations import query_based
        recs = query_based("")
        # Must not crash. Returns empty (vector_search guards on empty string)
        self.assertIsInstance(recs, list)

    def test_returns_list(self):
        from src.ai.recommendations import query_based
        recs = query_based("unemployed youth job")
        self.assertIsInstance(recs, list)


class TestRecommendationsMerged(unittest.TestCase):
    """get_recommendations() — merged, deduplicated output"""

    def test_deduplication_profile_and_context_overlap(self):
        """If profile_based and context_based both return swasthya_sathi, it appears once."""
        from src.ai.recommendations import get_recommendations
        recs = get_recommendations(
            profile={"age": 38, "gender": "female", "caste": "sc"},
            current_scheme_id="lakshmir_bhandar"
        )
        scheme_ids = [r["scheme_id"] for r in recs]
        # No duplicates
        self.assertEqual(len(scheme_ids), len(set(scheme_ids)))

    def test_current_scheme_excluded_from_results(self):
        from src.ai.recommendations import get_recommendations
        recs = get_recommendations(
            profile={"age": 38, "gender": "female", "caste": "sc"},
            current_scheme_id="lakshmir_bhandar"
        )
        ids = [r["scheme_id"] for r in recs]
        self.assertNotIn("lakshmir_bhandar", ids)

    def test_top_k_respected(self):
        from src.ai.recommendations import get_recommendations
        recs = get_recommendations(
            profile={"age": 38, "gender": "female", "caste": "sc", "has_daughter": True},
            top_k=2
        )
        self.assertLessEqual(len(recs), 2)

    def test_sulata_full_profile_gets_kanyashree_and_swasthya(self):
        """Sulata (has_daughter=True) must get both Kanyashree and Swasthya Sathi."""
        from src.ai.recommendations import get_recommendations
        recs = get_recommendations(
            profile={
                "age": 38, "gender": "female", "caste": "sc",
                "has_daughter": True, "is_govt_employee": False
            },
            current_scheme_id="lakshmir_bhandar",
            top_k=5
        )
        ids = [r["scheme_id"] for r in recs]
        self.assertIn("kanyashree",     ids, "Sulata must get Kanyashree (has_daughter=True)")
        self.assertIn("swasthya_sathi", ids, "Sulata must get Swasthya Sathi (always)")

    def test_no_args_returns_empty(self):
        from src.ai.recommendations import get_recommendations
        recs = get_recommendations()
        self.assertEqual([], recs)

    def test_output_schema_complete(self):
        from src.ai.recommendations import get_recommendations
        recs = get_recommendations(
            profile={"age": 38, "gender": "female", "caste": "sc"}
        )
        for r in recs:
            for field in ["scheme_id", "scheme_name", "reason", "matched_by",
                          "confidence", "benefit_display", "apply_at"]:
                self.assertIn(field, r, f"Recommendation missing field: '{field}'")


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = unittest.TestSuite()
    for cls in [TestLanguageDetector, TestResponseRouter,
                TestRecommendationsProfileBased, TestRecommendationsContextBased,
                TestRecommendationsQueryBased, TestRecommendationsMerged]:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)