import os
import shutil
from fastapi import FastAPI, UploadFile, File
from pydantic import BaseModel

from extract import extract_text
from chunker import chunk_pages
from embedder import build_vectorstore
from qa_chain import answer_question

app = FastAPI(title="AI-Powered Study Buddy API")

UPLOAD_DIR = "data"
os.makedirs(UPLOAD_DIR, exist_ok=True)


class Question(BaseModel):
    question: str


@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """
    Accepts a PDF upload, runs the full ingestion pipeline:
    extract -> chunk -> embed -> store in ChromaDB.
    """
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # save the uploaded file to disk first
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # run the pipeline
    pages = extract_text(file_path)
    chunks = chunk_pages(pages, source=file.filename)
    build_vectorstore(chunks)  # re-embeds into the same persistent chroma_db

    return {
        "filename": file.filename,
        "pages_extracted": len(pages),
        "chunks_created": len(chunks),
        "status": "success",
    }


@app.post("/ask")
async def ask_question(payload: Question):
    """
    Accepts a question, returns a grounded answer from the uploaded material.
    """
    result = answer_question(payload.question)
    return {"answer": result["answer"], "sources": result["sources"]}


@app.get("/")
async def root():
    return {"message": "Study Buddy API is running. See /docs for endpoints."}
