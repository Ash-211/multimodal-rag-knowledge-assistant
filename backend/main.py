import os
import shutil
import glob
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List
import sqlite3
from fastapi.security import OAuth2PasswordRequestForm
from auth import get_password_hash, verify_password, create_access_token, get_current_user
# Import our RAG components
# Ensure these imports match your actual file structure
from ingest.pdf_ingest import ingest_pdf
from vectorstore.document_index import DocumentIndex
from vectorstore.chunk_index import ChunkIndex
from vectorstore.image_store import ImageVectorStore
from vectorstore.index_manager import IndexManager
from rag.generator import generate_answer
from rag.reranker import rerank

DB_PATH = "../data/users.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        hashed_password TEXT NOT NULL
        )
        """)
    conn.commit()
    conn.close()
# --- Paths ---
# Assuming run from 'backend/' directory
DATA_DIR = "../data"
RAW_DIR = os.path.join(DATA_DIR, "raw")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed", "images")
INDICES_DIR = os.path.join(DATA_DIR, "indices")

CHUNK_INDEX_PATH = os.path.join(INDICES_DIR, "chunks")
DOC_INDEX_PATH = os.path.join(INDICES_DIR, "docs")
IMAGE_INDEX_PATH = os.path.join(INDICES_DIR, "images")

# --- Global State ---
# Initialize generic stores
doc_index = DocumentIndex()
chunk_index = ChunkIndex()
image_store = ImageVectorStore()
# Manager will be bound on startup
index_manager = IndexManager(doc_index, chunk_index)

app = FastAPI()

# Enable CORS for Frontend (React default port is 5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static images so frontend can display them via URL
os.makedirs(PROCESSED_DIR, exist_ok=True)
@app.get("/images/{username}/{filename}")
async def save_user_image(username: str, filename: str):
    from fastapi.responses import FileResponse
    image_path = os.path.join(DATA_DIR, "users", username, "processed", "images", filename)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    return FileResponse(image_path)

@app.on_event("startup")
async def startup_event():
    init_db()
    """Load indices from disk on startup if they exist."""
    print("Checking for existing indices...")
    if os.path.exists(CHUNK_INDEX_PATH) and os.path.exists(DOC_INDEX_PATH) and os.path.exists(IMAGE_INDEX_PATH):
        try:
            chunk_index.load_local(CHUNK_INDEX_PATH)
            doc_index.load_local(DOC_INDEX_PATH)
            image_store.load_local(IMAGE_INDEX_PATH)
            
            # Re-bind manager with loaded indices
            global index_manager
            index_manager = IndexManager(doc_index, chunk_index)
            print("indices loaded successfully!")
        except Exception as e:
            print(f"Failed to load indices: {e}")
    else:
        print("No indices found. System execution will rely on /ingest endpoint.")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "Multimodal RAG Backend Ready"}

class UserRegister(BaseModel):
    username: str
    password: str

@app.post("/register")
async def register(user: UserRegister):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM users WHERE username = ?", (user.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed = get_password_hash(user.password)
    cursor.execute("INSERT INTO users (username, hashed_password) VALUES (?, ?)", (user.username, hashed))
    conn.commit()
    conn.close()
    return {"message": "User registered!"}

@app.post("/token")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT hashed_password FROM users WHERE username = ?", (form_data.username,))
    result = cursor.fetchone()
    conn.close()

    if not result or not verify_password(form_data.password, result[0]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(data={"sub": form_data.username})
    return {"access_token": access_token, "token_type": "bearer"}
@app.post("/ingest")
async def ingest_endpoint(file: UploadFile = File(...),
                          username: str = Depends(get_current_user)
                          ):
    USER_DIR = os.path.join(DATA_DIR, "users", username)
    USER_RAW_DIR = os.path.join(USER_DIR, "raw")
    USER_PROCESSED_DIR = os.path.join(USER_DIR, "processed", "images")
    USER_INDICES_DIR = os.path.join(USER_DIR, "indices")
    
    USER_CHUNK_INDEX_PATH = os.path.join(USER_INDICES_DIR, "chunks")
    USER_DOC_INDEX_PATH = os.path.join(USER_INDICES_DIR, "docs")
    USER_IMAGE_INDEX_PATH = os.path.join(USER_INDICES_DIR, "images")
   
    user_doc_index = DocumentIndex()
    user_chunk_index = ChunkIndex()
    user_image_store = ImageVectorStore()
    
    # Load existing user data if available
    if os.path.exists(USER_CHUNK_INDEX_PATH):
        user_chunk_index.load_local(USER_CHUNK_INDEX_PATH)
        user_doc_index.load_local(USER_DOC_INDEX_PATH)
        user_image_store.load_local(USER_IMAGE_INDEX_PATH)
    
    filename = file.filename
    save_path = os.path.join(USER_RAW_DIR, filename)
    os.makedirs(USER_RAW_DIR, exist_ok=True)
    
    # Save Uploaded File
    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    print(f"[{username}] Ingesting {filename}...")
    text_chunks, _ = ingest_pdf(save_path, USER_PROCESSED_DIR)
    
    # --- Index Text ---
    from collections import defaultdict
    chunks_by_source = defaultdict(list)
    for chunk in text_chunks:
        chunks_by_source[chunk["source"]].append(chunk["text"])
    for source, chunks in chunks_by_source.items():
        slide_chunks = []
        full_text = ""
        for text in chunks:
            text = text.strip()
            if len(text) > 50:
                full_text += text + "\n"
                slide_chunks.append(text)
        
        if slide_chunks:
            user_doc_index.add_document(full_text, source)
            user_chunk_index.add_chunks(source, slide_chunks)
            
    # --- Index Images ---
    all_images = glob.glob(os.path.join(USER_PROCESSED_DIR, "*.png"))
    pdf_basename = os.path.basename(save_path)
    new_images = [img for img in all_images if pdf_basename in os.path.basename(img)]
    
    image_metadata = []
    for p in new_images:
        try:
            parts = p.split("_page_")
            page_num = int(parts[1].split("_img_")[0]) if len(parts) > 1 else 0
        except:
            page_num = 0
        image_metadata.append({"image_path": p, "page": page_num})
        
    if new_images:
        user_image_store.add_images(new_images, image_metadata)
    # --- Save Updates ---
    user_chunk_index.save_local(USER_CHUNK_INDEX_PATH)
    user_doc_index.save_local(USER_DOC_INDEX_PATH)
    user_image_store.save_local(USER_IMAGE_INDEX_PATH)
    
    return {
        "message": f"Successfully ingested {filename}", 
        "chunks": len(text_chunks), 
        "images": len(new_images)
    }

class QueryRequest(BaseModel):
    query: str

@app.post("/chat")
async def chat_endpoint(
    request: QueryRequest,
    username: str = Depends(get_current_user)  # <-- ADD THIS
):
    query = request.query
    
    # User-specific directories
    USER_DIR = os.path.join(DATA_DIR, "users", username)
    USER_INDICES_DIR = os.path.join(USER_DIR, "indices")
    USER_PROCESSED_DIR = os.path.join(USER_DIR, "processed", "images")
    
    USER_CHUNK_INDEX_PATH = os.path.join(USER_INDICES_DIR, "chunks")
    USER_DOC_INDEX_PATH = os.path.join(USER_INDICES_DIR, "docs")
    USER_IMAGE_INDEX_PATH = os.path.join(USER_INDICES_DIR, "images")
    
    # Load user's indices
    user_doc_index = DocumentIndex()
    user_chunk_index = ChunkIndex()
    user_image_store = ImageVectorStore()
    
    if not os.path.exists(USER_CHUNK_INDEX_PATH):
        return {
            "answer": "You haven't uploaded any documents yet. Please upload a PDF first.",
            "sources": [],
            "images": []
        }
    
    user_chunk_index.load_local(USER_CHUNK_INDEX_PATH)
    user_doc_index.load_local(USER_DOC_INDEX_PATH)
    user_image_store.load_local(USER_IMAGE_INDEX_PATH)
    
    user_index_manager = IndexManager(user_doc_index, user_chunk_index)
    
    # 1. Retrieve Text
    retrieved_chunks = user_index_manager.retrieve(query)
    
    # Deduplicate
    unique_chunks = []
    seen = set()
    for r in retrieved_chunks:
        if r["content"] not in seen:
            unique_chunks.append(r)
            seen.add(r["content"])
            
    # 2. Rerank
    ranked_chunks = rerank(query, unique_chunks, top_k=5)
    
    # 3. Retrieve Images
    image_results = user_image_store.search(query, k=4)
    
    # 4. Generate Answer
    try:
        answer = generate_answer(query, ranked_chunks, image_results)
    except Exception as e:
        answer = f"Error generating answer: {e}"
        
    # 5. Format Response for Frontend
    # Convert local image paths to URLs
    base_url = f"http://localhost:8000/images/{username}/"
    frontend_images = []
    for img in image_results:
        fname = os.path.basename(img["image_path"])
        frontend_images.append({
            "url": base_url + fname,
            "page": img.get("page", 0)
        })
        
    return {
        "answer": answer,
        "sources": ranked_chunks,
        "images": frontend_images
    }