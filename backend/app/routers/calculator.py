from fastapi import APIRouter
from app.models.calculator import (
    IndividualBaseCalculationRequest,
    IndividualBaseCalculationResponse,
    IntegratedCalculatorRequest,
    IntegratedCalculatorResponse,
    PregnancyBenefitRequest,
    PregnancyBenefitResponse,
)
from app.services.calculator_service import (
    calculate_individual_benefit_base,
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


@router.post("/benefit-base", response_model=IndividualBaseCalculationResponse)
def calc_individual_base(req: IndividualBaseCalculationRequest):
    return calculate_individual_benefit_base(req, parameter_store.get())

