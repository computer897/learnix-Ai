# 🚀 Qdrant RAG Backend - Quick Reference

## Installation (One-Time Setup)

```powershell
# Option 1: Use the setup script
.\setup.ps1

# Option 2: Manual setup
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Configuration

Edit `backend/.env`:
```env
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=your_api_key_here
GEMINI_API_KEY=your_gemini_key_here
QDRANT_COLLECTION=learnix_documents
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

## Testing

```powershell
# Test Qdrant integration
python test_qdrant.py
```

## Running the Server

```powershell
cd backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## API Usage

### Health Check
```bash
curl http://localhost:8000/api/health
```

### Upload Document
```bash
curl -X POST "http://localhost:8000/api/upload/" \
  -F "file=@document.pdf"
```

### Ask Question
```bash
curl -X POST "http://localhost:8000/api/ask/" \
  -F "question=What is machine learning?" \
  -F "top_k=5"
```

### List Documents
```bash
curl http://localhost:8000/api/documents/
```

## Important Changes

### ✅ What's New
- All chunks stored in Qdrant (vector database)
- Real embeddings using sentence-transformers
- 384-dimensional vectors
- Cosine similarity search
- `/tmp` temporary storage (Render-friendly)

### ❌ What's Removed
- Local JSON file storage
- Mock embedding mode
- DocumentStorage class usage
- InMemoryIndex usage
- File download endpoint

## File Structure

```
backend/
├── app.py                    # Main FastAPI app (MODIFIED)
├── requirements.txt          # Dependencies (UPDATED)
├── .env                      # Configuration (UPDATED)
├── utils/
│   ├── qdrant_store.py      # NEW: Qdrant integration
│   ├── embeddings.py        # MODIFIED: Real embeddings only
│   ├── loader.py            # Unchanged
│   ├── chunker.py           # Unchanged
│   ├── gemini.py            # Unchanged
│   └── chat_history.py      # Unchanged
├── QDRANT_MIGRATION.md      # NEW: Full documentation
└── .env.example             # UPDATED: Template

Root/
├── MIGRATION_SUMMARY.md     # NEW: Summary
├── setup.ps1                # NEW: Setup script
└── test_qdrant.py           # NEW: Test suite
```

## Key Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `QDRANT_URL` | ✅ Yes | - | Qdrant instance URL |
| `QDRANT_API_KEY` | ✅ Yes | - | Qdrant API key |
| `QDRANT_COLLECTION` | No | `learnix_documents` | Collection name |
| `EMBEDDING_MODEL` | No | `sentence-transformers/all-MiniLM-L6-v2` | Model name |
| `GEMINI_API_KEY` | ✅ Yes | - | Google Gemini API key |

## Common Commands

```powershell
# Activate virtual environment
cd backend
.\venv\Scripts\Activate.ps1

# Install/update dependencies
pip install -r requirements.txt

# Run tests
cd ..
python test_qdrant.py

# Start server
cd backend
uvicorn app:app --reload

# Check logs
# Logs appear in terminal with timestamps
```

## Troubleshooting Quick Fixes

| Problem | Solution |
|---------|----------|
| "Qdrant store not initialized" | Check `.env` has correct `QDRANT_URL` and `QDRANT_API_KEY` |
| "Failed to load model" | Ensure `sentence-transformers` installed, first run downloads model |
| "No text extracted" | Verify PDF is valid, check `PyPDF2` installed |
| Import errors | Activate virtual environment, reinstall requirements |
| Connection timeout | Check internet, verify Qdrant URL is correct |

## Next Steps

1. ✅ Configure `.env` with your API keys
2. ✅ Run `test_qdrant.py` to verify setup
3. ✅ Start the server
4. ✅ Upload a test document
5. ✅ Ask a test question
6. ✅ Monitor Qdrant dashboard for storage metrics

## Documentation

- **Full Guide**: `backend/QDRANT_MIGRATION.md`
- **Summary**: `MIGRATION_SUMMARY.md`
- **Code Docs**: Inline docstrings in all modules

## Support

- Check logs in terminal for detailed error messages
- Review `backend/QDRANT_MIGRATION.md` for detailed troubleshooting
- Verify environment variables are set correctly
- Ensure all dependencies are installed

---

**That's it! Your RAG backend is now fully Qdrant-powered with zero local JSON files.** 🎉
