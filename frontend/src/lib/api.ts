import type {
  DebtStatusResponse,
  DocumentGuidanceResponse,
  EzlaCertificate,
  IndividualBaseCalculationRequest,
  IndividualBaseCalculationResponse,
  InsuranceTitle,
  IntegratedCalculatorResponse,
  LegalParameters,
  LoginResponse,
  OfficialLink,
  PdfAnalysisResult,
  PregnancyBenefitResponse,
  RiskItem,
  SampleCase,
  SimulatedUserProfile,
  SupportOrganization,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers || {}),
    },
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getPersonas: () => apiFetch<SimulatedUserProfile[]>("/auth/personas"),
  loginMobywatel: (persona_id: string) =>
    apiFetch<LoginResponse>("/auth/mobywatel/login", {
      method: "POST",
      body: JSON.stringify({ persona_id }),
    }),
  getEzla: (personaId: string) => apiFetch<EzlaCertificate[]>(`/zus/ezla/${personaId}`),
  getDebtStatus: (personaId: string) => apiFetch<DebtStatusResponse>(`/zus/debt/${personaId}`),
  submitPueInquiry: (payload: { persona_id: string; subject: string; message: string }) =>
    apiFetch<{ ticket_id: string; status: string; estimated_response: string; echo_subject: string }>(
      "/zus/pue/inquiry",
      { method: "POST", body: JSON.stringify(payload) }
    ),

  calculatePregnancy: (payload: Record<string, unknown>) =>
    apiFetch<PregnancyBenefitResponse>("/calculator/pregnancy", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  calculateIntegrated: (payload: Record<string, unknown>) =>
    apiFetch<IntegratedCalculatorResponse>("/calculator/integrated", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  calculateIndividualBase: (payload: IndividualBaseCalculationRequest) =>
    apiFetch<IndividualBaseCalculationResponse>("/calculator/benefit-base", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getDocumentGuidance: (insuranceTitle: InsuranceTitle, employerInsuredCount: number) =>
    apiFetch<DocumentGuidanceResponse>(
      `/documents/guidance?insurance_title=${insuranceTitle}&employer_insured_count=${employerInsuredCount}`
    ),
  submitApplication: (payload: Record<string, unknown>) =>
    apiFetch<{
      reference_number: string;
      application_type: string;
      recipient: string;
      submitted_at: string;
      status: string;
      summary: string;
    }>("/documents/submit", { method: "POST", body: JSON.stringify(payload) }),
  getSampleCases: () => apiFetch<SampleCase[]>("/documents/sample-cases"),
  analyzePdf: async (file: File): Promise<PdfAnalysisResult> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/documents/analyze-pdf`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      throw new Error(`Błąd przesyłania PDF (${res.status})`);
    }
    return res.json();
  },

  getRisks: () => apiFetch<RiskItem[]>("/guidance/risks"),
  getSupportOrganizations: () => apiFetch<SupportOrganization[]>("/guidance/support-organizations"),
  getOfficialLinks: () => apiFetch<OfficialLink[]>("/guidance/official-links"),

  getParameters: () => apiFetch<LegalParameters>("/admin/parameters"),
  updateParameters: (params: LegalParameters) =>
    apiFetch<LegalParameters>("/admin/parameters", {
      method: "PUT",
      body: JSON.stringify(params),
    }),
  resetParameters: () =>
    apiFetch<LegalParameters>("/admin/parameters/reset", { method: "POST" }),
};
