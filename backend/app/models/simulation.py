from datetime import date
from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, field_validator, model_validator
from app.models.calculator import PaymentVariant


class ApplicationType(str, Enum):
    LEAVE_EMPLOYER = "leave_employer"
    LEAVE_SUPPLEMENTARY = "leave_supplementary"
    LEAVE_RESIGNATION = "leave_resignation"
    LEAVE_WORK_COMBINATION = "leave_work_combination"
    LEAVE_PATERNITY = "leave_paternity"
    LEAVE_ADOPTION_FOSTER = "leave_adoption_foster"
    LEAVE_PRE_BIRTH = "leave_pre_birth"
    LEAVE_FATHER_TAKEOVER = "leave_father_takeover"
    ZAM_ZUS = "zam_zus"
    USC_BIRTH_CERTIFICATE = "usc_birth_certificate"


class SimulatedUserProfile(BaseModel):
    id: str
    full_name: str
    pesel_masked: str
    role_label: str
    insurance_title: str
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
    application_type: ApplicationType
    applicant_name: str = Field(..., min_length=2, max_length=120)
    pesel_masked: str = Field(..., min_length=5, max_length=20)
    child_birth_date: Optional[str] = None
    leave_start_date: Optional[str] = None
    leave_end_date: Optional[str] = None
    leave_parts_count: Optional[int] = Field(1, ge=1, le=5)
    work_fte_fraction: Optional[float] = Field(None, gt=0.0, le=0.5)
    work_during_extended_part: Optional[bool] = None
    maternity_end_date: Optional[str] = None
    hospitalization_from: Optional[str] = None
    hospitalization_to: Optional[str] = None
    resignation_date: Optional[str] = None
    usc_copy_type: Literal["skrocony", "zupelny"] = "skrocony"
    payment_variant: Optional[PaymentVariant] = PaymentVariant.COMBINED_81_5
    recipient: str = Field(..., min_length=2, max_length=150)
    notes: Optional[str] = Field(None, max_length=2000)
    reference_number: Optional[str] = Field(None, max_length=64)

    @field_validator("applicant_name", "pesel_masked", "recipient", mode="before")
    @classmethod
    def strip_required_text(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("notes", "reference_number", mode="before")
    @classmethod
    def strip_optional_text(cls, v: object) -> object:
        if isinstance(v, str):
            cleaned = v.strip()
            return cleaned or None
        return v

    @field_validator(
        "child_birth_date",
        "leave_start_date",
        "leave_end_date",
        "maternity_end_date",
        "hospitalization_from",
        "hospitalization_to",
        "resignation_date",
    )
    @classmethod
    def validate_iso_date(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        try:
            date.fromisoformat(v)
        except ValueError as exc:
            raise ValueError(f"Nieprawidłowa data '{v}' — wymagany poprawny format RRRR-MM-DD.") from exc
        return v

    @model_validator(mode="after")
    def validate_date_ranges(self) -> "ApplicationSubmissionRequest":
        if self.leave_start_date and self.leave_end_date:
            if date.fromisoformat(self.leave_end_date) < date.fromisoformat(self.leave_start_date):
                raise ValueError("Data zakończenia urlopu/zasiłku nie może być wcześniejsza niż data rozpoczęcia.")
        if self.hospitalization_from and self.hospitalization_to:
            if date.fromisoformat(self.hospitalization_to) < date.fromisoformat(self.hospitalization_from):
                raise ValueError("Data zakończenia hospitalizacji nie może być wcześniejsza niż data jej rozpoczęcia.")
        return self


class ApplicationSubmissionResponse(BaseModel):
    reference_number: str
    application_type: ApplicationType
    recipient: str
    submitted_at: str
    deadline_21_days: Optional[str] = None
    status: str
    summary: str
    generated_document_text: str
