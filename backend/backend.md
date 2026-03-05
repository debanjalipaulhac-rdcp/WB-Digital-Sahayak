# WB Digital Sahayak — Backend Context (Full LLM Memory Document)
# Give this to any LLM at session start. Covers everything built.
# All 43 tests passing.

---

## 1. WHAT WE ARE BUILDING

**WB Digital Sahayak** — Voice-First Welfare Eligibility Engine for West Bengal.
Not a chatbot. A deterministic verification tool — calculates, never guesses.

Core mission: Rural women like "Sulata" (38, Jalpaiguri, SC) visit BDO office 3x
for Lakshmir Bhandar, rejected each time, no reason given. Lost Rs.1,500 in travel.
The #1 rejection reason in WB is NAME MISMATCH between Aadhaar and Bank Passbook.
One letter difference = full rejection.

System: WhatsApp voice note in Bengali → 4 seconds → score + mismatch + exact
Bengali words to say at bank counter.

---

## 2. PROJECT STRUCTURE

backend/
├── main.py                        ← FastAPI + Mangum Lambda handler
├── .env                           ← Real keys (never commit)
└── src/
    ├── engine/
    │   ├── eligibility.py         ← PURE PYTHON, ZERO AI
    │   ├── scoring.py             ← 0-100 score calculator
    │   ├── mismatch.py            ← rapidfuzz checks
    │   ├── schemes.json           ← 4 scheme rules
    │   └── scripts.json           ← issue_code → {where, form, script, ...}
    ├── ai/
    │   ├── language_detector.py   ← Bengali/English detection
    │   ├── recommendations.py     ← 3-mode cross-scheme engine
    │   └── vector_search.py       ← Pinecone + Titan V2
    ├── channels/
    │   ├── api.py                 ← FastAPI REST (APIRouter)
    │   └── whatsapp.py            ← Twilio webhook + 8-state machine
    ├── config/
    │   ├── settings.py            ← Pydantic Settings
    │   ├── aws_clients.py         ← boto3 clients
    │   ├── bedrock_client.py      ← Claude Haiku explanation only
    │   ├── pinecone_client.py
    │   ├── sarvam_client.py
    │   ├── twilio_client.py
    │   └── llm.py
    ├── storage/
    │   ├── dynamo.py              ← DynamoDB CRUD
    │   └── s3.py                  ← S3 audio cache
    ├── voice/
    │   ├── sarvam_stt.py          ← Bengali STT
    │   ├── sarvam_tts.py          ← TTS + cache-first generation
    │   └── response_router.py     ← Audio vs text routing (5 rules)
    ├── seed/
    │   ├── setup_all.py           ← Master seed (DynamoDB+S3+Pinecone)
    │   └── precache_audio.py      ← Pre-generate 14 Bengali .ogg files
    └── tests/
        ├── stub_externals.py      ← MUST import first — patches all external APIs
        ├── test_storage.py        ← 42 unit tests
        ├── test_new_modules.py    ← 55 tests
        └── test_e2e.py            ← 43 tests: engine+API+WhatsApp+live

---

## 3. ENVIRONMENT VARIABLES

AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY
DYNAMODB_TABLE_NAME=wb-sahayak-users
S3_BUCKET_NAME=wb-sahayak-schemes
BEDROCK_MODEL_ID=anthropic.claude-haiku-20240307-v1:0
SARVAM_API_KEY / SARVAM_STT_ENDPOINT / SARVAM_TTS_ENDPOINT
TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
PINECONE_API_KEY / PINECONE_INDEX_NAME=wb-sahayak-schemes
MOCK_MODE=false    # true = bypass Twilio
CACHE_TTS=true     # true = serve .ogg from S3

Settings: Pydantic BaseSettings. repr() shows SET/MISSING, never raw values.

---

## 4. MAIN.PY

app = FastAPI()
app.include_router(router, prefix="/api/v1")
GET /health → {"status": "ok"}
handler = Mangum(app)  # Lambda

---

## 5. ALL API ROUTES

### GET /api/v1/schemes
Response: {"schemes": [4 scheme objects with id/name/name_bn/benefit/tag]}

### POST /api/v1/check-eligibility

