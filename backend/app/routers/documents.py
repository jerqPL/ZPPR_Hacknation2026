from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from app.models.calculator import InsuranceTitle
from app.models.guidance import DocumentGuidanceResponse, PdfAnalysisResult, SampleCase
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


@router.get("/sample-cases", response_model=list[SampleCase])
def get_sample_cases():
    return pdf_parser_service.list_sample_cases()


@router.post("/analyze-pdf", response_model=PdfAnalysisResult)
async def analyze_pdf(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Dozwolone są wyłącznie pliki PDF.")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Plik przekracza limit 10 MB.")
    return pdf_parser_service.analyze_pdf_bytes(file.filename, content)
