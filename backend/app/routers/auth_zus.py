from fastapi import APIRouter
from app.models.simulation import (
    DebtStatusResponse,
    EzlaCertificate,
    LoginRequest,
    LoginResponse,
    PueInquiryRequest,
    PueInquiryResponse,
    SimulatedUserProfile,
)
from app.services import zus_mock_service

router = APIRouter(tags=["Symulacja mObywatel / ZUS / PUE"])


@router.get("/auth/personas", response_model=list[SimulatedUserProfile])
def get_personas():
    return zus_mock_service.list_personas()


@router.post("/auth/mobywatel/login", response_model=LoginResponse)
def mobywatel_login(req: LoginRequest):
    return zus_mock_service.simulate_mobywatel_login(req.persona_id)


@router.get("/zus/profile/{persona_id}", response_model=SimulatedUserProfile)
def get_zus_profile(persona_id: str):
    return zus_mock_service.get_profile(persona_id)


@router.get("/zus/ezla/{persona_id}", response_model=list[EzlaCertificate])
def get_zus_ezla(persona_id: str):
    return zus_mock_service.get_ezla_list(persona_id)


@router.get("/zus/debt/{persona_id}", response_model=DebtStatusResponse)
def get_zus_debt(persona_id: str):
    return zus_mock_service.get_debt_status(persona_id)


@router.post("/zus/pue/inquiry", response_model=PueInquiryResponse)
def create_pue_inquiry(req: PueInquiryRequest):
    return zus_mock_service.submit_pue_inquiry(req)
