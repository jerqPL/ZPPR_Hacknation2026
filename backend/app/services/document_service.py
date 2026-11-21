from datetime import datetime, timezone
import uuid
from app.models.calculator import InsuranceTitle
from app.models.guidance import DocumentGuidanceResponse, DocumentRequirement
from app.models.parameters import LegalParameters
from app.models.simulation import ApplicationSubmissionRequest, ApplicationSubmissionResponse


def get_document_guidance(
    insurance_title: InsuranceTitle,
    employer_insured_count: int,
    params: LegalParameters,
) -> DocumentGuidanceResponse:
    employer_pays = (
        insurance_title in (InsuranceTitle.UOP, InsuranceTitle.ZLECENIE)
        and employer_insured_count > params.payer_employee_threshold
    )

    if employer_pays:
        payer = "Płatnik składek (pracodawca / zleceniodawca)"
        payer_explanation = (
            f"Płatnik zgłasza do ubezpieczenia chorobowego powyżej {params.payer_employee_threshold} osób "
            "(stan na 30 listopada poprzedniego roku), dlatego to on ustala prawo i wypłaca zasiłek."
        )
    else:
        payer = "Zakład Ubezpieczeń Społecznych (ZUS)"
        payer_explanation = (
            f"Dla osób na JDG, po ustaniu zatrudnienia lub u płatników zgłaszających do {params.payer_employee_threshold} osób "
            "prawo do zasiłku ustala i wypłaca go bezpośrednio ZUS."
        )

    docs: list[DocumentRequirement] = []

    if insurance_title == InsuranceTitle.UOP:
        docs.append(
            DocumentRequirement(
                form_code="Wniosek o urlop (KP)",
                title="Wniosek o udzielenie urlopu macierzyńskiego i rodzicielskiego",
                submitted_by="Pracownik (matka/ojciec)",
                submitted_to="Pracodawca",
                deadline=f"Do {params.combined_application_deadline_days} dni po porodzie (dla stawki 81,5%)",
                notes="Można złożyć jeden łączny wniosek o urlop macierzyński i rodzicielski.",
            )
        )
        if not employer_pays:
            docs.append(
                DocumentRequirement(
                    form_code="Z-3",
                    title="Zaświadczenie płatnika składek (dla pracownika)",
                    submitted_by="Pracodawca",
                    submitted_to="ZUS (PUE/eZUS)",
                    deadline="Niezwłocznie po otrzymaniu wniosku pracownika",
                    notes="Na dalszy okres zasiłku chorobowego pracodawca może złożyć ZAS-12.",
                )
            )
    elif insurance_title == InsuranceTitle.ZLECENIE:
        docs.append(
            DocumentRequirement(
                form_code="ZAM",
                title="Wniosek o zasiłek macierzyński",
                submitted_by="Ubezpieczony (zleceniobiorca)",
                submitted_to="Płatnik składek lub ZUS",
                deadline=f"Do {params.combined_application_deadline_days} dni po porodzie (dla stawki 81,5%)",
                notes="Zleceniobiorca nie ma urlopu z Kodeksu pracy, ale ma prawo do zasiłku za okres odpowiadający urlopowi.",
            )
        )
        if not employer_pays:
            docs.append(
                DocumentRequirement(
                    form_code="Z-3a",
                    title="Zaświadczenie płatnika składek (dla zleceniobiorcy)",
                    submitted_by="Zleceniodawca",
                    submitted_to="ZUS (PUE/eZUS)",
                    deadline="Niezwłocznie po zgłoszeniu niezdolności / wniosku",
                    notes="Zawiera okresy ubezpieczenia i podstawę wymiaru składek.",
                )
            )
    else:
        docs.append(
            DocumentRequirement(
                form_code="ZAM",
                title="Wniosek o zasiłek macierzyński",
                submitted_by="Osoba prowadząca JDG / ubezpieczony",
                submitted_to="ZUS (PUE/eZUS)",
                deadline=f"Do {params.combined_application_deadline_days} dni po porodzie (dla stawki 81,5%)",
                notes="Dla zasiłku chorobowego w ciąży na JDG należy złożyć również wniosek ZAS-53.",
            )
        )
        docs.append(
            DocumentRequirement(
                form_code="ZAS-53",
                title="Wniosek o zasiłek chorobowy (okres ciąży)",
                submitted_by="Osoba prowadząca JDG",
                submitted_to="ZUS (PUE/eZUS)",
                deadline="Po wystawieniu e-ZLA przez lekarza",
                notes="Samo e-ZLA nie uruchamia wypłaty na JDG — potrzebny jest wniosek ZAS-53.",
            )
        )

    docs.append(
        DocumentRequirement(
            form_code="Akt urodzenia (USC)",
            title="Odpis skrócony aktu urodzenia dziecka",
            submitted_by="Rodzic",
            submitted_to="Pracodawca lub ZUS (załącznik do wniosku)",
            deadline="Po rejestracji urodzenia w Urzędzie Stanu Cywilnego",
            notes="Można uzyskać online przez ePUAP / gov.pl (Rejestr Stanu Cywilnego).",
        )
    )

    notes_2026 = [
        "Od 24 października 2026 r. formularze ZUR (rodzicielski) oraz ZAO (ojcowski) zostały połączone z formularzem ZAM i zlikwidowane.",
        "Od 24 października 2026 r. formularz Z-3b został zlikwidowany.",
        "Wzory aktualnych formularzy ZUS dostępne są na stronie www.zus.pl (zakładka Wzory formularzy -> Zasiłki).",
    ]

    return DocumentGuidanceResponse(
        payer=payer,
        payer_explanation=payer_explanation,
        documents=docs,
        important_notes_2026=notes_2026,
    )


def simulate_application_submission(
    req: ApplicationSubmissionRequest,
) -> ApplicationSubmissionResponse:
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prefix = {
        "leave_employer": "URLOP",
        "zam_zus": "ZUS-ZAM",
        "usc_birth_certificate": "USC-AKT",
    }.get(req.application_type, "WNIOSEK")

    ref = f"{prefix}-SIM-{uuid.uuid4().hex[:8].upper()}"
    return ApplicationSubmissionResponse(
        reference_number=ref,
        application_type=req.application_type,
        recipient=req.recipient,
        submitted_at=now_iso,
        status="Złożono pomyślnie (SYMULACJA — nie wysłano realnych danych)",
        summary=f"Wygenerowano i zasymulowano wysłanie dokumentu ({req.application_type}) dla {req.applicant_name} do: {req.recipient}.",
    )
