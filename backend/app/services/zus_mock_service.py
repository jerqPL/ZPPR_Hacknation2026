from datetime import datetime, timezone
import uuid
from app.models.simulation import (
    DebtStatusResponse,
    EzlaCertificate,
    LoginResponse,
    PueInquiryRequest,
    PueInquiryResponse,
    SimulatedUserProfile,
)

MOCK_PERSONAS: dict[str, SimulatedUserProfile] = {
    "uop_standard": SimulatedUserProfile(
        id="uop_standard",
        full_name="Anna Kowalska",
        pesel_masked="920514*****",
        role_label="Pracownik (Umowa o pracę, duży pracodawca >20 os.)",
        insurance_title="uop",
        has_sickness_insurance=True,
        insurance_start_date="2023-03-01",
        insurance_days=1360,
        declared_gross_salary=7800.0,
        employer_name="TechPol Sp. z o.o.",
        employer_insured_count=85,
        has_contribution_debt=False,
        debt_amount_pln=0.0,
    ),
    "uop_small_employer": SimulatedUserProfile(
        id="uop_small_employer",
        full_name="Katarzyna Nowak",
        pesel_masked="950821*****",
        role_label="Pracownik (Umowa o pracę, mała firma ≤20 os. -> wypłaca ZUS)",
        insurance_title="uop",
        has_sickness_insurance=True,
        insurance_start_date="2025-06-01",
        insurance_days=538,
        declared_gross_salary=5800.0,
        employer_name="Studio Projektowe Kwadrat s.c.",
        employer_insured_count=8,
        has_contribution_debt=False,
        debt_amount_pln=0.0,
    ),
    "jdg_with_debt": SimulatedUserProfile(
        id="jdg_with_debt",
        full_name="Magdalena Wiśniewska",
        pesel_masked="891103*****",
        role_label="Działalność gospodarcza (JDG, dobrowolne chorobowe + zaległość)",
        insurance_title="jdg",
        has_sickness_insurance=True,
        insurance_start_date="2024-01-10",
        insurance_days=680,
        declared_gross_salary=6200.0,
        employer_name="MW Consulting Magdalena Wiśniewska",
        employer_insured_count=1,
        has_contribution_debt=True,
        debt_amount_pln=1842.50,
    ),
    "zlecenie_no_voluntary": SimulatedUserProfile(
        id="zlecenie_no_voluntary",
        full_name="Karolina Zielińska",
        pesel_masked="980217*****",
        role_label="Umowa zlecenie (brak dobrowolnego ubezpieczenia chorobowego)",
        insurance_title="zlecenie",
        has_sickness_insurance=False,
        insurance_start_date=None,
        insurance_days=0,
        declared_gross_salary=5200.0,
        employer_name="Agencja Eventowa Nova Sp. z o.o.",
        employer_insured_count=15,
        has_contribution_debt=False,
        debt_amount_pln=0.0,
    ),
}

MOCK_EZLA: dict[str, list[EzlaCertificate]] = {
    "uop_standard": [
        EzlaCertificate(
            certificate_number="EZLA/2026/09/884120",
            issue_date="2026-09-14",
            date_from="2026-09-15",
            date_to="2026-10-14",
            days=30,
            letter_code="B",
            doctor_specialty="Położnictwo i ginekologia",
            status="Przekazane do ZUS i na profil PUE/eZUS płatnika",
        ),
        EzlaCertificate(
            certificate_number="EZLA/2026/10/912045",
            issue_date="2026-10-14",
            date_from="2026-10-15",
            date_to="2026-11-13",
            days=30,
            letter_code="B",
            doctor_specialty="Położnictwo i ginekologia",
            status="Przekazane do ZUS i na profil PUE/eZUS płatnika",
        ),
    ],
    "jdg_with_debt": [
        EzlaCertificate(
            certificate_number="EZLA/2026/11/104422",
            issue_date="2026-11-02",
            date_from="2026-11-03",
            date_to="2026-11-24",
            days=22,
            letter_code="B",
            doctor_specialty="Położnictwo i ginekologia",
            status="Przekazane do ZUS (wymaga złożenia wniosku ZAS-53)",
        )
    ],
}


def list_personas() -> list[SimulatedUserProfile]:
    return list(MOCK_PERSONAS.values())


def simulate_mobywatel_login(persona_id: str) -> LoginResponse:
    profile = MOCK_PERSONAS.get(persona_id, MOCK_PERSONAS["uop_standard"])
    return LoginResponse(
        authenticated=True,
        auth_method="mObywatel (symulacja)",
        session_token=f"sim-mobywatel-{uuid.uuid4().hex[:12]}",
        profile=profile,
    )


def get_profile(persona_id: str) -> SimulatedUserProfile:
    return MOCK_PERSONAS.get(persona_id, MOCK_PERSONAS["uop_standard"])


def get_ezla_list(persona_id: str) -> list[EzlaCertificate]:
    return MOCK_EZLA.get(persona_id, [])


def get_debt_status(persona_id: str) -> DebtStatusResponse:
    from app.services.parameter_store import parameter_store

    profile = get_profile(persona_id)
    params = parameter_store.get()
    threshold_1pct = round(params.minimum_wage_gross * 0.01, 2)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if profile.has_contribution_debt and profile.debt_amount_pln > threshold_1pct:
        warning = (
            f"Wykryto zadłużenie z tytułu składek na ubezpieczenia społeczne ({profile.debt_amount_pln:.2f} zł), "
            f"które przekracza próg 1% minimalnego wynagrodzenia ({threshold_1pct:.2f} zł w {params.year} r. — art. 2a ust. 1 ustawy zasiłkowej). "
            "Dla osób prowadzących działalność gospodarczą wstrzymuje to wypłatę zasiłku do czasu spłaty całości zadłużenia "
            "(brak uregulowania w ciągu 6 miesięcy od dnia powstania prawa powoduje przedawnienie prawa do świadczenia — art. 2a ust. 2)."
        )
    elif profile.has_contribution_debt:
        warning = (
            f"Wykryto zaległość {profile.debt_amount_pln:.2f} zł, która nie przekracza progu 1% minimalnego wynagrodzenia ({threshold_1pct:.2f} zł) — nie wstrzymuje wypłaty zasiłku, ale zaleca się jej uregulowanie."
        )
    else:
        warning = f"Brak zaległości z tytułu składek na ubezpieczenia społeczne na dzień sprawdzenia (próg wstrzymania wypłaty z art. 2a: {threshold_1pct:.2f} zł)."

    return DebtStatusResponse(
        checked_at=now_iso,
        has_debt=profile.has_contribution_debt,
        debt_amount_pln=profile.debt_amount_pln,
        certificate_number=f"ZUS-RD-SIM-{uuid.uuid4().hex[:8].upper()}",
        impact_warning=warning,
    )


def submit_pue_inquiry(req: PueInquiryRequest) -> PueInquiryResponse:
    return PueInquiryResponse(
        ticket_id=f"PUE-{uuid.uuid4().hex[:8].upper()}",
        status="Wysłano do konsultanta PUE/eZUS (symulacja)",
        estimated_response="Do 2 dni roboczych na skrzynce odbiorczej PUE/eZUS",
        echo_subject=req.subject,
    )
