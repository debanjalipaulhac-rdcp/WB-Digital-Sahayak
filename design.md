# Design Document: WB Digital Sahayak

---

## 1. Executive Summary

WB Digital Sahayak is a voice-first, serverless welfare eligibility and readiness verification system for citizens of West Bengal.

The system enables citizens to:

* Verify eligibility for Lakshmir Bhandar
* Calculate a document Readiness Score (0–100%)
* Understand missing documents BEFORE visiting government offices
* Receive simple Bengali explanations

This is an informational system only. It does NOT make official eligibility determinations and does NOT integrate with government databases.

MVP Scope (Hackathon):

* Single Scheme: Lakshmir Bhandar
* Voice + Text interface
* Deterministic eligibility
* Readiness score
* RAG-based scheme Q&A
* AI explanation layer
* Graceful degradation

---

## 2. Problem Alignment

Problem:

* 40%+ welfare applications fail due to incomplete documentation
* Citizens lack clarity before visiting block offices
* Low digital literacy restricts portal usage
* Multiple failed visits increase travel cost and drop-off rate

Core Gap:
There is no accessible, voice-first verification system that checks readiness BEFORE office visits.

Solution Strategy:

* Deterministic eligibility (no hallucination)
* Quantified readiness score
* Bengali AI explanations
* Official-PDF-backed RAG responses

---

## 3. Architecture Overview

Architecture Style:
Serverless + Hybrid AI + Deterministic Core

Layers:

Interface Layer

* Web UI (Voice + Text)
* Sarvam AI (STT / TTS)

Application Layer

* AWS API Gateway
* AWS Lambda (Eligibility + RAG + Renewal)

Intelligence Layer

* Deterministic Rule Engine (Python)
* Readiness Score Engine
* Amazon Bedrock (Claude Haiku)
* Titan Embeddings
* FAISS Vector Store

Data Layer

* Amazon DynamoDB (90-day TTL)
* Amazon S3 (PDF + FAISS index)

Monitoring Layer

* CloudWatch Logs
* CloudWatch Metrics
* CloudWatch Alarms

Infrastructure as Code

* AWS SAM Template

---

## 4. Core Components

### 4.1 Rule Engine (Deterministic)

Hard-coded Python logic for Lakshmir Bhandar.

Criteria:

* Gender: Female
* Age: 18–60
* Annual Income: ≤ ₹1,20,000
* Marital Status: Married or Widowed
* Residency: West Bengal

AI is NOT used for eligibility decisions.

Output:

* eligible (boolean)
* passed_criteria
* failed_criteria

Design Goal:
Auditability + Zero hallucination.

---

### 4.2 Readiness Score Engine

Weighted document scoring model.

Weights:

* Aadhaar Card: 30%
* Bank Passbook: 25%
* Income Certificate: 20%
* Ration Card: 15%
* Residence Proof: 10%

Formula:
(sum of possessed document weights / total weight) × 100

Outputs:

* readiness_score
* missing_documents
* possessed_documents

Purpose:
Convert vague eligibility into actionable preparation.

---

### 4.3 AI Explanation Layer (Amazon Bedrock)

Model: Claude Haiku
Temperature: 0.3
Max Tokens: 300

Responsibilities:

* Explain eligibility result
* Explain readiness score meaning
* Provide next steps

Constraints:

* Cannot override rule engine
* Must remain consistent with deterministic result
* 4-second timeout

Fallback:
Template-based Bengali explanation

Circuit Breaker:

* 3 failures in 60 seconds → Template mode for 5 minutes

---

### 4.4 RAG Layer

Purpose:
Answer Lakshmir Bhandar questions strictly from official PDF.

Pipeline:

* PDF stored in S3
* 1000-token chunking (100 overlap)
* Titan embeddings
* FAISS index
* Cached in Lambda /tmp
* Top-3 similarity retrieval

Prompt Safety:

* Context-only
* Explicit fallback phrase: "এই তথ্য আমার কাছে নেই"
* Temperature: 0.1

Outputs:

* answer_bengali
* source page reference
* confidence_score

---

### 4.5 Voice Interface

Primary:

* Sarvam AI STT (≤3s)
* Sarvam AI TTS (≤3s)

Fallback Mode:

* Automatic switch to text
* Bengali message displayed

Goal:
Maintain 95% availability even if voice fails.

---

## 5. Data Architecture

### DynamoDB: eligibility_checks

Partition Key: user_id
Sort Key: timestamp
TTL: 90 days

Stored:

* scheme
* eligible
* readiness_score
* renewal_date
* failed_criteria
* missing_documents

No Aadhaar or sensitive data stored.

---

### DynamoDB: renewal_notifications

Key: user_id#scheme

Fields:

* renewal_date
* last_notification_date
* notification_count (max 3)

---

## 6. Error Handling & Graceful Degradation

Timeout Budget:

* Rule Engine: 2s
* Readiness: 1s
* FAISS: 3s
* Bedrock: 4s
* STT/TTS: 3s
* Total max user wait: 10s

If services fail:

* Voice → Text fallback
* Bedrock → Template explanation
* RAG → "Information unavailable" message
* DynamoDB → Continue response without storage

System always returns usable output.

---

## 7. Scalability Strategy

* Lambda auto-scaling (0 → 1000 concurrent)
* DynamoDB on-demand
* S3 unlimited scaling
* FAISS cached in /tmp

Target:
100 concurrent users minimum

---

## 8. Security Model

* TLS 1.2+
* DynamoDB encryption (AES-256)
* IAM least privilege
* Secrets Manager for Sarvam key
* No storage of Aadhaar, bank numbers
* Input validation and sanitization

---

## 9. Cost Optimization

Design optimized for <₹5/user/month at 10K users.

Strategies:

* Claude Haiku (not Sonnet)
* Lambda ARM64
* DynamoDB on-demand
* FAISS caching
* Controlled token usage

---

## 10. Monitoring & Observability

Tracked Metrics:

* Lambda latency
* Error rate
* Bedrock token usage
* Voice service availability
* Cost metrics

CloudWatch Alarms:

* > 5% Lambda error rate
* > 5s average latency
* DynamoDB throttling

---

## 11. Deployment Model

Infrastructure as Code using AWS SAM.

Resources Created:

* API Gateway
* 3 Lambda Functions
* 2 DynamoDB Tables
* S3 Bucket
* SNS Topic
* CloudWatch Dashboard
* IAM Roles

Environments:

* dev
* prod

Deployment:

* sam build
* sam deploy

---

## 12. MVP Boundaries

Implemented:

* Lakshmir Bhandar only
* Voice + Text
* Eligibility + Readiness
* RAG
* AI Explanation
* Monitoring

Out of Scope:

* Multi-scheme live support
* OCR
* Government API integration
* WhatsApp integration

---

## 13. Innovation Summary

1. Hybrid deterministic + AI explanation model
2. Quantified Readiness Score instead of binary eligibility
3. Context-only RAG for misinformation prevention
4. Voice-first with strict fallback
5. Cost-conscious serverless design

---

## 14. Why This Architecture Wins

* Eliminates hallucination in eligibility
* Maintains resilience under service failure
* Demonstrates AWS-native best practices
* Production-ready scalability model
* Realistic hackathon scope

---

End of Document
