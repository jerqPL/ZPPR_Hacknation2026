export type InsuranceTitle = "uop" | "zlecenie" | "jdg" | "none";
export type BenefitScenario = "birth" | "adoption" | "foster";
export type FosterFamilyType = "non_professional" | "professional";
export type PaymentVariant = "100_70" | "81_5";

export interface SimulatedUserProfile {
  id: string;
  full_name: string;
  pesel_masked: string;
  role_label: string;
  insurance_title: InsuranceTitle;
  has_sickness_insurance: boolean;
  insurance_start_date?: string | null;
  insurance_days: number;
  declared_gross_salary: number;
  employer_name?: string | null;
  employer_insured_count: number;
  has_contribution_debt: boolean;
  debt_amount_pln: number;
}

export interface LoginResponse {
  authenticated: boolean;
  auth_method: string;
  session_token: string;
  profile: SimulatedUserProfile;
}

export interface EzlaCertificate {
  certificate_number: string;
  issue_date: string;
  date_from: string;
  date_to: string;
  days: number;
  letter_code?: string | null;
  doctor_specialty: string;
  status: string;
}

export interface DebtStatusResponse {
  checked_at: string;
  has_debt: boolean;
  debt_amount_pln: number;
  certificate_number: string;
  impact_warning: string;
}

export interface IndividualBaseCalculationResponse {
  computed_base_monthly: number;
  daily_rate_100_percent: number;
  daily_rate_81_5_percent: number;
  daily_rate_70_percent: number;
  cap_applied: boolean;
  floor_applied: boolean;
  legal_basis: string;
  explanation_steps: string[];
}

export interface PregnancyBenefitResponse {
  eligible_sickness_benefit: boolean;
  eligible_maternity_equivalent: boolean;
  waiting_period_required_days: number;
  waiting_period_met: boolean;
  benefit_rate_percent: number;
  benefit_base_monthly: number;
  benefit_base_explanation?: string | null;
  daily_benefit_gross: number;
  monthly_benefit_gross: number;
  rehabilitation_monthly_gross: number;
  rehabilitation_daily_gross: number;
  rehabilitation_max_days: number;
  max_benefit_days: number;
  employer_pay_days: number;
  payer: string;
  warnings: string[];
  summary: string;
}

export interface LeaveBreakdownItem {
  label: string;
  parent: string;
  weeks: number;
  rate_percent: number;
  monthly_gross_pln: number;
  total_gross_pln: number;
  notes?: string | null;
}

export interface IntegratedCalculatorResponse {
  eligible: boolean;
  ineligibility_reason?: string | null;
  benefit_base_parent1: number;
  benefit_base_parent2: number;
  benefit_base_explanation?: string | null;
  benefit_base_parent2_explanation?: string | null;
  minimum_benefit_top_up_applied: boolean;
  equalization_to_100_pln: number;
  total_weeks: number;
  maternity_weeks: number;
  supplementary_maternity_weeks: number;
  parental_weeks_total: number;
  parental_weeks_extended_by_work: number;
  paternity_weeks: number;
  payer: string;
  breakdown: LeaveBreakdownItem[];
  total_estimated_gross_pln: number;
  warnings: string[];
  required_documents: string[];
}

export interface DocumentRequirement {
  form_code: string;
  title: string;
  submitted_by: string;
  submitted_to: string;
  deadline: string;
  notes: string;
}

export interface DocumentGuidanceResponse {
  payer: string;
  payer_explanation: string;
  documents: DocumentRequirement[];
  important_notes_2026: string[];
}

export interface RiskItem {
  id: string;
  title: string;
  severity: "high" | "medium" | "info";
  description: string;
  how_to_avoid: string;
  applies_to: string[];
}

export interface SupportOrganization {
  name: string;
  category: string;
  description: string;
  website: string;
  helpline?: string | null;
  charitable_only: boolean;
}

export interface OfficialLink {
  institution: string;
  title: string;
  url: string;
  description: string;
}

