# WB Digital Sahayak — Project Context File
> **Use this file as context when working with any LLM (Claude, GPT, Gemini, etc.)**  
> It describes everything about this project: what we're building, why, the tech stack, build order, current status, and open problems.
>
> **Last reviewed:** Post feature-review session. Sections 4, 10, 11, 12, 15, 16, 19 updated with final decisions.

---

## 1. PROJECT IDENTITY

| Field | Value |
|---|---|
| **Project Name** | WB Digital Sahayak (ডিজিটাল সহায়ক) |
| **Tagline** | Voice-First Welfare Eligibility Engine for West Bengal |
| **Hackathon** | AI for Bharat Hackathon — Powered by AWS |
| **Team** | Team Web |
| **Team Leader** | Souvik Karmakar |
| **Deadline** | 2 days from project start |
| **Stage** | Phase 0 complete — Building Phase 1 now |

---

## 2. THE PROBLEM WE ARE SOLVING

West Bengal has **₹25,000+ crore in annual welfare benefits** that millions of citizens cannot access because:

- Portals are text-heavy, English-centric, and require high digital literacy
- Citizens visit government offices **unprepared** and get rejected — wasting ₹500/trip (₹200 bus + ₹300 lost daily wage)
- **The #1 rejection reason is NOT missing documents — it is NAME MISMATCH** between Aadhaar and Bank Passbook (a single letter difference causes full rejection)
- Bank accounts go **dormant** — benefits get credited but bounce back; citizen thinks govt cheated them
- Application rejection reasons are never explained ("hobe na" / "slowly slowly") — total black box
- Rural smartphone penetration in some WB districts is as low as 5.8% — web-only solutions miss the real target
- Average **2.3 documents missing per user** at time of application
- Scheme rules change with new Government Orders (GOs) from Nabanna — static PDFs go stale fast
- Unscrupulous intermediaries intentionally introduce name errors to force citizens to pay for "corrections"

**We are NOT building a chatbot. We are building a Verification Tool that calculates, not guesses.**

---

## 3. WHO WE ARE BUILDING FOR

**Primary User — "Sulata":** Rural/semi-urban women in West Bengal, age 25–60, applying for Lakshmir Bhandar
- Low or zero digital literacy
- Speaks Bengali (rural dialect, NOT "book Bengali")
- Uses WhatsApp on a basic Android smartphone
- Has been to the BDO office 2–3 times and been rejected without explanation
- Cannot afford to waste another day of daily wage labor (₹300/day) on a failed trip

**Secondary Users:**
- Youth (18–45) applying for Yuva Sathi unemployment allowance
- Families applying for Swasthya Sathi health coverage
- Parents with daughters applying for Kanyashree Prakalpa

---

## 4. WHAT WE ARE BUILDING

### PRIMARY CHANNEL: WhatsApp Bot (Twilio + Sarvam AI)
> **This is the demo channel. Make it perfect. Everything else is secondary.**

- **Text flow:** User sends message → guided Lakshmir Bhandar check → score + mismatch alert + roadmap + script
- **Voice note flow:** User sends Bengali voice note → Sarvam STT → Eligibility engine → Sarvam TTS → Bengali voice note reply
- **Session state:** Multi-turn conversation tracked in DynamoDB per phone number
- **The winning moment:** Voice note goes in Bengali → 4 seconds → Bot replies in Bengali with exact mismatch + exact words to say at the bank

### SECONDARY CHANNEL: Web App (React)
- Profile → Scheme selection → Step-by-step eligibility check → Readiness Score (animated) → Action Roadmap
- Multilingual: English / Bengali / Hindi
- Works on low-end Android (Chrome)
- **Doubles as demo backup if Twilio flakes during presentation**

### Core Engine (shared by both channels):
- **Deterministic Eligibility Engine** — pure Python rules, zero AI hallucination
- **Readiness Score (0–100)** — weighted scoring with animated circular reveal
- **Mismatch Detector** — name/DOB/address discrepancy check, side-by-side visual
- **Script Generator** — exact Bengali words to say at each office ← KEY DIFFERENTIATOR
- **Missing Document Identifier** — what's missing + exactly where to get it
- **Action Roadmap** — ordered office visit steps
- **Cross-Scheme Recommendation Engine** — rule engine + vector similarity

