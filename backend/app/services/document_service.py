from datetime import date, datetime, timedelta, timezone
import uuid
from app.models.calculator import InsuranceTitle, PaymentVariant
from app.models.guidance import DocumentGuidanceResponse, DocumentRequirement
from app.models.parameters import LegalParameters
from app.models.simulation import (
    ApplicationSubmissionRequest,
    ApplicationSubmissionResponse,
    ApplicationType,
)


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
                title="Wniosek o udzielenie urlopu macierzyńskiego i rodzicielskiego (lub pisemna deklaracja 81,5%)",
                submitted_by="Pracownik (matka/ojciec)",
                submitted_to="Pracodawca",
                deadline=f"Do {params.combined_application_deadline_days} dni po porodzie (dla stawki {params.combined_21_days_rate*100:.1f}%)",
                notes="Alternatywnie można złożyć sam wniosek/deklarację o wypłatę 81,5% za pełny wymiar (art. 30a ustawy zasiłkowej).",
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
                deadline=f"Do {params.combined_application_deadline_days} dni po porodzie (dla stawki {params.combined_21_days_rate*100:.1f}%)",
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
                deadline=f"Do {params.combined_application_deadline_days} dni po porodzie (dla stawki {params.combined_21_days_rate*100:.1f}%)",
                notes="Rozpoczęcie zasiłku macierzyńskiego na JDG powoduje automatyczne ustanie dobrowolnego ubezpieczenia chorobowego — po zakończeniu zasiłku wymagane jest ponowne zgłoszenie ZUS ZUA.",
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
        "Od 24 października 2026 r. formularze ZUR (rodzicielski) oraz ZAO (ojcowski) zostały połączone z formularzem ZAM i zlikwidowane; zlikwidowano również Z-3b.",
        f"Roszczenie o wypłatę zasiłku przedawnia się po upływie {params.claim_limitation_months} miesięcy od ostatniego dnia okresu, za który zasiłek przysługuje (art. 67 ustawy zasiłkowej).",
        f"W przypadku urodzenia martwego dziecka rodzinie przysługuje również zasiłek pogrzebowy w wysokości {params.funeral_grant_pln:,.0f} zł (wniosek Z-12).".replace(",", " "),
        "Dla stawki 81,5% można złożyć jeden wniosek o oba urlopy albo odrębną pisemną deklarację w terminie 21 dni od porodu (art. 30a ustawy zasiłkowej).",
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
    params: LegalParameters | None = None,
) -> ApplicationSubmissionResponse:
    from app.services.parameter_store import parameter_store

    p = params or parameter_store.get()
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    prefix_map = {
        ApplicationType.LEAVE_EMPLOYER: "URLOP",
        ApplicationType.LEAVE_SUPPLEMENTARY: "URLOP-UZUP",
        ApplicationType.LEAVE_RESIGNATION: "REZYGNACJA",
        ApplicationType.LEAVE_WORK_COMBINATION: "LACZENIE-PRACY",
        ApplicationType.ZAM_ZUS: "ZUS-ZAM",
        ApplicationType.USC_BIRTH_CERTIFICATE: "USC-AKT",
    }
    prefix = prefix_map.get(req.application_type, "WNIOSEK")
    ref = f"{prefix}-SIM-{uuid.uuid4().hex[:8].upper()}"

    deadline_21: str | None = None
    if req.child_birth_date:
        try:
            birth = date.fromisoformat(req.child_birth_date)
            deadline_21 = (birth + timedelta(days=p.combined_application_deadline_days)).isoformat()
        except ValueError:
            deadline_21 = None

    title_map = {
        ApplicationType.LEAVE_EMPLOYER: "WNIOSEK O UDZIELENIE URLOPU MACIERZYŃSKIEGO I RODZICIELSKIEGO",
        ApplicationType.LEAVE_SUPPLEMENTARY: "WNIOSEK O UDZIELENIE UZUPEŁNIAJĄCEGO URLOPU MACIERZYŃSKIEGO (art. 180² KP)",
        ApplicationType.LEAVE_RESIGNATION: "WNIOSEK O REZYGNACJĘ Z CZĘŚCI URLOPU MACIERZYŃSKIEGO / RODZICIELSKIEGO",
        ApplicationType.LEAVE_WORK_COMBINATION: "WNIOSEK O ŁĄCZENIE URLOPU RODZICIELSKIEGO Z WYKONYWANIEM PRACY (art. 182¹ᵉ KP)",
        ApplicationType.ZAM_ZUS: "WNIOSEK O ZASIŁEK MACIERZYŃSKI (FORMULARZ ZAM)",
        ApplicationType.USC_BIRTH_CERTIFICATE: "WNIOSEK O WYDANIE ODPISU AKTU URODZENIA (USC)",
    }

    lines = [
        f"Nr referencyjny (symulacja): {ref}",
        f"Data wygenerowania: {now_iso}",
        "",
        f"Wnioskodawca: {req.applicant_name} (PESEL: {req.pesel_masked})",
        f"Adresat: {req.recipient}",
        "",
        f"=== {title_map[req.application_type]} ===",
        "",
    ]
    if req.child_birth_date:
        lines.append(f"Data urodzenia dziecka: {req.child_birth_date}")
    if deadline_21:
        lines.append(
            f"Termin {p.combined_application_deadline_days} dni na wniosek/deklarację o 81,5%: {deadline_21}"
        )
    if req.leave_start_date or req.leave_end_date:
        lines.append(f"Wnioskowany okres urlopu/zasiłku: od {req.leave_start_date or '—'} do {req.leave_end_date or '—'}")
    if req.leave_parts_count and req.application_type in (ApplicationType.LEAVE_EMPLOYER, ApplicationType.ZAM_ZUS):
        lines.append(f"Planowana liczba części urlopu rodzicielskiego: {req.leave_parts_count} (maks. {p.parental_max_parts})")
    if req.payment_variant and req.application_type in (ApplicationType.LEAVE_EMPLOYER, ApplicationType.ZAM_ZUS):
        variant_txt = (
            f"{p.combined_21_days_rate*100:.1f}% za cały okres (wniosek w {p.combined_application_deadline_days} dni)"
            if req.payment_variant == PaymentVariant.COMBINED_81_5
            else f"{p.maternity_rate_standard*100:.0f}% macierzyński + {p.parental_rate_standard*100:.0f}% rodzicielski"
        )
        lines.append(f"Wybrany wariant wypłaty zasiłku: {variant_txt}")
    if req.application_type == ApplicationType.LEAVE_WORK_COMBINATION and req.work_fte_fraction:
        lines.append(f"Wymiar czasu pracy podczas urlopu rodzicielskiego: {req.work_fte_fraction} etatu (maks. 0.5)")
    if req.application_type == ApplicationType.LEAVE_SUPPLEMENTARY and (req.hospitalization_from or req.hospitalization_to):
        lines.append(f"Okres hospitalizacji dziecka: od {req.hospitalization_from or '—'} do {req.hospitalization_to or '—'}")
    if req.application_type == ApplicationType.LEAVE_RESIGNATION and req.resignation_date:
        lines.append(f"Data rezygnacji z dalszej części urlopu: {req.resignation_date}")
    if req.notes:
        lines.append(f"Uwagi dodatkowe: {req.notes}")

    lines.extend(["", "Podpis wnioskodawcy (symulacja): ________________________"])

    return ApplicationSubmissionResponse(
        reference_number=ref,
        application_type=req.application_type,
        recipient=req.recipient,
        submitted_at=now_iso,
        deadline_21_days=deadline_21,
        status="Wygenerowano i zasymulowano wysłanie dokumentu",
        summary=f"Przygotowano dokument ({title_map[req.application_type]}) dla {req.applicant_name} do: {req.recipient}.",
        generated_document_text="\n".join(lines),
    )