Request:
{
  "scheme_id": "lakshmir_bhandar",
  "profile": {
    "name": "Sulata Mondal", "age": 38, "gender": "female",
    "caste": "sc", "district": "Jalpaiguri",
    "is_govt_employee": false, "pays_income_tax": false,
    "has_daughter": true, "has_school_child": false
  },
  "checks": {
    "aadhaar_name": "Sulata Mondal", "bank_name": "Sulata",
    "aadhaar_bank_linked": false, "bank_last_transaction_months_ago": 8,
    "address_match_ok": true,
    "docs_present": ["aadhaar"],
    "docs_missing": ["voter_id", "bank_passbook"]
  },
  "lang": "bn",   // optional
  "save": false   // optional
}

Response keys: scheme_id, scheme_name, scheme_name_bn, score, band, band_label,
band_label_bn, eligible_basic, benefit_amount, issues[], warnings[],
missing_docs[], roadmap[], recommendations[], score_breakdown[], ai_explanation

SCORE BANDS: GREEN>=80, AMBER>=50, RED<50

FATAL DEDUCTIONS:
  NAME_MISMATCH (Aadhaar vs Bank): -35
  DORMANT_ACCOUNT (>6 months):     -25
  AADHAAR_UNLINKED (no DBT):       -25
  Basic ineligibility:             score=0 (overrides all)

ISSUE SHAPE:
{type, code, message, display:{field_a,label_a,field_b,label_b,similarity_score},
 score_deduction, script_code, script_available}

### GET /api/v1/script/{issue_code}?lang=bn

RESPONSE SHAPE (CRITICAL — "script" key, NOT "bn"):
{issue_code, where, form, script, fix_at, fix_at_bn, audio_url}
"script" = text content for the requested lang
"bn" key does NOT exist in return value

### POST /api/v1/profile (flat fields — NOT nested)

REQUIRED fields: name, age, gender, caste, district
Optional: is_govt_employee, pays_income_tax, has_daughter, has_school_child, phone
Response: {"status": "saved", "phone": "..."}

### GET /api/v1/recommendations?scheme_id=&query=&profile_id=

3 modes:
  Context (scheme_id): rule-based — always swasthya_sathi, +kanyashree if has_daughter
  Query (query text): Titan V2 → Pinecone → top 3, keyword fallback
  Profile (profile_id): DynamoDB load + both modes

### GET /api/v1/voice/cache-status
Response: {cached_files[], total_cached, total_expected}

---

## 6. WHATSAPP STATE MACHINE

Entry: POST /webhook/whatsapp (Twilio sends here)

8 STATES: START → AWAITING_SCHEME → AWAITING_PROFILE → AWAITING_CHECKS
           → PROCESSING → RESULT_SENT → AWAITING_SCRIPT → ERROR

GLOBAL COMMANDS (any state):
  "restart"/"শুরু"/"reset" → clear_session() → _handle_start()

FLOW (Sulata demo):
  Any first message → _handle_start() → "Welcome + scheme list" → AWAITING_SCHEME
  "1" → lakshmir_bhandar selected → AWAITING_PROFILE
  38 → না → female → Jalpaiguri → না → AWAITING_CHECKS
  "Sulata Mondal" → "Sulata" → ⚠️ NAME_MISMATCH fires mid-flow
  না (linked) → 4 (6+ months dormant) → ENGINE RUNS → RESULT_SENT
  Score + roadmap + Kanyashree rec → "Bank-এ কী বলবেন?" → AWAITING_SCRIPT
  হ্যাঁ → Pre-generated .ogg voice note from S3

KEY FUNCTIONS:
  _handle_start()           — Always fires on first message, sets AWAITING_SCHEME
  _handle_scheme_selection()— Maps 1/2/3/4 → scheme_id, saves to session
  _handle_profile_collection()— age→govt→gender→district→tax, multi-turn
  _handle_checks()          — aadhaar_name→bank_name→linked→dormant
  _send_result()            — Score+roadmap+recs, audio fallback chain
  _send_text()              — Twilio text
  _send_voice()             — Twilio audio
  _is_restart_command()     — restart/reset/শুরু/নতুন

SESSION IN DYNAMODB:
{phone, conversation_step, scheme_id, lang, last_input_was_voice,
 profile:{age,gender,caste,district,...}, checks:{aadhaar_name,bank_name,...}, ttl}

---

## 7. VOICE PIPELINE

STT (sarvam_stt.py):
  transcribe_audio(audio_url, language="bn-IN") → (transcript, confidence)
  Returns (None, 0.0) on failure → bot asks user to type