---

## 5. SCHEMES COVERED

### MVP — Demo (WhatsApp = Lakshmir Bhandar ONLY):
> Hard-code one scheme perfectly. Judges remember depth, not breadth.

| Scheme | Benefit | Target | WhatsApp | Web |
|---|---|---|---|---|
| Lakshmir Bhandar | ₹1,000–₹1,200/month | Women 25–60 | ✅ Full flow | ✅ |
| Swasthya Sathi | ₹5 lakh health cover/year | All families | ❌ Text mention | ✅ |
| Kanyashree Prakalpa | ₹1,000/yr + ₹25,000 at 18 | Girls 13–19 | ✅ Recommendation only | ✅ |
| Yuva Sathi | ₹1,500–₹2,000/month | Youth 18–45 | ❌ Text mention | ✅ |

### Phase 2 (3 months):
- All 4 schemes on WhatsApp, add Ration Card / Sabuj Sathi / Rupashree schemes
- Digilocker integration for auto-document fetch
- Admin interface for clerks to update scheme JSON without redeployment

### Phase 3 (1 year):
- All 20+ WB schemes + tribal dialects (Santali, Rajbanshi)
- IVR / USSD for feature phones

---

## 6. TECH STACK (EXACT TOOLS — DO NOT DEVIATE)

### Backend / Core Engine
| Component | Technology | Why |
|---|---|---|
| Eligibility Engine | **Pure Python** — no AI | Zero hallucination, deterministic, unit-testable |
| Name Mismatch Detection | **`rapidfuzz`** | Fuzzy matching — catches "Sulata" vs "Sulata Mondal" |
| Scoring Algorithm | Custom Python function | Full control over weights |
| Script Generator | Python dict lookup (`issue_code → script`) | Simple, fast, no AI needed |
| API Layer | **AWS Lambda + API Gateway** | Serverless, scales, in original PDF spec |
| User Profile Storage | **Amazon DynamoDB** | In PDF spec, schemaless |
| Scheme Rules Storage | **Amazon S3** (JSON files) | In PDF spec — updatable without redeploy |
| Background Alerts | **AWS Lambda cron** (EventBridge) | Renewal reminders |
| Monitoring | **AWS CloudWatch** | In PDF spec |

### AI / Intelligence Layer
| Component | Technology | Why |
|---|---|---|
| Natural Language Explanations | **Amazon Bedrock** (Claude Haiku) | In PDF spec — explains deterministic output, doesn't calculate it |
| Scheme Knowledge Base (RAG) | **Amazon Bedrock Knowledge Bases** | Ingests new GOs automatically — answer to "how do you scale rules?" |
| Semantic Scheme Search | **Pinecone** (free tier) | Vector DB for freeform queries "scheme for sick mother" |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`) | Embed scheme descriptions |
| Cross-Scheme Recommendations | Vector cosine similarity + rule engine | Kanyashree fires on `has_daughter: true` |

### Voice Pipeline
| Component | Technology | Why |
|---|---|---|
| Speech-to-Text | **Sarvam AI** (`sarvam-2b`) | Bengali STT — Indic-specific, in PDF spec |
| Text-to-Speech | **Sarvam AI TTS** | Bengali voice with natural rural inflection |
| Language Detection | Sarvam AI built-in | Auto-detects Bengali / Hindi / English |
| TTS Latency Fix | Pre-generated `.ogg` files cached on S3 | Eliminates live TTS latency during demo |

### WhatsApp Channel
| Component | Technology | Why |
|---|---|---|
| WhatsApp API | **Twilio WhatsApp** | In PDF spec, ₹0.35/conversation |
| Webhook Handler | AWS Lambda (Python) | Receives Twilio POST events |
| Voice Note Processing | Twilio media URL → Sarvam STT → engine → Sarvam TTS → Twilio send | Full voice loop |
| Session State | DynamoDB (`phone_number` partition key) | Lambda is stateless — conversation context persisted here |
| Mock / Fallback Mode | `MOCK_MODE=true` env flag | Bypasses Twilio — web UI simulates WhatsApp if Twilio flakes |

### Frontend (Web)
| Component | Technology | Why |
|---|---|---|
| Framework | **React** (Vite) | Fast dev |
| Animations | **Antigravity** | Score meter reveal — specified in plan |
| Design System | **Stitch** | Specified in plan |
| Multilingual | `i18next` + `en.json`, `bn.json`, `hi.json` | EN / Bengali / Hindi |
| State | React Context + `useState` | Sufficient complexity |
| API calls | `axios` — all in `src/api/client.js` | Centralised, easy to mock |

### Infrastructure
| Component | Technology |
|---|---|
| IaC | AWS SAM (`template.yaml`) |
| CI/CD | GitHub Actions |
| Secrets | `.env` + AWS Secrets Manager |
| Local Dev | `sam local start-api` |

---

## 7. SCORING MATRIX (LOCKED — DO NOT CHANGE WITHOUT UPDATING TESTS)

```
BASE SCORE = 100

