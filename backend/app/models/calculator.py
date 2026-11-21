from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, model_validator


class InsuranceTitle(str, Enum):
    UOP = "uop"  # Umowa o pracę (obowiązkowe ubezpieczenie chorobowe)
    ZLECENIE = "zlecenie"  # Umowa zlecenie (dobrowolne ubezpieczenie chorobowe)
    JDG = "jdg"  # Działalność gospodarcza (dobrowolne ubezpieczenie chorobowe)
    NONE = "none"  # Brak ubezpieczenia chorobowego


class BenefitScenario(str, Enum):
    BIRTH = "birth"  # Poród (rodzice biologiczni)
    ADOPTION = "adoption"  # Przysposobienie (adopcja)
    FOSTER = "foster"  # Rodzina zastępcza (niezawodowa / zawodowa)


class FosterFamilyType(str, Enum):
    NON_PROFESSIONAL = "non_professional"  # Rodzina zastępcza niezawodowa / spokrewniona
    PROFESSIONAL = "professional"  # Rodzina zastępcza zawodowa (wyłączona z art. 183 § 1 KP)


class PaymentVariant(str, Enum):
    STANDARD_100_70 = "100_70"  # 100% macierzyński + 70% rodzicielski
    COMBINED_81_5 = "81_5"  # 81,5% za całość (wniosek/deklaracja w ciągu 21 dni po porodzie)


class TerminationReason(str, Enum):
    BANKRUPTCY_LIQUIDATION = "bankruptcy_liquidation"
    EMPLOYER_DEATH = "employer_death"
    UNLAWFUL_TERMINATION_COURT_RULING = "unlawful_termination_court_ruling"
    POST_EMPLOYMENT_ART7 = "post_employment_art7"


class WaitingPeriodExemptionReason(str, Enum):
    NONE = "none"
    MANDATORY_10_YEARS = "mandatory_10_years"  # Art. 4 ust. 3 pkt 3 (wyłącznie ubezpieczeni obowiązkowo)
    GRADUATE_90_DAYS = "graduate_90_days"  # Art. 4 ust. 3 pkt 1 (obowiązkowo i dobrowolnie)
    COMMUTE_ACCIDENT = "commute_accident"  # Art. 4 ust. 3 pkt 2 (obowiązkowo i dobrowolnie)


class IndividualBaseCalculationRequest(BaseModel):
    insurance_title: InsuranceTitle = InsuranceTitle.UOP
    mode: Literal["uop_12m", "previous_benefit", "jdg_art48a"] = Field(
        "uop_12m",
        description="Tryb wyliczenia: 'uop_12m', 'previous_benefit' (art. 43), 'jdg_art48a' (art. 48/48a/49)",
    )
    monthly_gross_salaries: list[float] = Field(
        default_factory=list,
        description="Wynagrodzenia miesięczne brutto z poszczególnych miesięcy (do 12 mies.)",
    )
    quarterly_bonuses_total: float = Field(0.0, ge=0)
    annual_bonus_total: float = Field(0.0, ge=0)
    uncompleted_months_excluded: int = Field(
        0,
        ge=0,
        le=11,
        description="Liczba miesięcy wyłączonych (<1/2 przepracowanego czasu — art. 38 ust. 2 pkt 1)",
    )
    fte_fraction: float = Field(1.0, gt=0.0, le=1.0)
    previous_benefit_base: Optional[float] = Field(None, ge=0)
    jdg_insured_months: int = Field(12, ge=0, le=12)
    jdg_declared_monthly_gross: float = Field(6200.0, ge=0)
    jdg_min_monthly_gross: Optional[float] = Field(None, ge=0)
    jdg_preferential_zus: bool = Field(
        False,
        description="Czy przedsiębiorca korzysta z preferencyjnych składek ZUS (30% płacy minimalnej)",
    )


class IndividualBaseCalculationResponse(BaseModel):
    computed_base_monthly: float
    daily_rate_100_percent: float
    daily_rate_81_5_percent: float
    daily_rate_70_percent: float
    cap_applied: bool = False
    floor_applied: bool = False
    legal_basis: str
    explanation_steps: list[str]


class PregnancyBenefitRequest(BaseModel):
    insurance_title: InsuranceTitle = InsuranceTitle.UOP
    has_voluntary_sickness_insurance: bool = True
    insurance_days: int = Field(180, ge=0)
    waiting_period_exempt: bool = Field(
        False,
        description="Zwolnienie z okresu wyczekiwania (kompatybilność wsteczna — domyślnie art. 4 ust. 3 pkt 3: 10 lat stażu dla UoP)",
    )
    waiting_period_exemption_reason: WaitingPeriodExemptionReason = Field(
        WaitingPeriodExemptionReason.NONE,
        description="Konkretna przesłanka zwolnienia z okresu wyczekiwania z art. 4 ust. 3 ustawy zasiłkowej",
    )
    gross_monthly_salary: float = Field(6500.0, ge=0)
    fte_fraction: float = Field(1.0, gt=0.0, le=1.0)
    custom_benefit_base: Optional[float] = Field(None, ge=0)
    has_code_b: bool = True
    age_over_50: bool = False
    employer_insured_count: int = Field(25, ge=0)
    contribution_debt_pln: float = Field(0.0, ge=0)
    employment_terminated_special: bool = False
    termination_reason: Optional[TerminationReason] = None

    @model_validator(mode="after")
    def validate_special_termination(self) -> "PregnancyBenefitRequest":
        if self.employment_terminated_special and self.termination_reason is None:
            raise ValueError(
                "Przy zaznaczeniu ustania zatrudnienia/ubezpieczenia w ciąży należy wskazać przyczynę (termination_reason)."
            )
        return self


