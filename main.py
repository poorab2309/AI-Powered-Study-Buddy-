import os
import uuid
import shutil
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional

from extract import extract_text
from chunker import chunk_pages
from embedder import build_vectorstore
from qa_chain import answer_question, generate_document_summary, SUMMARY_FILE
from quiz import (
    generate_quiz,
    generate_flashcards,
    record_quiz_results,
    reset_weak_areas,
    get_progress_summary,
)

app = FastAPI(title="AI-Powered Study Buddy API")

UPLOAD_DIR = "data"
CHROMA_DIR = "chroma_db"
CURRENT_COLLECTION_FILE = "current_collection.txt"
CURRENT_DOC_FILE = "current_document.txt"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


class ChatMessage(BaseModel):
    role: str
    content: str


class Question(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = []


class QuizRequest(BaseModel):
    topic: Optional[str] = ""
    num_questions: Optional[int] = 5
    question_type: Optional[str] = "mcq"  # 'mcq', 'short_answer', 'formula'


class FlashcardRequest(BaseModel):
    topic: Optional[str] = ""
    num_cards: Optional[int] = 8


class QuizResultItem(BaseModel):
    source_page: Optional[int] = None
    correct: bool


class QuizResults(BaseModel):
    results: List[QuizResultItem]


def has_active_document() -> bool:
    return os.path.exists(CURRENT_COLLECTION_FILE) and os.path.exists(SUMMARY_FILE)


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {
            "filename": file.filename,
            "status": "error",
            "message": f"Unsupported file type '{ext}'. Supported types: PDF, DOCX, TXT.",
        }

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        pages = extract_text(file_path)
    except Exception as e:
        return {
            "filename": file.filename,
            "status": "error",
            "message": f"Could not extract text: {e}",
        }

    if not pages:
        return {
            "filename": file.filename,
            "status": "error",
            "message": "No extractable text found in this file.",
        }

    collection_name = f"doc_{uuid.uuid4().hex[:12]}"

    chunks = chunk_pages(pages, source=file.filename)
    build_vectorstore(chunks, persist_dir=CHROMA_DIR, collection_name=collection_name)

    with open(CURRENT_COLLECTION_FILE, "w") as f:
        f.write(collection_name)
    with open(CURRENT_DOC_FILE, "w") as f:
        f.write(file.filename)

    full_text = "\n\n".join(text for _, text in pages)
    summary = generate_document_summary(full_text)
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        f.write(summary)

    reset_weak_areas()

    return {
        "filename": file.filename,
        "pages_extracted": len(pages),
        "chunks_created": len(chunks),
        "status": "success",
    }


@app.post("/ask")
async def ask_question(payload: Question):
    if not has_active_document():
        return {
            "answer": "No document has been uploaded yet. Please upload a file first.",
            "sources": [],
            "used_web_search": False,
        }

    history_dicts = [{"role": m.role, "content": m.content} for m in payload.history]
    result = answer_question(payload.question, history=history_dicts)
    return result


@app.post("/quiz")
async def create_quiz(payload: QuizRequest):
    if not has_active_document():
        return {
            "questions": [],
            "error": "No document has been uploaded yet. Please upload a file first.",
        }

    result = generate_quiz(
        topic=payload.topic,
        num_questions=payload.num_questions,
        question_type=payload.question_type,
    )
    return result


@app.post("/quiz-result")
async def submit_quiz_result(payload: QuizResults):
    results = [
        {"source_page": r.source_page, "correct": r.correct} for r in payload.results
    ]
    record_quiz_results(results)
    return {"status": "recorded"}


@app.post("/flashcards")
async def create_flashcards(payload: FlashcardRequest):
    if not has_active_document():
        return {
            "cards": [],
            "error": "No document has been uploaded yet. Please upload a file first.",
        }

    result = generate_flashcards(topic=payload.topic, num_cards=payload.num_cards)
    return result


@app.get("/progress")
async def progress():
    if not has_active_document():
        return {
            "total_questions_answered": 0,
            "correct": 0,
            "wrong": 0,
            "accuracy_percent": None,
            "weak_pages": [],
        }
    return get_progress_summary()


@app.get("/status")
async def status():
    if has_active_document():
        with open(CURRENT_DOC_FILE, "r") as f:
            filename = f.read().strip()
        return {"document_loaded": True, "filename": filename}
    return {"document_loaded": False, "filename": None}


@app.get("/")
async def root():
    return {"message": "Study Buddy API is running. See /docs for endpoints."}
