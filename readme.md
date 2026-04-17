NeuroNote AI AI-powered assistant that converts PDFs into interactive study tools using a RAG-based system

Features:
PDF Intelligence: Upload PDFs, extract and chunk text for retrieval
RAG Chat: Ask questions with answers grounded in document content
Summarization: 5-point summaries, simple explanations, revision notes
Mind Maps: Visual representation of topic hierarchies
Question Predictor (USP): Identifies high- and medium-probability exam questions

Architecture
PDF → Text Extraction → Chunking → Embeddings → Vector DB  
→ RAG Retrieval → AI Features (Chat, Summary, Mind Map, Question Prediction)

Tech Stack
Frontend: React / Next.js
Backend: FastAPI
AI Models: OpenRouter
Vector Database: Chroma
PDF Processing: PyPDF / pdfplumber
Embeddings: Sentence Transformers

How It Works
Upload PDF
Extract, chunk, and generate embeddings
Store in vector database
User interacts via chat, summaries, mind maps, and question prediction
AI retrieves context and generates responses

Demo Flow
Upload PDF → Ask questions → Generate summary → View mind map → Get important questions

Why This Project
Converts static PDFs into interactive learning tools
Combines retrieval, reasoning, and prediction
Improves study efficiency


Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

Frontend
cd frontend
npm install
npm start