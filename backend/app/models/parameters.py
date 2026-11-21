from pydantic import BaseModel, Field


class LegalParameters(BaseModel):
    """Konfigurowalne parametry prawne (możliwe do edycji w panelu administracyjnym)."""

    year: int = Field(2026, ge=2024, le=2100)
    minimum_wage_gross: float = Field(4806.0, gt=0)
    employee_social_security_rate: float = Field(0.1371, ge=0, le=0.5)

    waiting_period_mandatory_days: int = Field(30, ge=0)
    waiting_period_voluntary_days: int = Field(90, ge=0)
    sickness_benefit_pregnancy_max_days: int = Field(270, ge=1)
    sickness_pay_employer_days_under_50: int = Field(33, ge=0)
    sickness_pay_employer_days_over_50: int = Field(14, ge=0)

    sickness_benefit_pregnancy_rate: float = Field(1.0, gt=0, le=1.0)
    maternity_rate_standard: float = Field(1.0, gt=0, le=1.0)
    parental_rate_standard: float = Field(0.7, gt=0, le=1.0)
    combined_21_days_rate: float = Field(0.815, gt=0, le=1.0)
    non_transferable_parental_rate: float = Field(0.7, gt=0, le=1.0)
    paternity_rate: float = Field(1.0, gt=0, le=1.0)
    supplementary_maternity_rate: float = Field(1.0, gt=0, le=1.0)

    combined_application_deadline_days: int = Field(21, ge=1)
    maternity_min_mother_weeks: int = Field(14, ge=1)
    maternity_pre_birth_max_weeks: int = Field(6, ge=0)
    maternity_weeks_by_children: dict[str, int] = Field(
        default_factory=lambda: {"1": 20, "2": 31, "3": 33, "4": 35, "5": 37}
    )

    parental_weeks_single: int = Field(41, ge=1)
    parental_weeks_multiple: int = Field(43, ge=1)
    parental_weeks_za_zyciem_single: int = Field(65, ge=1)
    parental_weeks_za_zyciem_multiple: int = Field(67, ge=1)
    parental_non_transferable_weeks: int = Field(9, ge=0)
    parental_max_parts: int = Field(5, ge=1)
    parental_work_max_fte: float = Field(0.5, gt=0, le=1.0)
    paternity_weeks: int = Field(2, ge=0)

    supplementary_maternity_max_weeks_extreme: int = Field(15, ge=0)
    supplementary_maternity_max_weeks_standard: int = Field(8, ge=0)
    stillbirth_maternity_weeks: int = Field(8, ge=0)
    child_death_min_days: int = Field(7, ge=0)
    payer_employee_threshold: int = Field(20, ge=1)

    foster_max_child_age: int = Field(7, ge=1)
    foster_deferred_school_max_child_age: int = Field(10, ge=1)
    adoption_max_child_age: int = Field(14, ge=1)
    adoption_foster_min_maternity_weeks: int = Field(9, ge=1)
    adoption_foster_reduced_parental_weeks: int = Field(38, ge=1)
    adoption_foster_reduced_parental_weeks_za_zyciem: int = Field(62, ge=1)
    voluntary_sickness_max_monthly_gross: float = Field(23550.0, gt=0)
    jdg_preferential_min_base_gross: float = Field(1441.8, gt=0)
    jdg_standard_min_base_gross: float = Field(5652.0, gt=0)