export interface SampleCase {
  case_id: string;
  title: string;
  description: string;
  scenario: BenefitScenario;
  insurance_title: InsuranceTitle;
  insured_on_event_date: boolean;
  expected_decision: string;
  expected_eligible: boolean;
  expected_base_parent1?: number | null;
  gross_monthly_salary: number;
  custom_benefit_base?: number | null;
  benefit_base_details?: string | null;
  second_parent_gross_salary?: number | null;
  second_parent_custom_base?: number | null;
  children_count: number;
  child_age_years?: number | null;
  foster_family_type: FosterFamilyType;
  foster_deferred_school: boolean;
  payment_variant: PaymentVariant;
  has_za_zyciem: boolean;
  employer_insured_count: number;
  mother_maternity_weeks?: number | null;
  father_takes_parental_weeks: number;
  father_takes_paternity_leave: boolean;
  notes: string;
}

export interface ExtractedPdfFields {
  form_type: string;
  insurance_title: InsuranceTitle;
  insurance_periods: string[];
  amount_is_net_base: boolean;
  extracted_amounts: number[];
  employer_insured_count?: number | null;
  children_count: number;
  ocr_required: boolean;
}

export interface PdfAnalysisResult {
  filename: string;
  detected_forms: string[];
  extracted_text_preview: string;
  verification_status: "verified" | "denied" | "needs_review";
  confidence: "high" | "medium" | "low";
  insurance_verified: boolean;
  suggested_insurance_title: InsuranceTitle;
  suggested_gross_salary?: number | null;
  suggested_custom_benefit_base?: number | null;
  extracted_fields: ExtractedPdfFields;
  notes: string[];
}

export interface ApplicationSubmissionResponse {
  reference_number: string;
  application_type: string;
  recipient: string;
  submitted_at: string;
  deadline_21_days?: string | null;
  status: string;
  summary: string;
  generated_document_text: string;
}

export interface LegalParameters {
  year: number;
  minimum_wage_gross: number;
  employee_social_security_rate: number;
  waiting_period_mandatory_days: number;
  waiting_period_voluntary_days: number;
  sickness_benefit_pregnancy_max_days: number;
  sickness_pay_employer_days_under_50: number;
  sickness_pay_employer_days_over_50: number;
  sickness_benefit_pregnancy_rate: number;
  sickness_benefit_standard_rate: number;
  maternity_rate_standard: number;
  parental_rate_standard: number;
  combined_21_days_rate: number;
  non_transferable_parental_rate: number;
  paternity_rate: number;
  supplementary_maternity_rate: number;
  combined_application_deadline_days: number;
  maternity_min_mother_weeks: number;
  maternity_pre_birth_max_weeks: number;
  maternity_weeks_by_children: Record<string, number>;
  parental_weeks_single: number;
  parental_weeks_multiple: number;
  parental_weeks_za_zyciem_single: number;
  parental_weeks_za_zyciem_multiple: number;
  parental_non_transferable_weeks: number;
  parental_max_parts: number;
  parental_work_max_fte: number;
  paternity_weeks: number;
  supplementary_maternity_max_weeks_extreme: number;
  supplementary_maternity_max_weeks_standard: number;
  stillbirth_maternity_weeks: number;
  child_death_min_days: number;
  payer_employee_threshold: number;
  foster_max_child_age: number;
  foster_deferred_school_max_child_age: number;
  adoption_max_child_age: number;
  adoption_foster_min_maternity_weeks: number;
  adoption_foster_reduced_parental_weeks: number;
  adoption_foster_reduced_parental_weeks_za_zyciem: number;
  voluntary_sickness_max_monthly_gross: number;
  post_employment_sickness_cap_monthly_gross: number;
  jdg_preferential_min_base_gross: number;
  jdg_standard_min_base_gross: number;
  parental_benefit_minimum_monthly: number;
  rehabilitation_benefit_pregnancy_rate: number;
  rehabilitation_benefit_max_days: number;
  debt_threshold_min_wage_fraction: number;
  weeks_per_year: number;
  funeral_grant_pln: number;
  claim_limitation_months: number;
}
