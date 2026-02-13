# Requirements Document: WB Digital Sahayak

## Introduction

WB Digital Sahayak is a voice-first AI-powered welfare eligibility and readiness verification system designed for citizens of West Bengal. The system helps citizens verify their eligibility for government welfare schemes and calculate their document readiness score BEFORE visiting government offices. This informational system combines deterministic rule-based eligibility checking with AI-powered explanations in Bengali, ensuring transparency and accessibility for users with low digital literacy.

**MVP Scope (Hackathon):** The system focuses on **Lakshmir Bhandar** (women's income support scheme) as the primary use case. The architecture is designed for multi-scheme extensibility, with plans to add Swasthya Sathi, Ration Entitlements, and Yuva Sathi in post-hackathon phases.

## Glossary

- **System**: The WB Digital Sahayak platform
- **Rule_Engine**: The deterministic component that evaluates eligibility based on hard-coded criteria
- **Readiness_Score_Engine**: The component that calculates document completeness percentage (0-100%)
- **AI_Explanation_Layer**: Amazon Bedrock (Claude Haiku) component that generates simple Bengali explanations
- **RAG_Layer**: Retrieval-Augmented Generation system using FAISS vector store with official scheme PDFs
- **Voice_Interface**: Sarvam AI integration for Speech-to-Text and Text-to-Speech (with fallback to text-only)
- **User**: A citizen of West Bengal seeking welfare scheme information
- **Scheme**: A government welfare program (MVP: Lakshmir Bhandar only)
- **Eligibility_Criteria**: Hard-coded rules including age, income, gender, marital status, and residency requirements
- **Readiness_Score**: A percentage (0-100%) indicating document completeness for scheme application
- **Renewal_Window**: The time period before a scheme benefit expires when renewal reminders are sent (30 days)
- **Context_Only_Prompt**: A RAG safety strategy that restricts AI responses to retrieved document content only
- **Fallback_Mode**: System behavior when external services (voice, AI) are unavailable

## Requirements

### Requirement 1: Eligibility Verification (Core Functionality)

**User Story:** As a citizen, I want to check if I am eligible for Lakshmir Bhandar, so that I know whether to proceed with the application process.

#### Acceptance Criteria

1. WHEN a User provides demographic information (age, gender, income, marital status, residency), THE Rule_Engine SHALL evaluate eligibility against hard-coded criteria for Lakshmir Bhandar
2. THE Rule_Engine SHALL return a binary eligibility result (eligible or not eligible) within 2 seconds
3. THE System SHALL NOT use AI to make the eligibility decision (AI only explains, never decides)
4. THE Rule_Engine SHALL validate that age is between 18-60, income is non-negative, gender is "female", marital status is "married" or "widowed", and residency is "west_bengal"
5. WHEN a User is ineligible, THE System SHALL identify which specific Eligibility_Criteria were not met
6. THE Rule_Engine SHALL use hard-coded Python functions for MVP (not configuration files)

**Rationale:** Hard-coded rules ensure accuracy, auditability, and faster implementation for hackathon timeline. Configuration-driven approach is documented for post-MVP extensibility.

---

### Requirement 2: Document Readiness Calculation

**User Story:** As a citizen, I want to know what percentage of required documents I have ready, so that I can prepare missing documents before visiting the office.

#### Acceptance Criteria

1. WHEN a User indicates which documents they possess, THE Readiness_Score_Engine SHALL calculate a percentage score from 0 to 100
2. THE Readiness_Score_Engine SHALL use the following weights for Lakshmir Bhandar:
   - Aadhaar Card: 30%
   - Bank Account Passbook: 25%
   - Income Certificate: 20%
   - Ration Card: 15%
   - Residence Proof: 10%
3. WHEN the readiness calculation is complete, THE System SHALL return the score within 1 second
4. THE Readiness_Score_Engine SHALL identify which specific documents are missing with their weights
5. WHEN all required documents are present, THE Readiness_Score_Engine SHALL return exactly 100%
6. THE System SHALL clearly indicate which documents are mandatory vs. optional

---

### Requirement 3: AI-Powered Explanations

**User Story:** As a citizen with low digital literacy, I want to receive explanations in simple Bengali, so that I can understand my eligibility status and next steps.

#### Acceptance Criteria

1. WHEN eligibility results are generated, THE AI_Explanation_Layer SHALL produce a simple Bengali explanation using Amazon Bedrock (Claude Haiku)
2. THE AI_Explanation_Layer SHALL explain why a User is eligible or ineligible in language appropriate for low-literacy users (5th-grade reading level)
3. WHEN generating explanations, THE AI_Explanation_Layer SHALL complete within 4 seconds (increased from 3 to account for variability)
4. THE AI_Explanation_Layer SHALL provide actionable next steps based on the User's readiness score
5. THE AI_Explanation_Layer SHALL NOT contradict the Rule_Engine's eligibility determination
6. WHEN Bedrock is unavailable, THE System SHALL use pre-written template explanations (Fallback Mode)
7. THE AI_Explanation_Layer SHALL use temperature 0.3 and max tokens 300 for consistency

---

### Requirement 4: RAG-Based Scheme Information Retrieval

**User Story:** As a citizen, I want to ask questions about Lakshmir Bhandar scheme, so that I can understand program details and requirements.

#### Acceptance Criteria

1. WHEN a User asks a question about Lakshmir Bhandar, THE RAG_Layer SHALL retrieve relevant content from the official scheme PDF stored in S3
2. THE RAG_Layer SHALL use FAISS vector store with 1000-token chunks and 100-token overlap for better context preservation
3. WHEN generating responses, THE RAG_Layer SHALL use Context_Only_Prompt strategy to prevent hallucination
4. THE RAG_Layer SHALL return top-3 most relevant chunks (not 5, to stay concise)
5. THE RAG_Layer SHALL return responses within 4 seconds
6. WHEN no relevant information is found in the documents, THE RAG_Layer SHALL explicitly state "এই তথ্য আমার কাছে নেই" (I don't have this information) rather than generating speculative content
7. THE RAG_Layer SHALL cite source page numbers in responses for transparency

---

### Requirement 5: Voice Interface Integration (with Fallback)

**User Story:** As a citizen who prefers voice interaction, I want to speak my queries and hear responses, so that I can use the system without typing.

#### Acceptance Criteria

1. WHEN a User speaks in Bengali, THE Voice_Interface SHALL convert speech to text using Sarvam AI STT
2. THE Voice_Interface SHALL achieve speech-to-text accuracy of at least 80% for Bengali language (realistic target)
3. WHEN the System generates a response, THE Voice_Interface SHALL convert text to speech in Bengali using Sarvam AI TTS
4. THE Voice_Interface SHALL complete speech-to-text conversion within 3 seconds
5. THE Voice_Interface SHALL complete text-to-speech conversion within 3 seconds
6. **WHEN Sarvam AI is unavailable or slow (timeout >3 seconds), THE System SHALL offer text-based input/output (Fallback Mode)**
7. THE System SHALL display a clear message in Bengali when falling back to text mode: "ভয়েস সেবা বর্তমানে উপলব্ধ নেই। দয়া করে টাইপ করুন।" (Voice service currently unavailable. Please type.)
8. THE System SHALL log voice failures to CloudWatch for monitoring
9. THE System SHALL maintain 95%+ availability even during voice service outages (via text fallback)

**Fallback Strategy:**
- Primary: Sarvam AI (Bengali STT/TTS)
- Fallback: Text-only interface (always available)
- Detection: 3-second timeout or HTTP 5xx errors
- User notification: Automatic switch with clear Bengali message

---

### Requirement 6: User Session Management

**User Story:** As a citizen, I want my eligibility checks to be saved, so that I can track my progress over time.

#### Acceptance Criteria

1. WHEN a User accesses the system for the first time, THE System SHALL generate a UUID and store it in browser localStorage (web) or device storage (mobile)
2. WHEN a User completes an eligibility check, THE System SHALL store user_id, scheme, readiness_score, timestamp, and renewal_date in DynamoDB
3. THE System SHALL NOT store Aadhaar numbers, identity documents, or other sensitive personal information
4. WHEN storing user data, THE System SHALL complete the operation within 1 second
5. WHEN a User returns, THE System SHALL automatically retrieve their UUID and display previous checks
6. WHEN UUID is lost (e.g., browser cache cleared), THE System SHALL treat User as new and generate a fresh UUID
7. **THE System SHALL set DynamoDB TTL to 90 days (not 2 years) to minimize storage costs and respect privacy**

**MVP Limitation:** No login or authentication required. Post-MVP will add phone number OTP authentication for cross-device access.

---

### Requirement 7: Renewal Reminder System

**User Story:** As a beneficiary, I want to receive reminders when my scheme benefits are due for renewal, so that I don't miss renewal deadlines.

#### Acceptance Criteria

1. WHEN a renewal_date is within 30 days, THE System SHALL send a notification to the User
2. THE System SHALL run a scheduled Lambda job daily at 9:00 AM IST to check for upcoming renewals
3. WHEN checking renewals, THE System SHALL query DynamoDB for all records within the 30-day Renewal_Window
4. THE System SHALL send a maximum of 3 notifications per user per renewal cycle (at 30 days, 15 days, and 7 days before expiry)
5. THE System SHALL check the renewal_notifications table to prevent duplicate notifications
6. WHEN sending notifications, THE System SHALL include the scheme name, renewal deadline, and required documents checklist
7. THE System SHALL support SMS notifications via Amazon SNS as the primary channel
8. WHEN a notification is sent, THE System SHALL record notification_sent_date and increment notification_count in the renewal_notifications table

**Notification Deduplication:**
- DynamoDB table: renewal_notifications (Partition Key: user_id + scheme)
- Attributes: notification_sent_date, renewal_date, notification_count (max 3)
- Logic: Only send if not already sent for this renewal_date OR last notification was >7 days ago

---

### Requirement 8: API Gateway and Request Routing

**User Story:** As a system integrator, I want a well-defined API, so that I can integrate the system with various client applications.

#### Acceptance Criteria

1. THE System SHALL expose REST API endpoints through AWS API Gateway
2. WHEN a request is received, THE API_Gateway SHALL route it to the appropriate Lambda function within 100 milliseconds
3. THE API_Gateway SHALL validate request payloads using JSON Schema before forwarding to Lambda functions
4. THE API_Gateway SHALL return appropriate HTTP status codes (200 for success, 400 for bad request, 500 for server error)
5. THE API_Gateway SHALL implement rate limiting: 100 requests per minute per IP, 1000 requests per hour per user_id
6. THE API_Gateway SHALL enable CORS for frontend domains
7. THE System SHALL expose the following endpoints:
   - POST /eligibility/check (eligibility + readiness calculation)
   - POST /schemes/query (RAG-based Q&A)
   - GET /user/{user_id}/history (previous checks)
   - POST /voice/stt (speech-to-text)
   - POST /voice/tts (text-to-speech)

---

### Requirement 9: Logging and Monitoring

**User Story:** As a system administrator, I want comprehensive logging and monitoring, so that I can troubleshoot issues and track system performance.

#### Acceptance Criteria

1. WHEN any Lambda function executes, THE System SHALL log execution details to CloudWatch
2. THE System SHALL log all eligibility checks with timestamp, user_id, scheme, eligibility result, and readiness score
3. WHEN errors occur, THE System SHALL log error details including stack traces, user_id, and request payload (sanitized) to CloudWatch
4. THE System SHALL track API response times and log requests exceeding 5 seconds as warnings
5. THE System SHALL create CloudWatch alarms for:
   - Lambda function errors exceeding 5% error rate
   - API Gateway 5xx responses exceeding 10 per minute
   - DynamoDB throttling events
   - Bedrock timeouts exceeding 3 per minute
6. THE System SHALL create a CloudWatch dashboard showing:
   - Requests per minute
   - Average response time
   - Error rate
   - Voice service availability
   - Cost tracking (Lambda invocations, Bedrock tokens)

---

### Requirement 10: Security and Data Privacy

**User Story:** As a citizen, I want my personal information to be secure, so that my privacy is protected.

#### Acceptance Criteria

1. THE System SHALL encrypt all data in transit using TLS 1.2 or higher
2. THE System SHALL encrypt all data at rest in DynamoDB using AWS managed encryption (AES-256)
3. THE System SHALL NOT store Aadhaar numbers, scanned identity documents, or bank account numbers
4. WHEN accessing S3 buckets, THE System SHALL use IAM roles with least-privilege permissions
5. THE System SHALL implement input validation to prevent SQL injection, XSS, and command injection attacks
6. THE System SHALL sanitize all user inputs before logging to prevent log injection
7. THE System SHALL use AWS Secrets Manager for storing Sarvam AI API keys (not hardcoded)
8. THE System SHALL implement API key rotation every 90 days
9. THE System SHALL mask sensitive data in CloudWatch logs (e.g., partial user_id display only)

---

### Requirement 11: Multi-Scheme Extensibility (Post-MVP)

**User Story:** As a system administrator, I want to add new schemes easily, so that I can expand the system without major refactoring.

#### Acceptance Criteria

1. THE System architecture SHALL support adding new schemes by creating new rule files in the `rules/` directory
2. WHEN a new scheme is added, THE System SHALL require only:
   - A new Python file with eligibility function (e.g., `rules/swasthya_sathi.py`)
   - A new document weight configuration
   - A new PDF uploaded to S3
3. THE System SHALL use a scheme registry that maps scheme names to rule functions
4. THE System SHALL NOT require code changes to the core Rule_Engine or Readiness_Score_Engine
5. **THE MVP SHALL demonstrate extensibility by documenting the process for adding Swasthya Sathi (without actually implementing it)**

**MVP Note:** Only Lakshmir Bhandar is fully implemented. Architecture proves multi-scheme scalability.

---

### Requirement 12: Error Handling and Graceful Degradation

**User Story:** As a citizen, I want the system to handle errors gracefully, so that I receive helpful feedback when something goes wrong.

#### Acceptance Criteria

1. WHEN the AI_Explanation_Layer fails or times out (>4 seconds), THE System SHALL return eligibility results with a pre-written template explanation in Bengali
2. WHEN the RAG_Layer fails, THE System SHALL inform the User: "প্রকল্প তথ্য বর্তমানে উপলব্ধ নেই। দয়া করে পরে আবার চেষ্টা করুন।" (Scheme information currently unavailable. Please try again later.)
3. WHEN DynamoDB is unavailable, THE System SHALL complete eligibility checks but inform the User that results cannot be saved
4. THE System SHALL return user-friendly error messages in Bengali, not technical error codes
5. WHEN external services timeout, THE System SHALL fail gracefully within 10 seconds maximum
6. THE System SHALL implement circuit breaker pattern: If Bedrock fails 3 times in 1 minute, use template explanations for 5 minutes
7. THE System SHALL log all fallback events to CloudWatch for monitoring and debugging

**Error Budget:**
- Rule Engine: 2 seconds (hard timeout, should never fail)
- Readiness Score: 1 second (hard timeout)
- FAISS Search: 3 seconds → Fallback: Generic scheme info
- Bedrock Explanation: 4 seconds → Fallback: Template explanation
- Sarvam STT: 3 seconds → Fallback: Text input
- Sarvam TTS: 3 seconds → Fallback: Text output
- Total user-facing timeout: 10 seconds absolute maximum

---

### Requirement 13: Performance and Scalability

**User Story:** As a system administrator, I want the system to handle high traffic volumes, so that all citizens can access the service during peak times.

#### Acceptance Criteria

1. THE System SHALL handle at least 100 concurrent requests without degradation
2. WHEN traffic increases, THE System SHALL auto-scale Lambda functions to meet demand (up to 1000 concurrent executions)
3. THE System SHALL maintain response times under 5 seconds for 95% of requests (p95 latency)
4. THE System SHALL use DynamoDB on-demand capacity to handle variable workloads
5. WHEN Lambda functions are cold-started, THE System SHALL complete initialization within 3 seconds
6. THE System SHALL cache FAISS index in Lambda /tmp storage to reduce load times on warm starts
7. THE System SHALL implement request batching for renewal checks (process 100 users per Lambda invocation, not 1)

---

### Requirement 14: Deployment and Infrastructure

**User Story:** As a DevOps engineer, I want infrastructure-as-code deployment, so that I can deploy and manage the system consistently.

#### Acceptance Criteria

1. THE System SHALL be deployable using AWS SAM (Serverless Application Model) templates
2. WHEN deploying, THE System SHALL create all required AWS resources:
   - API Gateway (REST API with 5 endpoints)
   - Lambda Functions (3 functions: eligibility, RAG query, renewal reminder)
   - DynamoDB Tables (eligibility_checks, renewal_notifications)
   - S3 Bucket (scheme PDFs and FAISS index)
   - CloudWatch Log Groups and Alarms
   - IAM Roles (with least-privilege permissions)
3. THE System SHALL support deployment to development and production environments using environment variables
4. THE System SHALL use environment variables for:
   - Sarvam AI API key
   - Bedrock model ID
   - DynamoDB table names
   - S3 bucket names
5. WHEN infrastructure changes are made, THE System SHALL support rollback to previous SAM template versions
6. THE System SHALL include a deployment script (`deploy.sh`) that validates environment, runs tests, and deploys to AWS

---

### Requirement 15: Testing and Validation

**User Story:** As a developer, I want automated tests, so that I can verify system correctness before deployment.

#### Acceptance Criteria

1. THE Rule Engine SHALL have unit tests covering all eligibility combinations:
   - All criteria passed → eligible
   - Age too low/high → not eligible
   - Wrong gender → not eligible
   - Income too high → not eligible
   - Wrong marital status → not eligible
   - Wrong residency → not eligible
   - Multiple criteria failed → not eligible
2. THE Readiness Score Engine SHALL have tests for:
   - All documents present → 100%
   - No documents → 0%
   - Only mandatory documents → calculated percentage
   - Various document combinations
3. THE RAG Layer SHALL be validated against 20 ground-truth Q&A pairs extracted from Lakshmir Bhandar PDF:
   - "What is the income limit?" → ₹1.5 lakh per year
   - "What documents are needed?" → List of 5 documents
   - "Who is eligible?" → Married/widowed women aged 18-60
   - And 17 more test questions
4. THE System SHALL have integration tests for the complete eligibility check flow:
   - User input → Eligibility result → Readiness score → AI explanation → DynamoDB storage
5. THE Bengali explanations SHALL be reviewed by at least 2 native Bengali speakers for linguistic accuracy
6. THE System SHALL achieve:
   - Rule Engine: 100% code coverage (critical path)
   - Readiness Score: 100% code coverage (deterministic)
   - Lambda functions: 80%+ code coverage
   - RAG accuracy: 85%+ (measured against ground truth Q&A)
7. THE System SHALL include a test suite that runs in GitHub Actions on every commit

**Test Files:**
- `tests/test_eligibility.py` (Rule Engine unit tests)
- `tests/test_readiness.py` (Readiness Score unit tests)
- `tests/test_rag.py` (RAG accuracy validation)
- `tests/test_integration.py` (End-to-end flow tests)
- `tests/ground_truth_qa.json` (20 validation Q&A pairs)

---

### Requirement 16: Cost Monitoring and Optimization

**User Story:** As a project manager, I want to track AWS costs, so that I can ensure the system remains financially sustainable.

#### Acceptance Criteria

1. THE System SHALL track costs per user using CloudWatch custom metrics
2. THE System SHALL set up AWS Cost Explorer alerts when monthly costs exceed ₹5,000 (₹0.50/user at 10K users)
3. THE System SHALL log the following cost-relevant metrics:
   - Lambda invocations per user
   - Bedrock tokens consumed per request
   - DynamoDB read/write capacity units
   - S3 API calls
4. THE System SHALL include a cost calculator spreadsheet (`docs/cost_analysis.xlsx`) showing:
   - Per-service costs at 1K, 10K, 100K users
   - Cost per user per month
   - Projected yearly costs
5. THE System SHALL optimize costs by:
   - Using Claude Haiku (not Sonnet) for explanations
   - Using DynamoDB on-demand (not provisioned)
   - Caching FAISS index to reduce S3 GET requests
   - Using Lambda ARM64 architecture (20% cheaper)

**Target Cost:** ₹0.50-1.00 per user per month at 10K users (excluding Sarvam AI, pending pricing confirmation)

---

## Non-Functional Requirements

### Performance
- API response time: p95 under 5 seconds, p50 under 3 seconds
- Rule Engine evaluation: under 2 seconds
- Readiness Score calculation: under 1 second
- AI explanation generation: under 4 seconds (with 4s timeout → fallback)
- RAG query response: under 4 seconds
- Voice conversion (STT/TTS): under 3 seconds each (with fallback to text)
- Cold start: under 3 seconds for Lambda initialization

### Security
- TLS 1.2+ for all data in transit
- AWS managed encryption (AES-256) for data at rest
- No storage of Aadhaar, scanned documents, or bank account numbers
- IAM least-privilege access controls (separate roles per Lambda)
- Input validation on all user inputs (regex, type checking, length limits)
- Rate limiting: 100 requests/min per IP, 1000 requests/hour per user_id
- API key rotation every 90 days
- Secrets stored in AWS Secrets Manager, not environment variables

### Usability
- Voice-first interface with text fallback for accessibility
- Simple Bengali language explanations (5th-grade reading level)
- Clear indication of missing documents with weights
- Actionable next steps in all responses
- Error messages in Bengali, not technical jargon
- Visual readiness score indicator (progress bar or percentage)

### Reliability
- 95% uptime target (99.5% too ambitious for MVP)
- Graceful degradation when external services fail (voice, AI)
- Automatic retry for transient failures (with exponential backoff)
- CloudWatch monitoring and alerting on all critical paths
- Lambda function error rate target: under 5%
- Circuit breaker on Bedrock failures (3 failures in 1 min → template mode for 5 min)

### Scalability
- Serverless architecture for automatic scaling (0 to 1000 concurrent users)
- Support for 100+ concurrent users without manual intervention
- DynamoDB on-demand capacity (scales automatically)
- S3 for document storage (unlimited scalability)
- FAISS vector store optimization (index size <100MB for fast loading)
- Lambda concurrency limit: 1000 (request increase if needed)

### Maintainability
- Infrastructure as Code (AWS SAM templates)
- Comprehensive CloudWatch logging
- Code comments in English (for international collaboration)
- README with architecture diagrams and setup instructions
- Automated tests with >80% coverage
- Environment-specific configurations (dev, prod)

---

## System Constraints

1. **MVP Scope**: Single scheme (Lakshmir Bhandar) only. Post-MVP: Swasthya Sathi, Ration, Yuva Sathi
2. **Informational Only**: System provides guidance only, not official eligibility determination
3. **No Government Integration**: No direct access to official government databases or e-District portal
4. **No OCR in MVP**: Document validation through user self-reporting only (no Textract)
5. **AWS Serverless Only**: Must use Lambda, API Gateway, DynamoDB, S3 (no EC2, ECS, or containers)
6. **No Sensitive Data Storage**: Cannot store Aadhaar numbers, scanned documents, bank account numbers
7. **Primary Language**: Bengali for voice and explanations, English for technical documentation
8. **Context-Only RAG**: AI responses must be strictly based on retrieved PDF content (no external knowledge)
9. **No User Authentication**: UUID-based identification only (no login/password for MVP)
10. **7-Day Build Timeline**: All features must be implementable within hackathon timeframe
11. **Sarvam AI Dependency**: Voice interface depends on third-party service (fallback to text if unavailable)

---

## Assumptions

1. Users have access to a device with internet connectivity (mobile or web browser)
2. Users consent to storing non-sensitive session data (UUID, eligibility results)
3. Official Lakshmir Bhandar PDF is available, up-to-date, and legally distributable
4. Sarvam AI service has 95%+ uptime and <3 second latency for Bengali
5. Amazon Bedrock (Claude Haiku) is available in us-east-1 region
6. Users can self-report document possession accurately (no fraud prevention in MVP)
7. Eligibility criteria for Lakshmir Bhandar remain stable during hackathon (no mid-hackathon policy changes)
8. Network latency for Indian users is <500ms to AWS us-east-1
9. Bengali text rendering works correctly on all target devices
10. AWS Free Tier credits or hackathon credits are available for deployment

---

## Success Metrics

1. **User Adoption**: 100+ unique users during hackathon demo period (realistic for MVP)
2. **Accuracy**: 95%+ accuracy in eligibility determination (validated against 50 manual test cases)
3. **User Satisfaction**: 80%+ positive feedback on usability (from 20 beta testers)
4. **Performance**: 95% of requests complete within 5 seconds (p95 latency)
5. **Availability**: 95% uptime during demo period (48-hour demo window)
6. **Voice Accuracy**: 80%+ speech-to-text accuracy for Bengali (measured on 50 sample phrases)
7. **RAG Accuracy**: 85%+ correct answers on ground-truth Q&A (20 test questions)
8. **Error Rate**: Less than 5% Lambda function error rate
9. **Cost Efficiency**: Under ₹1.00 per user per month in AWS costs (at 10K user scale)
10. **Demo Success**: Complete end-to-end demo working without failures during judging

**Hackathon-Specific Metrics:**
- Working demo video (3 minutes, clear audio/video)
- GitHub repo with >80% code coverage
- Live deployment accessible via public URL
- 10+ user interviews documented
- Positive judge feedback on innovation and impact

---

## Out of Scope (Post-MVP Features)

The following features are explicitly OUT of scope for the hackathon MVP but documented for future phases:

1. **Multi-scheme support** (Swasthya Sathi, Ration, Yuva Sathi)
2. **Phone number OTP authentication** (cross-device session sync)
3. **OCR document validation** (Textract + Bedrock for Aadhaar verification)
4. **WhatsApp integration** (Twilio Business API)
5. **SMS/Email notifications** (Amazon SNS/SES for renewal reminders)
6. **Multi-language support** (Hindi, Odia in addition to Bengali)
7. **Government API integration** (e-District portal for real-time verification)
8. **Advanced analytics dashboard** (user demographics, popular schemes, dropout points)
9. **Scheme comparison feature** (compare eligibility across multiple schemes)
10. **Mobile app** (React Native iOS/Android apps)
11. **Configuration-driven rule engine** (JSON-based criteria management)
12. **Admin panel** (update scheme rules without code deployment)

These features are documented in the design for architectural extensibility but will not be implemented during the hackathon.

---

## Appendix A: Test Cases for Rule Engine

**Lakshmir Bhandar Eligibility Test Cases (20 scenarios):**

1. ✅ **All criteria met**: age=30, gender=female, income=100000, marital_status=married, residency=west_bengal → **Eligible**
2. ❌ **Age too low**: age=17 → **Not Eligible** (failed: age_check)
3. ❌ **Age too high**: age=61 → **Not Eligible** (failed: age_check)
4. ❌ **Wrong gender**: gender=male → **Not Eligible** (failed: gender_check)
5. ❌ **Income too high**: income=200000 → **Not Eligible** (failed: income_check)
6. ❌ **Wrong marital status**: marital_status=unmarried → **Not Eligible** (failed: marital_check)
7. ❌ **Wrong residency**: residency=bihar → **Not Eligible** (failed: residency_check)
8. ✅ **Widowed status**: marital_status=widowed → **Eligible** (widowed counts as eligible)
9. ❌ **Multiple failures**: age=17, gender=male → **Not Eligible** (failed: age_check, gender_check)
10. ✅ **Boundary case - minimum age**: age=18 → **Eligible**
11. ✅ **Boundary case - maximum age**: age=60 → **Eligible**
12. ✅ **Boundary case - maximum income**: income=120000 → **Eligible**
13. ❌ **Income just over limit**: income=120001 → **Not Eligible** (failed: income_check)
14. ❌ **Invalid age (negative)**: age=-5 → **Validation Error**
15. ❌ **Invalid age (string)**: age="thirty" → **Validation Error**
16. ❌ **Invalid income (negative)**: income=-10000 → **Validation Error**
17. ❌ **Missing required field**: gender=null → **Validation Error**
18. ✅ **Case insensitive gender**: gender="Female" → **Eligible** (normalized to lowercase)
19. ✅ **Case insensitive residency**: residency="West_Bengal" → **Eligible** (normalized)
20. ❌ **Empty marital status**: marital_status="" → **Not Eligible** (failed: marital_check)

---

## Appendix B: Ground Truth Q&A for RAG Validation

**20 test questions extracted from Lakshmir Bhandar official PDF:**

1. Q: "What is Lakshmir Bhandar?" → A: "A financial assistance scheme for women in West Bengal providing ₹500-1000/month"
2. Q: "What is the income limit?" → A: "Annual family income must be below ₹1.5 lakh"
3. Q: "What documents are needed?" → A: "Aadhaar card, bank passbook, income certificate, ration card, residence proof"
4. Q: "Who is eligible?" → A: "Married or widowed women aged 18-60 residing in West Bengal"
5. Q: "What is the benefit amount?" → A: "₹500/month for general category, ₹1000/month for SC/ST"
6. Q: "How to apply?" → A: "Visit nearest block office with required documents"
7. Q: "Is Aadhaar mandatory?" → A: "Yes, Aadhaar card is mandatory and must be linked to bank account"
8. Q: "Can unmarried women apply?" → A: "No, only married or widowed women are eligible"
9. Q: "What is the age limit?" → A: "Between 18 and 60 years"
10. Q: "Is bank account required?" → A: "Yes, benefits are transferred directly to bank account"
11. Q: "What is the renewal period?" → A: "Annual renewal required"
12. Q: "What happens if documents are incomplete?" → A: "Application will be rejected, resubmission needed"
13. Q: "Can divorced women apply?" → A: "PDF does not specify, assume no (only married/widowed mentioned)"
14. Q: "What if I don't have ration card?" → A: "Ration card is helpful but check if alternative residence proof works"
15. Q: "How long does processing take?" → A: "PDF does not specify processing time" → **Fallback: Information not available**
16. Q: "Can I apply online?" → A: "PDF mentions block office visit, online portal not specified" → **Fallback: Information not available**
17. Q: "What is income certificate validity?" → A: "PDF does not specify" → **Fallback: Information not available**
18. Q: "Can I get benefit if husband is employed?" → A: "Depends on total family income being below ₹1.5 lakh"
19. Q: "What is the scheme start date?" → A: "PDF does not specify" → **Fallback: Information not available**
20. Q: "How is benefit paid?" → A: "Direct bank transfer (DBT) to linked bank account"

**Validation Criteria:**
- 17/20 questions should be answered correctly from PDF content
- 3/20 questions should correctly trigger "information not available" fallback
- No hallucinated answers (making up information not in PDF)

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-13 | Development Team | Initial draft with 4 schemes |
| 2.0 | 2026-02-13 | Development Team | **MVP scope reduction to 1 scheme, added testing requirements, voice fallback strategy, error budgets, cost monitoring, realistic success metrics** |

**Key Changes in v2.0:**
- Reduced scope from 4 schemes to 1 (Lakshmir Bhandar only)
- Added Requirement 15 (Testing and Validation)
- Added Requirement 16 (Cost Monitoring)
- Enhanced Requirement 5 (Voice fallback strategy)
- Enhanced Requirement 12 (Error budgets and timeouts)
- Added Appendix A (20 test cases for Rule Engine)
- Added Appendix B (20 ground truth Q&A for RAG validation)
- Changed DynamoDB TTL from 2 years to 90 days
- Changed RAG chunk size from 512 to 1000 tokens
- Specified hard-coded rules for MVP (not config-driven)
- Added out-of-scope features list
- Realistic success metrics for hackathon (100 users, not 10K)