━━━ FATAL DEDUCTIONS ━━━
Name mismatch Aadhaar ↔ Bank Passbook           -35 pts
Dormant bank account (>6 months inactive)       -25 pts
Aadhaar NOT linked to bank (DBT not set up)     -25 pts
Basic ineligibility (age/gender/govt/tax)       -40 pts  ← overrides everything

━━━ WARNING DEDUCTIONS ━━━
Address mismatch Ration Card ↔ Voter Card       -10 pts
Missing optional doc (e.g. Caste Certificate)   -05 pts
Bank account < 3 months old                     -08 pts

━━━ MISSING REQUIRED DOCS ━━━
Each missing required document                  -10 pts

━━━ SCORE BANDS ━━━
80–100  🟢 GREEN   "Go to office tomorrow — you are ready"
50–79   🟡 AMBER   "Fix the issues, THEN go. Don't waste the trip."
00–49   🔴 RED     "Do NOT go yet. You WILL be rejected. Follow the roadmap."
```

---

## 8. DOCUMENT CROSS-VERIFICATION RULES (Mismatch Engine)

| Check | Field A | Field B | Severity |
|---|---|---|---|
| Name match | Aadhaar name | Bank passbook name | FATAL |
| Name match | Aadhaar name | Voter Card name | FATAL |
| DOB match | Aadhaar DOB | Birth Certificate | FATAL |
| Address match | Ration Card address | Voter Card address | WARNING |
| Account active | Last bank transaction | Today (>6 months = dormant) | FATAL |
| Aadhaar-Bank link | DBT seeding | User self-report | FATAL |
| Caste cert residency | WB resident since 1950 | Cert issue date | WARNING |

**Implementation:** No OCR in MVP. User types name from each card. `rapidfuzz.ratio()` — if < 90, flag mismatch. UI shows both names side-by-side with red ❌ when mismatch fires.

---

## 9. CROSS-SCHEME RECOMMENDATION LOGIC

```
Rule-based (checked first, instant):
  Lakshmir Bhandar eligible + has_daughter: true  → Kanyashree Prakalpa
  Lakshmir Bhandar eligible + has_school_child    → Sabuj Sathi (bicycle)
  Any scheme eligible                             → Swasthya Sathi (always)
  caste = SC/ST                                   → Show ₹1,200 (not ₹1,000) for Lakshmir Bhandar
  unemployed + age 18–45                          → Yuva Sathi alongside any scheme

Vector search (Pinecone — for freeform queries):
  "scheme for sick mother" → embed → cosine similarity → top 3 → filter through engine → return

DEMO REQUIREMENT: Sulata profile MUST have has_daughter: true
  so Kanyashree suggestion fires automatically in the live demo.
