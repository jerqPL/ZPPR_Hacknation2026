from typing import Optional
from pydantic import BaseModel, Field


class SimulatedUserProfile(BaseModel):
    id: str
    full_name: str
    pesel_masked: str
    role_label: str
    insurance_title: str  # uop | zlecenie | jdg | none
    has_sickness_insurance: bool
    insurance_start_date: Optional[str] = None
    insurance_days: int
    declared_gross_salary: float
    employer_name: Optional[str] = None
    employer_insured_count: int = 0
    has_contribution_debt: bool = False
    debt_amount_pln: float = 0.0


class LoginRequest(BaseModel):
    persona_id: str = "uop_standard"


class LoginResponse(BaseModel):
    authenticated: bool
    auth_method: str = "mObywatel (symulacja)"
    session_token: str
    profile: SimulatedUserProfile


class EzlaCertificate(BaseModel):
    certificate_number: str
    issue_date: str
    date_from: str
    date_to: str
    days: int
    letter_code: Optional[str] = "B"
    doctor_specialty: str
    status: str


class DebtStatusResponse(BaseModel):
    checked_at: str
    has_debt: bool
    debt_amount_pln: float
    certificate_number: str
    impact_warning: str


class PueInquiryRequest(BaseModel):
    persona_id: str
    subject: str = Field(..., min_length=3, max_length=200)
    message: str = Field(..., min_length=5, max_length=2000)


class PueInquiryResponse(BaseModel):
    ticket_id: str
    status: str
    estimated_response: str
    echo_subject: str


class ApplicationSubmissionRequest(BaseModel):
    application_type: str  # "leave_employer" | "zam_zus" | "usc_birth_certificate"
    applicant_name: str
    pesel_masked: str
    child_birth_date: Optional[str] = None
    leave_start_date: Optional[str] = None
    payment_variant: Optional[str] = "81_5"
    recipient: str  # "Pracodawca" | "ZUS (PUE/eZUS)" | "Urząd Stanu Cywilnego"
    notes: Optional[str] = None


class ApplicationSubmissionResponse(BaseModel):
    reference_number: str
    application_type: str
    recipient: str
    submitted_at: str
    status: str
    summary: str
