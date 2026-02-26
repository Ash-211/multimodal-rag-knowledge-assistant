import os
import shutil
import glob
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.responses import StreamingResponse
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
from ingest.audio_ingest import ingest_audio
from vectorstore.document_index import DocumentIndex
from vectorstore.chunk_index import ChunkIndex
from vectorstore.image_store import ImageVectorStore
from vectorstore.index_manager import IndexManager
from rag.generator import generate_answer, generate_answer_stream, generate_title
from rag.reranker import rerank

DB_PATH = "../data/users.db"

def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        username TEXT PRIMARY KEY,
        hashed_password TEXT NOT NULL,
        first_name TEXT DEFAULT '',
        last_name TEXT DEFAULT '',
        email TEXT DEFAULT ''
        )
        """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversations(
        id TEXT PRIMARY KEY,
        username TEXT NOT NULL,
        title TEXT DEFAULT 'New Chat',
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (username) REFERENCES users(username)
        )
        """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS chat_messages(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        username TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        sources TEXT DEFAULT '[]',
        images TEXT DEFAULT '[]',
        timestamp TEXT NOT NULL,
        FOREIGN KEY (username) REFERENCES users(username),
        FOREIGN KEY (conversation_id) REFERENCES conversations(id)
        )
        """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_documents(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id TEXT NOT NULL,
        filename TEXT NOT NULL,
        username TEXT NOT NULL,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        FOREIGN KEY (username) REFERENCES users(username)
        )
        """)
    # Migrate existing DBs that don't have the new columns
    for col in ['first_name', 'last_name', 'email']:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
    # Migrate chat_messages to have conversation_id
    try:
        cursor.execute("ALTER TABLE chat_messages ADD COLUMN conversation_id TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
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
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173").split(","),
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

@app.get("/api/health")
def health_check():
    return {"status": "ok", "message": "VectorMind Backend Ready"}

class UserRegister(BaseModel):
    username: str
    password: str
    first_name: str = ''
    last_name: str = ''
    email: str = ''

@app.post("/register")
async def register(user: UserRegister):
    # Validate email format
    if user.email:
        import re
        email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        if not email_pattern.match(user.email):
            raise HTTPException(status_code=400, detail="Invalid email address")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT username FROM users WHERE username = ?", (user.username,))
    if cursor.fetchone():
        raise HTTPException(status_code=400, detail="Username already exists")

    hashed = get_password_hash(user.password)
    cursor.execute(
        "INSERT INTO users (username, hashed_password, first_name, last_name, email) VALUES (?, ?, ?, ?, ?)",
        (user.username, hashed, user.first_name, user.last_name, user.email)
    )
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

@app.post("/clear-data")
async def logout_endpoint(username: str = Depends(get_current_user)):
    """Clear all user-uploaded data (files, images, indices) on logout."""
    user_dir = os.path.join(DATA_DIR, "users", username)
    if os.path.exists(user_dir):
        shutil.rmtree(user_dir)
    return {"message": "User data cleared successfully"}

@app.post("/ingest")
async def ingest_endpoint(file: UploadFile = File(...),
                          conversation_id: str = Form(None),
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
    
    # Determine file type and ingest accordingly
    AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
    file_ext = os.path.splitext(filename)[1].lower()
    
    text_chunks = []
    new_images = []
    
    if file_ext in AUDIO_EXTENSIONS:
        # --- Audio Ingestion ---
        transcript = ingest_audio(save_path)
        if transcript and len(transcript.strip()) > 50:
            # Split transcript into ~500-char chunks for better retrieval
            chunk_size = 500
            words = transcript.split()
            current_chunk = ""
            audio_chunks = []
            for word in words:
                if len(current_chunk) + len(word) + 1 > chunk_size and current_chunk:
                    audio_chunks.append(current_chunk.strip())
                    current_chunk = word
                else:
                    current_chunk += " " + word
            if current_chunk.strip():
                audio_chunks.append(current_chunk.strip())
            
            source = filename
            user_doc_index.add_document(transcript, source)
            user_chunk_index.add_chunks(source, audio_chunks)
            text_chunks = [{"source": source, "text": c} for c in audio_chunks]
    else:
        # --- PDF Ingestion ---
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
    
    # Associate document with conversation if conversation_id provided
    if conversation_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation_documents (conversation_id, filename, username) VALUES (?, ?, ?)",
            (conversation_id, filename, username)
        )
        conn.commit()
        conn.close()

    return {
        "message": f"Successfully ingested {filename}", 
        "chunks": len(text_chunks), 
        "images": len(new_images)
    }

class QueryRequest(BaseModel):
    query: str
    conversation_id: str = None

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
    base_url = f"/images/{username}/"
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

@app.post("/chat/stream")
async def chat_stream_endpoint(
    request: QueryRequest,
    username: str = Depends(get_current_user)
):
    query = request.query
    conversation_id = request.conversation_id
    
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
        async def no_docs():
            no_docs_msg = json.dumps({'type': 'text', 'content': "You haven't uploaded any documents yet. Please upload a PDF first."})
            done_msg = json.dumps({'type': 'done', 'sources': [], 'images': []})
            yield f"data: {no_docs_msg}\n\n"
            yield f"data: {done_msg}\n\n"
        return StreamingResponse(no_docs(), media_type="text/event-stream")
    
    user_chunk_index.load_local(USER_CHUNK_INDEX_PATH)
    user_doc_index.load_local(USER_DOC_INDEX_PATH)
    user_image_store.load_local(USER_IMAGE_INDEX_PATH)
    
    # Look up documents associated with this conversation
    conv_doc_filenames = None  # None means no filtering (search all)
    if conversation_id:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT filename FROM conversation_documents WHERE conversation_id = ? AND username = ?",
            (conversation_id, username)
        )
        rows = cursor.fetchall()
        conn.close()
        if rows:
            conv_doc_filenames = {row[0] for row in rows}
    
    user_index_manager = IndexManager(user_doc_index, user_chunk_index)
    
    # 1. Retrieve Text (filtered to conversation's documents if available)
    retrieved_chunks = user_index_manager.retrieve(query, source_filter=conv_doc_filenames)
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
    
    # 4. Format images for frontend
    base_url = f"/images/{username}/"
    frontend_images = []
    for img in image_results:
        fname = os.path.basename(img["image_path"])
        frontend_images.append({
            "url": base_url + fname,
            "page": img.get("page", 0)
        })
    
    # 5. Stream the answer
    async def event_stream():
        try:
            for chunk in generate_answer_stream(query, ranked_chunks, image_results):
                yield f"data: {json.dumps({'type': 'text', 'content': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"
        
        # Send sources and images as the final event
        yield f"data: {json.dumps({'type': 'done', 'sources': ranked_chunks, 'images': frontend_images})}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")

