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
    FOSTER = "foster"  # Rodzina zastępcza (niezawodowa / zawodowa)


class FosterFamilyType(str, Enum):
    NON_PROFESSIONAL = "non_professional"  # Rodzina zastępcza niezawodowa / spokrewniona
    PROFESSIONAL = "professional"  # Rodzina zastępcza zawodowa (wyłączona z art. 183 § 1 KP)


class PaymentVariant(str, Enum):
    STANDARD_100_70 = "100_70"  # 100% macierzyński + 70% rodzicielski
    COMBINED_81_5 = "81_5"  # 81,5% za całość (wniosek w ciągu 21 dni po porodzie)


class IndividualBaseCalculationRequest(BaseModel):
    insurance_title: InsuranceTitle = InsuranceTitle.UOP
    mode: str = Field(
        "uop_12m",
        description="Tryb wyliczenia: 'uop_12m' (średnia z mies. + premie), 'previous_benefit' (art. 43), 'jdg_art48a' (art. 48/48a dla JDG)",
    )
    monthly_gross_salaries: list[float] = Field(
        default_factory=list,
        description="Wynagrodzenia miesięczne brutto z poszczególnych pełnych miesięcy (do 12 mies.)",
    )
    quarterly_bonuses_total: float = Field(
        0.0, ge=0, description="Suma premii kwartalnych z 4 poprzednich kwartałów (wliczana w 1/12 — art. 42 ust. 2)"
    )
    annual_bonus_total: float = Field(
        0.0, ge=0, description="Nagroda roczna / 13. pensja za rok poprzedni (wliczana w 1/12 — art. 42 ust. 3)"
    )
    uncompleted_months_excluded: int = Field(
        0, ge=0, le=11, description="Liczba miesięcy wyłączonych (<1/2 przepracowanego czasu — art. 38 ust. 2 pkt 1)"
    )
    fte_fraction: float = Field(1.0, gt=0.0, le=1.0, description="Wymiar etatu (dla minimalnej podstawy z art. 45)")
    previous_benefit_base: Optional[float] = Field(
        None, ge=0, description="Poprzednia podstawa wymiaru zasiłku przy przerwie < 1 miesiąc (art. 43)"
    )
    jdg_insured_months: int = Field(
        12, ge=1, le=12, description="Liczba pełnych miesięcy ubezpieczenia chorobowego (dla art. 48a)"
    )
    jdg_declared_monthly_gross: float = Field(
        6200.0, ge=0, description="Przeciętna zadeklarowana podstawa wymiaru składek na JDG"
    )
    jdg_min_monthly_gross: Optional[float] = Field(
        None, ge=0, description="Najniższa podstawa wymiaru składek na JDG (np. 5652 zł lub 1441,80 zł)"
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
    insurance_days: int = Field(180, ge=0, description="Liczba dni nieprzerwanego ubezpieczenia chorobowego")
    waiting_period_exempt: bool = Field(
        False,
        description="Zwolnienie z okresu wyczekiwania (art. 4 ust. 3 ustawy zasiłkowej — np. 10 lat wcześniejszego obowiązkowego ubezpieczenia lub absolwent w ciągu 90 dni)",
    )
    gross_monthly_salary: float = Field(6500.0, ge=0)
    custom_benefit_base: Optional[float] = Field(None, ge=0)
    has_code_b: bool = True
    age_over_50: bool = False
    employer_insured_count: int = Field(25, ge=0)
    contribution_debt_pln: float = Field(0.0, ge=0, description="Kwota zadłużenia z tytułu składek ZUS (dla JDG — art. 2a)")
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
    benefit_base_explanation: Optional[str] = None
    daily_benefit_gross: float
    monthly_benefit_gross: float
    rehabilitation_monthly_gross: float = 0.0
    rehabilitation_daily_gross: float = 0.0
    rehabilitation_max_days: int = 360
    max_benefit_days: int
    employer_pay_days: int
    payer: str
    warnings: list[str]
    summary: str


class IntegratedCalculatorRequest(BaseModel):
    scenario: BenefitScenario = BenefitScenario.BIRTH
    insurance_title: InsuranceTitle = InsuranceTitle.UOP
    has_sickness_insurance_on_birth_date: bool = True
    second_parent_insured_claim: bool = Field(
        False,
        description="Gdy matka nie podlega ubezpieczeniu chorobowemu w dniu porodu, oblicz uprawnienia ubezpieczonego ojca (art. 31 ust. 3h oraz art. 182³ KP)",
    )
    children_count: int = Field(1, ge=1, le=6)
    child_age_years: Optional[float] = Field(None, ge=0, le=18)
    foster_family_type: FosterFamilyType = FosterFamilyType.NON_PROFESSIONAL
    foster_deferred_school: bool = False
    adoption_short_period_9_weeks: bool = False
    previously_used_foster_maternity_weeks: int = Field(0, ge=0, le=37)
    previously_used_foster_parental_weeks: int = Field(0, ge=0, le=67)
    has_za_zyciem_certificate: bool = False
    stillbirth_or_early_death: bool = Field(
        False,
        description="Urodzenie martwego dziecka lub zgon dziecka przed upływem 8 tygodni życia (art. 180¹ § 1 KP — 8 tyg. urlopu macierzyńskiego, 100%)",
    )
    mother_early_transfer_8_weeks: bool = Field(
        False,
        description="Szczególna sytuacja z art. 180 § 6, § 10, § 13 KP (hospitalizacja matki / niezdolność do samodzielnej egzystencji) — przekazanie urlopu ojcu po min. 8 tyg.",
    )
    pre_birth_maternity_weeks: int = Field(
        0,
        ge=0,
        le=6,
        description="Liczba tygodni urlopu macierzyńskiego wykorzystana przed przewidywaną datą porodu (maks. 6 tyg. — art. 180 § 2 KP)",
    )

    # Wcześniak / hospitalizacja -> uzupełniający urlop macierzyński
    premature_or_hospitalized: bool = False
    gestation_week: Optional[int] = Field(None, ge=20, le=42)
    birth_weight_grams: Optional[int] = Field(None, ge=300, le=6000)
    hospitalization_weeks: int = Field(0, ge=0, le=20)

    # Podstawa wymiaru (standardowa lub indywidualna - pkt f)
    gross_monthly_salary: float = Field(7000.0, ge=0)
    custom_benefit_base: Optional[float] = Field(None, ge=0)
    individual_base_config: Optional[IndividualBaseCalculationRequest] = None
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
    work_during_extended_part: bool = Field(
        True,
        description="True = praca również w okresie wydłużenia (art. 182¹ᶠ § 7 KP: W*fte/(1-fte)), False = bez pracy w okresie wydłużenia (art. 182¹ᶠ § 2 KP: W*fte)",
    )

    # Płatnik i zadłużenie JDG
    employer_insured_count: int = Field(25, ge=0)
    contribution_debt_pln: float = Field(0.0, ge=0)


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
    benefit_base_explanation: Optional[str] = None
    benefit_base_parent2_explanation: Optional[str] = None
    minimum_benefit_top_up_applied: bool = False
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


