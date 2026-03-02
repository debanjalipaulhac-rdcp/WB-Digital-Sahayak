#!/usr/bin/env python3
"""
scripts/seed_pinecone.py
=========================
One-time setup: embed all 4 schemes → upsert to Pinecone.

Run ONCE before demo:
    python scripts/seed_pinecone.py

Prerequisites:
    1. PINECONE_API_KEY in .env.local
    2. AWS Bedrock Titan Embeddings V2 enabled in console
    3. Pinecone index created: name=wb-sahayak-schemes, dims=1024, metric=cosine

Verifies the round-trip after upsert.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.ai.vector_search import setup_index

if __name__ == "__main__":
    print("🔄 Seeding Pinecone index with scheme vectors...")
    ok = setup_index()
    if ok:
        print("✅ Pinecone seeded. Run a test query:")
        print('   python -c "from src.ai.vector_search import search; print(search(\'scheme for sick mother\'))"')
    else:
        print("❌ Seed failed — check logs above")
        sys.exit(1)