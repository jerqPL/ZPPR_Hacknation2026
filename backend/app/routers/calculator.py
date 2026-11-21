from fastapi import APIRouter
from app.models.calculator import (
    IntegratedCalculatorRequest,
    IntegratedCalculatorResponse,
    PregnancyBenefitRequest,
    PregnancyBenefitResponse,
)
from app.services.calculator_service import (
    calculate_integrated_maternity,
    calculate_pregnancy_benefit,
)
from app.services.parameter_store import parameter_store

router = APIRouter(prefix="/calculator", tags=["Kalkulatory zasiłkowe"])


@router.post("/pregnancy", response_model=PregnancyBenefitResponse)
def calc_pregnancy(req: PregnancyBenefitRequest):
    return calculate_pregnancy_benefit(req, parameter_store.get())


@router.post("/integrated", response_model=IntegratedCalculatorResponse)
def calc_integrated(req: IntegratedCalculatorRequest):
    return calculate_integrated_maternity(req, parameter_store.get())
