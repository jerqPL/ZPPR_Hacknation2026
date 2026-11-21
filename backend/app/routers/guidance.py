from fastapi import APIRouter
from app.models.guidance import OfficialLink, RiskItem, SupportOrganization
from app.services import guidance_service

router = APIRouter(prefix="/guidance", tags=["Ryzyka, wsparcie i oficjalne źródła"])


@router.get("/risks", response_model=list[RiskItem])
def list_risks():
    return guidance_service.get_risks()


@router.get("/support-organizations", response_model=list[SupportOrganization])
def list_support_organizations():
    return guidance_service.get_support_organizations()


@router.get("/official-links", response_model=list[OfficialLink])
def list_official_links():
    return guidance_service.get_official_links()
