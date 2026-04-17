import os
import json
import uuid
from typing import List
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
import pypdf
from gtts import gTTS
from sentence_transformers import SentenceTransformer
import chromadb
import requests
from dotenv import load_dotenv

load_dotenv()

# Create an instance of the FastAPI application
app = FastAPI()

# Initialize SentenceTransformer model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

# Initialize local persistent ChromaDB client
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="pdf_chunks")

# Define a GET endpoint at the root path ("/")
@app.get("/")
async def root():
    return {"message": "Backend is running"}

# ensure the uploads directory exists
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ensure the audio output directory exists
AUDIO_DIR = "audio_outputs"
os.makedirs(AUDIO_DIR, exist_ok=True)

def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Splits text into chunks of `chunk_size` words with `overlap` words."""
    words = text.split()
    chunks = []
    
    if not words:
        return chunks
        
    for i in range(0, len(words), chunk_size - overlap):
        chunk_words = words[i:i + chunk_size]
        chunks.append(" ".join(chunk_words))
        
        # Break if we've reached the end of the text
        if i + chunk_size >= len(words):
            break
            
    return chunks

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    # Save the file locally
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    # Extract text using PyPDF
    extracted_text = ""
    try:
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"
    except Exception as e:
        return {"filename": file.filename, "error": f"Failed to extract PDF text: {str(e)}"}
        
    # Split the extracted text into chunks
    text_content = extracted_text.strip()
    chunks = chunk_text(text_content)
    
    if chunks:
        # Convert text chunks to embeddings
        embeddings = embedding_model.encode(chunks).tolist()
        
        # Create unique IDs and metadata for each chunk
        ids = [f"{file.filename}_chunk_{i}" for i in range(len(chunks))]
        metadatas = [{"filename": file.filename} for _ in range(len(chunks))]
        
        # Store embeddings locally in ChromaDB
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
        
    return {
        "filename": file.filename,
        "total_chunks": len(chunks),
        "message": "Text successfully extracted, embedded, and stored in ChromaDB."
    }

@app.get("/search")
async def search(query: str):
    if not query.strip():
        return {"error": "Query cannot be empty"}

    query_embedding = embedding_model.encode(query).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=8  # get more for better filtering
    )

    docs = results.get("documents", [[]])[0]
    distances = results.get("distances", [[]])[0]

    if not docs:
        return {
            "query": query,
            "results": [],
            "message": "No relevant content found in uploaded PDFs"
        }

    # Pair + sort by relevance (lower distance = better match)
    paired = sorted(zip(docs, distances), key=lambda x: x[1])

    response = []
    seen = set()

    # Take top relevant unique chunks
    for doc, dist in paired:
        if doc in seen:
            continue
        seen.add(doc)

        # skip weak matches (important improvement)
        if dist > 1.2:
            continue

        cleaned = doc.strip().replace("\n", " ")
        cleaned = " ".join(cleaned.split())  # remove extra spaces

        short_snippet = cleaned[:300] + "..." if len(cleaned) > 300 else cleaned

        response.append({
            "snippet": short_snippet,
            "score": round(float(dist), 3)
        })

        if len(response) == 3:
            break

    if not response:
        return {
            "query": query,
            "results": [],
            "message": "No strong matches found in your PDF"
        }

    return {
        "query": query,
        "results": response
    }




def call_openrouter(prompt: str) -> str:
    """Calls OpenRouter API using mistralai/mistral-7b-instruct"""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return "Error: OPENROUTER_API_KEY missing in .env"
        
    response = requests.post(
        url="https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json={
            "model": "meta-llama/llama-3-8b-instruct",
            "messages": [{"role": "user", "content": prompt}]
        }
    )
    
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    return f"Error API Call Failed: {response.status_code} - {response.text}"

class ChatRequest(BaseModel):
    question: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    if not request.question.strip():
        return {"error": "Question cannot be empty"}
        
    # 1. Convert question to embedding
    query_embedding = embedding_model.encode(request.question).tolist()
    
    # 2. Retrieve top 3 chunks + scores
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )
    
    retrieved_chunks = results.get("documents", [[]])[0]
    scores = results.get("distances", [[]])[0]
    
    # ✅ 3. ADD THIS (VERY IMPORTANT)
    if not scores or scores[0] > 1.2:
        return {
            "answer": "This question is not related to the uploaded PDF"
        }
    
    # 4. Create strict prompt
    context_text = "\n\n".join(retrieved_chunks)
    
    prompt = f"""
You are a strict AI assistant.

Answer ONLY using the provided context.
Do NOT include page numbers or extra formatting.
Give a short, clear explanation (3-4 lines).

If the answer is not present, respond ONLY:
"This question is not related to the uploaded PDF."

Context:
{context_text}

Question:
{request.question}
"""
    
    # 5. Call LLM
    answer = call_openrouter(prompt)
    
    # 6. Return response
    return {
        "question": request.question,
        "answer": answer
    }