```

---

## 10. THE "SCRIPT GENERATOR" FEATURE ← KEY DIFFERENTIATOR

> Nobody else will build this. It turns "fix your name" into "here are the exact words to say."

**How it works:**
Each issue code maps to a pre-written script with: where to go, which form to ask for, exact Bengali words, exact English words. Delivered as a voice note on WhatsApp (Sarvam TTS) or text card on Web.

**`scripts.json` (stored in S3):**
```json
{
  "NAME_MISMATCH": {
    "where": "Bank Branch or Post Office",
    "form": "KYC Update Form",
    "bn": "Counter-e jaao, bolo: 'Amar Aadhaar-e naam {aadhaar_name}, kintu bank-e {bank_name} ache. Aadhaar onujayi KYC update korte chai. Form ta deben please.'",
    "en": "Go to the counter and say: 'My name on Aadhaar is {aadhaar_name} but my bank shows {bank_name}. I want to update my KYC as per Aadhaar. Please give me the form.'"
  },
  "DORMANT_ACCOUNT": {
    "where": "Your Bank Branch",
    "form": "Account Reactivation Request",
    "bn": "Branch-e jao, bolo: 'Amar account dormant hoye geche. Reactivate korte chai. Ki korte hobe?'",
    "en": "Go to the branch and say: 'My account has gone dormant. I want to reactivate it. What do I need to do?'"
  },
  "AADHAAR_UNLINKED": {
    "where": "Bank Branch (bring Aadhaar card)",
    "form": "Aadhaar Seeding Form",
    "bn": "Aadhaar card niye bank-e jao, bolo: 'Amar account-e Aadhaar seeding korte chai DBT-r jonyo.'",
    "en": "Go to the bank with Aadhaar and say: 'I want Aadhaar seeding done on my account for DBT.'"
  },
  "ADDRESS_MISMATCH": {
    "where": "Gram Panchayat / Ward Office",
    "form": "Address Correction Form",
    "bn": "Panchayat-e jao, duto card niye. Bolo: 'Ration card-er thikana Voter card-er sathe mile na. Update korte chai.'",
    "en": "Go to Gram Panchayat with both cards. Say: 'My Ration Card address doesn't match my Voter Card. I need it corrected.'"
  }
}
```

**WhatsApp delivery sequence:**
```
Bot detects NAME_MISMATCH →
"⚠️ নামে গরমিল! Aadhaar: 'Sulata Mondal' | Bank: 'Sulata' ❌"
"Bank-এ কী বলবেন জানতে চান?"
[Button: হ্যাঁ, বলুন]
→ User taps → Bot sends pre-generated .ogg voice note in Bengali with exact script
```

---

## 11. WHATSAPP CONVERSATION FLOW (Lakshmir Bhandar — Hard-coded)

```
User  → "Lakshmir Bhandar" (text) OR voice note in Bengali
Bot   → "আপনার বয়স কত?" (How old are you?)
User  → "38" or voice
Bot   → "আপনি কি সরকারি কর্মী?" [হ্যাঁ / না buttons]
User  → না
Bot   → "Aadhaar card-এ আপনার নাম কী?"
User  → "Sulata Mondal"
Bot   → "Bank passbook-এ নাম কী?"
User  → "Sulata"
Bot   → [ENGINE FIRES — NAME_MISMATCH]
       "⚠️ নামে গরমিল পাওয়া গেছে!
        Aadhaar: 'Sulata Mondal' | Bank: 'Sulata' ❌
        এটাই Lakshmir Bhandar reject-এর #1 কারণ।"
Bot   → "শেষ bank transaction কতদিন আগে?"
       [<1 month | 1–3 months | 3–6 months | 6+ months]
User  → 6+ months
Bot   → "⚠️ Account dormant হতে পারে। Benefit ঢুকবে না।"
Bot   → "🔴 Readiness Score: 42/100
        এখনই BDO office যাবেন না।"
Bot   → "✅ আপনার Roadmap:
        1️⃣ Bank/Post Office → নাম ঠিক করুন (জরুরি)
        2️⃣ Bank → Account reactivate করুন (জরুরি)
        3️⃣ BDO Office → Application submit করুন"
Bot   → "📢 আপনার মেয়ে আছে? Kanyashree-তে ₹25,000 পেতে পারেন!"
Bot   → "Bank-এ কী বলবেন? [হ্যাঁ] টিপুন 👇"
→ [Pre-generated Bengali voice note plays]
```

**Voice Note Pipeline:**
```
1. User sends voice note on WhatsApp
2. Twilio webhook fires → Lambda receives media URL
3. Lambda downloads audio → sends to Sarvam AI STT
4. Transcript returned → NLU extracts intent + entities
5. Eligibility engine runs → response text built
6. Check S3 cache for pre-generated audio
   → Cache hit: serve instantly
   → Cache miss: call Sarvam TTS → save to S3 → serve
