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


class ExtractedPdfFields(BaseModel):
    form_type: str = "UNKNOWN"
    form_description: Optional[str] = None
    applicant_name: Optional[str] = None
    pesel_masked: Optional[str] = None
    insurance_title: str = "uop"
    insurance_periods: list[str] = Field(default_factory=list)
    amount_is_net_base: bool = False
    extracted_amounts: list[float] = Field(default_factory=list)
    employer_insured_count: Optional[int] = None
    children_count: int = 1
    filled_form_fields_count: int = 0
    key_extracted_fields: dict[str, str] = Field(default_factory=dict)
    ocr_required: bool = False


class PdfAnalysisResult(BaseModel):
    filename: str
    detected_forms: list[str]
    extracted_text_preview: str
    verification_status: Literal["verified", "denied", "needs_review"] = "needs_review"
    confidence: Literal["high", "medium", "low"] = "low"
    insurance_verified: bool
    suggested_insurance_title: str
    suggested_gross_salary: Optional[float] = None
    suggested_custom_benefit_base: Optional[float] = None
    extracted_fields: ExtractedPdfFields = Field(default_factory=ExtractedPdfFields)
    notes: list[str]
