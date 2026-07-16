# 📚 AI-Powered Study Buddy

An AI-powered RAG (Retrieval-Augmented Generation) study assistant that helps engineering students learn from their own course materials — upload a PDF, DOCX, or TXT file, ask questions, generate quizzes and flashcards, and get personalized revision focus based on performance.

Built as a solo capstone project for an IBM MLOps/DevOps internship.

---

## Features

- Document ingestion — Upload PDF, DOCX, or TXT study materials
- Grounded Q&A — Ask questions and get answers sourced directly from your uploaded material, with page citations
- Reasoning & evaluation — Ask for explanations, evaluations, and analysis, not just fact lookup
- Conversation memory — Follow-up questions work naturally
- Web search fallback — When the document doesn't have an answer, the assistant searches the web and clearly labels sources
- Math & science support — Formulas render properly using LaTeX
- Quiz generation — MCQ, short-answer, and formula-recall question types, via natural language
- Flashcard generation — Front/back flashcards for quick review
- Adaptive weak-area tracking — biases future quizzes toward weak areas
- Progress tracking — ask "my progress" anytime

---

## Architecture

Streamlit (frontend, chat UI) -> HTTP -> FastAPI (backend) -> extract -> chunk -> embed -> ChromaDB -> retriever -> qa_chain / quiz -> Gemini

- Frontend: Streamlit
- Backend: FastAPI
- Vector store: ChromaDB (persistent, local)
- Embeddings: HuggingFace all-MiniLM-L6-v2
- LLM: Google Gemini (gemini-2.5-flash)
- Web search: Tavily API (fallback only)

---

## Tech Stack

Python, LangChain, ChromaDB, HuggingFace Embeddings, Google Gemini API, Tavily API, Streamlit, FastAPI, Docker

---

## Setup & Running

### Option 1 - Docker (recommended)

git clone https://github.com/poorab2309/AI-Powered-Study-Buddy-
cd study-buddy
copy .env.example .env
docker-compose up --build

Streamlit UI: http://localhost:8501
FastAPI docs: http://localhost:8000/docs

### Option 2 - Manual (local Python)

git clone https://github.com/poorab2309/AI-Powered-Study-Buddy-
cd study-buddy
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

Run in separate terminals:
uvicorn main:app
streamlit run app.py

### Required API Keys
- Google Gemini API key - aistudio.google.com (free tier)
- Tavily API key - tavily.com (free tier)

---

## Spec Coverage

Built against an official internship project catalog spec (AI-Powered Study Buddy for Engineering Students, EdTech/RAG/NLP, difficulty 3/5). All core objectives implemented: document ingestion, RAG knowledge base, LLM Q&A agent, quiz generation (MCQ/short-answer/formula-recall), flashcard generation, adaptive weak-area tracking.

---

## Known Limitations & Design Decisions

- Web search fallback extends beyond "strictly from source" per original spec - a deliberate design choice for usefulness, clearly labeled in the UI
- Gemini free-tier quota is limited (as low as 20 requests/day)
- Math/science extraction may be imperfect on formula-heavy scanned PDFs
- DOCX/TXT files use simulated page numbers (no native page concept)
- Single active document at a time - no multi-document cross-referencing yet

---

## Future Improvements

- Multi-document support
- Re-ranking / hybrid search
- OCR for scanned PDFs
- Persistent progress across sessions
- Streaming responses

---

## Author

Poorab Jain  - BTech Data Science, NorthCap University  - IBM MLOps/DevOps Internship Capstone, July 2026
