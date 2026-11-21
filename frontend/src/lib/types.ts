export type InsuranceTitle = "uop" | "zlecenie" | "jdg" | "none";
export type BenefitScenario = "birth" | "adoption" | "foster";
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

export interface PregnancyBenefitResponse {
  eligible_sickness_benefit: boolean;
  eligible_maternity_equivalent: boolean;
  waiting_period_required_days: number;
  waiting_period_met: boolean;
  benefit_rate_percent: number;
  benefit_base_monthly: number;
  daily_benefit_gross: number;
  monthly_benefit_gross: number;
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
  insurance_title: InsuranceTitle;
  insured_on_event_date: boolean;
  expected_decision: string;
  gross_monthly_salary: number;
  children_count: number;
  payment_variant: PaymentVariant;
  has_za_zyciem: boolean;
  employer_insured_count: number;
  notes: string;
}

export interface PdfAnalysisResult {
  filename: string;
  detected_forms: string[];
  extracted_text_preview: string;
  insurance_verified: boolean;
  suggested_insurance_title: InsuranceTitle;
  suggested_gross_salary?: number | null;
  notes: string[];
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
}