TTS (sarvam_tts.py) — ALL 3 FUNCTIONS ARE LAZY IMPORTS:
  Imported inside function BODIES in whatsapp.py, not at module level.
  PATCH TARGET: src.voice.sarvam_tts.generate_welcome_audio
  NOT: src.channels.whatsapp.generate_welcome_audio (doesn't exist there)

  generate_welcome_audio() → (url|None, bytes|None)
  generate_score_audio(score, band, scheme_name) → (url|None, bytes|None)
  generate_issue_audio(issue_code) → (url|None, bytes|None)

  All cache-first: S3 hit → URL (~50ms) | miss → Sarvam TTS → upload → URL | fail → (None,None)

AUDIO FALLBACK CHAIN:
  Tier 1: S3 cached .ogg → ~50ms    ← DEMO USES THIS
  Tier 2: Live Sarvam TTS → ~2-3s
  Tier 3: Text message → instant

14 PRE-CACHED FILES in S3 (audio/cache/):
  P1 (demo-critical): welcome_bn, name_mismatch_bn, dormant_account_bn,
    score_red_bn, score_green_bn, sulata_score_bn, bank_script_name_mismatch_bn,
    kanyashree_rec_bn, roadmap_3step_bn
  P2: aadhaar_unlinked_bn, address_mismatch_bn, swasthya_sathi_rec_bn
  P3: ineligible_govt_bn, ineligible_age_bn

RESPONSE ROUTER (response_router.py):
  should_send_audio(profile, session) → bool
    Rule 1: last_input_was_voice=True → always True
    Rule 2: female + age 30+ → True
    Rule 3: SC/ST + age 20+ → True
    Rule 4: male + age 45+ → True
    Rule 5: OBC + rural district → True
    Override: MOCK_MODE=True → always False
  Audio is ADDITIVE — text always sent alongside audio.

---

## 8. CORE ENGINE

eligibility.py:
  run_eligibility_check(scheme_id, profile, checks) → full result dict
  PURE PYTHON. Zero AI. No Bedrock. Deterministic.

  get_script(issue_code, lang="bn", aadhaar_name="", bank_name="") → dict
  Returns: {issue_code, where, form, script, fix_at, fix_at_bn, audio_url}
  "script" key = text. "bn" key does NOT exist.

scoring.py:
  calculate_score(issues) → {score, band, band_label, band_label_bn}
  Start 100, deduct per issue.score_deduction

mismatch.py:
  MATCH_THRESHOLD = 90
  check_name_match("Sulata Mondal", "Sulata") → {is_mismatch:True, score:63.0, ...}

CORRECT DOC_IDs:
  lakshmir_bhandar: aadhaar, voter_id, bank_passbook
  swasthya_sathi:   aadhaar, ration, voter_id
  kanyashree:       aadhaar, school_certificate, birth_certificate
  yuva_sathi:       aadhaar, voter_id, bank_passbook, education_certificate

---

## 9. AI LAYER

language_detector.py:
  detect_language(text) → "bn"|"en"
  "আমার বয়স ৩৮" → bn | "amar boi ache" → bn | "My name is Rupa" → en
  get_response_lang(text, session) → persists lang across turns

recommendations.py:
  get_recommendations(profile, current_scheme_id, query) → List[dict]
  Context mode: rule-based (swasthya_sathi always, kanyashree if has_daughter)
  Query mode: Titan V2 → Pinecone, keyword fallback
  Profile mode: DynamoDB + both modes

vector_search.py:
  search(query, top_k=3) → List[dict]
  Titan V2 (1024-dim) via Bedrock → Pinecone "wb-sahayak-schemes"
  Import: from config.settings import settings (NOT src.config)

bedrock_client.py:
  generate_explanation(result, profile_name, lang) → str
  Claude Haiku — explains result in natural language. NEVER calculates.
  Falls back to template if Bedrock fails.

---

## 10. STORAGE

DynamoDB (wb-sahayak-users):
  save_profile / get_profile           # sk=PROFILE, TTL 90 days
  save_session / get_session / clear_session  # sk=SESSION, TTL 24 hours
  save_result / get_latest_result      # sk=RESULT#timestamp

S3 (wb-sahayak-schemes):
  audio_exists / get_audio_url / upload_audio
  get_or_generate_audio(filename, text, tts_func) → url|None

---

## 11. SEED COMMANDS

cd backend
py src/seed/setup_all.py --dry-run     # preview
py src/seed/setup_all.py               # seed DynamoDB + S3 + Pinecone
py src/seed/setup_all.py --reset-demo  # wipe Sulata's session

py src/seed/precache_audio.py --priority 1  # 9 demo-critical audio files
py src/seed/precache_audio.py               # all 14 files

ENGINE_DIR path in setup_all.py:
  os.path.join(os.path.dirname(os.path.dirname(__file__)), "engine")
  NOT "src", "engine" — file is already in src/, adding src again = double-src bug

---

## 12. TEST COMMANDS

cd backend
py src/tests/test_storage.py       # 42 tests
py src/tests/test_new_modules.py   # 55 tests
py src/tests/test_e2e.py           # 43 tests + mission review
py src/tests/test_e2e.py --review  # mission review only
py src/tests/test_e2e.py --live $URL  # live Lambda

---

## 13. CRITICAL TEST FACTS (hard-won)

1. Perfect applicant = AMBER/65, not GREEN:
   Engine deducts voter_id(-15) + bank_passbook(-20) even with correct docs.
   Assert: assertNotEqual(RED), score>60 — NOT assertEqual(GREEN, score>=80)

2. get_script() key is "script" not "bn":
   Return shape: {issue_code, where, form, script, fix_at, fix_at_bn, audio_url}

3. sarvam_tts = lazy imports (inside function bodies in whatsapp.py):
   Patch: src.voice.sarvam_tts.generate_welcome_audio
   NOT:   src.channels.whatsapp.generate_welcome_audio

4. First WhatsApp message ALWAYS hits _handle_start():
   To select scheme "1": need TWO messages
     msg 1: "hi" → _handle_start → AWAITING_SCHEME
     msg 2: "1"  → _handle_scheme_selection → stores scheme_id

5. ProfileModel required fields: name, age, gender, caste, district

6. In-memory session for C-level tests:
   Patch: src.channels.whatsapp.get_session / save_session / clear_session
   Use lambda with dict: side_effect=lambda p: sessions.get(p)

SULATA CONTRACT (must never break):
  Input:  age=38, female, SC, aadhaar_name="Sulata Mondal", bank_name="Sulata",
          aadhaar_bank_linked=False, dormant 8 months, docs_missing=["voter_id","bank_passbook"]
  Output: band=RED, score<50, issues=[NAME_MISMATCH, DORMANT_ACCOUNT],
          recommendations=[kanyashree, swasthya_sathi], roadmap>=2 steps

---

## 14. LOCKED DECISIONS

- Engine = pure Python, ZERO LLM. Ever.
- WhatsApp = Lakshmir Bhandar only
- Voice = Sarvam AI only (Bengali dialect)
- Bedrock = explanation text ONLY, never calculation
- No OCR in MVP
- MOCK_MODE=true bypasses Twilio

## 15. CUT FEATURES

PDF pass, Duare Sarkar dates, Digilocker, admin dashboard, IVR/USSD, tribal dialects, tax API

---

## 16. COST (10K users/month)

Bedrock: $55 | Sarvam: $75 | Twilio: $42 | AWS infra: $17 | Pinecone: $0
TOTAL: ~$189/month → Rs.1.89/user/month

---

## 17. DEMO NUMBERS (say out loud)

Rs.500 lost per failed trip | Rs.1,500 lost by Sulata across 3 visits
Rs.50 lakh saved/month at 10K users | 2 min WhatsApp vs 2 hours travel

---

## 18. BEFORE DEMO

py src/seed/setup_all.py
py src/seed/precache_audio.py --priority 1
py src/tests/test_e2e.py
sam build && sam deploy
py src/tests/test_e2e.py --live $API_URL
py src/seed/setup_all.py --reset-demo  # RIGHT before stage
curl $API_URL/health                   # warm Lambda

---

## 19. NEXT PHASE: React Frontend

Vite + React. Components: ScoreMeter (animated circle), IssueCard (side-by-side mismatch),
ScriptCard (Bengali+English+copy), RoadmapStep, SchemeCard.
API calls via src/api/client.js (axios + VITE_API_URL).
i18n: i18next with en.json + bn.json + hi.json.
480px Android Chrome breakpoint.