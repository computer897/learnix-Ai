# Render Deployment Guide for Learnix RAG Backend

## ✅ Pre-Deployment Checklist

### 1. **Security - Remove Secrets from Git**
```bash
# Remove .env from git if accidentally committed
git rm --cached backend/.env
git commit -m "Remove .env from repository"

# IMPORTANT: Rotate all API keys that were committed!
# - Generate new GEMINI_API_KEY
# - Generate new QDRANT_API_KEY
```

### 2. **Verify Project Structure**
```
learnix/
├── backend/
│   ├── app.py                 # FastAPI application
│   ├── requirements.txt       # Python dependencies
│   ├── .env.example          # Template (safe to commit)
│   └── utils/
│       └── qdrant_store.py   # Qdrant vector storage
├── render.yaml               # Render configuration
└── .gitignore               # Excludes .env
```

## 🚀 Render Deployment Steps

### Step 1: Create New Web Service on Render

1. Go to https://dashboard.render.com
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository: `learnix`
4. Configure:
   - **Name**: `learnix-backend`
   - **Region**: Oregon (or closest to your Qdrant instance)
   - **Branch**: `main`
   - **Root Directory**: Leave blank (or set to `backend` if needed)
   - **Runtime**: Python 3
   - **Build Command**: 
     ```bash
     cd backend && pip install -r requirements.txt
     ```
   - **Start Command**:
     ```bash
     cd backend && uvicorn app:app --host 0.0.0.0 --port $PORT
     ```

### Step 2: Set Environment Variables

In the Render Dashboard → Environment tab, add these variables:

| Variable | Value | Notes |
|----------|-------|-------|
| `QDRANT_URL` | `https://2486c712-...gcp.cloud.qdrant.io` | Your Qdrant cloud URL |
| `QDRANT_API_KEY` | `eyJhbGci...` | Your Qdrant API key |
| `QDRANT_COLLECTION` | `learnix_documents` | Collection name |
| `GEMINI_API_KEY` | `AIzaSy...` | Google Gemini API key |
| `EMBEDDING_MODEL` | `sentence-transformers/all-MiniLM-L6-v2` | (Optional) |
| `PYTHON_VERSION` | `3.9.18` | (Optional) Pin Python version |

**⚠️ IMPORTANT**: Click the 🔒 icon to mark sensitive variables as secret!

### Step 3: Deploy

1. Click **"Create Web Service"**
2. Render will:
   - Clone your repo
   - Install dependencies (~5-10 minutes)
   - Start the server
   - Assign a URL: `https://learnix-backend.onrender.com`

### Step 4: Verify Deployment

Check the logs in Render Dashboard for:
```
INFO:app:🚀 Starting Learnix backend...
INFO:utils.qdrant_store:Connecting to Qdrant at https://...
INFO:utils.qdrant_store:✅ Collection 'learnix_documents' already exists
INFO:app:✅ Connected to Qdrant collection: {...}
INFO:     Application startup complete.
```

Test the health endpoint:
```bash
curl https://learnix-backend.onrender.com/api/health
```

Expected response:
```json
{
  "status": "ok",
  "qdrant": "connected",
  "collection": {
    "name": "learnix_documents",
    "points_count": 0,
    "status": "green"
  }
}
```

## 📦 How Data Storage Works

### Upload Flow (Chunks → Qdrant)

1. **User uploads PDF** via `/api/upload/`
2. **Extract text** using PyPDF2
3. **Chunk text** (1000 chars, 200 overlap)
4. **Generate embeddings** (384-dim vectors using all-MiniLM-L6-v2)
5. **Store in Qdrant**:
   ```python
   {
     "id": "hash_chunk_001",
     "vector": [0.123, -0.456, ...],  # 384 dimensions
     "payload": {
       "text": "chunk content...",
       "filename": "document.pdf",
       "chunk_index": 0,
       "total_chunks": 15
     }
   }
   ```
6. **Delete temp file** from `/tmp`

### Query Flow (Search Qdrant)

1. **User asks question** via `/api/ask/`
2. **Embed question** (same model → 384-dim)
3. **Search Qdrant** (cosine similarity, top 5)
4. **Retrieve chunks**:
   ```python
   results = [
     {"text": "...", "filename": "doc.pdf", "score": 0.89},
     {"text": "...", "filename": "doc.pdf", "score": 0.82},
     ...
   ]
   ```
5. **Generate answer** using Gemini with context
6. **Return answer + sources**

### Storage Location Summary

| Data Type | Storage | Persistence | Notes |
|-----------|---------|-------------|-------|
| **Embeddings** | Qdrant Cloud | Permanent | 384-dim vectors |
| **Chunk text** | Qdrant payload | Permanent | `"text"` field |
| **Metadata** | Qdrant payload | Permanent | filename, chunk_index |
| **Uploaded files** | `/tmp` | Ephemeral | Deleted after processing |
| **Chat history** | `backend/storage/` | Persistent disk | JSON file |