7. Lambda sends .ogg audio back via Twilio
```

**Fallback chain:**
- Sarvam STT fails → ask user to type: "Voice বুঝিনি। Type করুন please."
- Twilio fails → switch to `MOCK_MODE=true`, demo from web UI

---

## 12. BUILD ORDER — 2 DAYS

### DAY 1

**PHASE 1 — Core Engine (4 hrs) ← START HERE**
- [ ] `schemes.json` — all 4 schemes with rules, required docs, weights
- [ ] `eligibility.py` — pure Python rules engine, all 4 schemes
- [ ] `scoring.py` — weighted score calculator
- [ ] `mismatch.py` — rapidfuzz name/address checks
- [ ] `scripts.json` — Script Generator lookup, all 4 issue codes with Bengali + English
- [ ] `test_eligibility.py` — minimum 10 test cases including Sulata's exact scenario (score = 42)
- [ ] **No UI, no AI, no API — just pure Python that is tested and works**

**PHASE 2 — API Layer (2 hrs)**
- [ ] `lambda_handler.py` — routes requests to correct channel handler
- [ ] `api.py` — REST handlers for all routes
- [ ] Routes: `POST /check-eligibility`, `GET /schemes`, `POST /profile`, `GET /recommendations`, `GET /script/{code}?lang=bn`
- [ ] Deploy to Lambda + API Gateway
- [ ] Test every route with curl — verify Sulata's scenario returns score 42

**PHASE 3 — Vector Search (2 hrs)**
- [ ] Embed all scheme descriptions → push to Pinecone
- [ ] `/recommendations?query=` endpoint working
- [ ] Rule-based cross-scheme logic confirmed (Kanyashree on `has_daughter: true`)

**⚠️ BEFORE SLEEPING: Record backup demo video** — full Sulata flow narrated. If Twilio dies, play this.

---

### DAY 2

**PHASE 4 — Voice + WhatsApp (4 hrs)**
- [ ] `sarvam_stt.py` — STT tested with real Bengali audio file
- [ ] `sarvam_tts.py` — TTS tested, generates Bengali .ogg
- [ ] Pre-generate + upload common response audio to S3 cache
- [ ] `whatsapp.py` — Twilio webhook, full conversation state machine
- [ ] Text path working end-to-end on WhatsApp first
- [ ] Voice note path working end-to-end
- [ ] Script Generator voice note fires correctly on NAME_MISMATCH
- [ ] `MOCK_MODE=true` working — web UI simulates WhatsApp conversation

**PHASE 5 — Web UI (3 hrs)**
- [ ] React (Vite) scaffolded, connected to real API Gateway
- [ ] Screens: Home, Profile, CheckFlow (step-by-step), Results
- [ ] Score meter: Antigravity animated circular progress reveal on results page
- [ ] Mismatch visual: side-by-side `Aadhaar: Sulata Mondal ❌ Bank: Sulata` in red
- [ ] Script card: "What to say at bank" card — Bengali + English text
- [ ] Cross-scheme card: Kanyashree auto-fires when `has_daughter: true`
- [ ] i18n: English + Bengali strings minimum

**PHASE 6 — Polish + Demo (2 hrs)**
- [ ] All API calls have error handling + graceful fallback
- [ ] Mobile responsive (480px, Chrome Android)
- [ ] Lambda warmed before demo (hit it once)
- [ ] Rehearse full demo 3 times out loud with impact numbers spoken aloud
- [ ] Prepare "how do you update rules?" answer rehearsed
- [ ] Mock mode tested as backup switch

---

## 13. FOLDER STRUCTURE

```
wb-digital-sahayak/
├── PROJECT.md                          ← THIS FILE — update Section 20 status as you build
│
├── backend/
│   ├── engine/
│   │   ├── eligibility.py              ← Core rules (pure Python, no AI)
│   │   ├── scoring.py                  ← Readiness score calculator
│   │   ├── mismatch.py                 ← rapidfuzz name/address checks
│   │   ├── scripts.json                ← issue_code → {where, form, bn, en}
│   │   └── schemes.json                ← All scheme rules as structured data
│   ├── ai/
│   │   ├── bedrock.py                  ← Bedrock Claude Haiku explanation generator
│   │   └── vector_search.py            ← Pinecone embedding + similarity search
│   ├── voice/
│   │   ├── sarvam_stt.py               ← Sarvam STT wrapper
│   │   ├── sarvam_tts.py               ← Sarvam TTS wrapper
│   │   └── cache/                      ← Pre-generated .ogg files
│   │       ├── name_mismatch_bn.ogg
│   │       ├── dormant_bn.ogg
│   │       └── score_42_bn.ogg
│   ├── channels/
│   │   ├── whatsapp.py                 ← Twilio webhook + conversation state machine
│   │   └── api.py                      ← REST handlers
│   ├── lambda_handler.py               ← Lambda entry point
│   ├── requirements.txt
│   └── tests/
│       ├── test_eligibility.py         ← 10+ unit tests including Sulata
│       ├── test_scoring.py
│       └── test_mismatch.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ScoreMeter.jsx          ← Antigravity animated score circle
│   │   │   ├── SchemeCard.jsx          ← Stitch design card
│   │   │   ├── IssueCard.jsx           ← Fatal/warning with mismatch side-by-side
│   │   │   ├── ScriptCard.jsx          ← "What to say" card ← NEW
│   │   │   └── RoadmapStep.jsx
│   │   ├── pages/
│   │   │   ├── Home.jsx
│   │   │   ├── Profile.jsx
│   │   │   ├── CheckFlow.jsx
│   │   │   └── Results.jsx
│   │   ├── i18n/
│   │   │   ├── en.json
│   │   │   ├── bn.json
│   │   │   └── hi.json
│   │   ├── api/client.js               ← All API Gateway calls here
│   │   └── App.jsx
│   └── vite.config.js
│
└── infra/
    ├── template.yaml                   ← AWS SAM
    └── .env.example
