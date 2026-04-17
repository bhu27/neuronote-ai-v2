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
        
    # Convert query to embedding
    query_embedding = embedding_model.encode(query).tolist()
    
    # Retrieve top 3 similar chunks from ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=3
    )
    
    # Extract the retrieved text chunks (results are returned as a list of lists)
    retrieved_chunks = results.get("documents", [[]])[0]
    
    return {
        "query": query,
        "results": retrieved_chunks
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


class SummarizeRequest(BaseModel):
    text: str

@app.post("/summarize")
async def summarize_endpoint(request: SummarizeRequest):
    text = request.text.strip()

    if not text or len(text) < 50:
        return {
            "error": "Please provide valid PDF extracted text (minimum 50 characters required)"
        }
        
    prompt = f"""
You are an expert academic assistant designed for exam preparation.

You will be given extracted text from a PDF.

VERY IMPORTANT RULES:
- Use ONLY the provided text
- Do NOT add external knowledge
- Do NOT hallucinate
- If content is unclear or insufficient, respond:
  "Insufficient content to generate a proper summary."

You MUST follow this format exactly:

---

1. QUICK SUMMARY (5 bullet points)
- Capture the most important concepts
- Keep each bullet short and clear

2. SIMPLE EXPLANATION
- Explain the topic in very easy language
- Use short sentences
- Make it beginner friendly

3. EXAM REVISION NOTES
- Important definitions
- Key concepts likely to appear in exams
- Structured bullet points

---

TEXT:
{request.text}
"""

@app.post("/important-questions")
async def generate_questions(request: QuestionsRequest):
    if not request.text.strip():
        return {"error": "Text cannot be empty"}
        
    prompt = f"""You are an experienced professor parsing a textbook. Analyze the following text and generate exactly 10 important exam questions based on it.
Respond ONLY with a valid JSON object matching this exact format. Do not include markdown codeblocks or outer text.
{{
  "questions": [
    {{
      "question": "The formal exam question",
      "difficulty": "Easy", 
      "reason": "Explain why this tests a critical concept"
    }},
    {{
      "question": "Another question",
      "difficulty": "Hard",
      "reason": "..."
    }}
  ]
}}

Text:
{request.text}
"""
    
    response_text = call_openrouter(prompt)
    
    try:
        # Mistral and others occasionally return markdown markers despite instructions
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        return json.loads(clean_text.strip())
    except Exception as e:
        return {"error": "Failed to parse structured JSON from LLM", "raw_response": response_text}

class WeakTopicRequest(BaseModel):
    incorrect_answers: List[str]
    repeated_questions: List[str]

WEAK_TOPICS_FILE = "weak_topics.json"

@app.post("/analyze-weak-topics")
async def analyze_weak_topics(request: WeakTopicRequest):
    if not request.incorrect_answers and not request.repeated_questions:
        return {"error": "Must provide incorrect answers or repeated questions to analyze."}
        
    prompt = f"""You are an educational AI. Based on the following incorrect answers and frequently repeated questions by a student, identify their top 3 weak topics. 
Return ONLY a valid JSON object matching this exact format, with no markdown code blocks:
{{
    "weak_topics": [
        "Topic 1",
        "Topic 2",
        "Topic 3"
    ]
}}

Incorrect Answers:
{request.incorrect_answers}

Repeated Questions:
{request.repeated_questions}
"""
    
    response_text = call_openrouter(prompt)
    
    try:
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        topics_json = json.loads(clean_text.strip())
        
        # Store in local JSON file
        try:
            if os.path.exists(WEAK_TOPICS_FILE):
                with open(WEAK_TOPICS_FILE, "r") as f:
                    existing_data = json.load(f)
            else:
                existing_data = {"student_history": []}
                
            existing_data["student_history"].append({
                "incorrect_answers": request.incorrect_answers,
                "repeated_questions": request.repeated_questions,
                "identified_weak_topics": topics_json.get("weak_topics", [])
            })
            
            with open(WEAK_TOPICS_FILE, "w") as f:
                json.dump(existing_data, f, indent=4)
        except Exception as e:
            # Silently pass file writing errors to not break API return
            pass
            
        return topics_json
    except Exception as e:
        return {"error": "Failed to parse JSON identifying weak topics", "raw_response": response_text}

class FocusAreaRequest(BaseModel):
    important_topics: List[str]
    weak_topics: List[str]

@app.post("/focus-areas")
async def focus_areas_endpoint(request: FocusAreaRequest):
    prompt = f"""You are an educational AI guiding a student's study plan. Combine the following important course topics and the student's weak topics into a consolidated list of "Focus Areas".
Assign importance and weakness accurately based on the overlaps between the two lists. 
Format each string in the output list exactly like this example: "Neural Networks (High importance + weak)"

Return ONLY a valid JSON object matching this exact format, with no markdown code blocks or text outside it:
{{
    "focus_areas": [
        "Topic Name (Importance level + Weakness indication)"
    ]
}}

Important Topics:
{request.important_topics}

Student Weak Topics:
{request.weak_topics}
"""
    
    response_text = call_openrouter(prompt)
    
    try:
        clean_text = response_text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        elif clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]
            
        return json.loads(clean_text.strip())
    except Exception as e:
        return {"error": "Failed to parse JSON for focus areas", "raw_response": response_text}

class MindmapRequest(BaseModel):
    text: str

@app.post("/mindmap")
async def generate_mindmap(request: MindmapRequest):
    if not request.text.strip():
        return {"error": "Text cannot be empty"}
        
    prompt = f"""You are an educational AI. Create a hierarchical mindmap mapping core topics to subtopics based on the following text.
Output ONLY a plaintext tree structure using indentation (e.g., using hyphens, asterisks, or plus signs to show depth). Do not include any JSON or conversational filler.

Example Format:
- Main Topic
  - Subtopic A
    - Detail 1
    - Detail 2
  - Subtopic B

Text:
{request.text}
"""
    
    response_text = call_openrouter(prompt)
    
    return {
        "mindmap_tree": response_text.strip()
    }

class TTSRequest(BaseModel):
    text: str