class PregnancyBenefitResponse(BaseModel):
    eligible_sickness_benefit: bool
    eligible_maternity_equivalent: bool
    eligible_post_birth_maternity_art30: bool = False
    payout_suspended_due_to_debt: bool = False
    waiting_period_required_days: int
    waiting_period_met: bool
    benefit_rate_percent: float
    benefit_base_monthly: float
    benefit_base_explanation: Optional[str] = None
    daily_benefit_gross: float
    monthly_benefit_gross: float
    rehabilitation_monthly_gross: float = 0.0
    rehabilitation_daily_gross: float = 0.0
    rehabilitation_max_days: int = 360
    max_benefit_days: int
    benefit_duration_label: Optional[str] = None
    employer_pay_days: int
    payer: str
    warnings: list[str]
    summary: str


class IntegratedCalculatorRequest(BaseModel):
    scenario: BenefitScenario = BenefitScenario.BIRTH
    insurance_title: InsuranceTitle = InsuranceTitle.UOP
    has_sickness_insurance_on_birth_date: bool = True
    second_parent_insured_claim: bool = False
    second_parent_insurance_title: InsuranceTitle = InsuranceTitle.UOP
    second_parent_has_sickness_insurance: bool = True
    single_parent_or_no_second_parent: bool = False

    children_count: int = Field(1, ge=1, le=15)
    child_age_years: Optional[float] = Field(None, ge=0, le=18)
    foster_family_type: FosterFamilyType = FosterFamilyType.NON_PROFESSIONAL
    foster_deferred_school: bool = False
    adoption_short_period_9_weeks: bool = False
    previously_used_foster_maternity_weeks: int = Field(0, ge=0, le=37)
    previously_used_foster_parental_weeks: int = Field(0, ge=0, le=67)
    has_za_zyciem_certificate: bool = False
    stillbirth_or_early_death: bool = False
    mother_early_transfer_8_weeks: bool = False
    pre_birth_maternity_weeks: int = Field(0, ge=0, le=6)

    # Wcześniak / hospitalizacja -> uzupełniający urlop macierzyński
    premature_or_hospitalized: bool = False
    gestation_week: Optional[int] = Field(None, ge=20, le=42)
    birth_weight_grams: Optional[int] = Field(None, ge=300, le=6000)
    hospitalization_weeks: int = Field(0, ge=0, le=20)
    full_term_hospitalization_condition_met: bool = Field(
        True,
        description="Dla urodzenia po 37. tyg. (masa >1000 g): czy pobyt trwał ≥2 kolejne dni z 1. dniem w przedziale 5.–28. dnia po porodzie (art. 180² § 1 pkt 3 KP)",
    )

    # Podstawa wymiaru
    gross_monthly_salary: float = Field(7000.0, ge=0)
    fte_fraction: float = Field(1.0, gt=0.0, le=1.0)
    custom_benefit_base: Optional[float] = Field(None, ge=0)
    individual_base_config: Optional[IndividualBaseCalculationRequest] = None
    second_parent_gross_salary: Optional[float] = Field(None, ge=0)
    second_parent_fte_fraction: float = Field(1.0, gt=0.0, le=1.0)
    second_parent_custom_base: Optional[float] = Field(None, ge=0)

    # Wariant wypłaty i podział między rodziców (domyślnie bez narzucania urlopu drugiego rodzica)
    payment_variant: PaymentVariant = PaymentVariant.COMBINED_81_5
    mother_maternity_weeks: Optional[int] = Field(None, ge=0)
    mother_takes_parental_weeks: Optional[int] = Field(None, ge=0)
    father_takes_parental_weeks: int = Field(0, ge=0)
    father_takes_paternity_leave: bool = False

    # Łączenie urlopu rodzicielskiego z pracą — Rodzic 1
    combine_parental_with_work: bool = False
    work_fte_fraction: float = Field(0.0, ge=0.0, le=0.5)
    combined_work_weeks: int = Field(0, ge=0)
    work_during_extended_part: bool = True

    # Łączenie urlopu rodzicielskiego z pracą — Rodzic 2
    father_combine_parental_with_work: bool = False
    father_work_fte_fraction: float = Field(0.0, ge=0.0, le=0.5)
    father_combined_work_weeks: int = Field(0, ge=0)
    father_work_during_extended_part: bool = True

    # Płatnik i zadłużenie JDG
    employer_insured_count: int = Field(25, ge=0)
    second_parent_employer_insured_count: Optional[int] = Field(None, ge=0)
    contribution_debt_pln: float = Field(0.0, ge=0)
    second_parent_contribution_debt_pln: float = Field(0.0, ge=0)


class LeaveBreakdownItem(BaseModel):
    label: str
    parent: str
    weeks: float
    days: Optional[int] = None
    rate_percent: float
    monthly_gross_pln: float
    total_gross_pln: float
    notes: Optional[str] = None


class IntegratedCalculatorResponse(BaseModel):
    eligible: bool
    ineligibility_reason: Optional[str] = None
    payout_suspended_due_to_debt: bool = False
    benefit_base_parent1: float
    benefit_base_parent2: float
    benefit_base_explanation: Optional[str] = None
    benefit_base_parent2_explanation: Optional[str] = None
    minimum_benefit_top_up_applied: bool = False
    equalization_to_100_pln: float = 0.0
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
