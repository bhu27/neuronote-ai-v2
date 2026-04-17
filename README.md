# NeuroNote AI
AI-powered assistant that converts PDFs into interactive study tools using a RAG-based system.
---
## Features

* **PDF Intelligence**
  Upload PDFs, extract and chunk text for retrieval
* **RAG Chat**
  Ask questions with answers grounded in document content
* **Summarization**
  * 5-point summaries
  * Simple explanations
  * Revision notes
* **Mind Maps**
  Visual representation of topic hierarchies
* **Question Predictor (USP)**
  Identifies high- and medium-probability exam questions
---
## Architecture

```id="9qg9s1"
PDF → Text Extraction → Chunking → Embeddings → Vector DB  
→ RAG Retrieval → AI Features (Chat, Summary, Mind Map, Question Prediction)
```

---
## Tech Stack

* **Frontend:** React / Next.js
* **Backend:** FastAPI
* **AI Models:** OpenRouter
* **Vector Database:** Chroma
* **PDF Processing:** PyPDF / pdfplumber
* **Embeddings:** Sentence Transformers

---

## How It Works

1. Upload PDF
2. Extract, chunk, and generate embeddings
3. Store in vector database
4. User interacts via:

   * Chat
   * Summaries
   * Mind maps
   * Question prediction
5. AI retrieves context and generates responses

---

## Demo Flow

Upload PDF → Ask questions → Generate summary → View mind map → Get important questions

---

## Why This Project

* Converts static PDFs into interactive learning tools
* Combines retrieval, reasoning, and prediction
* Improves study efficiency

---

## Setup Instructions

### Backend

```bash id="dn17mo"
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend

```bash id="6uhgjo"
cd frontend
npm install
npm start
```