@app.get("/documents")
def get_documents(username: str = Depends(get_current_user)):

    user_raw_dir = os.path.join(DATA_DIR, "users", username, "raw")
    if not os.path.exists(user_raw_dir):
        return {'documents': []}
    
    documents = []
    for filename in os.listdir(user_raw_dir):
        filepath = os.path.join(user_raw_dir, filename)
        if os.path.isfile(filepath):
            documents.append({
                "name" : filename,
                "size" : os.path.getsize(filepath),
                "uploaded_at" : os.path.getmtime(filepath)
            })
        
    return {"documents": documents}



@app.delete("/documents/{filename}")
async def delete_document(filename: str, username: str = Depends(get_current_user)):
    user_dir = os.path.join(DATA_DIR, "users", username)
    user_raw_dir = os.path.join(user_dir, "raw")
    file_path = os.path.join(user_raw_dir, filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Remove the target file
    os.remove(file_path)
    
    # Wipe old indices and processed images
    indices_dir = os.path.join(user_dir, "indices")
    processed_dir = os.path.join(user_dir, "processed")
    if os.path.exists(indices_dir):
        shutil.rmtree(indices_dir)
    if os.path.exists(processed_dir):
        shutil.rmtree(processed_dir)

    # Rebuild indices from remaining files
    remaining_files = []
    if os.path.exists(user_raw_dir):
        remaining_files = [f for f in os.listdir(user_raw_dir) if os.path.isfile(os.path.join(user_raw_dir, f))]

    if remaining_files:
        USER_PROCESSED_DIR = os.path.join(user_dir, "processed", "images")
        USER_INDICES_DIR = os.path.join(user_dir, "indices")
        USER_CHUNK_INDEX_PATH = os.path.join(USER_INDICES_DIR, "chunks")
        USER_DOC_INDEX_PATH = os.path.join(USER_INDICES_DIR, "docs")
        USER_IMAGE_INDEX_PATH = os.path.join(USER_INDICES_DIR, "images")

        rebuild_chunk_index = ChunkIndex()
        rebuild_doc_index = DocumentIndex()
        rebuild_image_store = ImageVectorStore()

        AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}

        for remaining_file in remaining_files:
            remaining_path = os.path.join(user_raw_dir, remaining_file)
            file_ext = os.path.splitext(remaining_file)[1].lower()

            try:
                if file_ext in AUDIO_EXTENSIONS:
                    transcript = ingest_audio(remaining_path)
                    if transcript and len(transcript.strip()) > 50:
                        chunk_size = 500
                        words = transcript.split()
                        current_chunk = ""
                        audio_chunks = []
                        for word in words:
                            if len(current_chunk) + len(word) + 1 > chunk_size and current_chunk:
                                audio_chunks.append(current_chunk.strip())
                                current_chunk = word
                            else:
                                current_chunk += " " + word
                        if current_chunk.strip():
                            audio_chunks.append(current_chunk.strip())
                        rebuild_doc_index.add_document(transcript, remaining_file)
                        rebuild_chunk_index.add_chunks(remaining_file, audio_chunks)
                else:
                    text_chunks, _ = ingest_pdf(remaining_path, USER_PROCESSED_DIR)
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
                            rebuild_doc_index.add_document(full_text, source)
                            rebuild_chunk_index.add_chunks(source, slide_chunks)

                    all_images = glob.glob(os.path.join(USER_PROCESSED_DIR, "*.png"))
                    pdf_basename = os.path.basename(remaining_path)
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
                        rebuild_image_store.add_images(new_images, image_metadata)
            except Exception as e:
                print(f"[{username}] Warning: failed to re-index {remaining_file}: {e}")

        rebuild_chunk_index.save_local(USER_CHUNK_INDEX_PATH)
        rebuild_doc_index.save_local(USER_DOC_INDEX_PATH)
        rebuild_image_store.save_local(USER_IMAGE_INDEX_PATH)

    return {"message": f"Deleted {filename}"}

