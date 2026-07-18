"""
8. API Design
--------------
Free stack: FastAPI + Uvicorn — pip install fastapi uvicorn python-multipart

Run locally (from inside the ai-ml/ folder):
    uvicorn ingestion.main:app --reload

Endpoints:
  POST /ingest/pdf       (multipart file upload)
  POST /ingest/youtube   ({"url": "..."})
  POST /ingest/article   ({"url": "..."})
"""

import shutil
import tempfile
import os

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

from ingestion.pdf.extractor import ingest_pdf
from ingestion.youtube.transcript import ingest_youtube
from ingestion.web.scraper import ingest_article


app = FastAPI(title="StudyMind AI - Content Ingestion Pipeline")


class URLRequest(BaseModel):
    url: str


# -----------------------------
# PDF INGESTION
# -----------------------------
@app.post("/ingest/pdf")
async def ingest_pdf_endpoint(file: UploadFile = File(...)):

    # Validate file type
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="File must be a PDF"
        )

    # Save uploaded PDF temporarily
    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".pdf"
    ) as tmp:

        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Run PDF ingestion pipeline
        result = ingest_pdf(
            file_path=tmp_path,
            original_filename=file.filename
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        # Remove temporary file after processing
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return result


# -----------------------------
# YOUTUBE INGESTION
# -----------------------------
@app.post("/ingest/youtube")
async def ingest_youtube_endpoint(payload: URLRequest):

    try:
        result = ingest_youtube(payload.url)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return result


# -----------------------------
# ARTICLE INGESTION
# -----------------------------
@app.post("/ingest/article")
async def ingest_article_endpoint(payload: URLRequest):

    try:
        result = ingest_article(payload.url)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    return result


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.get("/")
async def root():

    return {
        "status": "ok",
        "service": "StudyMind AI Content Ingestion Pipeline"
    }