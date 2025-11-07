# Qdrant Migration - RAG Backend Update

## Overview

Your RAG backend has been successfully migrated to use **Qdrant** as the vector database for storing document chunks and embeddings. All local JSON file storage has been removed, and the system now operates entirely through Qdrant for document management.

## What Changed

### 1. **New Qdrant Integration** (`utils/qdrant_store.py`)
- Created a comprehensive `QdrantStore` class that handles all vector database operations
- Automatically creates and manages the Qdrant collection with proper configuration
- Generates embeddings using `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- Provides methods for:
  - Upserting document chunks with embeddings
  - Searching for similar chunks using cosine similarity
  - Managing collection metadata
  - Listing stored documents

### 2. **Updated Dependencies** (`requirements.txt`)
Added production-ready packages:
- `sentence-transformers` - for generating embeddings
- `qdrant-client` - for Qdrant database operations
- `transformers` - required by sentence-transformers
- `PyPDF2` and `python-docx` - for document processing

### 3. **Simplified Embeddings Module** (`utils/embeddings.py`)
- Removed mock mode entirely
- Always uses real embeddings with `all-MiniLM-L6-v2` model
- Generates consistent 384-dimensional vectors
- Better error handling

### 4. **Refactored Main Application** (`app.py`)

#### Upload Endpoint (`/api/upload/`)
- Extracts text from uploaded PDFs/documents
- Chunks text into 1000-character segments with 200-character overlap
- Generates embeddings for each chunk
- **Directly upserts to Qdrant** (no local JSON files)
- Uses `/tmp` directory for temporary file storage (Render-friendly)
- Stores metadata: `text`, `filename`, `chunk_index`, `file_size`, `text_length`

#### Query Endpoint (`/api/ask/`)
- Embeds the user's question
- Searches Qdrant for top 5 most similar chunks (configurable)
- Returns matching chunks with:
  - Full text
  - Source filename
  - Chunk index
  - Similarity score
- Generates answer using Gemini API with retrieved context

#### Documents Endpoint (`/api/documents/`)
- Lists all unique filenames stored in Qdrant
- No longer reads from local JSON metadata

#### Startup Event
- Initializes Qdrant connection on startup
- Validates collection configuration
- Ensures proper connection before accepting requests

### 5. **Environment Configuration** (`.env`)
Updated with required Qdrant settings:
```env
# Gemini API Configuration
GEMINI_API_KEY=your_key_here

# Qdrant Configuration (REQUIRED)
QDRANT_URL=https://your-qdrant-instance.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_COLLECTION=learnix_documents

# Embedding Model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Key Features

### ✅ No Local JSON Files
- All document chunks and embeddings stored in Qdrant
- No `documents_metadata.json` or chunk files
- Cleaner, more scalable architecture

### ✅ Automatic Collection Management
- Creates Qdrant collection automatically if it doesn't exist
- Configured with:
  - 384-dimensional vectors
  - Cosine distance metric
  - Proper indexing for fast retrieval

### ✅ Production-Ready Error Handling
- Comprehensive logging at every step
- Graceful error messages
- Connection validation on startup

### ✅ Render-Friendly Deployment
- Uses `/tmp` directory for temporary files
- No persistent local storage required
- Environment variable configuration

## API Endpoints

### 1. **POST /api/upload/**
Upload a document and store chunks in Qdrant.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/upload/" \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "message": "document.pdf uploaded and indexed successfully!",
  "filename": "document.pdf",
  "status": "success",
  "chunks_stored": 15
}
```

### 2. **POST /api/ask/**
Query the knowledge base.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/ask/" \
  -F "question=What is machine learning?" \
  -F "top_k=5"
```

**Response:**
```json
{
  "answer": "Machine learning is...",
  "sources": [
    {
      "filename": "ml_textbook.pdf",
      "chunk_index": 3,
      "score": 0.89
    }
  ],
  "chunks": [
    {
      "text": "Machine learning is a subset...",
      "filename": "ml_textbook.pdf"
    }
  ]
}
```

### 3. **GET /api/documents/**
List all uploaded documents.

**Response:**
```json
{
  "documents": [
    {"name": "document1.pdf"},
    {"name": "document2.pdf"}
  ],
  "total": 2
}
```

### 4. **GET /api/health**
Check system health and Qdrant connection.

**Response:**
```json
{
  "status": "ok",
  "qdrant": "connected",
  "collection": {
    "name": "learnix_documents",
    "points_count": 150,
    "vectors_count": 150,
    "status": "green"
  }
}
```

## Installation & Setup

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create/update `.env` file:
```env
QDRANT_URL=https://your-instance.cloud.qdrant.io
QDRANT_API_KEY=your_api_key_here
QDRANT_COLLECTION=learnix_documents
GEMINI_API_KEY=your_gemini_key_here
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### 3. Run the Application
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## Testing

### Test Upload
```bash
curl -X POST "http://localhost:8000/api/upload/" \
  -F "file=@test.pdf"
```

### Test Query
```bash
curl -X POST "http://localhost:8000/api/ask/" \
  -F "question=What is the main topic?" \
  -F "top_k=5"
```

### Check Health
```bash
curl "http://localhost:8000/api/health"
```

## Migration Notes

### What Was Removed
- ❌ `utils/storage.py` - No longer used (replaced by `qdrant_store.py`)
- ❌ `utils/rag.py` - InMemoryIndex no longer needed
- ❌ Local JSON file storage (`documents_metadata.json`)
- ❌ Text file storage in `data/` directory
- ❌ Mock embedding mode
- ❌ `/api/download/{filename}` endpoint

### What's Still Used
- ✅ `utils/loader.py` - Document text extraction
- ✅ `utils/chunker.py` - Text chunking logic
- ✅ `utils/gemini.py` - Answer generation
- ✅ `utils/chat_history.py` - Chat history management
- ✅ `utils/embeddings.py` - Simplified for real embeddings only

## Troubleshooting

### "Qdrant store not initialized"
- Check that `QDRANT_URL` and `QDRANT_API_KEY` are set in `.env`
- Verify Qdrant instance is accessible
- Check logs for connection errors

### "Failed to load embedding model"
- Ensure `sentence-transformers` is installed
- First run downloads the model (~90MB)
- Check internet connection

### "No text extracted from file"
- Verify PDF/DOCX file is valid
- Check that `PyPDF2` and `python-docx` are installed
- Review file encoding

## Performance Considerations

- **First Query**: Model loading takes ~5-10 seconds on first request
- **Embeddings**: ~100ms per chunk (batch processing optimized)
- **Search**: Sub-second query response with Qdrant
- **Storage**: 384 floats × 4 bytes = ~1.5KB per chunk vector

## Next Steps

1. **Monitor Qdrant Usage**: Check your Qdrant dashboard for storage and query metrics
2. **Optimize Chunk Size**: Adjust `chunk_size` and `overlap` in chunker if needed
3. **Add Batch Upload**: Consider implementing batch document upload
4. **Implement Deletion**: Add endpoint to delete specific documents from Qdrant
5. **Add Filtering**: Extend search to filter by document metadata

## Questions?

Your RAG backend is now fully operational with Qdrant! All documents are stored as vector embeddings with efficient similarity search. No local JSON files are created or read.
