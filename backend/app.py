import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
import logging
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from utils.loader import process_file
from utils.chunker import chunk_text
from utils.gemini import generate_answer_from_context
from utils.chat_history import ChatHistory
from utils.qdrant_store import create_qdrant_store

APP_DIR = Path(__file__).parent

# Use /tmp for temporary file storage (Render-friendly)
TEMP_DIR = Path(tempfile.gettempdir()) / "learnix_uploads"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Initialize chat history
chat_history = ChatHistory(APP_DIR / "storage")

# Initialize Qdrant store
qdrant_store = None

app = FastAPI(title="Learnix - College AI Assistant")

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize Qdrant connection on startup."""
    global qdrant_store
    
    logger.info("🚀 Starting Learnix backend...")
    
    # Initialize Qdrant store
    qdrant_store = create_qdrant_store()
    
    if qdrant_store:
        collection_info = qdrant_store.get_collection_info()
        logger.info(f"✅ Connected to Qdrant collection: {collection_info}")
    else:
        logger.error("❌ Failed to initialize Qdrant store. Check your environment variables.")
        raise RuntimeError("Qdrant initialization failed")


@app.get("/api/health")
def health():
    """Health check endpoint."""
    if qdrant_store:
        collection_info = qdrant_store.get_collection_info()
        return {
            "status": "ok",
            "qdrant": "connected",
            "collection": collection_info
        }
    return {"status": "error", "qdrant": "not connected"}


@app.post("/api/upload/")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a document, storing chunks directly in Qdrant."""
    try:
        if not qdrant_store:
            raise HTTPException(status_code=500, detail="Qdrant store not initialized")
        
        content = await file.read()
        logger.info(f"Uploading file: {file.filename}, size: {len(content)} bytes")
        
        # Save to temporary location for processing
        temp_file_path = TEMP_DIR / file.filename
        with open(temp_file_path, 'wb') as f:
            f.write(content)
        
        # Extract and clean text
        logger.info(f"Processing file: {file.filename}")
        text = process_file(file.filename, content)
        if not text:
            logger.warning(f"No text extracted from: {file.filename}")
            # Clean up temp file
            if temp_file_path.exists():
                temp_file_path.unlink()
            raise HTTPException(status_code=400, detail="No text extracted from file")

        logger.info(f"Extracted {len(text)} characters from {file.filename}")
        
        # Split into chunks for better retrieval
        chunks = chunk_text(text, chunk_size=1000, overlap=200)
        logger.info(f"Split into {len(chunks)} chunks")

        # Store chunks directly in Qdrant with embeddings
        logger.info(f"Storing {len(chunks)} chunks in Qdrant")
        result = qdrant_store.upsert_chunks(
            chunks=chunks,
            filename=file.filename,
            metadata={
                "file_size": len(content),
                "text_length": len(text)
            }
        )
        
        # Clean up temporary file
        if temp_file_path.exists():
            temp_file_path.unlink()
        
        if result["status"] == "success":
            logger.info(f"Successfully uploaded: {file.filename}")
            return {
                "message": f"{file.filename} uploaded and indexed successfully!",
                "filename": file.filename,
                "status": "success",
                "chunks_stored": result["count"]
            }
        else:
            raise HTTPException(status_code=500, detail=result["message"])
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading {file.filename}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")


@app.post("/api/ask/")
async def ask_question(question: str = Form(...), top_k: int = Form(5)):
    """Query endpoint that searches Qdrant for similar chunks and generates an answer."""
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")
    
    if not qdrant_store:
        raise HTTPException(status_code=500, detail="Qdrant store not initialized")
    
    try:
        # Search Qdrant for top K similar chunks
        logger.info(f"Searching for top {top_k} chunks for query: {question[:50]}...")
        hits = qdrant_store.search_similar_chunks(query=question, top_k=top_k)
        
        if not hits:
            logger.warning("No matching chunks found in Qdrant")
            return JSONResponse({
                "answer": "I couldn't find any relevant information to answer your question. Please make sure documents are uploaded.",
                "sources": [],
                "chunks": []
            })
        
        # Extract context texts from search results
        context_texts: List[str] = [hit["text"] for hit in hits]
        
        # Generate answer using Gemini (or mock)
        answer = generate_answer_from_context(question, context_texts)
        
        # Format sources with filenames and chunk info
        sources = [
            {
                "filename": hit["filename"],
                "chunk_index": hit["chunk_index"],
                "score": hit["score"]
            }
            for hit in hits
        ]
        
        # Save to chat history (save source filenames)
        source_ids = [f"{hit['filename']}_chunk_{hit['chunk_index']}" for hit in hits]
        chat_history.add_message(question, answer, source_ids)
        
        logger.info(f"Successfully answered query with {len(hits)} sources")
        return JSONResponse({
            "answer": answer,
            "sources": sources,
            "chunks": [{"text": hit["text"][:200] + "...", "filename": hit["filename"]} for hit in hits[:3]]
        })
    
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")


@app.get("/api/documents/")
def list_documents():
    """List all uploaded documents stored in Qdrant."""
    if not qdrant_store:
        raise HTTPException(status_code=500, detail="Qdrant store not initialized")
    
    try:
        # Get unique filenames from Qdrant
        filenames = qdrant_store.list_documents()
        
        documents = [{"name": filename} for filename in filenames]
        
        return {
            "documents": documents,
            "total": len(documents)
        }
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listing documents: {str(e)}")


# Chat History Endpoints
@app.get("/api/chat/history")
def get_chat_history(limit: int = 20):
    """Get recent chat history."""
    history = chat_history.get_history(limit=limit)
    return JSONResponse({"history": history, "count": len(history)})


@app.delete("/api/chat/history")
def clear_chat_history():
    """Clear all chat history."""
    success = chat_history.clear_history()
    if success:
        return JSONResponse({"message": "Chat history cleared successfully"})
    else:
        raise HTTPException(status_code=500, detail="Failed to clear chat history")


@app.delete("/api/chat/message/{message_id}")
def delete_message(message_id: str):
    """Delete a specific message from history."""
    success = chat_history.delete_message(message_id)
    if success:
        return JSONResponse({"message": "Message deleted successfully"})
    else:
        raise HTTPException(status_code=404, detail="Message not found")


@app.get("/api/chat/stats")
def get_chat_stats():
    """Get chat history statistics."""
    stats = chat_history.get_stats()
    return JSONResponse(stats)


# Mount frontend static files LAST (after all API routes)
# This must be last because it uses catch-all routing
static_dir = APP_DIR / "frontend"
if static_dir.exists():
    app.mount("/", StaticFiles(directory=str(static_dir), html=True), name="frontend")
