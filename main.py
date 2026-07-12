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
from quiz import generate_quiz

app = FastAPI(title="AI-Powered Study Buddy API")

UPLOAD_DIR = "data"
CHROMA_DIR = "chroma_db"
CURRENT_COLLECTION_FILE = "current_collection.txt"
CURRENT_DOC_FILE = "current_document.txt"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class ChatMessage(BaseModel):
    role: str
    content: str


class Question(BaseModel):
    question: str
    history: Optional[List[ChatMessage]] = []


class QuizRequest(BaseModel):
    topic: Optional[str] = ""
    num_questions: Optional[int] = 5


def has_active_document() -> bool:
    return os.path.exists(CURRENT_COLLECTION_FILE) and os.path.exists(SUMMARY_FILE)


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    pages = extract_text(file_path)

    if not pages:
        return {
            "filename": file.filename,
            "status": "error",
            "message": "No extractable text found in this PDF. It may be a scanned document without a text layer.",
        }

    # unique collection per upload -- avoids Windows file-lock issues entirely
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
            "answer": "No document has been uploaded yet. Please upload a PDF first.",
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
            "error": "No document has been uploaded yet. Please upload a PDF first.",
        }

    result = generate_quiz(topic=payload.topic, num_questions=payload.num_questions)
    return result


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