```

---

## 14. API CONTRACT

### POST /check-eligibility
```json
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
    "address_match_ok": false,
    "docs_present": ["aadhaar", "voter"], "docs_missing": ["bank", "ration"]
  }
}

Response:
{
  "score": 42, "band": "RED",
  "verdict": "Do not visit yet. Follow the roadmap.",
  "eligible_basic": true,
  "issues": [{
    "type": "fatal", "code": "NAME_MISMATCH",
    "message": "Name mismatch detected",
    "display": { "field_a": "Sulata Mondal", "label_a": "Aadhaar", "field_b": "Sulata", "label_b": "Bank" },
    "action": "Visit Bank or Post Office to correct name",
    "script_code": "NAME_MISMATCH",
    "script_audio_url": "https://s3.../cache/name_mismatch_bn.ogg"
  }],
  "warnings": [{ "type": "warning", "code": "ADDRESS_MISMATCH", "message": "...", "action": "..." }],
  "missing_docs": ["bank", "ration"],
  "roadmap": [
    { "step": 1, "where": "Bank / Post Office", "what": "Fix name mismatch", "urgent": true },
    { "step": 2, "where": "Bank Branch", "what": "Reactivate dormant account", "urgent": true },
    { "step": 3, "where": "BDO Office", "what": "Submit application", "urgent": false }
  ],
  "recommendations": [{
    "scheme_id": "kanyashree",
    "reason": "You have a daughter aged 10–19",
    "benefit": "₹25,000 at 18 + ₹1,000/year",
    "trigger": "has_daughter"
  }],
  "ai_explanation": "Sulata, আপনার নামে গরমিল আছে এবং account dormant। আগে bank-এ যান।"
}
```

### GET /script/{issue_code}?lang=bn
```json
{
  "issue_code": "NAME_MISMATCH",
  "where": "Bank Branch or Post Office",
  "form": "KYC Update Form",
  "script_bn": "Counter-e jaao, bolo: 'Amar Aadhaar-e naam Sulata Mondal...'",
  "script_en": "Go to the counter and say: 'My name on Aadhaar is Sulata Mondal...'",
  "audio_url": "https://s3.../cache/name_mismatch_bn.ogg"
}
```

### GET /schemes
```json
{ "schemes": [{ "id", "name", "name_bn", "benefit", "dept", "tag", "eligibility_summary" }] }
```

### POST /profile
```json
Request: { user profile object }
Response: { "profile_id": "uuid", "status": "saved" }
```

### GET /recommendations?query=scheme+for+sick+mother&profile_id=uuid
```json
{ "results": [{ "scheme_id", "score", "reason", "matched_by": "vector|rule" }] }
```

---

## 15. KEY DECISIONS — LOCKED (DO NOT REVISIT DURING HACKATHON)

| Decision | Rationale |
|---|---|
| **WhatsApp demo = Lakshmir Bhandar only** | Perfect one flow. Judges remember depth not breadth. |
| **Eligibility engine = pure Python, no LLM** | LLMs hallucinate rules. Wrong answer = user wastes a trip = mission failed. |
| **LLM (Bedrock) only for explanation text** | Safe use — explaining a deterministic result, not computing it. |
| **Sarvam AI for all voice** | Bengali dialect support. Google TTS sounds robotic in Bengali. |
| **WhatsApp primary, Web secondary** | WhatsApp penetration far higher than smartphone ownership in rural WB. |
| **Mock mode built before live Twilio** | Twilio WILL flake during the live demo. 30-second switch to mock is survival. |
| **Pre-cache TTS audio on S3** | Sarvam TTS latency will kill the demo moment. Pre-generate common responses. |
| **DynamoDB for session state** | Lambda is stateless. Multi-turn WhatsApp conversations need persistent state. |
| **No OCR in MVP** | 6-hour rabbit hole. Users type names from cards. Post-hackathon: Digilocker. |
| **Pinecone free tier** | Fastest setup, zero infra. Swap to pgvector post-hackathon. |

---

## 16. FEATURES EXPLICITLY CUT — DO NOT BUILD

| Feature | Why Cut | Phase |
|---|---|---|
| PDF "Eligibility Pass" | PDF gen + S3 + Twilio media = 6-hour rabbit hole for a feature judges glance at for 4 seconds | Phase 2 |
| Duare Sarkar live camp dates | Even mocked — judge from Cooch Behar asks for dates you don't have. Empty promise kills credibility. | Phase 2 with real API |
| Hyper-local slang STT fine-tuning | Cannot fine-tune Sarvam in 2 days. Would break the pipeline before demo. | Phase 3 |
| Digilocker auto-verification | Requires govt MoU. Not hackathon feasible. | Phase 2 |
| Admin dashboard for clerks | Answer verbally if asked. | Phase 2 |
| IVR / USSD feature phones | Phase 3 roadmap. | Phase 3 |
| Santali / Rajbanshi dialects | Phase 3 roadmap. | Phase 3 |
| Income Tax payer check via API | Self-report only in MVP. | Phase 2 |

---

## 17. ENVIRONMENT VARIABLES

```bash
# AWS
AWS_REGION=ap-south-1
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
DYNAMODB_TABLE_NAME=wb-sahayak-users
S3_BUCKET_NAME=wb-sahayak-schemes

