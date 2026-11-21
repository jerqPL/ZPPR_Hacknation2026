from typing import Optional
from pydantic import BaseModel


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
    category: str  # "wcześniaki" | "strata_dziecka" | "dziecko_chore" | "wsparcie_rodziny"
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
    scenario: str = "birth"  # "birth" | "adoption" | "foster"
    insurance_title: str
    insured_on_event_date: bool
    expected_decision: str
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
    father_takes_parental_weeks: int = 9
    father_takes_paternity_leave: bool = False
    notes: str


class PdfAnalysisResult(BaseModel):
    filename: str
    detected_forms: list[str]
    extracted_text_preview: str
    insurance_verified: bool
    suggested_insurance_title: str
    suggested_gross_salary: Optional[float] = None
    suggested_custom_benefit_base: Optional[float] = None
    notes: list[str]

