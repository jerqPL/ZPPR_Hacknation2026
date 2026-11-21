from datetime import date, datetime, timezone
import uuid
from fastapi import HTTPException
from app.models.simulation import (
    DebtStatusResponse,
    EzlaCertificate,
    LoginResponse,
    PueInquiryRequest,
    PueInquiryResponse,
    SimulatedUserProfile,
)


def _days_since(iso_date: str | None) -> int:
    if not iso_date:
        return 0
    try:
        start = date.fromisoformat(iso_date)
        return max(0, (date.today() - start).days)
    except ValueError:
        return 0


_RAW_PERSONAS: dict[str, dict] = {
    "uop_standard": {
        "id": "uop_standard",
        "full_name": "Anna Kowalska",
        "pesel_masked": "920514*****",
        "role_label": "Pracownik (Umowa o pracę, duży pracodawca >20 os.)",
        "insurance_title": "uop",
        "has_sickness_insurance": True,
        "insurance_start_date": "2023-03-01",
        "declared_gross_salary": 7800.0,
        "employer_name": "TechPol Sp. z o.o.",
        "employer_insured_count": 85,
        "has_contribution_debt": False,
        "debt_amount_pln": 0.0,
    },
    "uop_small_employer": {
        "id": "uop_small_employer",
        "full_name": "Katarzyna Nowak",
        "pesel_masked": "950821*****",
        "role_label": "Pracownik (Umowa o pracę, mała firma ≤20 os. -> wypłaca ZUS)",
        "insurance_title": "uop",
        "has_sickness_insurance": True,
        "insurance_start_date": "2025-06-01",
        "declared_gross_salary": 5800.0,
        "employer_name": "Studio Projektowe Kwadrat s.c.",
        "employer_insured_count": 8,
        "has_contribution_debt": False,
        "debt_amount_pln": 0.0,
    },
    "jdg_with_debt": {
        "id": "jdg_with_debt",
        "full_name": "Magdalena Wiśniewska",
        "pesel_masked": "891103*****",
        "role_label": "Działalność gospodarcza (JDG, dobrowolne chorobowe + zaległość)",
        "insurance_title": "jdg",
        "has_sickness_insurance": True,
        "insurance_start_date": "2024-01-10",
        "declared_gross_salary": 6200.0,
        "employer_name": "MW Consulting Magdalena Wiśniewska",
        "employer_insured_count": 1,
        "has_contribution_debt": True,
        "debt_amount_pln": 1842.50,
    },
    "zlecenie_no_voluntary": {
        "id": "zlecenie_no_voluntary",
        "full_name": "Karolina Zielińska",
        "pesel_masked": "980217*****",
        "role_label": "Umowa zlecenie (brak dobrowolnego ubezpieczenia chorobowego)",
        "insurance_title": "zlecenie",
        "has_sickness_insurance": False,
        "insurance_start_date": None,
        "declared_gross_salary": 5200.0,
        "employer_name": "Agencja Eventowa Nova Sp. z o.o.",
        "employer_insured_count": 15,
        "has_contribution_debt": False,
        "debt_amount_pln": 0.0,
    },
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


def _build_profile(raw: dict) -> SimulatedUserProfile:
    return SimulatedUserProfile(
        **raw,
        insurance_days=_days_since(raw["insurance_start_date"]) if raw["has_sickness_insurance"] else 0,
    )


def list_personas() -> list[SimulatedUserProfile]:
    return [_build_profile(v) for v in _RAW_PERSONAS.values()]


def get_profile(persona_id: str) -> SimulatedUserProfile:
    raw = _RAW_PERSONAS.get(persona_id)
    if raw is None:
        raise HTTPException(status_code=404, detail=f"Nie znaleziono profilu ubezpieczonego '{persona_id}'.")
    return _build_profile(raw)


def simulate_mobywatel_login(persona_id: str) -> LoginResponse:
    profile = get_profile(persona_id)
    return LoginResponse(
        authenticated=True,
        auth_method="mObywatel (symulacja)",
        session_token=f"sim-mobywatel-{uuid.uuid4().hex[:12]}",
        profile=profile,
    )


def get_ezla_list(persona_id: str) -> list[EzlaCertificate]:
    get_profile(persona_id)
    return MOCK_EZLA.get(persona_id, [])


def get_debt_status(persona_id: str) -> DebtStatusResponse:
    from app.services.parameter_store import parameter_store

    profile = get_profile(persona_id)
    params = parameter_store.get()
    threshold_pct = params.debt_threshold_min_wage_fraction
    threshold_pln = round(params.minimum_wage_gross * threshold_pct, 2)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    if profile.has_contribution_debt and profile.debt_amount_pln > threshold_pln:
        warning = (
            f"Wykryto zadłużenie z tytułu składek na ubezpieczenia społeczne ({profile.debt_amount_pln:.2f} zł), "
            f"które przekracza próg {threshold_pct*100:.1f}% minimalnego wynagrodzenia ({threshold_pln:.2f} zł w {params.year} r. — art. 2a ust. 1 ustawy zasiłkowej). "
            f"Dla osób prowadzących działalność gospodarczą wstrzymuje to wypłatę zasiłku do czasu spłaty całości zadłużenia "
            f"(brak uregulowania w ciągu {params.claim_limitation_months} miesięcy od dnia powstania prawa powoduje przedawnienie prawa do świadczenia — art. 2a ust. 2)."
        )
    elif profile.has_contribution_debt:
        warning = (
            f"Wykryto zaległość {profile.debt_amount_pln:.2f} zł, która nie przekracza progu {threshold_pct*100:.1f}% minimalnego wynagrodzenia ({threshold_pln:.2f} zł) — nie wstrzymuje wypłaty zasiłku, ale zaleca się jej uregulowanie."
        )
    else:
        warning = f"Brak zaległości z tytułu składek na ubezpieczenia społeczne na dzień sprawdzenia (próg wstrzymania wypłaty z art. 2a: {threshold_pln:.2f} zł)."

    return DebtStatusResponse(
        checked_at=now_iso,
        has_debt=profile.has_contribution_debt,
        debt_amount_pln=profile.debt_amount_pln,
        certificate_number=f"ZUS-RD-SIM-{uuid.uuid4().hex[:8].upper()}",
        impact_warning=warning,
    )


def submit_pue_inquiry(req: PueInquiryRequest) -> PueInquiryResponse:
    get_profile(req.persona_id)
    return PueInquiryResponse(
        ticket_id=f"PUE-{uuid.uuid4().hex[:8].upper()}",
        status="Wysłano do konsultanta PUE/eZUS (symulacja)",
        estimated_response="Do 2 dni roboczych na skrzynce odbiorczej PUE/eZUS",
        echo_subject=req.subject,
    )
