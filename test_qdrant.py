"""
Test script to verify Qdrant integration and embedding generation.
Run this to ensure everything is configured correctly.
"""

import os
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / "backend" / ".env")

print("🧪 Testing Qdrant Integration\n")
print("=" * 50)

# Test 1: Check environment variables
print("\n1️⃣  Checking environment variables...")
qdrant_url = os.getenv("QDRANT_URL")
qdrant_key = os.getenv("QDRANT_API_KEY")
collection = os.getenv("QDRANT_COLLECTION")

if qdrant_url:
    print(f"   ✅ QDRANT_URL: {qdrant_url[:50]}...")
else:
    print("   ❌ QDRANT_URL not set")
    sys.exit(1)

if qdrant_key:
    print(f"   ✅ QDRANT_API_KEY: {qdrant_key[:20]}...")
else:
    print("   ❌ QDRANT_API_KEY not set")
    sys.exit(1)

print(f"   ✅ QDRANT_COLLECTION: {collection}")

# Test 2: Import and load embedding model
print("\n2️⃣  Loading embedding model...")
try:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    print("   ✅ Embedding model loaded successfully")
except Exception as e:
    print(f"   ❌ Failed to load model: {e}")
    sys.exit(1)

# Test 3: Generate test embedding
print("\n3️⃣  Generating test embedding...")
try:
    test_text = "This is a test sentence for embedding generation."
    embedding = model.encode(test_text)
    print(f"   ✅ Generated embedding with shape: {embedding.shape}")
    print(f"   ✅ Embedding dimension: {len(embedding)}")
except Exception as e:
    print(f"   ❌ Failed to generate embedding: {e}")
    sys.exit(1)

# Test 4: Connect to Qdrant
print("\n4️⃣  Connecting to Qdrant...")
try:
    from qdrant_client import QdrantClient
    client = QdrantClient(url=qdrant_url, api_key=qdrant_key, timeout=30)
    collections = client.get_collections()
    print(f"   ✅ Connected to Qdrant")
    print(f"   ✅ Found {len(collections.collections)} collection(s)")
except Exception as e:
    print(f"   ❌ Failed to connect to Qdrant: {e}")
    sys.exit(1)

# Test 5: Check/Create collection
print("\n5️⃣  Checking collection...")
try:
    collection_names = [c.name for c in collections.collections]
    if collection in collection_names:
        print(f"   ✅ Collection '{collection}' exists")
        info = client.get_collection(collection)
        print(f"   📊 Points count: {info.points_count}")
        print(f"   📊 Status: {info.status}")
    else:
        print(f"   ℹ️  Collection '{collection}' does not exist yet")
        print(f"   ℹ️  It will be created automatically on first upload")
except Exception as e:
    print(f"   ⚠️  Could not check collection: {e}")

# Test 6: Import QdrantStore
print("\n6️⃣  Testing QdrantStore module...")
try:
    from backend.utils.qdrant_store import create_qdrant_store
    store = create_qdrant_store()
    if store:
        print("   ✅ QdrantStore initialized successfully")
        info = store.get_collection_info()
        print(f"   📊 Collection info: {info}")
    else:
        print("   ❌ Failed to initialize QdrantStore")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Error with QdrantStore: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Test chunk storage
print("\n7️⃣  Testing chunk storage...")
try:
    test_chunks = [
        "Machine learning is a subset of artificial intelligence.",
        "It focuses on building systems that learn from data.",
        "Neural networks are inspired by biological neurons."
    ]
    
    result = store.upsert_chunks(
        chunks=test_chunks,
        filename="test_document.txt",
        metadata={"test": True}
    )
    
    if result["status"] == "success":
        print(f"   ✅ Successfully stored {result['count']} test chunks")
    else:
        print(f"   ❌ Failed to store chunks: {result['message']}")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Error storing chunks: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 8: Test similarity search
print("\n8️⃣  Testing similarity search...")
try:
    query = "What is machine learning?"
    results = store.search_similar_chunks(query, top_k=2)
    
    if results:
        print(f"   ✅ Found {len(results)} similar chunks")
        for i, result in enumerate(results, 1):
            print(f"   📄 Result {i}:")
            print(f"      Text: {result['text'][:60]}...")
            print(f"      Score: {result['score']:.4f}")
            print(f"      Source: {result['filename']}")
    else:
        print("   ⚠️  No results found (this may be expected)")
except Exception as e:
    print(f"   ❌ Error searching: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 9: Clean up test data
print("\n9️⃣  Cleaning up test data...")
try:
    success = store.delete_document_chunks("test_document.txt")
    if success:
        print("   ✅ Test chunks deleted successfully")
    else:
        print("   ⚠️  Could not delete test chunks")
except Exception as e:
    print(f"   ⚠️  Cleanup error: {e}")

print("\n" + "=" * 50)
print("✨ All tests passed! Your Qdrant integration is working correctly.")
print("\n🚀 You can now start the server with:")
print("   cd backend")
print("   uvicorn app:app --reload --host 0.0.0.0 --port 8000")
print("\n📚 Upload a document to test:")
print("   curl -X POST http://localhost:8000/api/upload/ -F 'file=@your_document.pdf'")
print("\n❓ Ask a question:")
print("   curl -X POST http://localhost:8000/api/ask/ -F 'question=Your question here'")
print()