**Key Points:**
- ✅ All document chunks stored in Qdrant (no local JSON)
- ✅ Embeddings generated on-the-fly during upload
- ✅ `/tmp` used only for temporary file processing
- ✅ No persistent local storage needed for documents

## 🔍 Viewing Data in Qdrant

### Option 1: Qdrant Cloud Console
1. Go to https://cloud.qdrant.io
2. Select your cluster
3. Click on `learnix_documents` collection
4. View points, payloads, and collection stats

### Option 2: Python Script
```python
from qdrant_client import QdrantClient
import os

client = QdrantClient(
    url=os.environ["QDRANT_URL"],
    api_key=os.environ["QDRANT_API_KEY"]
)

# Get collection info
info = client.get_collection("learnix_documents")
print(f"Points: {info.points_count}")

# View first 10 chunks
points, _ = client.scroll(
    collection_name="learnix_documents",
    limit=10,
    with_payload=True
)

for point in points:
    print(f"ID: {point.id}")
    print(f"File: {point.payload.get('filename')}")
    print(f"Text: {point.payload.get('text')[:100]}...")
    print("---")
```

### Option 3: API Endpoint
```bash
curl https://learnix-backend.onrender.com/api/documents/
```

## 🐛 Troubleshooting

### Build Fails
- **Error**: `ModuleNotFoundError`
  - **Fix**: Verify `requirements.txt` path in build command
  
- **Error**: `torch` version mismatch
  - **Fix**: Pin versions in requirements.txt (already done)

### Runtime Fails
- **Error**: `Qdrant initialization failed`
  - **Fix**: Check QDRANT_URL and QDRANT_API_KEY in Render env vars
  
- **Error**: `Failed to load embedding model`
  - **Fix**: Model downloads on first use; check logs and wait (~2 min)
  - The model is lazy-loaded, so first upload will trigger download

### Model Download Issues
- **Symptom**: First upload times out
  - **Fix**: The embedding model (~90MB) downloads on first use
  - **Solution**: Add a warmup endpoint (optional):
    ```python
    @app.get("/api/warmup")
    def warmup():
        """Pre-load the embedding model"""
        if qdrant_store:
            # Trigger model load
            qdrant_store.generate_embedding("test")
            return {"status": "model loaded"}
    ```

## 📊 Testing Endpoints

### 1. Health Check
```bash
curl https://learnix-backend.onrender.com/api/health
```

### 2. Upload Document
```bash
curl -X POST https://learnix-backend.onrender.com/api/upload/ \
  -F "file=@document.pdf"
```

Response:
```json
{
  "message": "document.pdf uploaded and indexed successfully!",
  "filename": "document.pdf",
  "status": "success",
  "chunks_stored": 15
}
```

### 3. Ask Question
```bash
curl -X POST https://learnix-backend.onrender.com/api/ask/ \
  -F "question=What is the main topic?" \
  -F "top_k=5"
```

Response:
```json
{
  "answer": "The main topic is...",
  "sources": [
    {"filename": "document.pdf", "chunk_index": 3, "score": 0.89}
  ]
}
```

### 4. List Documents
```bash
curl https://learnix-backend.onrender.com/api/documents/
```

## 🔐 Security Best Practices

1. **Never commit .env files**
   - ✅ Added to `.gitignore`
   - ✅ Use Render environment variables

2. **Rotate leaked keys**
   - 🔴 Your current keys are visible in the conversation
   - Generate new keys immediately:
     - Gemini: https://makersuite.google.com/app/apikey
     - Qdrant: Cloud dashboard → API Keys

3. **Use HTTPS only**
   - ✅ Render provides SSL automatically

4. **Limit CORS in production**
   - Update `app.py`:
     ```python
     app.add_middleware(
         CORSMiddleware,
         allow_origins=["https://your-frontend.com"],  # Restrict!
         allow_credentials=True,
         allow_methods=["*"],
         allow_headers=["*"],
     )
     ```

## 📈 Monitoring

- **Render Logs**: Real-time logs in dashboard
- **Metrics**: CPU, memory, request count
- **Alerts**: Set up email notifications for crashes

## 🎯 Next Steps

1. ✅ Deploy to Render
2. ✅ Test all endpoints
3. ✅ Upload a test PDF
4. ✅ Query the knowledge base
5. 🔒 Rotate API keys
6. 🌐 Connect your frontend
7. 📊 Monitor usage and performance

---

**Your backend is now production-ready!** 🚀

All chunks are stored in Qdrant with embeddings, no local JSON files, and `/tmp` is used only for ephemeral uploads.
