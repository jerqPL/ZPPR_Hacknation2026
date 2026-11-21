from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import threading
import time
import uuid
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from app.models.calculator import InsuranceTitle
from app.models.guidance import (
    CaseDocumentsAnalysisResult,
    DocumentAnalysisJobStatus,
    DocumentGuidanceResponse,
    PdfAnalysisResult,
    SampleCase,
)
from app.models.simulation import ApplicationSubmissionRequest, ApplicationSubmissionResponse
from app.services import document_service, pdf_parser_service
from app.services.parameter_store import parameter_store

router = APIRouter(prefix="/documents", tags=["Dokumenty, wnioski i testy PDF"])

_OCR_JOBS: dict[str, tuple[float, DocumentAnalysisJobStatus]] = {}
_OCR_JOBS_LOCK = threading.Lock()
_OCR_JOB_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix="zppr-ocr")
_MAX_STORED_JOBS = 50
_JOB_TTL_SECONDS = 1800.0


def _prune_old_jobs() -> None:
    now = time.monotonic()
    with _OCR_JOBS_LOCK:
        expired = [jid for jid, (ts, _) in _OCR_JOBS.items() if now - ts > _JOB_TTL_SECONDS]
        for jid in expired:
            _OCR_JOBS.pop(jid, None)
        while len(_OCR_JOBS) > _MAX_STORED_JOBS:
            oldest_id = min(_OCR_JOBS.items(), key=lambda item: item[1][0])[0]
            _OCR_JOBS.pop(oldest_id, None)


def _update_job(job_id: str, **updates) -> None:
    with _OCR_JOBS_LOCK:
        entry = _OCR_JOBS.get(job_id)
        if not entry:
            return
        ts, cur = entry
        _OCR_JOBS[job_id] = (ts, cur.model_copy(update=updates))


@router.get("/guidance", response_model=DocumentGuidanceResponse)
def documents_guidance(
    insurance_title: InsuranceTitle = Query(InsuranceTitle.UOP),
    employer_insured_count: int = Query(25, ge=0),
):
    return document_service.get_document_guidance(
        insurance_title, employer_insured_count, parameter_store.get()
    )


@router.post("/submit", response_model=ApplicationSubmissionResponse)
def submit_application(req: ApplicationSubmissionRequest):
    return document_service.simulate_application_submission(req)


@router.post("/pdf")
def download_application_pdf(req: ApplicationSubmissionRequest):
    ref, pdf_bytes = document_service.generate_application_pdf(req, parameter_store.get())
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{ref}.pdf"'},
    )


@router.get("/sample-cases", response_model=list[SampleCase])
def get_sample_cases():
    return pdf_parser_service.list_sample_cases()


def _validate_document_extension(filename: str | None) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Brak nazwy przesłanego pliku.")
    ext = Path(filename).suffix.lower()
    if ext not in pdf_parser_service.SUPPORTED_DOCUMENT_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Dozwolone są wyłącznie pliki PDF oraz obrazy/skany (PNG, JPG, WEBP, TIFF).",
        )
    return filename


async def _read_case_payloads(files: list[UploadFile]) -> list[tuple[str, bytes]]:
    if not files:
        raise HTTPException(status_code=400, detail="Prześlij co najmniej jeden plik dokumentu.")
    if len(files) > 10:
        raise HTTPException(status_code=400, detail="Maksymalnie można przesłać 10 dokumentów w jednej sprawie.")
    payloads: list[tuple[str, bytes]] = []
    total_bytes = 0
    for f in files:
        filename = _validate_document_extension(f.filename)
        content = await f.read()
        if len(content) > 10 * 1024 * 1024:
            raise HTTPException(status_code=400, detail=f"Plik '{filename}' przekracza limit 10 MB.")
        total_bytes += len(content)
        if total_bytes > 25 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="Łączny rozmiar plików w sprawie przekracza limit 25 MB.")
        payloads.append((filename, content))
    return payloads


@router.post("/analyze-pdf", response_model=PdfAnalysisResult)
async def analyze_pdf(file: UploadFile = File(...)):
    filename = _validate_document_extension(file.filename)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Plik przekracza limit 10 MB.")
    return await pdf_parser_service.analyze_pdf_bytes_async(filename, content)


@router.post("/analyze-case", response_model=CaseDocumentsAnalysisResult)
async def analyze_case(files: list[UploadFile] = File(...)):
    payloads = await _read_case_payloads(files)
    return await pdf_parser_service.analyze_case_documents_async(payloads)


@router.post("/analyze-case-async", response_model=DocumentAnalysisJobStatus)
async def analyze_case_async(files: list[UploadFile] = File(...)):
    """Uruchamia analizę OCR (wszystkie strony, bez limitu) asynchronicznie w tle i natychmiast zwraca job_id."""
    payloads = await _read_case_payloads(files)
    _prune_old_jobs()

    job_id = uuid.uuid4().hex
    initial = DocumentAnalysisJobStatus(
        job_id=job_id,
        status="queued",
        files_total=len(payloads),
        files_processed=0,
        current_file=payloads[0][0] if payloads else None,
        pages_processed=0,
        pages_total=0,
    )
    with _OCR_JOBS_LOCK:
        _OCR_JOBS[job_id] = (time.monotonic(), initial)

    def _on_progress(files_done: int, files_total: int, current_file: str, done_pages: int, total_pages: int) -> None:
        _update_job(
            job_id,
            status="processing",
            files_processed=files_done,
            files_total=files_total,
            current_file=current_file,
            pages_processed=done_pages,
            pages_total=total_pages,
        )

    def _run_job_sync() -> None:
        _update_job(job_id, status="processing")
        try:
            result = pdf_parser_service.analyze_case_documents(
                payloads,
                progress_cb=_on_progress,
            )
            _update_job(
                job_id,
                status="completed",
                files_processed=len(payloads),
                pages_processed=result.merged.extracted_fields.ocr_pages_processed or result.merged.extracted_fields.page_count,
                pages_total=result.merged.extracted_fields.page_count,
                result=result,
            )
        except Exception as exc:
            _update_job(job_id, status="failed", error=f"Błąd analizy OCR: {exc}")

    _OCR_JOB_EXECUTOR.submit(_run_job_sync)
    return initial


@router.get("/jobs/{job_id}", response_model=DocumentAnalysisJobStatus)
async def get_document_analysis_job(job_id: str):
    """Zwraca bieżący postęp (strony/pliki) oraz wynik asynchronicznego zadania OCR."""
    with _OCR_JOBS_LOCK:
        entry = _OCR_JOBS.get(job_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Nie znaleziono zadania analizy OCR o podanym identyfikatorze.")
    return entry[1]
