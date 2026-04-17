import os
import json
import uuid
from typing import List
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LAST_UPLOADED_TEXT = ""

class SummarizeRequest(BaseModel):
    pass

class ChatRequest(BaseModel):
    question: str


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

    filename = file.filename  # ✅ FIX: safe reuse

    file_path = os.path.join(UPLOAD_DIR, filename)

    # Save file
    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    # Extract text
    extracted_text = ""

    try:
        reader = pypdf.PdfReader(file_path)

        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"

    except Exception as e:
        return {"error": f"PDF read failed: {str(e)}"}

    extracted_text = extracted_text.strip()

    if not extracted_text:
        return {"error": "No text found in PDF"}

    # =========================
    # 🔹 CHUNK STORAGE (RAG)
    # =========================
    chunks = chunk_text(extracted_text)

    if chunks:
        chunk_embeddings = embedding_model.encode(chunks).tolist()

        chunk_ids = [f"{filename}_chunk_{i}" for i in range(len(chunks))]

        chunk_metadata = [
            {
                "filename": filename,
                "type": "chunk"
            }
            for _ in chunks
        ]

        collection.add(
            documents=chunks,
            embeddings=chunk_embeddings,
            ids=chunk_ids,
            metadatas=chunk_metadata
        )

    # =========================
    # 🔹 FULL TEXT STORAGE (SUMMARY + MINDMAP)
    # =========================
    full_id = f"{filename}_full"

    full_embedding = embedding_model.encode(
        " ".join(extracted_text.split()[:4000])  # safe limit
    ).tolist()

    collection.add(
        documents=[extracted_text],
        embeddings=[full_embedding],
        ids=[full_id],
        metadatas=[{
            "filename": filename,
            "type": "full_pdf"
        }]
    )

    return {
        "message": "Upload successful",
        "chunks": len(chunks),
        "text_length": len(extracted_text)
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


@app.get("/summarize")
async def summarize_pdf(mode: str = "quick"):

    # 1. Get full PDF from DB
    results = collection.get(where={"type": "full_pdf"})
    docs = results.get("documents", [])

    if not docs:
        return {"error": "No PDF found. Please upload first."}

    full_text = docs[-1] if docs else ""

    if not full_text.strip() or len(full_text.strip()) < 50:
        return {"error": "PDF too small to summarize."}

    # 2. Limit size (VERY IMPORTANT)
    full_text = " ".join(full_text.split()[:4000])

    # 3. Strong prompt control (IMPORTANT FIX)
    prompt = f"""
You are an expert academic assistant.

MODE: {mode}

YOU MUST FOLLOW MODE STRICTLY:

- quick → ONLY 5 bullet points
- exam → structured exam notes with headings + key definitions
- beginner → simple explanation with examples

RULES:
- Follow ONLY the selected mode
- Do NOT mix modes
- Do NOT add extra information outside the mode

TEXT:
{full_text}
"""

    # 4. Call LLM
    result = call_openrouter(prompt)

    return {
        "status": "success",
        "mode": mode,
        "summary": result
    }

@app.get("/mindmap")
async def generate_mindmap():

    # 1. Get full PDF
    results = collection.get(where={"type": "full_pdf"})
    docs = results.get("documents", [])

    if not docs:
        return {"error": "No PDF found. Please upload first."}

    full_text = docs[-1]

    if len(full_text.strip()) < 50:
        return {"error": "PDF too small to generate mindmap."}

    # 2. Trim text
    trimmed_text = " ".join(full_text.split()[:4000])

    # 3. Prompt
    prompt = f"""
You are a mind map generator.

Convert the text into a hierarchical mind map.

STRICT RULES:
- ONLY valid JSON
- NO markdown
- NO explanation
- NO extra text

FORMAT:
{{
  "topic": "Main Topic",
  "subtopics": [
    {{
      "name": "Subtopic",
      "points": ["point1", "point2"]
    }}
  ]
}}

TEXT:
{trimmed_text}
"""

    # 4. Call LLM
    result_text = call_openrouter(prompt)

    # 5. Clean response
    result_text = result_text.replace("```json", "").replace("```", "")

    try:
        result_json = json.loads(result_text)
    except:
        result_json = {"raw": result_text}

    return {
        "status": "success",
        "mindmap": result_json
    }

