from typing import Literal, Optional
from pydantic import BaseModel, Field


class DocumentRequirement(BaseModel):
    form_code: str
    title: str
    submitted_by: str
    submitted_to: str
    deadline: str
    notes: str


class DocumentGuidanceResponse(BaseModel):
    payer: str
    payer_explanation: str
    documents: list[DocumentRequirement]
    important_notes_2026: list[str]


class RiskItem(BaseModel):
    id: str
    title: str
    severity: str  # "high" | "medium" | "info"
    description: str
    how_to_avoid: str
    applies_to: list[str]


class SupportOrganization(BaseModel):
    name: str
    category: str
    description: str
    website: str
    helpline: Optional[str] = None
    charitable_only: bool = True


class OfficialLink(BaseModel):
    institution: str
    title: str
    url: str
    description: str


class SampleCase(BaseModel):
    case_id: str
    title: str
    description: str
    scenario: str = "birth"
    insurance_title: str
    insured_on_event_date: bool
    expected_decision: str
    expected_eligible: bool = True
    expected_base_parent1: Optional[float] = None
    gross_monthly_salary: float
    custom_benefit_base: Optional[float] = None
    benefit_base_details: Optional[str] = None
    second_parent_gross_salary: Optional[float] = None
    second_parent_custom_base: Optional[float] = None
    children_count: int = 1
    child_age_years: Optional[float] = None
    foster_family_type: str = "non_professional"
    foster_deferred_school: bool = False
    payment_variant: str = "81_5"
    has_za_zyciem: bool = False
    employer_insured_count: int = 25
    mother_maternity_weeks: Optional[int] = None
    father_takes_parental_weeks: int = 0
    father_takes_paternity_leave: bool = False
    notes: str


DocumentDomain = Literal[
    "sickness_pregnancy",
    "sickness_general",
    "maternity_parental",
    "payer_or_insurance_certificate",
    "care_benefit",
    "other_benefit",
    "unknown",
]

RecommendedCalculator = Literal[
    "pregnancy_sickness",
    "maternity_parental",
    "both",
    "info_only",
]

SicknessInsuranceStatus = Literal["confirmed", "denied", "unknown"]


class DocumentConflict(BaseModel):
    field: str
    field_label: str
    values: list[str]
    documents: list[str]
    message: str


class ExtractedPdfFields(BaseModel):
    form_type: str = "UNKNOWN"
    form_description: Optional[str] = None
    document_domain: DocumentDomain = "unknown"
    recommended_calculator: RecommendedCalculator = "both"
    applicant_name: Optional[str] = None
    pesel_masked: Optional[str] = None
    insurance_title: Optional[str] = None
    zus_title_code: Optional[str] = None
    sickness_insurance_status: SicknessInsuranceStatus = "unknown"
    insurance_days: Optional[int] = None
    insurance_periods: list[str] = Field(default_factory=list)
    amount_is_net_base: bool = False
    extracted_amounts: list[float] = Field(default_factory=list)
    fte_fraction: Optional[float] = None
    employer_insured_count: Optional[int] = None
    has_contribution_debt: Optional[bool] = None
    contribution_debt_pln: Optional[float] = None
    # Zwolnienie chorobowe / ciąża
    ezla_number: Optional[str] = None
    incapacity_period: Optional[str] = None
    incapacity_days: Optional[int] = None
    letter_codes: list[str] = Field(default_factory=list)
    has_code_b: Optional[bool] = None
    pregnancy_confirmed: Optional[bool] = None
    employment_terminated_special: Optional[bool] = None
    termination_reason: Optional[str] = None
    waiting_period_exemption_reason: Optional[str] = None
    # Macierzyński / rodzicielski / adopcja / piecza
    scenario: Optional[str] = None
    children_count: Optional[int] = None
    child_birth_date: Optional[str] = None
    payment_variant: Optional[str] = None
    has_za_zyciem: Optional[bool] = None
    stillbirth_or_early_death: Optional[bool] = None
    premature_or_hospitalized: Optional[bool] = None
    gestation_week: Optional[int] = None
    birth_weight_grams: Optional[int] = None
    hospitalization_weeks: Optional[int] = None
    combine_parental_with_work: Optional[bool] = None
    work_fte_fraction: Optional[float] = None
    father_takes_paternity_leave: Optional[bool] = None
    mother_uninsured_father_claim: Optional[bool] = None
    # Metadane odczytu
    page_count: int = 0
    ocr_pages_processed: int = 0
    filled_form_fields_count: int = 0
    key_extracted_fields: dict[str, str] = Field(default_factory=dict)
    ocr_required: bool = False
    ocr_used: bool = False


class PdfAnalysisResult(BaseModel):
    filename: str
    file_kind: Literal["pdf", "image"] = "pdf"
    detected_forms: list[str]
    document_domain: DocumentDomain = "unknown"
    recommended_calculator: RecommendedCalculator = "both"
    extracted_text_preview: str
    verification_status: Literal["verified", "denied", "needs_review"] = "needs_review"
    sickness_insurance_status: SicknessInsuranceStatus = "unknown"
    confidence: Literal["high", "medium", "low"] = "low"
    insurance_verified: bool = False
    suggested_insurance_title: Optional[str] = None
    suggested_gross_salary: Optional[float] = None
    suggested_custom_benefit_base: Optional[float] = None
    extracted_fields: ExtractedPdfFields = Field(default_factory=ExtractedPdfFields)
    missing_fields_for_calculation: list[str] = Field(default_factory=list)
    guidance_banner: Optional[str] = None
    notes: list[str] = Field(default_factory=list)


class CaseDocumentsAnalysisResult(BaseModel):
    documents: list[PdfAnalysisResult]
    merged: PdfAnalysisResult
    conflicts: list[DocumentConflict] = Field(default_factory=list)
