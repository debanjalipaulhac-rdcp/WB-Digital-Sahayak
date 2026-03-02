#!/usr/bin/env python3
"""
scripts/seed_dynamodb.py
=========================
Seed DynamoDB with test data for local/staging development.

Creates:
  - Sulata's profile (the demo user)
  - A test session

Run:
    python scripts/seed_dynamodb.py

Requires: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, DYNAMODB_TABLE_NAME in .env.local
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

def seed():
    from src.storage.dynamo import save_profile, save_session

    sulata_phone = "+919876543210"

    print("📌 Saving Sulata's profile...")
    ok = save_profile(sulata_phone, {
        "name":             "Sulata Mondal",
        "age":              38,
        "gender":           "female",
        "caste":            "sc",
        "district":         "Jalpaiguri",
        "is_govt_employee": False,
        "pays_income_tax":  False,
        "has_daughter":     True,
        "has_school_child": False,
        "is_unemployed":    False,
    })
    print(f"   {'✅' if ok else '❌'} Sulata profile")

    print("📌 Saving test session...")
    ok = save_session(sulata_phone, {
        "conversation_step": "START",
        "lang":              "bn",
        "partial_profile":   {},
        "partial_checks":    {},
    })
    print(f"   {'✅' if ok else '❌'} Test session")

    print("\n✅ DynamoDB seed complete")
    print(f"   Test with: GET /api/v1/profile/{sulata_phone}")

if __name__ == "__main__":
    seed()