# --- Conversation Management ---

@app.get("/conversations")
async def list_conversations(username: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, created_at, updated_at FROM conversations WHERE username = ? ORDER BY updated_at DESC",
        (username,)
    )
    rows = cursor.fetchall()
    conn.close()
    return {"conversations": [
        {"id": r[0], "title": r[1], "created_at": r[2], "updated_at": r[3]}
        for r in rows
    ]}

@app.post("/conversations")
async def create_conversation(username: str = Depends(get_current_user)):
    conv_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat() + "Z"
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO conversations (id, username, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
        (conv_id, username, "New Chat", now, now)
    )
    conn.commit()
    conn.close()
    return {"id": conv_id, "title": "New Chat", "created_at": now, "updated_at": now}

@app.delete("/conversations/{conv_id}")
async def delete_conversation(conv_id: str, username: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE conversation_id = ? AND username = ?", (conv_id, username))
    cursor.execute("DELETE FROM conversations WHERE id = ? AND username = ?", (conv_id, username))
    conn.commit()
    conn.close()
    return {"message": "Conversation deleted"}

@app.get("/conversations/{conv_id}/messages")
async def get_conversation_messages(conv_id: str, username: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT role, content, sources, images, timestamp FROM chat_messages WHERE conversation_id = ? AND username = ? ORDER BY id ASC",
        (conv_id, username)
    )
    rows = cursor.fetchall()
    conn.close()
    return {"messages": [
        {"role": r[0], "content": r[1], "sources": json.loads(r[2]), "images": json.loads(r[3]), "timestamp": r[4]}
        for r in rows
    ]}

class ChatMessage(BaseModel):
    conversation_id: str
    role: str
    content: str
    sources: list = []
    images: list = []
    timestamp: str

@app.post("/chat/history")
async def save_chat_message(message: ChatMessage, username: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO chat_messages (conversation_id, username, role, content, sources, images, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (message.conversation_id, username, message.role, message.content, json.dumps(message.sources), json.dumps(message.images), message.timestamp)
    )
    # Update conversation's updated_at
    cursor.execute(
        "UPDATE conversations SET updated_at = ? WHERE id = ?",
        (message.timestamp, message.conversation_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Saved"}

@app.post("/conversations/{conv_id}/generate-title")
async def generate_conversation_title(conv_id: str, request: dict = None, username: str = Depends(get_current_user)):
    # Get the message text from request body, or fall back to DB query
    message_text = None
    if request and "message" in request:
        message_text = request["message"]
    
    if not message_text:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT content FROM chat_messages WHERE conversation_id = ? AND username = ? AND role = 'user' ORDER BY id ASC LIMIT 1",
            (conv_id, username)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return {"title": "New Chat"}
        message_text = row[0]
    
    title = generate_title(message_text)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE conversations SET title = ? WHERE id = ? AND username = ?", (title, conv_id, username))
    conn.commit()
    conn.close()
    return {"title": title}

@app.delete("/chat/history")
async def clear_all_chat_history(username: str = Depends(get_current_user)):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM chat_messages WHERE username = ?", (username,))
    cursor.execute("DELETE FROM conversations WHERE username = ?", (username,))
    conn.commit()
    conn.close()
    return {"message": "All chat history cleared"}

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    from fastapi.responses import FileResponse
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(frontend_dist, "index.html"))