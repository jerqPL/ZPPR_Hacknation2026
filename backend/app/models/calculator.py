from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class InsuranceTitle(str, Enum):
    UOP = "uop"  # Umowa o pracę (obowiązkowe ubezpieczenie chorobowe)
    ZLECENIE = "zlecenie"  # Umowa zlecenie (dobrowolne ubezpieczenie chorobowe)
    JDG = "jdg"  # Działalność gospodarcza (dobrowolne ubezpieczenie chorobowe)
    NONE = "none"  # Brak ubezpieczenia chorobowego


class BenefitScenario(str, Enum):
    BIRTH = "birth"  # Poród (rodzice biologiczni)
    ADOPTION = "adoption"  # Przysposobienie (adopcja)
    FOSTER = "foster"  # Rodzina zastępcza niezawodowa


class PaymentVariant(str, Enum):
    STANDARD_100_70 = "100_70"  # 100% macierzyński + 70% rodzicielski
    COMBINED_81_5 = "81_5"  # 81,5% za całość (wniosek w ciągu 21 dni po porodzie)


class PregnancyBenefitRequest(BaseModel):
    insurance_title: InsuranceTitle = InsuranceTitle.UOP
    has_voluntary_sickness_insurance: bool = True
    insurance_days: int = Field(180, ge=0, description="Liczba dni nieprzerwanego ubezpieczenia chorobowego")
    gross_monthly_salary: float = Field(6500.0, ge=0)
    custom_benefit_base: Optional[float] = Field(None, ge=0)
    has_code_b: bool = True
    age_over_50: bool = False
    employer_insured_count: int = Field(25, ge=0)
    employment_terminated_special: bool = False
    termination_reason: Optional[str] = Field(
        None,
        description="np. 'bankruptcy_liquidation', 'employer_death', 'unlawful_termination_court_ruling'",
    )


class PregnancyBenefitResponse(BaseModel):
    eligible_sickness_benefit: bool
    eligible_maternity_equivalent: bool
    waiting_period_required_days: int
    waiting_period_met: bool
    benefit_rate_percent: float
    benefit_base_monthly: float
    daily_benefit_gross: float
    monthly_benefit_gross: float
    max_benefit_days: int
    employer_pay_days: int
    payer: str
    warnings: list[str]
    summary: str


class IntegratedCalculatorRequest(BaseModel):
    scenario: BenefitScenario = BenefitScenario.BIRTH
    insurance_title: InsuranceTitle = InsuranceTitle.UOP
    has_sickness_insurance_on_birth_date: bool = True
    children_count: int = Field(1, ge=1, le=6)
    child_age_years: Optional[float] = Field(None, ge=0, le=18)
    foster_deferred_school: bool = False
    has_za_zyciem_certificate: bool = False

    # Wcześniak / hospitalizacja -> uzupełniający urlop macierzyński
    premature_or_hospitalized: bool = False
    gestation_week: Optional[int] = Field(None, ge=20, le=42)
    birth_weight_grams: Optional[int] = Field(None, ge=300, le=6000)
    hospitalization_weeks: int = Field(0, ge=0, le=20)

    # Podstawa wymiaru
    gross_monthly_salary: float = Field(7000.0, ge=0)
    custom_benefit_base: Optional[float] = Field(None, ge=0)
    second_parent_gross_salary: Optional[float] = Field(None, ge=0)
    second_parent_custom_base: Optional[float] = Field(None, ge=0)

    # Wariant wypłaty i podział między rodziców
    payment_variant: PaymentVariant = PaymentVariant.COMBINED_81_5
    mother_maternity_weeks: Optional[int] = Field(None, ge=0)
    father_takes_parental_weeks: int = Field(9, ge=0)
    father_takes_paternity_leave: bool = True

    # Łączenie urlopu rodzicielskiego z pracą
    combine_parental_with_work: bool = False
    work_fte_fraction: float = Field(0.0, ge=0.0, le=0.5)
    combined_work_weeks: int = Field(0, ge=0)

    # Płatnik
    employer_insured_count: int = Field(25, ge=0)


class LeaveBreakdownItem(BaseModel):
    label: str
    parent: str  # "Matka" / "Ojciec" / "Rodzic adopcyjny/zastępczy"
    weeks: float
    rate_percent: float
    monthly_gross_pln: float
    total_gross_pln: float
    notes: Optional[str] = None


class IntegratedCalculatorResponse(BaseModel):
    eligible: bool
    ineligibility_reason: Optional[str] = None
    benefit_base_parent1: float
    benefit_base_parent2: float
    total_weeks: float
    maternity_weeks: int
    supplementary_maternity_weeks: int
    parental_weeks_total: float
    parental_weeks_extended_by_work: float
    paternity_weeks: int
    payer: str
    breakdown: list[LeaveBreakdownItem]
    total_estimated_gross_pln: float
    warnings: list[str]
    required_documents: list[str]
