from pathlib import Path
from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from fastapi.responses import Response
from app.models.calculator import InsuranceTitle
from app.models.guidance import (
    CaseDocumentsAnalysisResult,
    DocumentGuidanceResponse,
    PdfAnalysisResult,
    SampleCase,
)
from app.models.simulation import ApplicationSubmissionRequest, ApplicationSubmissionResponse
from app.services import document_service, pdf_parser_service
from app.services.parameter_store import parameter_store

router = APIRouter(prefix="/documents", tags=["Dokumenty, wnioski i testy PDF"])


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


@router.post("/analyze-pdf", response_model=PdfAnalysisResult)
async def analyze_pdf(file: UploadFile = File(...)):
    filename = _validate_document_extension(file.filename)
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Plik przekracza limit 10 MB.")
    return pdf_parser_service.analyze_pdf_bytes(filename, content)


@router.post("/analyze-case", response_model=CaseDocumentsAnalysisResult)
async def analyze_case(files: list[UploadFile] = File(...)):
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
    return pdf_parser_service.analyze_case_documents(payloads)