# Amazon Bedrock
BEDROCK_MODEL_ID=anthropic.claude-haiku-20240307-v1:0
BEDROCK_KNOWLEDGE_BASE_ID=

# Sarvam AI
SARVAM_API_KEY=
SARVAM_STT_ENDPOINT=https://api.sarvam.ai/speech-to-text
SARVAM_TTS_ENDPOINT=https://api.sarvam.ai/text-to-speech

# Twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Pinecone
PINECONE_API_KEY=
PINECONE_INDEX_NAME=wb-sahayak-schemes
PINECONE_ENVIRONMENT=gcp-starter

# Feature Flags
MOCK_MODE=false       # true = bypass Twilio, simulate in web UI
CACHE_TTS=true        # true = serve pre-generated .ogg from S3
```

---

## 18. COST + IMPACT NUMBERS (Memorise for demo)

| Service | Cost/Month (10K users) |
|---|---|
| Amazon Bedrock (Claude Haiku) | $55 (₹4,600) |
| Sarvam AI API | $75 (₹6,300) |
| Twilio WhatsApp | $42 (₹3,500) |
| AWS Lambda + DynamoDB + S3 + CloudWatch | $17 (₹1,400) |
| Pinecone | $0 (free tier) |
| **TOTAL** | **~$189/month → ₹1.89/user/month** |

**Impact numbers to say out loud during demo:**
- ₹500 lost per failed trip (₹200 bus + ₹300 daily wage)
- ₹1,500 lost by Sulata across 3 failed visits
- ₹50 lakh saved per month at 10,000 users
- 2 minutes on WhatsApp vs 2 hours of travel

---

## 19. DEMO SCRIPT — REHEARSE 3 TIMES OUT LOUD

**Opening (30 sec):**
> "Meet Sulata. 38. Jalpaiguri. She went to the BDO office three times for Lakshmir Bhandar. Three rejections. No reason given. She lost ₹1,500 in bus fare and lost wages. The benefit she's trying to claim is ₹1,000 a month."

**Live demo (2 min):** *(see Section 11 for full WhatsApp flow)*
1. Voice note sent in Bengali — "Lakshmir Bhandar scheme"
2. Bot guides through age, govt status, Aadhaar name, bank name
3. NAME_MISMATCH fires — side-by-side red visual
4. Bot sends Bengali voice note: exact words to say at the bank
5. Dormant account fires
6. Score: **42/100 🔴** — animated meter fills up, turns red
7. Roadmap: Bank → Bank → BDO (in that order)
8. Kanyashree suggestion: "Your daughter can get ₹25,000"

**Impact statement:**
> "Without us: ₹500 wasted, 2 hours of travel, rejection #4. With us: 2 minutes on WhatsApp in Bengali. At 10,000 users: ₹50 lakh saved every month."

**"How do you keep rules updated?" answer:**
> "Scheme rules are JSON files in S3. A government clerk can update them through a simple interface — no redeployment. New Government Orders from Nabanna are piped directly into Amazon Bedrock Knowledge Bases. The explanation layer stays current automatically."

**Closing:**
> "We've built the engine. Next: Digilocker integration to auto-verify documents, and a pilot in Jalpaiguri with 50 real users next month. The only thing between Sulata and her ₹1,000 was information. We fixed that."

---

## 20. CURRENT BUILD STATUS — UPDATE THIS AS YOU BUILD

- [x] Phase 0 — Planning complete, PROJECT.md written + updated
- [ ] Phase 1 — Core engine (`eligibility.py`, `scoring.py`, `mismatch.py`, `scripts.json`, tests passing)
- [ ] Phase 2 — API layer (Lambda + API Gateway, all routes tested with curl)
- [ ] Phase 3 — Vector search (Pinecone loaded, `/recommendations` live, cross-scheme firing)
- [ ] Phase 4 — Voice + WhatsApp (full Sulata voice loop, mock mode ready to switch)
- [ ] Phase 5 — Web UI (connected to API, score animation, mismatch visual, script card)
- [ ] Phase 6 — Backup video recorded, demo rehearsed 3x, Lambda warmed

---

## 21. HOW TO USE THIS FILE WITH ANY LLM

Paste entire file at start of chat. Then say:

> *"Read this project context. I am building WB Digital Sahayak. I am on [PHASE X]. Help me build [SPECIFIC FILE]. Respect all locked decisions in Section 15. Use only tools in Section 6. Do not suggest anything in Section 16."*

**Rules for the LLM:**
- Eligibility engine = pure Python only. No LLM calls inside the engine. Ever.
- WhatsApp demo = Lakshmir Bhandar only. Don't add other schemes to the bot.
- Voice = Sarvam AI only. Not Google, not ElevenLabs, not Azure.
- If you want to suggest a new feature — check Section 16 first.
- Update Section 20 checkboxes every time a phase is complete.

---

*Last updated: Post feature-review. Added: Script Generator (Sec 10), finalised WhatsApp flow (Sec 11), updated build order (Sec 12), added cuts list (Sec 16), updated demo script with impact numbers (Sec 19).*